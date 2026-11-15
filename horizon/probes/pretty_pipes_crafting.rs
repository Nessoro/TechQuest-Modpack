// Developer-only native recipe-manager comparison. No actor or client login.
// Args: EFFECTIVE_CONTENT_ROOT ORIGINAL_CASES_JSON ORIGINAL_ORACLE_JSON.
use horizon_client_lib::{
    blocks::BlockFacts,
    crafting::Recipes,
    items::{ItemStack, Items},
};
use horizon_world::{loot::PackOverlay, registry::BlockRegistry};
use serde_json::{Value, json};
use std::{env, fs, path::Path};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = env::args().collect();
    assert_eq!(args.len(), 4, "expected ROOT CASES ORIGINAL_ORACLE");
    let root = Path::new(&args[1]);
    let cases: Value = serde_json::from_slice(&fs::read(&args[2])?)?;
    let original: Value = serde_json::from_slice(&fs::read(&args[3])?)?;
    let overlay = PackOverlay { files: &[] };
    let registry = BlockRegistry::from_facts_json(fs::File::open(root.join("facts.json"))?)?;
    let facts = BlockFacts::load(root, &registry)?;
    let items = Items::load(root, &registry, &facts, &overlay)?;
    let recipes = Recipes::load(root, &items, &overlay)?;
    let pipe = registry.default_state("prettypipes:pipe").unwrap();
    assert_eq!(
        items.block_loot_table(&registry, pipe).as_deref(),
        Some("prettypipes:blocks/pipe")
    );
    let mut random = horizon_core::random::LegacyRandom::new(263);
    let pipe_drops = items.block_drops(&registry, pipe, None, &mut random);
    assert_eq!(pipe_drops.len(), 1);
    assert_eq!(&*pipe_drops[0].item, "prettypipes:pipe");
    assert_eq!(pipe_drops[0].count, 1);
    let rows = cases["cases"].as_array().unwrap();
    let oracle = original["crafting"].as_array().unwrap();
    assert_eq!(rows.len(), oracle.len());
    let mut checked = Vec::new();
    for (case, expected) in rows.iter().zip(oracle) {
        assert_eq!(case["name"], expected["name"]);
        let grid: Vec<_> = case["grid"]
            .as_array()
            .unwrap()
            .iter()
            .map(|item| item.as_str().map(|id| ItemStack::new(id, 1)))
            .collect();
        let matched = recipes.find(&grid, 3);
        let mut actual = json!({"name": case["name"], "matched": matched.is_some()});
        if let Some((id, output)) = matched {
            actual["recipe"] = json!(id);
            actual["item"] = json!(&*output.item);
            actual["count"] = json!(output.count);
        }
        assert_eq!(&actual, expected, "{}", case["name"]);
        checked.push(actual);
    }
    println!(
        "{}",
        serde_json::to_string_pretty(&json!({
            "schema": 1, "minecraft": "26.3", "cases": checked,
            "native_recipe_manager_executed": true, "real_client_tested": false,
            "crafting_inventory_consumption_tested": false,
        "pipe_loot_table_evaluated": true,
        }))?
    );
    Ok(())
}
