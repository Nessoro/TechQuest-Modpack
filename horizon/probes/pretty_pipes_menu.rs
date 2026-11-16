// Developer-only comparison against the original MainPipeContainer oracle.
// Runs Horizon's actual Menu engine, including compiled native slot rules.
// Args: EFFECTIVE_CONTENT_ROOT INSTALLED_MENU_DECLARATION ORIGINAL_MENU_ORACLE_JSON.
use horizon_client_lib::{
    banner::Banners,
    blocks::BlockFacts,
    brewing::Brewing,
    containers::ModMenuType,
    crafting::Recipes,
    items::{ItemStack, Items},
    menu::{Env, Input, Kind, Menu},
};
use horizon_items::item_nbt;
use horizon_world::{loot::PackOverlay, nbt::Tag, registry::BlockRegistry};
use serde_json::{Value, json};
use std::{env, fs, path::Path};

fn inventory_slot(slot: usize) -> usize {
    67 + if slot < 9 { 27 + slot } else { slot - 9 }
}

fn stack(value: &Value) -> Option<ItemStack> {
    let id = value["id"].as_str()?;
    let count = value["count"].as_u64().unwrap() as u32;
    let marker = value["marker"].as_i64().unwrap() as i32;
    if marker == 0 {
        return Some(ItemStack::new(id, count));
    }
    item_nbt::item_from_nbt(&Tag::compound([
        ("id", Tag::String(id.into())),
        ("count", Tag::Int(count as i32)),
        (
            "components",
            Tag::compound([(
                "minecraft:custom_data",
                Tag::compound([("tq_marker", Tag::Int(marker))]),
            )]),
        ),
    ]))
}

fn describe(stack: Option<&ItemStack>) -> Value {
    let Some(stack) = stack else {
        return Value::Null;
    };
    let marker = stack
        .data()
        .and_then(|d| d.other("minecraft:custom_data"))
        .and_then(|tag| tag.get("tq_marker"))
        .and_then(|tag| match tag {
            Tag::Int(n) => Some(*n),
            _ => None,
        })
        .unwrap_or(0);
    json!({"id": &*stack.item, "count": stack.count, "marker": marker})
}

fn snapshot(menu: &Menu) -> Value {
    let mut dropped = std::collections::BTreeMap::<String, u32>::new();
    for stack in &menu.dropped {
        *dropped.entry(stack.item.to_string()).or_default() += stack.count;
    }
    json!({
        "modules": (0..3).map(|i| describe(menu.slot(i))).collect::<Vec<_>>(),
        "inventory": (0..36).map(|i| describe(menu.slot(inventory_slot(i)))).collect::<Vec<_>>(),
        "cursor": describe(menu.carried.as_ref()), "dropped": dropped,
        "queued": (3..67).filter_map(|i| menu.slot(i)).map(|s| s.count).sum::<u32>(),
    })
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = env::args().collect();
    assert_eq!(
        args.len(),
        4,
        "expected ROOT INSTALLED_MENU_DECLARATION ORIGINAL_MENU_ORACLE"
    );
    let root = Path::new(&args[1]);
    let original: Value = serde_json::from_slice(&fs::read(&args[3])?)?;
    let declaration: Value = serde_json::from_slice(&fs::read(&args[2])?)?;
    let registry = BlockRegistry::from_facts_json(fs::File::open(root.join("facts.json"))?)?;
    let facts = BlockFacts::load(root, &registry)?;
    let overlay = PackOverlay::NONE;
    let items = Items::load(root, &registry, &facts, &overlay)?;
    let recipes = Recipes::load(root, &items, &overlay)?;
    let brewing = Brewing::load(root, &items, &overlay);
    let (banners, station_recipes) = (Banners::default(), Default::default());
    let (enchantments, names) = (Default::default(), Default::default());
    let env = Env {
        items: &items,
        recipes: &recipes,
        brewing: &brewing,
        banners: &banners,
        station_recipes: &station_recipes,
        enchantments: &enchantments,
        names: &names,
        trade: None,
        maps: None,
        limited_crafting: false,
        known_recipes: None,
    };
    let kind = Kind::Mod(Box::leak(Box::new(ModMenuType {
        id: "prettypipes:pipe",
        slots: declaration["slots"].as_u64().unwrap() as usize,
        data_slots: 0,
        results: vec![],
    })));
    let mut menu = Menu::new(kind);
    for i in 3..67 {
        menu.hide_slot(i);
    }
    menu.set_slot(&env, 3, Some(ItemStack::new("minecraft:iron_ingot", 8)));
    // Hostile packet indices must not expose a hidden transport slot.
    let before = snapshot(&menu);
    for mode in [
        Input::Pickup,
        Input::QuickMove,
        Input::Swap,
        Input::Throw,
        Input::PickupAll,
    ] {
        menu.carried = if mode == Input::PickupAll {
            Some(ItemStack::new("minecraft:iron_ingot", 4))
        } else {
            None
        };
        let target = if mode == Input::PickupAll { 0 } else { 3 };
        let expected = snapshot(&menu);
        menu.click(&env, target, 0, mode)?;
        assert_eq!(snapshot(&menu), expected, "hidden transport slot: {mode:?}");
        let mut visible = Menu::new(kind);
        visible.set_slot(&env, 3, Some(ItemStack::new("minecraft:iron_ingot", 8)));
        visible.carried = menu.carried.clone();
        let control = snapshot(&visible);
        visible.click(&env, target, 0, mode)?;
        assert_ne!(
            snapshot(&visible),
            control,
            "visible-slot positive control: {mode:?}"
        );
    }
    menu.carried = None;
    assert_eq!(snapshot(&menu), before);
    let mut steps = Vec::new();
    for row in original["steps"].as_array().unwrap() {
        if !row["setup_cursor"].is_null() {
            menu.carried = stack(&row["setup_cursor"]);
        }
        let n = row["slot"].as_u64().unwrap() as usize;
        let slot = if row["area"] == "module" {
            n
        } else {
            inventory_slot(n)
        };
        let input = match row["mode"].as_str().unwrap() {
            "PICKUP" => Input::Pickup,
            "QUICK_MOVE" => Input::QuickMove,
            "SWAP" => Input::Swap,
            "THROW" => Input::Throw,
            other => panic!("unsupported original mode {other}"),
        };
        menu.click(
            &env,
            slot as i32,
            row["button"].as_i64().unwrap() as i32,
            input,
        )?;
        let observed = snapshot(&menu);
        for key in ["modules", "inventory", "cursor", "dropped", "queued"] {
            assert_eq!(observed[key], row[key], "{}: {key}", row["name"]);
        }
        steps.push(json!({"name": row["name"], "observed": observed}));
    }
    println!(
        "{}",
        serde_json::to_string_pretty(&json!({
            "schema": 1, "minecraft": "26.3", "native_menu_engine_executed": true,
        "steps_match_original": steps.len(), "steps": steps, "hidden_slot_actions_blocked": 5,
        "visible_slot_positive_controls_passed": 5,
            "real_client_tested": false, "game_player_dispatch_tested": false,
        }))?
    );
    Ok(())
}
