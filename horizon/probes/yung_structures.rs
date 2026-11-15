// First-party audit/planner for pinned Horizon. No blocks are placed here.
// Args: EFFECTIVE_CONTENT_ROOT ADAPTED_DATAPACK OUTPUT_JSON [small-dungeons].
// StructureKind classification uses a dummy empty biome resolver; real layouts
// use the full GeneratorData and /place structure's own structure_start path.
use horizon_core::position::ChunkPos;
use horizon_world::{
    nbt::{Compound, JavaString, Tag},
    registry::BlockRegistry,
    worldgen::{
        generator::{GeneratorData, OverworldGenerator},
        overrides::WorldgenOverrides,
        structure::{
            Mirror, Rotation,
            jigsaw::PoolElement,
            start::{Piece, StructureKind, StructureRegistry},
            template::StructureTemplate,
        },
    },
};
use serde_json::{Value, json};
use std::{
    collections::{BTreeMap, BTreeSet},
    fs, io,
    path::Path,
};

fn overlays(root: &Path, dir: &Path, ov: &mut WorldgenOverrides) -> io::Result<()> {
    for entry in fs::read_dir(dir)? {
        let entry = entry?;
        let path = entry.path();
        if entry.file_type()?.is_symlink() {
            return Err(io::Error::other("symlink in audit input"));
        }
        if path.is_dir() {
            overlays(root, &path, ov)?;
        } else if path.extension().is_some_and(|s| s == "json") {
            let name = path
                .strip_prefix(root)
                .map_err(io::Error::other)?
                .to_string_lossy();
            ov.add_file("trial", &name, || fs::read_to_string(&path).ok());
        }
    }
    Ok(())
}
fn bundle(
    root: &Path,
    kind: &str,
    ov: &WorldgenOverrides,
) -> Result<BTreeMap<String, String>, Box<dyn std::error::Error>> {
    let mut raw: BTreeMap<String, String> =
        serde_json::from_slice(&fs::read(root.join(format!("worldgen/{kind}.json")))?)?;
    for (id, v) in ov.entries(kind) {
        raw.insert(id.into(), v.into());
    }
    Ok(raw)
}
fn identifier(nbt: &Compound, key: &str) -> Option<String> {
    match nbt.get(&JavaString::from(key)) {
        Some(Tag::String(s)) => Some(s.to_string_lossy()),
        _ => None,
    }
}
fn candidates(
    element: &PoolElement,
    pos: [i32; 3],
    rotation: Rotation,
    registry: &BlockRegistry,
    out: &mut Vec<Value>,
) {
    match element {
        PoolElement::List { elements, .. } => {
            for e in elements {
                candidates(e, pos, rotation, registry, out)
            }
        }
        PoolElement::Single { template, .. } => {
            for (palette_index, palette) in template.palettes().iter().enumerate() {
                for block in palette.blocks() {
                    let state = registry.state(block.state).unwrap();
                    if !(state.name.ends_with("chest")
                        || state.name == "minecraft:spawner"
                        || state.name == "minecraft:barrel")
                    {
                        continue;
                    }
                    let p = StructureTemplate::transform(block.pos, Mirror::None, rotation, [0; 3]);
                    let position = [p[0] + pos[0], p[1] + pos[1], p[2] + pos[2]];
                    let loot = block
                        .nbt
                        .as_ref()
                        .and_then(|tag| identifier(tag, "LootTable"));
                    let spawn = block
                        .nbt
                        .as_ref()
                        .and_then(|tag| tag.get(&JavaString::from("SpawnData")))
                        .and_then(|v| v.get("entity"))
                        .and_then(|v| v.get("id"))
                        .and_then(|v| match v {
                            Tag::String(s) => Some(s.to_string_lossy()),
                            _ => None,
                        });
                    out.push(json!({"position":position,"block":state.name,"template":template.location.as_ref(),
                        "palette":palette_index,"source_loot_table":loot,"source_spawn_entity":spawn}));
                }
            }
        }
        _ => {}
    }
}
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().collect();
    if !(4..=5).contains(&args.len()) {
        return Err("expected EFFECTIVE_ROOT DATAPACK OUTPUT_JSON [small-dungeons]".into());
    }
    if args.len() == 5 && args[4] != "small-dungeons" {
        return Err("unknown plan mode".into());
    }
    if Path::new(&args[3]).exists() {
        return Err("output must be new".into());
    }
    let root = Path::new(&args[1]);
    let pack = Path::new(&args[2]);
    let mut ov = WorldgenOverrides::default();
    overlays(pack, &pack.join("data"), &mut ov)?;
    let structures = bundle(root, "structures", &ov)?;
    let sets = bundle(root, "structure_sets", &ov)?;
    let pools = bundle(root, "template_pools", &ov)?;
    let catalog = StructureRegistry::new(&structures, &sets, pools, &|_| Ok(BTreeSet::new()))?;
    let mut decoded = Vec::new();
    for s in &catalog.structures {
        if ![
            "betterdungeons:",
            "betterstrongholds:",
            "bettermineshafts:",
            "betterfortresses:",
        ]
        .iter()
        .any(|p| s.name.starts_with(p))
        {
            continue;
        }
        let source: Value = serde_json::from_str(&structures[&s.name])?;
        let unsupported = match &s.kind {
            StructureKind::Unsupported(reason) => Some(reason),
            _ => None,
        };
        decoded.push(json!({"id":s.name,"source_type":source["type"],"source_depth":source.get("size"),
            "decoder_supported":unsupported.is_none(),"unsupported_kind":unsupported,
            "raw_enhanced_terrain_present":source.get("enhanced_terrain_adaptation").is_some(),
            "native_enhanced_terrain_present":source.get("horizon:enhanced_terrain_adaptation").is_some()}));
    }
    let registry = Box::leak(Box::new(BlockRegistry::from_facts_json(fs::File::open(
        root.join("facts.json"),
    )?)?));
    let data = GeneratorData::load_with(&root.join("worldgen"), registry, &ov)?;
    let generator = OverworldGenerator::new(data, 263)?;
    let mut worker = generator.worker();
    let tests: Vec<_> = if args.len() == 5 {
        (0..16)
            .map(|i| ("betterdungeons:small_dungeon", 8 + i * 8, 32))
            .collect()
    } else {
        vec![
            ("betterdungeons:small_dungeon", 8, 8),
            ("betterdungeons:zombie_dungeon", 32, 8),
            ("betterdungeons:skeleton_dungeon", 56, 8),
            ("betterstrongholds:stronghold", 80, 8),
        ]
    };
    let mut plans = Vec::new();
    for (id, x, z) in tests {
        eprintln!("Planning {id} at chunk {x} {z}");
        let start = worker.structure_start(id, ChunkPos::new(x, z));
        match start {
            Some(start) => {
                let mut blocks = Vec::new();
                let mut templates = BTreeSet::new();
                for piece in &start.pieces {
                    if let Piece::Pool(p) = piece {
                        candidates(&p.element, p.position, p.rotation, registry, &mut blocks);
                        if let PoolElement::Single { template, .. } = p.element.as_ref() {
                            templates.insert(template.location.to_string());
                        }
                    }
                }
                plans.push(
                    json!({"id":id,"chunk":[x,z],"piece_count":start.pieces.len(),
                    "box_min":start.bounding_box.min,"box_max":start.bounding_box.max,
                    "templates":templates,"block_entity_candidates_before_processors":blocks}),
                );
            }
            None => plans.push(json!({"id":id,"chunk":[x,z],"no_start":true})),
        }
    }
    let report = json!({"schema":1,"minecraft":"26.3","seed":263,"decoder_classification":decoded,
        "biome_resolution_in_kind_classification_is_stubbed":true,"layouts_use_real_generator":true,
        "plans":plans,"blocks_placed":false,"natural_generation_verified":false,"loot_and_spawners_verified":false});
    fs::write(&args[3], serde_json::to_string_pretty(&report)?)?;
    Ok(())
}
