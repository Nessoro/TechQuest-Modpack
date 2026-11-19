// Developer audit of the generator's final biome data after enabled world packs.
use horizon_client_lib::{datapack, save::Level};
use horizon_world::{registry::BlockRegistry, worldgen::generator::GeneratorData};
use serde_json::{Value, json};
use std::{env, fs, path::Path};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = env::args().collect();
    assert!(
        args.len() == 3 || args.len() == 4,
        "EFFECTIVE_ROOT WORLD_ROOT [replay]"
    );
    let replay = args.get(3).is_some_and(|arg| arg == "replay");
    let root = Path::new(&args[1]);
    let world = Path::new(&args[2]);
    let packs = datapack::discover_with_features(world, root);
    let features = Level::read(world)
        .map(|l| l.enabled_features)
        .unwrap_or_default();
    let enabled = datapack::enabled_ids(world, &packs, &features);
    let selected: Vec<_> = enabled
        .iter()
        .filter_map(|id| packs.iter().find(|p| &p.id == id))
        .collect();
    let (mut overrides, mut warnings) = datapack::worldgen_overrides(&selected, |_| true);
    if replay {
        warnings.extend(horizon_client_lib::mod_content::reapply_worldpack_features(
            root,
            &mut overrides,
        )?);
    }
    let registry = Box::leak(Box::new(BlockRegistry::from_facts_json(fs::File::open(
        root.join("facts.json"),
    )?)?));
    let data = GeneratorData::load_with(&root.join("worldgen"), registry, &overrides)?;
    let bundled: Value = serde_json::from_slice(&fs::read(root.join("worldgen/biomes.json"))?)?;
    let mut rows = Vec::new();
    for name in data.biome_names() {
        let id = data.biome_id(name).unwrap();
        let actual: Value = serde_json::from_str(data.biome_json(id))?;
        let before: Value = serde_json::from_str(bundled[name.as_ref()].as_str().unwrap())?;
        let count = |v: &Value, feature: &str| {
            v["features"]
                .as_array()
                .into_iter()
                .flatten()
                .flat_map(|s| s.as_array().into_iter().flatten())
                .filter(|f| f.as_str() == Some(feature))
                .count()
        };
        rows.push(json!({"biome":&**name,"root_nickel":count(&before,"oritech:ore_nickel"),"active_nickel":count(&actual,"oritech:ore_nickel"),"root_platinum":count(&before,"oritech:ore_platinum"),"active_platinum":count(&actual,"oritech:ore_platinum"),"active_end_platinum":count(&actual,"oritech:ore_platinum_end")}));
    }
    println!(
        "{}",
        serde_json::to_string_pretty(
            &json!({"schema":1,"replay":replay,"enabled":enabled,"warnings":warnings,"rows":rows})
        )?
    );
    Ok(())
}
