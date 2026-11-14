// First-party native counterpart: calls the actual (base or mixed) selector.
// Args: EFFECTIVE_ROOT VANILLA_ROOT WORLD ORIGINAL_MEMBERSHIPS ORIGINAL_MASK_ORACLE.
use horizon_client::{blocks::BlockFacts, mobs::{MobData, tame::wolf_variant_for}, biome::Biomes};
use horizon_world::registry::BlockRegistry;
use horizon_world::loot::PackOverlay;
use serde_json::{json,Value};
use std::{fs,path::Path};

const TAGS:[&str;9]=["pale","spotted","snowy","black","ashen","rusty","woods","chestnut","striped"];
fn load(root:&Path)->Result<MobData,Box<dyn std::error::Error>> {
    let registry=BlockRegistry::from_facts_json(fs::File::open(root.join("facts.json"))?)?;
    let facts=BlockFacts::load(root,&registry)?;
    Ok(MobData::load(root,&facts))
}
fn selected(id:u8)->String { format!("minecraft:{}",TAGS[id as usize]) }
fn main()->Result<(),Box<dyn std::error::Error>> {
    #[cfg(techquest_native_wolves)] {
        use horizon_client::techquest_terralith_wolf_context as context;
        context::clear();context::stage("techquest:context_probe",4);
        assert_eq!(wolf_variant_for("techquest:context_probe",&|_|panic!("context must win before global tags")),4);
        assert_eq!(wolf_variant_for("techquest:context_probe",&|_|false),0);
        context::stage("techquest:another_biome",3);
        assert_eq!(wolf_variant_for("techquest:context_probe",&|_|false),0);
        assert_eq!(context::take("techquest:another_biome"),None);
    }
    let args:Vec<_>=std::env::args().collect();
    if args.len()!=6 { return Err("expected EFFECTIVE_ROOT VANILLA_ROOT WORLD SOURCE_MEMBERSHIPS MASK_ORACLE".into()); }
    let data=load(Path::new(&args[1]))?;
    let vanilla=load(Path::new(&args[2]))?;
    let packs=horizon_client::datapack::discover(Path::new(&args[3]));
    let store=horizon_client::datapack::DataStore::load(&packs.iter().collect::<Vec<_>>());
    assert!(store.errors.is_empty());
    let files:Vec<_>=store.files.into_iter().collect();let overlay=PackOverlay { files:&files };
    let world_tags=horizon_client::items::load_tags(Path::new(&args[1]),"worldgen/biome",&overlay)?;
    let source:Value=serde_json::from_slice(&fs::read(&args[4])?)?;
    let masks:Value=serde_json::from_slice(&fs::read(&args[5])?)?;
    let mut cases=Vec::new();let mut membership_mismatches=Vec::new();let mut globally_trimmed=Vec::new();
    for row in source["cases"].as_array().unwrap() {
        let biome=row["biome"].as_str().unwrap();
        let has=|tag:&str|world_tags.get(tag).is_some_and(|members|members.contains(biome));
        let native_tags:Vec<_>=TAGS.iter().map(|s|format!("c:has_wolf_variant/{s}")).filter(|t|has(t)).collect();
        let global_tags:Vec<_>=TAGS.iter().map(|s|format!("c:has_wolf_variant/{s}")).filter(|t|data.biome_has(t,biome)).collect();
        let expected_tags:Vec<_>=row["tags"].as_array().unwrap().iter().map(|s|s.as_str().unwrap().to_string()).collect();
        if native_tags!=expected_tags {membership_mismatches.push(biome);}
        if global_tags!=expected_tags {globally_trimmed.push(biome);}
        cases.push(json!({"biome":biome,"expected":row["expected"],
            "selected":selected(wolf_variant_for(biome,&has)),"tags":native_tags}));
    }
    let mut mask_cases=Vec::new();
    for row in masks["cases"].as_array().unwrap() {
        let mask=row["mask"].as_u64().unwrap();
        let result=wolf_variant_for("techquest:synthetic_mask",&|t| {
            TAGS.iter().enumerate().any(|(bit,s)|t==format!("c:has_wolf_variant/{s}") && mask&(1<<bit)!=0)
        });
        mask_cases.push(json!({"mask":mask,"expected":row["selected"],"selected":selected(result)}));
    }
    let biomes=Biomes::load(Path::new(&args[2]))?;
    let vanilla_cases:Vec<_>=biomes.registry_order().into_iter().map(|biome| {
        assert!(TAGS.iter().all(|s|!vanilla.biome_has(&format!("c:has_wolf_variant/{s}"),biome)));
        json!({"biome":biome,"selected":selected(wolf_variant_for(biome,&|t|vanilla.biome_has(t,biome)))})
    }).collect();
    println!("{}",serde_json::to_string_pretty(&json!({"schema":1,"minecraft":"26.3",
        "membership_mismatches":membership_mismatches,
        "globally_trimmed_memberships":globally_trimmed,
        "biome_mismatches":cases.iter().filter(|c|c["expected"]!=c["selected"]).count(),
        "mask_mismatches":mask_cases.iter().filter(|c|c["expected"]!=c["selected"]).count(),
        "cases":cases,"mask_cases":mask_cases,"vanilla_cases":vanilla_cases,
        "real_player_tested":false,"natural_spawning_tested":false}))?);
    Ok(())
}
