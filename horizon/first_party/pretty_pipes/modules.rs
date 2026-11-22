// Default module inventory semantics observed in Pretty Pipes 1.22.0.
// Copyright (c) 2020-2021 Ellpeck, MIT; see LICENSE-PRETTY-PIPES.
// NBT and ItemStack codecs use Horizon's MIT API; see LICENSE-HORIZON.
use horizon_items::{item_nbt, items::ItemStack};
use horizon_world::nbt::{Compound, JavaString, Tag};

pub const MODULE_SLOTS: usize = 3;
pub const QUEUE_SLOTS: usize = 64;
pub const TOTAL_SLOTS: usize = MODULE_SLOTS + QUEUE_SLOTS;
pub const REDSTONE: &str = "prettypipes:redstone_module";
const SCHEMA: &str = "techquest_inventory_schema";
const SNAPSHOT: &str = "techquest_modules_snapshot";

fn encoded(slots: &[Option<ItemStack>]) -> Tag {
    Tag::compound([
        ("Size", Tag::Int(3)),
        ("Items", item_nbt::encode_items(slots)),
    ])
}

/// Physical module slots are authoritative between menu clicks. The original
/// module NBT is a compatibility view; a changed view imports an explicit NBT
/// edit once. The snapshot distinguishes it from an unsaved menu change.
pub fn synchronize(nbt: &mut Compound, items: &mut Vec<Option<ItemStack>>) -> Option<()> {
    let source = read(nbt)?;
    let legacy = match nbt.get(&JavaString::from(SCHEMA)) {
        None => true,
        Some(Tag::Int(3)) => false,
        _ => return None,
    };
    if items.len() > TOTAL_SLOTS || (legacy && items.iter().skip(QUEUE_SLOTS).any(Option::is_some))
    {
        return None;
    }
    let import =
        legacy || nbt.get(&JavaString::from("modules")) != nbt.get(&JavaString::from(SNAPSHOT));
    items.resize(TOTAL_SLOTS, None);
    if legacy {
        for i in (0..QUEUE_SLOTS).rev() {
            items[i + MODULE_SLOTS] = items[i].take();
        }
        let pending: Vec<_> = (0..QUEUE_SLOTS)
            .map(|i| nbt.remove(&JavaString::from(format!("techquest_pending_{i}").as_str())))
            .collect();
        for (i, value) in pending.into_iter().enumerate() {
            if let Some(value) = value {
                nbt.insert(
                    JavaString::from(format!("techquest_pending_{}", i + MODULE_SLOTS).as_str()),
                    value,
                );
            }
        }
        nbt.insert(SCHEMA.into(), Tag::Int(3));
    }
    if import {
        items[..MODULE_SLOTS].clone_from_slice(&source);
    }
    let view = encoded(&items[..MODULE_SLOTS]);
    if nbt.get(&JavaString::from("modules")) != Some(&view) {
        nbt.insert("modules".into(), view.clone());
    }
    if nbt.get(&JavaString::from(SNAPSHOT)) != Some(&view) {
        nbt.insert(SNAPSHOT.into(), view);
    }
    Some(())
}

pub fn menu_accepts(items: &[Option<ItemStack>], stack: &ItemStack) -> bool {
    stack.count > 0
        && supported(&stack.item)
        && items.iter().take(MODULE_SLOTS).flatten().all(|other| {
            supported(&other.item)
                && ((stack.item.as_ref() == REDSTONE) != (other.item.as_ref() == REDSTONE))
        })
}

pub fn supported(item: &str) -> bool {
    item == REDSTONE || rates(item).is_some()
}

pub fn has_redstone(nbt: &Compound, items: &[Option<ItemStack>]) -> bool {
    let saved;
    let slots = if nbt.get(&JavaString::from(SCHEMA)) == Some(&Tag::Int(3)) {
        items
    } else {
        saved = read(nbt).unwrap_or_default();
        &saved
    };
    slots
        .iter()
        .take(MODULE_SLOTS)
        .flatten()
        .any(|s| s.item.as_ref() == REDSTONE)
}

pub fn take_inventory(
    nbt: &mut Compound,
    items: &mut Vec<Option<ItemStack>>,
) -> Option<Vec<Option<ItemStack>>> {
    synchronize(nbt, items)?;
    nbt.remove(&JavaString::from("modules"));
    nbt.remove(&JavaString::from(SNAPSHOT));
    Some(std::mem::take(items))
}

pub fn rates(item: &str) -> Option<(i64, u32)> {
    match item {
        "prettypipes:low_extraction_module" => Some((20, 1)),
        "prettypipes:medium_extraction_module" => Some((15, 8)),
        "prettypipes:high_extraction_module" => Some((10, 64)),
        _ => None,
    }
}

