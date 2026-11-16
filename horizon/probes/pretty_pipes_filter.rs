// Execute native ghost edits, filtering, direction cycling and compare original snapshots.
// Args: ORIGINAL_FILTER_ORACLE_JSON. Link against the current native build.
use horizon_client_lib::techquest_pretty_pipes_filter as filter;
use horizon_items::{item_data, item_nbt, items::ItemStack};
use horizon_world::nbt::Tag;
use serde_json::{Value, json};
use std::{env, fs};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let oracle: Value = serde_json::from_slice(&fs::read(env::args().nth(1).unwrap())?)?;
    assert_eq!(oracle["original_filter_and_direction_executed"], true);
    let rows = oracle["rows"].as_array().unwrap();
    assert_eq!(rows.len(), 27);
    let mut module = ItemStack::new("prettypipes:low_extraction_module", 1);
    let mut carried = None;
    for row in rows {
        let name = row["name"].as_str().unwrap();
        let (tier, action) = name.split_once('_').unwrap();
        if action == "default" {
            module = ItemStack::new(&format!("prettypipes:{tier}_extraction_module"), 1);
            carried = None;
        }
        let mut settings = filter::Settings::load(&module).unwrap();
        match action {
            "blacklist_iron" => {
                let mut iron = ItemStack::new("minecraft:iron_ingot", 64);
                iron.data_mut().set_other(
                    "minecraft:custom_data",
                    Some(Tag::compound([("tq_marker", Tag::Int(48))])),
                );
                carried = Some(iron);
                assert!(settings.ghost_click(0, carried.as_ref()));
                settings.save_filter(&mut module);
            }
            "whitelist_iron" | "empty_blacklist" => {
                settings.whitelist = !settings.whitelist;
                settings.save_filter(&mut module);
            }
            "whitelist_sword" => {
                let mut sword = ItemStack::new("minecraft:iron_sword", 1);
                sword.damage = 70;
                carried = Some(sword);
                assert!(settings.ghost_click(0, carried.as_ref()));
                settings.save_filter(&mut module);
            }
            "empty_whitelist" => {
                carried = None;
                assert!(settings.ghost_click(0, None));
                settings.save_filter(&mut module);
            }
            "direction_0" | "direction_1" | "direction_2" => {
                settings.cycle_direction([false, false, false, false, true, true]);
                settings.save_direction(&mut module);
            }
            "default" => {}
            other => panic!("unknown source operation {other}"),
        }
        let original =
            item_data::parse_stack(row["direct_component_snbt"].as_str().unwrap())?.unwrap();
        assert_eq!(
            item_nbt::item_to_nbt(&module),
            item_nbt::item_to_nbt(&original),
            "component snapshot {name}"
        );
        let settings = filter::Settings::load(&module).unwrap();
        for (id, expected) in row["allowed"].as_object().unwrap() {
            let mut item = ItemStack::new(
                if id == "damaged_sword" {
                    "minecraft:iron_sword"
                } else {
                    id
                },
                1,
            );
            if id == "damaged_sword" {
                item.damage = 30;
            }
            assert_eq!(
                settings.allows(&item),
                expected.as_bool().unwrap(),
                "{name} {id}"
            );
        }
        for (i, expected) in row["directions"].as_array().unwrap().iter().enumerate() {
            assert_eq!(
                settings.has_direction(i),
                expected.as_bool().unwrap(),
                "{name} direction {i}"
            );
        }
        assert_eq!(
            carried.as_ref().map_or(0, |s| s.count) as u64,
            row["cursor_count"].as_u64().unwrap()
        );
        assert_eq!(
            settings.samples[0].as_ref().map_or(0, |s| s.count) as u64,
            row["sample_count"].as_u64().unwrap()
        );
    }
    let mut invalid = ItemStack::new("prettypipes:low_extraction_module", 1);
    invalid
        .data_mut()
        .set_other(filter::FILTER, Some(Tag::String("broken".into())));
    assert!(filter::Settings::load(&invalid).is_none());
    let mut settings = filter::Settings::load(&module).unwrap();
    assert!(!settings.ghost_click(9, None));
    let before = item_nbt::item_to_nbt(&module);
    assert!(!settings.ghost_click(usize::MAX, Some(&module)));
    assert_eq!(before, item_nbt::item_to_nbt(&module));
    println!(
        "{}",
        serde_json::to_string_pretty(&json!({
            "schema":1,"steps_match_original":27,"filter_item_cases":108,
            "direction_cases":162,"component_snapshots_match":true,
            "cursor_and_sample_counts_match":true,"malformed_component_rejected":true,
            "out_of_range_ghost_edits_rejected":true,"real_client_tested":false,
        }))?
    );
    Ok(())
}
