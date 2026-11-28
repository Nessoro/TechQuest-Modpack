// Compare isolated entries from the actual staged module with original Java loot.
// Args: EFFECTIVE_CONTENT_ROOT CASES ORIGINAL_ORACLE [baseline].
use horizon_core::random::LegacyRandom;
use horizon_world::loot::{LootData, PackOverlay};
use serde_json::{Value, json};
use std::{collections::BTreeMap, env, fs, path::Path};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = env::args().collect();
    assert!(args.len() == 4 || args.len() == 5);
    let cases: Value = serde_json::from_slice(&fs::read(&args[2])?)?;
    let oracle: Value = serde_json::from_slice(&fs::read(&args[3])?)?;
    assert_eq!(oracle["minecraft"], "1.21.1");
    assert_eq!(oracle["original_loot_functions_executed"], true);
    let inputs = cases["cases"].as_array().unwrap();
    assert_eq!(inputs.len(), 23);
    let files: Vec<_> = inputs
        .iter()
        .map(|c| {
            (
                format!(
                    "loot_table/techquest_reference:{}",
                    c["name"].as_str().unwrap()
                ),
                vec![serde_json::to_vec(&c["native_table"]).unwrap()],
            )
        })
        .collect();
    let data = LootData::load(Path::new(&args[1]), &PackOverlay { files: &files })?;
    let mut rows = Vec::new();
    let mut mismatches = Vec::new();
    for expected in oracle["rows"].as_array().unwrap() {
        let name = expected["name"].as_str().unwrap();
        let seed = expected["seed"].as_i64().unwrap();
        let stacks: Vec<_> = data
            .roll(
                &format!("techquest_reference:{name}"),
                &mut LegacyRandom::new(seed),
                0.0,
                None,
                None,
            )
            .into_iter()
            .map(|s| {
                json!({"item":s.item,"count":s.count,"damage":s.damage,
                       "enchantments":s.enchantments.into_iter().collect::<BTreeMap<_,_>>(),
                       "potion":s.potion})
            })
            .collect();
        let actual = json!({"name":name,"seed":seed,"stacks":stacks});
        if &actual != expected {
            mismatches.push(json!({"expected":expected,"actual":actual}));
        }
        rows.push(actual);
    }
    assert_eq!(rows.len(), 69);
    println!(
        "{}",
        serde_json::to_string_pretty(&json!({
            "schema":1,"minecraft":"26.3","cases":23,"seeds_per_case":3,"rolls":69,
            "module_sha256":cases["module_sha256"],"native_loot_engine_executed":true,
            "isolated_source_entries":true,"rows":rows,"mismatches":mismatches,
            "real_client_tested":false,"full_table_rng_parity_tested":false,
        }))?
    );
    if args.get(4).is_some_and(|s| s == "baseline") {
        assert_eq!(
            mismatches.len(),
            69,
            "baseline must reproduce every missing modifier"
        );
    } else {
        assert!(mismatches.is_empty(), "modifier mismatch");
    }
    Ok(())
}