pub fn read(nbt: &Compound) -> Option<Vec<Option<ItemStack>>> {
    let Some(value) = nbt.get(&JavaString::from("modules")) else {
        return Some(vec![None; 3]);
    };
    let Tag::Compound(modules) = value else {
        return None;
    };
    if let Some(size) = modules.get(&JavaString::from("Size")) {
        if !matches!(size, Tag::Int(3)) {
            return None;
        }
    }
    let items = modules.get(&JavaString::from("Items"));
    if items.is_some_and(|v| !matches!(v, Tag::List(_))) {
        return None;
    }
    Some(item_nbt::decode_items(items, 3))
}

pub fn tier(nbt: &Compound) -> Option<(i64, u32)> {
    read(nbt)?.iter().flatten().find_map(|s| rates(&s.item))
}

pub fn take(nbt: &mut Compound) -> Vec<Option<ItemStack>> {
    let Some(slots) = read(nbt) else {
        return Vec::new();
    };
    nbt.remove(&JavaString::from("modules"));
    slots
}

/// Original mutual compatibility for the supported extractor/redstone subset.
/// Unknown modules remain owned but prevent installing new combinations.
pub fn install(nbt: &mut Compound, held: &mut Option<ItemStack>, can_have_modules: bool) -> bool {
    if !can_have_modules {
        return false;
    }
    let Some(stack) = held.as_ref().filter(|s| s.count > 0 && supported(&s.item)) else {
        return false;
    };
    let Some(mut slots) = read(nbt) else {
        return false;
    };
    if !menu_accepts(&slots, stack) {
        return false;
    }
    let Some(slot) = slots.iter().position(Option::is_none) else {
        return false;
    };
    let mut one = stack.clone();
    one.count = 1;
    slots[slot] = Some(one);
    let mut modules = Compound::new();
    modules.insert("Size".into(), Tag::Int(3));
    modules.insert("Items".into(), item_nbt::encode_items(&slots));
    nbt.insert("modules".into(), Tag::Compound(modules));
    let stack = held.as_mut().unwrap();
    // The original block consumes one even in creative: this is intentionally
    // independent of Game::consume_held's vanilla creative exemption.
    stack.count -= 1;
    if stack.count == 0 {
        *held = None;
    }
    true
}

#[cfg(test)]
mod tests {
    use super::*;

    fn oracle() -> serde_json::Value {
        let path =
            std::env::var("TQ_PRETTY_PIPES_INTERACTION_ORACLE").expect("original oracle required");
        serde_json::from_slice(&std::fs::read(path).unwrap()).unwrap()
    }

    #[test]
    fn observed_install_and_rejections_match_original() {
        let expected = oracle();
        for (name, have_inventory, item, occupied) in [
            (
                "survival_install",
                true,
                "prettypipes:low_extraction_module",
                false,
            ),
            (
                "creative_install",
                true,
                "prettypipes:low_extraction_module",
                false,
            ),
            (
                "no_inventory",
                false,
                "prettypipes:low_extraction_module",
                false,
            ),
            ("blank_rejected", true, "prettypipes:blank_module", false),
            (
                "duplicate_rejected",
                true,
                "prettypipes:high_extraction_module",
                true,
            ),
        ] {
            let mut nbt = Compound::new();
            if occupied {
                let mut first = Some(ItemStack::new("prettypipes:low_extraction_module", 1));
                assert!(install(&mut nbt, &mut first, true));
            }
            let mut held = Some(ItemStack::new(item, 2));
            let changed = install(&mut nbt, &mut held, have_inventory);
            let row = &expected["checks"][name];
            assert_eq!(changed, row["consumes_action"].as_bool().unwrap(), "{name}");
            assert_eq!(
                held.as_ref().map_or(0, |s| s.count) as u64,
                row["held"].as_u64().unwrap()
            );
            assert_eq!(
                read(&nbt)
                    .unwrap()
                    .iter()
                    .flatten()
                    .map(|s| s.count as u64)
                    .sum::<u64>(),
                row["installed"].as_u64().unwrap()
            );
        }
    }

    #[test]
    fn observed_nbt_count_defaults_match_original() {
        let expected = oracle();
        for count in [-1, 0, 1, 2] {
            let item = Tag::compound([
                ("Slot", Tag::Byte(0)),
                (
                    "id",
                    Tag::String("prettypipes:low_extraction_module".into()),
                ),
                ("count", Tag::Int(count)),
            ]);
            let mut nbt = Compound::new();
            nbt.insert(
                "modules".into(),
                Tag::compound([("Size", Tag::Int(3)), ("Items", Tag::List(vec![item]))]),
            );
            assert_eq!(
                read(&nbt).unwrap()[0].as_ref().unwrap().count as u64,
                expected["checks"]["nbt_counts"][count.to_string()]
                    .as_u64()
                    .unwrap()
            );
        }
    }

