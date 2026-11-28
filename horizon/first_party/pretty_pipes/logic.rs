// Initial native routing and persistent in-flight ownership for Pretty Pipes.
// Tier rates follow Pretty Pipes 1.22.0 (Ellpeck, MIT); see LICENSE-PRETTY-PIPES.
// This prototype does not yet implement equality modifiers, priorities or exact timing.
// Copyright (c) 2020-2021 Ellpeck, MIT (extraction semantics).
// Stack-size fallback: Copyright (c) 2026 Ludovic Marie and Horizon contributors,
// MIT; see LICENSE-HORIZON. Routing and native integration are first-party code.
use super::Game;
use horizon_client_lib::techquest_pretty_pipes_filter as filter;
use horizon_client_lib::techquest_pretty_pipes_modules as modules;
use horizon_client_lib::{containers::ModBlockEntity, items::ItemStack};
use horizon_core::geometry::Direction;
use horizon_world::nbt::{Compound, JavaString, Tag};
use std::collections::{BTreeSet, VecDeque};

const PIPE: &str = "prettypipes:pipe";
const MAX_NODES: usize = 4096;

fn synchronize(entity: &mut ModBlockEntity) -> bool {
    let fields = &mut **entity;
    modules::synchronize(&mut fields.nbt, &mut fields.items).is_some()
}

fn has_inventory(game: &Game<'_>, pos: [i32; 3]) -> bool {
    let dimension = game.native_dimension();
    Direction::ALL.iter().any(|d| {
        game.native_container_slots(dimension, at(pos, *d), d.opposite())
            .is_some_and(|slots| !slots.is_empty())
    })
}

pub(super) fn allow_open(game: &mut Game<'_>, pos: [i32; 3]) -> bool {
    if game.held().is_some()
        || game.hand != horizon_client_lib::first_person::Hand::Main
        || !has_inventory(game, pos)
    {
        return false;
    }
    // The engine normally builds this table on its first block-entity tick.
    // Opening a newly placed pipe must also work before that tick (or while
    // the world is frozen), without advancing the simulation.
    let state = game.world.block(pos[0], pos[1], pos[2]);
    if game.world.block_entities.mod_container(state.0).is_none() {
        let containers = game.native_containers();
        game.world.block_entities.set_mod_containers(containers);
    }
    let res = game.res.clone();
    game.native_with_mod_block_entity(pos, |entity| {
        if !synchronize(entity) {
            return false;
        }
        // The menu's fixed data width is ready before it opens, including
        // in a frozen world before the next block-entity tick.
        super::techquest_pretty_pipes_ui::update(res.items(), entity);
        true
    })
    .unwrap_or(false)
}

/// A chorus-plant geometry template has no vanilla OpenMenu effect. Preserve
/// Horizon's right-click hook order and secondary-use rule, then open only our
/// empty-main-hand interaction. Other blocks/hands keep the original path.
pub(super) fn interact(
    game: &mut Game<'_>,
    hit: Option<&crate::game::Hit>,
) -> std::ops::ControlFlow<horizon_client_lib::Result<bool>> {
    let Some(hit) = hit else {
        return std::ops::ControlFlow::Continue(());
    };
    if game.native_block(hit.pos) != PIPE
        || (game.keys.held(crate::game::Mapping::Sneak) && game.offhand.is_some())
        || !allow_open(game, hit.pos)
    {
        return std::ops::ControlFlow::Continue(());
    }
    let mut canceled = false;
    game.native_right_click_block(hit.pos, hit.face, &mut canceled);
    game.native_right_click_block_v2(hit.pos, hit.face, game.hand, &mut canceled);
    game.use_failed = canceled;
    if !canceled {
        game.open_menu(hit.pos);
        game.swing_arm();
    }
    std::ops::ControlFlow::Break(Ok(true))
}

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
            let fields = &mut **entity;
            let mut items = modules::take_inventory(&mut fields.nbt, &mut fields.items)?;
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

