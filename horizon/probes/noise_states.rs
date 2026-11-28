// First-party provider sampler against pinned horizon-world; no game files included.
use horizon_core::random::LegacyRandom;
use horizon_world::{
    heightmap::HeightmapType,
    registry::{BlockRegistry, BlockStateId},
    worldgen::{anchor::WorldGenerationContext, feature::FeatureWorld,
              placement::{PlacementContext, PlacementQueryError},
              state_provider::{BlockStateProvider, StateProviderBindings}},
};
use std::{collections::{BTreeMap, BTreeSet}, convert::Infallible, fs};

struct NoWorld;
impl PlacementContext for NoWorld {
    fn generation(&self) -> WorldGenerationContext { panic!("unexpected generation query") }
    fn min_y(&mut self) -> Result<i32, PlacementQueryError> { panic!("unexpected min-y query") }
    fn height(&mut self, _: HeightmapType, _: i32, _: i32) -> Result<i32, PlacementQueryError> {
        panic!("unexpected height query")
    }
}
impl FeatureWorld for NoWorld {
    type Error = Infallible;
    fn block(&mut self, _: [i32; 3]) -> Result<BlockStateId, Self::Error> {
        panic!("a noise provider must not read world blocks")
    }
    fn set_block(&mut self, _: [i32; 3], _: BlockStateId, _: i32) -> Result<bool, Self::Error> {
        panic!("a noise provider must not write world blocks")
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().collect();
    if args.len() != 4 { return Err("expected FACTS_JSON CASES_JSON OUTPUT_JSON".into()); }
    let registry = BlockRegistry::from_facts_json(fs::File::open(&args[1])?)?;
    let bindings = StateProviderBindings::new(&registry, BTreeSet::new(), &BTreeMap::new())?;
    let cases: Vec<serde_json::Value> = serde_json::from_str(&fs::read_to_string(&args[2])?)?;
    let mut output = Vec::new();
    for row in cases {
        let provider = BlockStateProvider::from_json(&row["native"].to_string(), &bindings)?;
        let at = std::array::from_fn(|i| row["position"][i].as_i64().unwrap() as i32);
        let mut random = LegacyRandom::new(row["random_seed"].as_i64().unwrap());
        let chosen = provider.get_state(&mut NoWorld, &mut random, at)?;
        output.push(registry.state(chosen).unwrap().name.to_string());
    }
    fs::write(&args[3], serde_json::to_string(&output)?)?;
    println!("Native provider cases: {}", output.len());
    Ok(())
}
