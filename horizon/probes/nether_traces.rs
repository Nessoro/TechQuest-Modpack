// First-party native counterpart for weighted nether vegetation flow.
use horizon_core::random::{LegacyRandom, RandomSource};
use horizon_world::{
    block_placement::BlockPlacementBindings, block_properties::BlockPropertiesRegistry,
    collision::CachedCollisionRegistry, heightmap::HeightmapType,
    registry::{BlockRegistry, BlockStateId, BlockTableFile}, worldgen::{anchor::WorldGenerationContext,
        block_feature::FeatureBlockBindings, feature::{FeatureBlocks,FeatureWorld},
        feature_graph::FeatureDefinition, placement::{PlacementContext,PlacementQueryError},
        state_provider::{StateProviderBindings,StateProviderCatalog}},
};
use std::{collections::{BTreeMap,BTreeSet},convert::Infallible,fs,path::Path};

struct World { support:BlockStateId, air:BlockStateId, stone:BlockStateId, origin_y:i32,
    mode:String, writes:Vec<([i32;3],BlockStateId)> }
impl World {
    fn read(&self,p:[i32;3])->BlockStateId {
        if p==[0,self.origin_y-1,0] { return self.support; }
        if self.mode=="all" || (self.mode=="mixed" && (p[0]*31+p[1]*7+p[2]*17).rem_euclid(3)!=0) {
            self.air
        } else { self.stone }
    }
}
impl PlacementContext for World {
    fn generation(&self)->WorldGenerationContext { WorldGenerationContext::new(-64,384,63) }
    fn min_y(&mut self)->Result<i32,PlacementQueryError> { Ok(-64) }
    fn max_y(&mut self)->Result<i32,PlacementQueryError> { Ok(319) }
    fn height(&mut self,_:HeightmapType,_:i32,_:i32)->Result<i32,PlacementQueryError> { panic!("unexpected height query") }
    fn block_state(&mut self,p:[i32;3])->Result<BlockStateId,PlacementQueryError> { Ok(self.read(p)) }
    fn block_survives(&mut self,_:BlockStateId,_:[i32;3])->Result<bool,PlacementQueryError> { Ok(true) }
}
impl FeatureWorld for World {
    type Error=Infallible;
    fn block(&mut self,p:[i32;3])->Result<BlockStateId,Self::Error> { Ok(self.read(p)) }
    fn set_block(&mut self,p:[i32;3],state:BlockStateId,flags:i32)->Result<bool,Self::Error> {
        assert_eq!(flags,2);self.writes.push((p,state));Ok(true)
    }
}
fn main()->Result<(),Box<dyn std::error::Error>> {
    let args:Vec<_>=std::env::args().collect();
    if args.len()!=4 { return Err("expected EFFECTIVE_CONTENT_ROOT CASES_JSON OUTPUT_JSON".into()); }
    let root=Path::new(&args[1]);
    let registry=BlockRegistry::from_facts_json(fs::File::open(root.join("facts.json"))?)?;
    let dir=root.join("worldgen/blocks");
    let collision_file=BlockTableFile::open(&dir.join("cached-collision.nbt"),&registry)?;
    let collisions=CachedCollisionRegistry::from_table(collision_file.table("collision")?)?;
    let property_file=BlockTableFile::open(&dir.join("block-properties.nbt"),&registry)?;
    let properties=BlockPropertiesRegistry::from_table(property_file.table("block property")?,&collisions)?;
    let tag:serde_json::Value=serde_json::from_str(&fs::read_to_string(root.join("data/minecraft/tags/block/nylium.json"))?)?;
    let members:Vec<String>=tag["values"].as_array().unwrap().iter().map(|v|v.as_str().unwrap().to_owned()).collect();
    let tags=BTreeMap::from([("minecraft:nylium".to_owned(),members)]);
    let bindings=FeatureBlockBindings::with_tags(&registry,BTreeSet::new(),&tags)?.with_state_providers(
        StateProviderBindings::new(&registry,BTreeSet::new(),&tags)?,
        StateProviderCatalog::from_resources(&BTreeMap::new())?,
        BlockPlacementBindings::new(&registry,&properties,&BTreeSet::new(),&BTreeSet::new())?)?;
    let blocks=FeatureBlocks::from_registry(&registry)?;
    let cases:Vec<serde_json::Value>=serde_json::from_str(&fs::read_to_string(&args[2])?)?;
    let mut output=Vec::new();
    for row in cases {
        let mut world=World { support:registry.default_state(row["support"].as_str().unwrap()).unwrap(),
            air:registry.default_state("minecraft:air").unwrap(),stone:blocks.stone,
            origin_y:row["origin_y"].as_i64().unwrap() as i32,mode:row["mode"].as_str().unwrap().to_owned(),writes:Vec::new() };
        let mut random=LegacyRandom::new(row["seed"].as_i64().unwrap());
        let feature=FeatureDefinition::from_json_with_blocks(&row["native"].to_string(),&bindings)?;
        let origin=[0,world.origin_y,0];let result=feature.place(&mut world,&mut random,origin,blocks)?;
        let writes:Vec<_>=world.writes.iter().map(|(p,state)|serde_json::json!({"position":p,
            "block":registry.state(*state).unwrap().name})).collect();
        output.push(serde_json::json!({"support":row["support"],"mode":row["mode"],"origin_y":row["origin_y"],
            "seed":row["seed"],"result":result,"writes":writes,"tail":random.next_int_bound(1000000007)?}));
    }
    fs::write(&args[3],serde_json::to_string(&output)?)?;println!("Native vegetation traces: {}",output.len());Ok(())
}
