// Developer controls: own fixture data, no Minecraft assets or source embedded.
use horizon_client_lib::mod_content::reapply_worldpack_features;
use horizon_world::worldgen::overrides::WorldgenOverrides;
use serde_json::{Value, json};
use std::{env, fs, path::Path};

fn write(root: &Path, name: &str, value: Value) {
    let path = root.join(name);
    fs::create_dir_all(path.parent().unwrap()).unwrap();
    fs::write(path, serde_json::to_vec(&value).unwrap()).unwrap();
}
fn biome(features: &[&str], marker: &str) -> Value {
    let mut steps = vec![json!([]); 11];
    steps[6] = json!(features);
    json!({"features":steps,"fixture_marker":marker,"spawners":{"creature":[{"type":"fixture:animal","weight":7}]}})
}
fn final_biome(root: &Path, overrides: &WorldgenOverrides, id: &str) -> Value {
    if let Some((_, text)) = overrides.entries("biomes").find(|(name, _)| *name == id) {
        serde_json::from_str(text).unwrap()
    } else {
        let bundle: Value =
            serde_json::from_slice(&fs::read(root.join("worldgen/biomes.json")).unwrap()).unwrap();
        serde_json::from_str(bundle[id].as_str().unwrap()).unwrap()
    }
}
fn count(value: &Value, feature: &str) -> usize {
    value["features"]
        .as_array()
        .unwrap()
        .iter()
        .flat_map(|step| step.as_array().unwrap())
        .filter(|entry| entry.as_str() == Some(feature))
        .count()
}
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = env::args().collect();
    assert_eq!(args.len(), 2, "NEW_WORK");
    let root = Path::new(&args[1]);
    assert!(!root.exists(), "fresh fixture required");
    fs::create_dir_all(root)?;
    let original = biome(&["fixture:base"], "root");
    let modified = biome(&["fixture:base", "fixture:ore"], "root");
    write(
        root,
        "worldgen/biomes_before_modifiers.json",
        json!({"fixture:a":original.to_string(),"fixture:b":original.to_string()}),
    );
    write(
        root,
        "worldgen/biomes.json",
        json!({"fixture:a":modified.to_string(),"fixture:b":modified.to_string()}),
    );
    write(
        root,
        "worldgen/biome_tags.json",
        json!({"fixture:targets":json!({"values":["fixture:a","fixture:b"]}).to_string()}),
    );
    write(
        root,
        "worldgen/placed_features.json",
        json!({"fixture:base":"{}","fixture:ore":"{}","fixture:world":"{}"}),
    );
    write(
        root,
        "data/fixture/neoforge/biome_modifier/10_add.json",
        json!({"type":"neoforge:add_features","biomes":"#fixture:targets","features":"fixture:ore","step":"underground_ores"}),
    );
    let world_biome = biome(&["fixture:world"], "world");
    let mut overrides = WorldgenOverrides::default();
    overrides.set("biomes", "fixture:a", world_biome.to_string());
    assert!(reapply_worldpack_features(root, &mut overrides)?.is_empty());
    let a = final_biome(root, &overrides, "fixture:a");
    assert_eq!(count(&a, "fixture:ore"), 1);
    assert_eq!(count(&a, "fixture:world"), 1);
    assert_eq!(a["fixture_marker"], "world");
    assert_eq!(a["spawners"], world_biome["spawners"]);
    let once: Vec<_> = overrides
        .entries("biomes")
        .map(|(id, text)| (id.to_owned(), text.to_owned()))
        .collect();
    reapply_worldpack_features(root, &mut overrides)?;
    let twice: Vec<_> = overrides
        .entries("biomes")
        .map(|(id, text)| (id.to_owned(), text.to_owned()))
        .collect();
    assert_eq!(once, twice, "replay must be idempotent");

    // A world tag replaces the original targets and includes a world-only biome.
    let mut retargeted = WorldgenOverrides::default();
    retargeted.set("biomes", "fixture:a", world_biome.to_string());
    retargeted.set("biomes", "fixture:new", world_biome.to_string());
    retargeted.add_file(
        "fixture_world",
        "data/fixture/tags/worldgen/biome/targets.json",
        || Some(json!({"replace":true,"values":["fixture:new"]}).to_string()),
    );
    reapply_worldpack_features(root, &mut retargeted)?;
    assert_eq!(
        count(&final_biome(root, &retargeted, "fixture:a"), "fixture:ore"),
        0
    );
    assert_eq!(final_biome(root, &retargeted, "fixture:b"), original);
    assert_eq!(
        count(
            &final_biome(root, &retargeted, "fixture:new"),
            "fixture:ore"
        ),
        1
    );

    // Removing a feature after adding it leaves unrelated features intact.
    write(
        root,
        "data/fixture/neoforge/biome_modifier/20_remove.json",
        json!({"type":"neoforge:remove_features","biomes":"#fixture:targets","features":"fixture:ore","steps":["underground_ores"]}),
    );
    let mut removed = WorldgenOverrides::default();
    removed.set("biomes", "fixture:a", world_biome.to_string());
    assert!(reapply_worldpack_features(root, &mut removed)?.is_empty());
    let a = final_biome(root, &removed, "fixture:a");
    assert_eq!(count(&a, "fixture:ore"), 0);
    assert_eq!(count(&a, "fixture:world"), 1);

    // No modifiers is a read-only no-op and requires no snapshot file.
    let vanilla = root.join("vanilla");
    fs::create_dir(&vanilla)?;
    let mut plain = WorldgenOverrides::default();
    plain.set("biomes", "fixture:a", world_biome.to_string());
    assert!(reapply_worldpack_features(&vanilla, &mut plain)?.is_empty());
    assert_eq!(final_biome(&vanilla, &plain, "fixture:a"), world_biome);
    let report = json!({"schema":1,"world_biome_features_restored":true,"non_feature_attributes_preserved":true,
        "repeat_replay_byte_identical":true,"world_tag_replace_removes_old_targets":true,
        "world_only_biome_targeted":true,"add_remove_order_preserved":true,"no_modifiers_read_only":true});
    fs::write(
        root.join("checked-result.json"),
        serde_json::to_vec_pretty(&report)?,
    )?;
    println!("{report}");
    Ok(())
}
