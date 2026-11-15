// Initial native routing and persistent in-flight ownership for Pretty Pipes.
// Tier rates follow Pretty Pipes 1.22.0 (Ellpeck, MIT); see LICENSE-PRETTY-PIPES.
// This prototype does not yet implement filters, priorities, GUI or exact timing.
// Copyright (c) 2020-2021 Ellpeck, MIT (extraction semantics).
// Stack-size fallback: Copyright (c) 2026 Ludovic Marie and Horizon contributors,
// MIT; see LICENSE-HORIZON. Routing and native integration are first-party code.
use super::Game;
use horizon_client_lib::techquest_pretty_pipes_modules as modules;
use horizon_client_lib::{containers::ModBlockEntity, items::ItemStack};
use horizon_core::geometry::Direction;
use horizon_world::nbt::{Compound, JavaString, Tag};
use std::collections::{BTreeSet, VecDeque};

const PIPE: &str = "prettypipes:pipe";
const MAX_NODES: usize = 4096;

pub(super) fn replace_contents(
    game: &mut Game<'_>,
    pos: [i32; 3],
    state: horizon_world::registry::BlockStateId,
) {
    if game.native_block(pos) != PIPE || game.res.facts().get(state).name.as_ref() == PIPE {
        return;
    }
    let contents = game
        .native_with_mod_block_entity(pos, |entity| {
            if entity.id != PIPE {
                return None;
            }
            let mut items = std::mem::take(&mut entity.items);
            items.extend(modules::take(&mut entity.nbt));
            items.retain(Option::is_some);
            Some(items)
        })
        .flatten();
    if let Some(items) = contents {
        let at = horizon_core::position::BlockPos::new(pos[0], pos[1], pos[2]);
        game.with_level(|_, level, _| level.drop_lost_contents(at, items));
    }
}

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

pub(super) fn use_module(game: &mut Game<'_>, stack: &ItemStack, pos: [i32; 3]) -> bool {
    if game.native_block(pos) != PIPE || modules::rates(&stack.item).is_none() {
        return false;
    }
    let Some(held) = game
        .held()
        .filter(|s| s.count > 0 && s.same_item_same_components(stack))
    else {
        return false;
    };
    let mut hand = Some(held.clone());
    let dimension = game.native_dimension();
    let can_have_modules = Direction::ALL.iter().any(|d| {
        game.native_container_slots(dimension, at(pos, *d), d.opposite())
            .is_some_and(|slots| !slots.is_empty())
    });
    let installed = game
        .native_with_mod_block_entity(pos, |entity| {
            entity.id == PIPE && modules::install(&mut entity.nbt, &mut hand, can_have_modules)
        })
        .unwrap_or(false);
    if installed {
        *game.held_mut() = hand;
        game.native_block_entity_sync(pos);
    }
    installed
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
    let Some((period, amount)) = modules::tier(&entity.nbt) else {
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