/// The original network subtracts every item's count on its way to the
/// inventory, including other item types. The current ticking pipe is out of
/// the world's block-entity map and must be counted explicitly, once.
fn on_the_way(game: &Game<'_>, current: &ModBlockEntity, destination: [i32; 3]) -> u32 {
    let count = |entity: &ModBlockEntity| {
        if entity.id != PIPE {
            return 0u32;
        }
        let first = if entity
            .nbt
            .get(&JavaString::from("techquest_inventory_schema"))
            == Some(&Tag::Int(3))
        {
            modules::MODULE_SLOTS
        } else {
            0
        };
        entity
            .items
            .iter()
            .enumerate()
            .skip(first)
            .fold(0u32, |total, (slot, item)| {
                let key = JavaString::from(format!("techquest_pending_{slot}").as_str());
                let matching = entity
                    .nbt
                    .get(&key)
                    .and_then(|p| p.get("destination"))
                    .is_some_and(
                        |p| matches!(p,Tag::IntArray(p) if p.as_slice() == destination.as_slice()),
                    );
                total.saturating_add(if matching {
                    item.as_ref().map_or(0, |s| s.count)
                } else {
                    0
                })
            })
    };
    game.world
        .block_entities
        .values()
        .fold(count(current), |total, entity| {
            total.saturating_add(match entity {
                horizon_client_lib::containers::BlockEntity::Mod(entity) => count(entity),
                _ => 0,
            })
        })
}

pub(super) fn use_module(game: &mut Game<'_>, stack: &ItemStack, pos: [i32; 3]) -> bool {
    if game.native_block(pos) != PIPE || !modules::supported(&stack.item) {
        return false;
    }
    let Some(held) = game
        .held()
        .filter(|s| s.count > 0 && s.same_item_same_components(stack))
    else {
        return false;
    };
    let mut hand = Some(held.clone());
    let can_have_modules = has_inventory(game, pos);
    let installed = game
        .native_with_mod_block_entity(pos, |entity| {
            if entity.id != PIPE || !synchronize(entity) {
                return false;
            }
            let installed = modules::install(&mut entity.nbt, &mut hand, can_have_modules);
            installed && synchronize(entity)
        })
        .unwrap_or(false);
    if installed {
        *game.held_mut() = hand;
        game.native_block_entity_sync(pos);
    }
    installed
}

fn work_blocked(game: &mut Game<'_>, pos: [i32; 3], current: Option<&ModBlockEntity>) -> bool {
    let installed = current.map_or_else(
        || match game.world.block_entities.get(&(pos[0], pos[1], pos[2])) {
            Some(horizon_client_lib::containers::BlockEntity::Mod(entity)) => {
                modules::has_redstone(&entity.nbt, &entity.items)
            }
            _ => false,
        },
        |entity| modules::has_redstone(&entity.nbt, &entity.items),
    );
    if !installed {
        return false;
    }
    let dimension = game.native_dimension().to_owned();
    game.native_neighbor_signal(&dimension, pos) > 0
}

