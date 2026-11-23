// Developer comparison: real pinned MIT Horizon placement/fluid/tick bindings
// loaded from the eight-mod content root, against original CC0 Oritech output.
// Native cable lifecycle and player inventory dispatch are tested separately.
use horizon_core::{
    geometry::{Direction, Vec3},
    position::{BlockPos, ChunkPos},
    random::LegacyRandom,
    ticks::TickTypeId,
};
use horizon_world::{
    fluid::FluidKind,
    level::{Behaviours, BucketContent, LevelAccess, PlaceContext, Ticks},
    registry::{BlockRegistry, BlockStateId},
};
use serde_json::{Value, json};
use std::{collections::BTreeMap, env, fs, path::Path};
const POS: BlockPos = BlockPos::new(0, 210, 0);
struct World {
    cells: BTreeMap<(i32, i32, i32), BlockStateId>,
    air: BlockStateId,
    random: LegacyRandom,
    time: i64,
}
impl World {
    fn new(air: BlockStateId) -> Self {
        Self {
            cells: BTreeMap::new(),
            air,
            random: LegacyRandom::new(263),
            time: 0,
        }
    }
}
impl LevelAccess for World {
    fn block_state(&self, p: BlockPos) -> BlockStateId {
        *self.cells.get(&(p.x, p.y, p.z)).unwrap_or(&self.air)
    }
    fn set_raw(&mut self, p: BlockPos, s: BlockStateId) -> Option<BlockStateId> {
        Some(self.cells.insert((p.x, p.y, p.z), s).unwrap_or(self.air))
    }
    fn is_loaded(&self, _: BlockPos) -> bool {
        true
    }
    fn random(&mut self) -> &mut LegacyRandom {
        &mut self.random
    }
    fn game_time(&self) -> i64 {
        self.time
    }
}
fn ticks() -> Ticks {
    let mut t = Ticks::new(263);
    for x in -1..=1 {
        for z in -1..=1 {
            t.add_empty_chunk(ChunkPos::new(x, z)).unwrap();
        }
    }
    t
}
fn state(r: &BlockRegistry, node: &Value) -> BlockStateId {
    let mut s = r
        .state(r.default_state(node["block"].as_str().unwrap()).unwrap())
        .unwrap()
        .clone();
    for (key, value) in node["properties"].as_object().unwrap() {
        s.properties
            .insert(key.clone(), value.as_str().unwrap().into());
    }
    r.id(&s).unwrap()
}
fn fields(b: &Behaviours, s: BlockStateId) -> Value {
    let f = b.fluid(s);
    json!({"fluid":f.kind().name(),"amount":f.amount(),"source":f.is_source(),"empty":f.kind()==FluidKind::Empty,"waterlogged":b.table.bool(s,b.props.waterlogged)})
}
fn expected(node: &Value) -> Value {
    json!({"fluid":node["fluid"],"amount":node["amount"],"source":node["source"],"empty":node["empty"],"waterlogged":node["properties"].get("waterlogged").and_then(Value::as_str)==Some("true")})
}
fn scheduled(t: &Ticks, p: BlockPos) -> Value {
    json!({"water":t.fluids.has_scheduled(p,TickTypeId(FluidKind::Water as u32)),"flowing_water":t.fluids.has_scheduled(p,TickTypeId(FluidKind::FlowingWater as u32))})
}
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = env::args().collect();
    assert_eq!(args.len(), 3, "CONTENT_ROOT ORIGINAL");
    let root = Path::new(&args[1]);
    let original: Value = serde_json::from_slice(&fs::read(&args[2])?)?;
    assert_eq!(original["original_waterlogging_callbacks_executed"], true);
    assert_eq!(original["flow_chunks_forced"], true);
    let registry = BlockRegistry::from_facts_json(fs::File::open(root.join("facts.json"))?)?;
    Behaviours::set_cache_dir(root.join("waterlogging-binding-cache"));
    let b = Behaviours::load(&registry, root)?;
    let air = registry.default_state("minecraft:air").unwrap();
    let glass = registry.default_state("minecraft:glass").unwrap();
    let mut materialized_states = 0;
    for id in 0..registry.len() {
        let id = BlockStateId(id as u32);
        let s = registry.state(id).unwrap();
        if matches!(
            s.name.as_str(),
            "oritech:energy_pipe" | "oritech:energy_pipe_connection"
        ) {
            let keys: Vec<_> = s.properties.iter().map(|(k, _)| k.to_string()).collect();
            assert_eq!(
                keys,
                [
                    "down",
                    "east",
                    "north",
                    "south",
                    "straight",
                    "up",
                    "waterlogged",
                    "west"
                ]
            );
            let wet = s.properties.get("waterlogged").unwrap() == "true";
            assert_eq!(b.fluid(id).is_source(), wet, "materialized fluid metadata");
            assert_eq!(b.fluid(id).amount(), if wet { 8 } else { 0 });
            materialized_states += 1;
        }
    }
    assert_eq!(materialized_states, 512);
    let mut checked = 0;
    let mut mismatches = Vec::new();
    let mut compare = |label: String, actual: Value, want: Value| {
        checked += 1;
        if actual != want {
            mismatches.push(json!({"case":label,"actual":actual,"expected":want}));
        }
    };
    for (i, row) in original["placements"]
        .as_array()
        .unwrap()
        .iter()
        .enumerate()
    {
        let mut w = World::new(air);
        let mut t = ticks();
        w.set_raw(POS, state(&registry, &row["before"]));
        w.set_raw(BlockPos::new(0, 209, 0), glass);
        let block = b
            .table
            .block_by_name(row["after"]["block"].as_str().unwrap())
            .unwrap();
        let ctx = PlaceContext {
            clicked_pos: BlockPos::new(0, 209, 0),
            face: Direction::Up,
            hit: Vec3::new(0.5, 210.0, 0.5),
            inside: false,
            yaw: 0.,
            pitch: 0.,
            sneaking: false,
            item: "oritech:energy_pipe".into(),
            can_use_game_master_blocks: false,
        };
        let placed = b
            .state_for_placement(&mut w, &mut t, block, &ctx)
            .expect("cable placement refused");
        compare(
            format!("placement_{i}"),
            fields(&b, placed),
            expected(&row["after"]),
        );
    }
    for (i, row) in original["liquid_callbacks"]
        .as_array()
        .unwrap()
        .iter()
        .enumerate()
    {
        let endpoint = row["endpoint"].as_bool().unwrap();
        let wet = row["wet"].as_bool().unwrap();
        let name = if endpoint {
            "oritech:energy_pipe_connection"
        } else {
            "oritech:energy_pipe"
        };
        let mut s = registry
            .state(registry.default_state(name).unwrap())
            .unwrap()
            .clone();
        s.properties.insert("waterlogged".into(), wet.to_string());
        let s = registry.id(&s).unwrap();
        let kind = FluidKind::from_name(row["fluid"].as_str().unwrap()).unwrap();
        compare(
            format!("can_place_{i}"),
            json!(b.can_place_liquid(s, kind, false)),
            row["can_place"].clone(),
        );
        if kind == FluidKind::Water {
            let mut w = World::new(air);
            let mut t = ticks();
            w.set_raw(POS, s);
            b.bucket_empty(
                &mut w,
                &mut t,
                POS,
                None,
                BucketContent::Fluid(kind),
                "minecraft:item.bucket.empty",
                false,
                false,
            );
            compare(
                format!("source_fill_{i}"),
                fields(&b, w.block_state(POS)),
                expected(&row["after"]),
            );
            compare(
                format!("source_fill_schedule_{i}"),
                scheduled(&t, POS),
                row["scheduled"].clone(),
            );
        }
    }
    for (i, row) in original["pickup_callbacks"]
        .as_array()
        .unwrap()
        .iter()
        .enumerate()
    {
        let after = state(&registry, &row["after"]);
        let before = b
            .table
            .set_bool(after, b.props.waterlogged, row["wet"].as_bool().unwrap());
        let mut w = World::new(air);
        let mut t = ticks();
        w.set_raw(POS, before);
        let got = b
            .bucket_pickup(&mut w, &mut t, POS, false)
            .unwrap_or("minecraft:air");
        compare(format!("pickup_item_{i}"), json!(got), row["item"].clone());
        compare(
            format!("pickup_state_{i}"),
            fields(&b, w.block_state(POS)),
            expected(&row["after"]),
        );
    }
    for (i, row) in original["neighbor_scheduling"]
        .as_array()
        .unwrap()
        .iter()
        .enumerate()
    {
        let name = if row["endpoint"] == true {
            "oritech:energy_pipe_connection"
        } else {
            "oritech:energy_pipe"
        };
        let s = registry.default_state(name).unwrap();
        let s = b
            .table
            .set_bool(s, b.props.waterlogged, row["wet"].as_bool().unwrap());
        let dir = Direction::ALL
            .into_iter()
            .find(|d| {
                ["down", "up", "north", "south", "west", "east"][*d as usize]
                    == row["side"].as_str().unwrap()
            })
            .unwrap();
        let d = dir.normal();
        let other = BlockPos::new(d[0], 210 + d[1], d[2]);
        let mut w = World::new(air);
        let mut t = ticks();
        w.set_raw(POS, s);
        let next = b.update_shape(&mut w, &mut t, s, POS, dir, other, air);
        compare(
            format!("neighbor_same_{i}"),
            json!(next == s),
            row["same_state"].clone(),
        );
        compare(
            format!("neighbor_schedule_{i}"),
            scheduled(&t, POS),
            row["scheduled"].clone(),
        );
    }
    // Real scheduled fluid simulation, initialized from the original zero-tick
    // block states. Native cable graph hooks are deliberately not part of this
    // standalone binding check. Geometry and fluid metadata come from content.
    let mut w = World::new(air);
    let mut t = ticks();
    for x in -3..=3 {
        for z in -3..=3 {
            w.set_raw(BlockPos::new(x, 209, z), glass);
        }
    }
    for cell in original["flow"][0]["cells"].as_array().unwrap() {
        let p = &cell["offset"];
        let p = BlockPos::new(
            p[0].as_i64().unwrap() as i32,
            210,
            p[1].as_i64().unwrap() as i32,
        );
        b.set_block(&mut w, &mut t, p, state(&registry, &cell["node"]), 3);
    }
    for row in original["flow"].as_array().unwrap() {
        let elapsed = row["elapsed"].as_i64().unwrap();
        while w.time < elapsed {
            w.time += 1;
            b.tick_scheduled(&mut w, &mut t);
        }
        for cell in row["cells"].as_array().unwrap() {
            let p = &cell["offset"];
            let p = BlockPos::new(
                p[0].as_i64().unwrap() as i32,
                210,
                p[1].as_i64().unwrap() as i32,
            );
            let s = w.block_state(p);
            let a = registry.state(s).unwrap();
            let want = &cell["node"];
            compare(
                format!("flow_{elapsed}_{}_{}", p.x, p.z),
                json!({"block":a.name,"properties":a.properties.iter().map(|(k,v)|(k.to_string(),v.to_string())).collect::<BTreeMap<_,_>>(),"fluid":fields(&b,s)}),
                json!({"block":want["block"],"properties":want["properties"],"fluid":expected(want)}),
            );
        }
    }
    drop(compare);
    println!(
        "{}",
        serde_json::to_string_pretty(
            &json!({"schema":1,"comparisons":checked,"materialized_cable_states":materialized_states,"mismatches":mismatches,"placement_bindings":34,"can_place_callbacks":16,"pickup_callbacks":4,"neighbor_callbacks":24,"flow_snapshots":6,"flow_cells_per_snapshot":25,"native_graph_or_player_inventory_dispatch_tested":false})
        )?
    );
    assert!(
        mismatches.is_empty(),
        "waterlogging binding differs from original"
    );
    Ok(())
}
