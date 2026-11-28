// First-party trace of native patch compositions, with a recording predicate world.
use horizon_core::random::{LegacyRandom, RandomSource};
use horizon_world::{
    heightmap::HeightmapType,
    registry::{BlockRegistry, BlockStateId},
    worldgen::{
        anchor::WorldGenerationContext, block_feature::FeatureBlockBindings,
        feature::{FeatureBlocks, FeatureWorld}, feature_graph::FeatureDefinition,
        placement::{PlacementContext, PlacementQueryError},
    },
};
use std::{collections::BTreeSet, convert::Infallible, fs};

struct World {
    trace: Vec<[i32; 3]>,
    accept: bool,
    air: BlockStateId,
    stone: BlockStateId,
}
impl PlacementContext for World {
    fn generation(&self) -> WorldGenerationContext { WorldGenerationContext::new(-64, 384, 63) }
    fn min_y(&mut self) -> Result<i32, PlacementQueryError> { Ok(-64) }
    fn height(&mut self, _: HeightmapType, _: i32, _: i32) -> Result<i32, PlacementQueryError> {
        panic!("unexpected height query")
    }
    fn block_state(&mut self, p: [i32; 3]) -> Result<BlockStateId, PlacementQueryError> {
        self.trace.push(p);
        Ok(if self.accept && self.trace.len() % 2 == 0 { self.stone } else { self.air })
    }
}
impl FeatureWorld for World {
    type Error = Infallible;
    fn block(&mut self, _: [i32; 3]) -> Result<BlockStateId, Self::Error> { panic!("unexpected read") }
    fn set_block(&mut self, _: [i32; 3], _: BlockStateId, _: i32) -> Result<bool, Self::Error> {
        panic!("unexpected write")
    }
}
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().collect();
    if args.len() != 4 { return Err("expected FACTS_JSON CASES_JSON OUTPUT_JSON".into()); }
    let registry = BlockRegistry::from_facts_json(fs::File::open(&args[1])?)?;
    let bindings = FeatureBlockBindings::new(&registry, BTreeSet::new())?;
    let blocks = FeatureBlocks::from_registry(&registry)?;
    let cases: Vec<serde_json::Value> = serde_json::from_str(&fs::read_to_string(&args[2])?)?;
    let mut output = Vec::new();
    for row in cases {
        let feature = FeatureDefinition::from_json_with_blocks(&row["native"].to_string(), &bindings)?;
        let mut world = World { trace: Vec::new(), accept: row["accept_alternate"].as_bool().unwrap(),
            air: registry.default_state("minecraft:air").unwrap(), stone: blocks.stone };
        let mut random = LegacyRandom::new(row["seed"].as_i64().unwrap());
        let result = feature.place(&mut world, &mut random, [-17, 80, 31], blocks)?;
        output.push(serde_json::json!({"positions": world.trace, "result": result,
                                     "tail": random.next_int_bound(1000000007)?}));
    }
    fs::write(&args[3], serde_json::to_string(&output)?)?;
    println!("Native patch traces: {}", output.len());
    Ok(())
}
