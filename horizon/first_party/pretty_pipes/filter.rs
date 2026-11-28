// Basic extraction filters and direction selection from Pretty Pipes 1.22.0.
// Copyright (c) 2020-2021 Ellpeck, MIT; see LICENSE-PRETTY-PIPES.
// Ghost entries are samples, never owned inventory or transport stacks.
use horizon_items::{item_nbt, items::ItemStack};
use horizon_world::nbt::Tag;

pub const FILTER: &str = "prettypipes:item_filter_data";
pub const DIRECTION: &str = "prettypipes:direction_selector_data";
pub const DIRECTIONS: [&str; 6] = ["down", "up", "north", "south", "west", "east"];

#[derive(Clone, Debug)]
pub struct Settings {
    pub samples: Vec<Option<ItemStack>>,
    pub whitelist: bool,
    pub direction: Option<usize>,
}

pub fn slots(item: &str) -> Option<usize> {
    match item {
        "prettypipes:low_extraction_module" => Some(3),
        "prettypipes:medium_extraction_module" => Some(6),
        "prettypipes:high_extraction_module" => Some(9),
        _ => None,
    }
}

impl Settings {
    pub fn load(stack: &ItemStack) -> Option<Self> {
        let size = slots(&stack.item)?;
        let mut result = Self {
            samples: vec![None; size],
            whitelist: false,
            direction: None,
        };
        if let Some(value) = stack.data().and_then(|d| d.other(FILTER)) {
            let Tag::Int(n) = value.get("items")?.get("size")? else {
                return None;
            };
            let Tag::List(items) = value.get("items")?.get("items")? else {
                return None;
            };
            let Tag::Byte(whitelist) = value.get("whitelist")? else {
                return None;
            };
            if *n != size as i32 || items.len() != size || ![0, 1].contains(whitelist) {
                return None;
            }
            for (slot, tag) in result.samples.iter_mut().zip(items) {
                let Tag::Compound(fields) = tag else {
                    return None;
                };
                if !fields.is_empty() {
                    *slot = Some(item_nbt::item_from_nbt(tag)?);
                }
            }
            result.whitelist = *whitelist != 0;
        }
        if let Some(value) = stack.data().and_then(|d| d.other(DIRECTION)) {
            let Tag::String(name) = value.get("direction")? else {
                return None;
            };
            result.direction = DIRECTIONS.iter().position(|d| *d == name.to_string_lossy());
        }
        Some(result)
    }

    pub fn allows(&self, item: &ItemStack) -> bool {
        // No equality-modifier module is implemented: the original default
        // compares item identity, ignoring count, damage and other components.
        self.samples.iter().flatten().any(|s| s.item == item.item) == self.whitelist
    }

    pub fn has_direction(&self, direction: usize) -> bool {
        self.direction.is_none_or(|d| d == direction)
    }

    pub fn ghost_click(&mut self, slot: usize, carried: Option<&ItemStack>) -> bool {
        let Some(target) = self.samples.get_mut(slot) else {
            return false;
        };
        *target = carried
            .filter(|s| s.count > 0 && &*s.item != "minecraft:air")
            .map(|s| {
                let mut sample = s.clone();
                sample.count = 1;
                sample
            });
        true
    }

    pub fn cycle_direction(&mut self, available: [bool; 6]) {
        let current = self.direction.unwrap_or(6);
        self.direction = (1..=7)
            .map(|i| (current + i) % 7)
            .find(|i| *i == 6 || available[*i])
            .filter(|i| *i < 6);
    }

    pub fn save_filter(&self, stack: &mut ItemStack) {
        let items = self
            .samples
            .iter()
            .map(|s| {
                s.as_ref()
                    .map_or_else(|| Tag::Compound(Default::default()), item_nbt::item_to_nbt)
            })
            .collect();
        stack.data_mut().set_other(
            FILTER,
            Some(Tag::compound([
                (
                    "items",
                    Tag::compound([
                        ("size", Tag::Int(self.samples.len() as i32)),
                        ("items", Tag::List(items)),
                    ]),
                ),
                ("whitelist", Tag::Byte(i8::from(self.whitelist))),
            ])),
        );
    }

    pub fn save_direction(&self, stack: &mut ItemStack) {
        stack.data_mut().set_other(
            DIRECTION,
            Some(Tag::compound([(
                "direction",
                Tag::String(self.direction.map_or("", |d| DIRECTIONS[d]).into()),
            )])),
        );
    }
}