/// A shortest pipe-only route to a reachable inventory, excluding the source.
/// Loaded blocks only; an unloaded chunk never becomes a route implicitly.
fn route(
    game: &mut Game<'_>,
    start: [i32; 3],
    source: [i32; 3],
    item: &ItemStack,
    destination: Option<[i32; 3]>,
    settings: Option<&filter::Settings>,
    current: &ModBlockEntity,
    prevent_oversending: bool,
) -> Option<([i32; 3], Direction, i32, u32)> {
    let mut seen = BTreeSet::from([start]);
    let mut queue = VecDeque::from([(start, 1)]);
    while let Some((pos, distance)) = queue.pop_front() {
        // Original canWork gates selection of new destinations, not transit
        // or direct arrival storage of an already routed item.
        let blocked =
            destination.is_none() && work_blocked(game, pos, (pos == start).then_some(current));
        for direction in Direction::ALL {
            let neighbor = at(pos, direction);
            if game.native_block(neighbor) == PIPE {
                if seen.len() < MAX_NODES && seen.insert(neighbor) {
                    queue.push_back((neighbor, distance + 1));
                }
                continue;
            }
            if blocked || neighbor == source || destination.is_some_and(|d| d != neighbor) {
                continue;
            }
            let direction_index = Direction::ALL.iter().position(|d| *d == direction).unwrap();
            let accepts = if pos == start {
                settings.is_none_or(|s| !s.has_direction(direction_index))
            } else if let Some(horizon_client_lib::containers::BlockEntity::Mod(entity)) =
                game.world.block_entities.get(&(pos[0], pos[1], pos[2]))
            {
                // Physical slots own current menu edits. A not-yet-migrated
                // neighbour still stores modules in the original NBT view.
                let saved;
                let items = if entity
                    .nbt
                    .get(&JavaString::from("techquest_inventory_schema"))
                    == Some(&Tag::Int(3))
                {
                    &entity.items
                } else {
                    saved = modules::read(&entity.nbt).unwrap_or_default();
                    &saved
                };
                items
                    .iter()
                    .take(3)
                    .flatten()
                    .find(|s| filter::slots(&s.item).is_some())
                    .is_none_or(|s| {
                        filter::Settings::load(s).is_some_and(|s| !s.has_direction(direction_index))
                    })
            } else {
                true
            };
            if !accepts {
                continue;
            }
            let face = direction.opposite();
            let Some(space) = super::machines::techquest_pretty_pipes_capacity::capacity(
                game, neighbor, face, item,
            ) else {
                continue;
            };
            let available = if prevent_oversending {
                space.saturating_sub(on_the_way(game, current, neighbor))
            } else {
                space
            };
            let accepted = item.count.min(available);
            if accepted > 0 {
                return Some((neighbor, face, distance, accepted));
            }
        }
    }
    None
}

pub(super) fn tick(game: &mut Game<'_>, pos: [i32; 3], entity: &mut ModBlockEntity) {
    if !synchronize(entity) {
        return;
    }
    super::techquest_pretty_pipes_ui::update(game.res.items(), entity);
    let module = entity
        .items
        .iter()
        .take(3)
        .flatten()
        .find(|s| filter::slots(&s.item).is_some());
    let settings = module.and_then(filter::Settings::load);
    if module.is_some() && settings.is_none() {
        return;
    }
    // Items are in the engine's owned container slots: normal chunk saves and
    // breaking the pipe retain/drop them through the existing container path.
    for slot in modules::MODULE_SLOTS..modules::TOTAL_SLOTS {
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
        } else if let Some((target, face, _, _)) = destination.and_then(|d| {
            route(
                game,
                pos,
                pos,
                &stack,
                Some(d),
                settings.as_ref(),
                entity,
                false,
            )
        }) {
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
    if work_blocked(game, pos, Some(entity)) {
        return;
    }
    if game.world.game_time % period != 0 {
        return;
    }
    let Some(free) =
        (modules::MODULE_SLOTS..modules::TOTAL_SLOTS).find(|&i| entity.items[i].is_none())
    else {
        return;
    };
    let dimension = game.native_dimension();
    for direction in Direction::ALL {
        let direction_index = Direction::ALL.iter().position(|d| *d == direction).unwrap();
        if !settings
            .as_ref()
            .is_some_and(|s| s.has_direction(direction_index))
        {
            continue;
        }
        let source = at(pos, direction);
        let face = direction.opposite();
        let Some(slots) = game.native_container_slots(dimension, source, face) else {
            continue;
        };
        for slot in slots {
            let Some(item) = slot.stack.filter(|_| slot.can_take) else {
                continue;
            };
            if !settings.as_ref().is_some_and(|s| s.allows(&item)) {
                continue;
            }
            let requested = ItemStack {
                count: item.count.min(amount),
                ..item.clone()
            };
            let Some((destination, _, distance, accepted)) = route(
                game,
                pos,
                source,
                &requested,
                None,
                settings.as_ref(),
                entity,
                amount > 1,
            ) else {
                continue;
            };
            let Some(stack) =
                game.native_extract_item(dimension, source, face, slot.slot, accepted)
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
