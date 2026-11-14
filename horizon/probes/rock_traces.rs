// First-party block-blob oracle counterpart: ordered mutations and random tail.
use horizon_core::random::{LegacyRandom, RandomSource};
use horizon_world::{
    heightmap::HeightmapType, registry::{BlockRegistry, BlockStateId},
    worldgen::{anchor::WorldGenerationContext, block_feature::FeatureBlockBindings,
        feature::{FeatureWorld, FeatureBlocks}, feature_graph::FeatureDefinition,
        placement::{PlacementContext, PlacementQueryError}},
};
use std::{collections::{BTreeMap, BTreeSet}, convert::Infallible, fs, path::Path};

struct World { support: BlockStateId, bedrock: BlockStateId, writes: Vec<[i32; 3]> }
impl World {
    fn read(&self, p: [i32; 3]) -> BlockStateId {
        if p == [0, 79, 0] { self.support } else { self.bedrock }
    }
}
impl PlacementContext for World {
    fn generation(&self) -> WorldGenerationContext { WorldGenerationContext::new(-64, 384, 63) }
    fn min_y(&mut self) -> Result<i32, PlacementQueryError> { Ok(-64) }
    fn height(&mut self, _: HeightmapType, _: i32, _: i32) -> Result<i32, PlacementQueryError> { panic!("unexpected height query") }
    fn block_state(&mut self, p: [i32; 3]) -> Result<BlockStateId, PlacementQueryError> { Ok(self.read(p)) }
}
impl FeatureWorld for World {
    type Error = Infallible;
    fn block(&mut self, p: [i32; 3]) -> Result<BlockStateId, Self::Error> { Ok(self.read(p)) }
    fn set_block(&mut self, p: [i32; 3], _: BlockStateId, flags: i32) -> Result<bool, Self::Error> {
        assert_eq!(flags, 3);
        self.writes.push(p); Ok(true)
    }
}
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().collect();
    if args.len()!=4 { return Err("expected EFFECTIVE_CONTENT_ROOT CASES_JSON OUTPUT_JSON".into()); }
    let root = Path::new(&args[1]);
    let registry = BlockRegistry::from_facts_json(fs::File::open(root.join("facts.json"))?)?;
    let mut tags = BTreeMap::new();
    for key in ["dirt", "base_stone_overworld"] {
        let value: serde_json::Value = serde_json::from_str(&fs::read_to_string(
            root.join(format!("data/minecraft/tags/block/{key}.json")))?)?;
        let members: Vec<String> = value["values"].as_array().unwrap().iter()
            .map(|v| v.as_str().unwrap().to_owned()).collect();
        tags.insert(format!("minecraft:{key}"), members);
    }
    let bindings = FeatureBlockBindings::with_tags(&registry, BTreeSet::new(), &tags)?;
    let blocks = FeatureBlocks::from_registry(&registry)?;
    let cases: Vec<serde_json::Value> = serde_json::from_str(&fs::read_to_string(&args[2])?)?;
    let mut output = Vec::new();
    for row in cases {
        let support = row["support"].as_str().unwrap();
        // The old chain ID became iron_chain; it is a rejected support in both versions.
        let native_support = if support == "minecraft:chain" { "minecraft:iron_chain" } else { support };
        let mut world = World { support: registry.default_state(native_support)
                .ok_or_else(|| format!("unknown support block {support}"))?,
            bedrock: registry.default_state("minecraft:bedrock").unwrap(), writes: Vec::new() };
        let mut random = LegacyRandom::new(row["seed"].as_i64().unwrap());
        let feature = FeatureDefinition::from_json_with_blocks(&row["native"].to_string(), &bindings)?;
        let result = feature.place(&mut world, &mut random, [0,80,0], blocks)?;
        output.push(serde_json::json!({"support":support,"seed":row["seed"],"result":result,
                                      "writes":world.writes,"tail":random.next_int_bound(1000000007)?}));
    }
    fs::write(&args[3], serde_json::to_string(&output)?)?;
    println!("Native rock traces: {}",output.len());
    Ok(())
}
