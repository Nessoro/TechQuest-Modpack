// Initial native routing and persistent in-flight ownership for Pretty Pipes.
// Tier rates follow Pretty Pipes 1.22.0 (Ellpeck, MIT); see LICENSE-PRETTY-PIPES.
// This prototype does not yet implement filters, priorities, GUI or exact timing.
use super::Game;
use horizon_client_lib::{containers::ModBlockEntity, items::ItemStack};
use horizon_core::geometry::Direction;
use horizon_world::nbt::{Compound, JavaString, Tag};
use std::collections::{BTreeSet, VecDeque};

const PIPE: &str = "prettypipes:pipe";
const MAX_NODES: usize = 4096;

fn at(pos: [i32; 3], direction: Direction) -> [i32; 3] {
    let delta = direction.normal();
    std::array::from_fn(|i| pos[i].saturating_add(delta[i]))
}

fn number(nbt: &Compound, key: &str) -> Option<i32> {
    match nbt.get(&JavaString::from(key)) {
        Some(Tag::Int(n)) => Some(*n),
        _ => None,
    }
}

fn tier(entity: &ModBlockEntity) -> Option<(i64, u32)> {
    let Tag::Compound(modules) = entity.nbt.get(&JavaString::from("modules"))? else {
        return None;
    };
    let Tag::List(items) = modules.get(&JavaString::from("Items"))? else {
        return None;
    };
    for item in items {
        let Some(Tag::String(id)) = item.get("id") else {
            continue;
        };
        match id.to_string_lossy().as_ref() {
            "prettypipes:low_extraction_module" => return Some((20, 1)),
            "prettypipes:medium_extraction_module" => return Some((15, 8)),
            "prettypipes:high_extraction_module" => return Some((10, 64)),
            _ => {}
        }
    }
    None
}

/// A shortest pipe-only route to a reachable inventory, excluding the source.
/// Loaded blocks only; an unloaded chunk never becomes a route implicitly.
fn route(
    game: &Game<'_>,
    start: [i32; 3],
    source: [i32; 3],
    item: &ItemStack,
    destination: Option<[i32; 3]>,
) -> Option<([i32; 3], Direction, i32)> {
    let dimension = game.native_dimension();
    let mut seen = BTreeSet::from([start]);
    let mut queue = VecDeque::from([(start, 1)]);
    let maximum = item
        .data()
        .and_then(|d| d.other("minecraft:max_stack_size"))
        .and_then(|n| match n {
            Tag::Int(n) => Some((*n).clamp(1, 99) as u32),
            _ => None,
        })
        .or_else(|| game.native_max_stack_size(&item.item))
        .unwrap_or(64);
    while let Some((pos, distance)) = queue.pop_front() {
        for direction in Direction::ALL {
            let neighbor = at(pos, direction);
            if game.native_block(neighbor) == PIPE {
                if seen.len() < MAX_NODES && seen.insert(neighbor) {
                    queue.push_back((neighbor, distance + 1));
                }
                continue;
            }
            if pos == start || neighbor == source || destination.is_some_and(|d| d != neighbor) {
                continue;
            }
            let face = direction.opposite();
            let Some(slots) = game.native_container_slots(dimension, neighbor, face) else {
                continue;
            };
            if slots.iter().any(|s| {
                s.stack
                    .as_ref()
                    .is_none_or(|held| held.same_item_same_components(item) && held.count < maximum)
            }) {
                return Some((neighbor, face, distance));
            }
        }
    }
    None
}

pub(super) fn tick(game: &mut Game<'_>, pos: [i32; 3], entity: &mut ModBlockEntity) {
    // Items are in the engine's owned container slots: normal chunk saves and
    // breaking the pipe retain/drop them through the existing container path.
    for slot in 0..entity.items.len() {
        let key = JavaString::from(format!("techquest_pending_{slot}").as_str());
        let Some(Tag::Compound(mut pending)) = entity.nbt.get(&key).cloned() else {
            continue;
        };
        let Some(stack) = entity.items[slot].take() else {
            entity.nbt.remove(&key);
            continue;
        };
        let remaining = number(&pending, "remaining").unwrap_or(0);
        let destination = match pending.get(&JavaString::from("destination")) {
            Some(Tag::IntArray(p)) if p.len() == 3 => Some([p[0], p[1], p[2]]),
            _ => None,
        };
        if remaining > 0 {
            pending.insert("remaining".into(), Tag::Int(remaining - 1));
            entity.items[slot] = Some(stack);
            entity.nbt.insert(key, Tag::Compound(pending));
        } else if let Some((target, face, _)) =
            destination.and_then(|d| route(game, pos, pos, &stack, Some(d)))
        {
            entity.items[slot] = game.native_insert_item(target, face, stack);
            if entity.items[slot].is_none() {
                entity.nbt.remove(&key);
            }
        } else {
            entity.items[slot] = Some(stack);
        }
    }
    let Some((period, amount)) = tier(entity) else {
        return;
    };
    if game.world.game_time % period != 0 {
        return;
    }
    let Some(free) = entity.items.iter().position(Option::is_none) else {
        return;
    };
    let dimension = game.native_dimension();
    for direction in Direction::ALL {
        let source = at(pos, direction);
        let face = direction.opposite();
        let Some(slots) = game.native_container_slots(dimension, source, face) else {
            continue;
        };
        for slot in slots {
            let Some(item) = slot.stack.filter(|_| slot.can_take) else {
                continue;
            };
            let Some((destination, _, distance)) = route(game, pos, source, &item, None) else {
                continue;
            };
            let Some(stack) = game.native_extract_item(dimension, source, face, slot.slot, amount)
            else {
                continue;
            };
            let mut pending = Compound::new();
            pending.insert("destination".into(), Tag::IntArray(destination.to_vec()));
            pending.insert("remaining".into(), Tag::Int(distance.saturating_mul(20)));
            entity.items[free] = Some(stack);
            entity.nbt.insert(
                JavaString::from(format!("techquest_pending_{free}").as_str()),
                Tag::Compound(pending),
            );
            return;
        }
    }
}