    #[test]
    fn pending_items_and_components_survive_install() {
        let mut nbt = Compound::new();
        let pending = Tag::compound([("remaining", Tag::Int(29))]);
        nbt.insert("techquest_pending_0".into(), pending.clone());
        let tag = Tag::compound([
            (
                "id",
                Tag::String("prettypipes:low_extraction_module".into()),
            ),
            ("count", Tag::Int(1)),
            (
                "components",
                Tag::compound([(
                    "minecraft:custom_data",
                    Tag::compound([("tq_marker", Tag::Int(48))]),
                )]),
            ),
        ]);
        let original = item_nbt::item_from_nbt(&tag).unwrap();
        let mut held = Some(original.clone());
        assert!(install(&mut nbt, &mut held, true));
        assert!(held.is_none());
        assert_eq!(nbt[&JavaString::from("techquest_pending_0")], pending);
        assert!(
            read(&nbt).unwrap()[0]
                .as_ref()
                .unwrap()
                .same_item_same_components(&original)
        );
    }

    #[test]
    fn invalid_inventory_is_not_destructively_repaired() {
        let mut nbt = Compound::new();
        nbt.insert("modules".into(), Tag::String("unexpected".into()));
        let before = nbt.clone();
        let mut held = Some(ItemStack::new("prettypipes:low_extraction_module", 1));
        assert!(!install(&mut nbt, &mut held, true));
        assert_eq!(nbt, before);
        assert_eq!(held.unwrap().count, 1);
    }

    #[test]
    fn removed_modules_are_owned_once() {
        let expected = oracle();
        let mut nbt = Compound::new();
        let mut held = Some(ItemStack::new("prettypipes:low_extraction_module", 2));
        assert!(install(&mut nbt, &mut held, true));
        let removed = take(&mut nbt);
        let total: u64 = removed.iter().flatten().map(|s| u64::from(s.count)).sum();
        for mode in ["replace", "destroy", "creative"] {
            assert_eq!(
                total,
                expected["checks"]["removal"][mode]["dropped"]["prettypipes:low_extraction_module"]
                    .as_u64()
                    .unwrap()
            );
        }
        assert!(take(&mut nbt).iter().all(Option::is_none));
        assert_eq!(held.unwrap().count, 1);
    }

    #[test]
    fn legacy_queue_migrates_once_with_pending_metadata() {
        let mut nbt = Compound::new();
        let mut hand = Some(ItemStack::new("prettypipes:low_extraction_module", 1));
        assert!(install(&mut nbt, &mut hand, true));
        let pending = Tag::compound([("remaining", Tag::Int(29))]);
        nbt.insert("techquest_pending_63".into(), pending.clone());
        let mut items = vec![None; 64];
        items[63] = Some(ItemStack::new("minecraft:iron_ingot", 8));
        synchronize(&mut nbt, &mut items).unwrap();
        assert_eq!(items[66].as_ref().unwrap().count, 8);
        assert_eq!(items[0].as_ref().unwrap().count, 1);
        assert_eq!(nbt[&JavaString::from("techquest_pending_66")], pending);
        assert!(!nbt.contains_key(&JavaString::from("techquest_pending_63")));
        let before = (nbt.clone(), items.clone());
        synchronize(&mut nbt, &mut items).unwrap();
        assert_eq!((nbt.clone(), items.clone()), before);
        let taken = take_inventory(&mut nbt, &mut items).unwrap();
        assert_eq!(taken.iter().flatten().map(|s| s.count).sum::<u32>(), 9);
        assert!(
            take_inventory(&mut nbt, &mut items)
                .unwrap()
                .iter()
                .all(Option::is_none)
        );
    }

    #[test]
    fn physical_menu_removal_survives_a_save_before_next_tick() {
        let mut nbt = Compound::new();
        let mut items = vec![None; 64];
        let mut hand = Some(ItemStack::new("prettypipes:low_extraction_module", 1));
        assert!(install(&mut nbt, &mut hand, true));
        synchronize(&mut nbt, &mut items).unwrap();
        let removed = items[0].take().unwrap();
        let mut saved_nbt = nbt.clone();
        let mut saved_items = items.clone();
        synchronize(&mut saved_nbt, &mut saved_items).unwrap();
        assert!(read(&saved_nbt).unwrap().iter().all(Option::is_none));
        assert!(saved_items.iter().all(Option::is_none));
        assert_eq!(removed.count, 1);
    }

    #[test]
    fn explicit_nbt_edit_updates_modules_without_touching_queue() {
        let mut nbt = Compound::new();
        nbt.insert(SCHEMA.into(), Tag::Int(3));
        let mut items = vec![None; TOTAL_SLOTS];
        items[3] = Some(ItemStack::new("minecraft:iron_ingot", 8));
        synchronize(&mut nbt, &mut items).unwrap();
        let mut hand = Some(ItemStack::new("prettypipes:high_extraction_module", 2));
        assert!(install(&mut nbt, &mut hand, true));
        synchronize(&mut nbt, &mut items).unwrap();
        assert_eq!(
            &*items[0].as_ref().unwrap().item,
            "prettypipes:high_extraction_module"
        );
        assert_eq!(items[3].as_ref().unwrap().count, 8);
        assert_eq!(hand.unwrap().count, 1);
    }
}
