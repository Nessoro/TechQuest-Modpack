// Developer comparison against the original binary recipe manager and ore loot.
use horizon_client_lib::{
    blocks::BlockFacts,
    crafting::Recipes,
    items::{ItemStack, Items},
};
use horizon_core::random::LegacyRandom;
use horizon_world::{loot::PackOverlay, registry::BlockRegistry};
use serde_json::{Value, json};
use std::{env, fs, path::Path};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = env::args().collect();
    assert_eq!(args.len(), 4, "ROOT CASES ORIGINAL");
    let root = Path::new(&args[1]);
    let cases: Value = serde_json::from_slice(&fs::read(&args[2])?)?;
    let oracle: Value = serde_json::from_slice(&fs::read(&args[3])?)?;
    assert_eq!(oracle["original_crafting_and_loot_executed"], true);
    let registry = BlockRegistry::from_facts_json(fs::File::open(root.join("facts.json"))?)?;
    let facts = BlockFacts::load(root, &registry)?;
    let items = Items::load(root, &registry, &facts, &PackOverlay::NONE)?;
    let recipes = Recipes::load(root, &items, &PackOverlay::NONE)?;
    let inputs = cases["crafting"].as_array().unwrap();
    let expected = oracle["crafting"].as_array().unwrap();
    assert_eq!(inputs.len(), expected.len());
    let mut crafting = Vec::new();
    let mut mismatches = Vec::new();
    for (input, expected) in inputs.iter().zip(expected) {
        assert_eq!(input["name"], expected["name"]);
        let grid: Vec<_> = input["grid"]
            .as_array()
            .unwrap()
            .iter()
            .map(|v| v.as_str().map(|id| ItemStack::new(id, 1)))
            .collect();
        let result = recipes.find(&grid, 3);
        let mut actual = json!({"name":input["name"],"matched":result.is_some()});
        if let Some((id, stack)) = result {
            actual["recipe"] = json!(if id.contains(':') {
                id.to_owned()
            } else {
                format!("minecraft:{id}")
            });
            actual["item"] = json!(&*stack.item);
            actual["count"] = json!(stack.count);
        }
        if &actual != expected {
            mismatches.push(json!({"expected":expected,"actual":actual}));
        }
        crafting.push(actual);
    }
    let mut loot = Vec::new();
    for expected in oracle["loot"].as_array().unwrap() {
        let ore = expected["ore"].as_str().unwrap();
        let mode = expected["tool"].as_str().unwrap();
        let seed = expected["seed"].as_i64().unwrap();
        let state = registry.default_state(&format!("oritech:{ore}")).unwrap();
        let mut tool = ItemStack::new("minecraft:diamond_pickaxe", 1);
        match mode {
            "silk" => tool.enchant("minecraft:silk_touch", 1),
            "fortune" => tool.enchant("minecraft:fortune", 3),
            _ => {}
        }
        let stacks: Vec<_> = items
            .block_drops(&registry, state, Some(&tool), &mut LegacyRandom::new(seed))
            .into_iter()
            .map(|s| json!({"item":&*s.item,"count":s.count}))
            .collect();
        let actual = json!({"ore":ore,"tool":mode,"seed":seed,"stacks":stacks});
        if &actual != expected {
            mismatches.push(json!({"expected":expected,"actual":actual}));
        }
        loot.push(actual);
    }
    println!(
        "{}",
        serde_json::to_string_pretty(
            &json!({"schema":1,"crafting_cases":crafting.len(),"ore_loot_rolls":loot.len(),"crafting":crafting,"loot":loot,"mismatches":mismatches,"native_recipe_and_loot_engines_executed":true,"real_client_tested":false})
        )?
    );
    assert!(mismatches.is_empty(), "content comparison failed");
    Ok(())
}
