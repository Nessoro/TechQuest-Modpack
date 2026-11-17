// Oritech 1.2.13 generator/furnace semantics: Rearth, CC0-1.0.
// Source pin and scope: README.md; dedication retained in LICENSE-ORITECH.
// Horizon integration adapts MIT Game::use_hand and native energy helpers;
// Copyright (c) 2026 Ludovic Marie and Horizon contributors. LICENSE-HORIZON.
use super::Game;
use horizon_client_lib::{containers::ModBlockEntity, items::ItemStack};
use horizon_core::geometry::Direction;
use horizon_world::nbt::{Compound, Tag};

pub(super) const GENERATOR: &str = "oritech:basic_generator_block";
pub(super) const FURNACE: &str = "oritech:powered_furnace_block";
pub(super) const CORE: &str = "oritech:machine_core_1";
const PROGRESS: &str = "oritech.machine_progress";
const ASSEMBLED: &str = "techquest_assembled";

pub(super) fn machine(id: &str) -> bool {
    matches!(id, GENERATOR | FURNACE)
}
fn int(nbt: &Compound, key: &str) -> i32 {
    match nbt.get(&key.into()) {
        Some(Tag::Int(n)) => *n,
        _ => 0,
    }
}
fn flag(nbt: &Compound, key: &str) -> bool {
    matches!(nbt.get(&key.into()), Some(Tag::Byte(1)))
}
fn put(nbt: &mut Compound, key: &str, n: i32) {
    nbt.insert(key.into(), Tag::Int(n));
}
fn above(pos: [i32; 3]) -> [i32; 3] {
    [pos[0], pos[1].saturating_add(1), pos[2]]
}
fn controller(game: &Game<'_>, pos: [i32; 3]) -> Option<[i32; 3]> {
    if game.native_block(pos) != CORE {
        return None;
    }
    let horizon_client_lib::containers::BlockEntity::Mod(core) =
        game.world.block_entities.get(&(pos[0], pos[1], pos[2]))?
    else {
        return None;
    };
    if !flag(&core.nbt, "techquest_core_used") {
        return None;
    }
    let p = std::array::from_fn(|i| {
        pos[i].saturating_add(int(
            &core.nbt,
            ["controller_x", "controller_y", "controller_z"][i],
        ))
    });
    (above(p) == pos && game.native_block(p) == FURNACE).then_some(p)
}
pub(super) fn assemble(game: &mut Game<'_>, pos: [i32; 3]) -> bool {
    let core_pos = above(pos);
    if game.native_block(core_pos) != CORE {
        return false;
    }
    let linked = controller(game, core_pos);
    if linked.is_some_and(|p| p != pos) {
        return false;
    }
    let connected = game
        .native_with_mod_block_entity(core_pos, |core| {
            core.nbt.insert("techquest_core_used".into(), Tag::Byte(1));
            for (key, n) in ["controller_x", "controller_y", "controller_z"]
                .into_iter()
                .zip([0, -1, 0])
            {
                put(&mut core.nbt, key, n);
            }
            true
        })
        .unwrap_or(false);
    connected
        && game
            .native_with_mod_block_entity(pos, |entity| {
                entity.nbt.insert(ASSEMBLED.into(), Tag::Byte(1));
                true
            })
            .unwrap_or(false)
}
fn shrink(slot: &mut Option<ItemStack>) {
    if let Some(stack) = slot {
        stack.count = stack.count.saturating_sub(1);
        if stack.count == 0 {
            *slot = None;
        }
    }
}
fn max_stack(game: &Game<'_>, stack: &ItemStack) -> u32 {
    if let Some(Tag::Int(n)) = stack
        .data()
        .and_then(|d| d.other("minecraft:max_stack_size"))
    {
        return (*n).clamp(1, 99) as u32;
    }
    game.res
        .items()
        .get(&stack.item)
        .map_or(64, |i| i.max_stack)
        .max(1)
}
pub(super) fn update(entity: &mut ModBlockEntity) {
    let energy = int(&entity.nbt, "energy").max(0);
    entity.data = vec![
        energy & 0xffff,
        (energy >> 16) & 0xffff,
        int(&entity.nbt, PROGRESS),
        int(&entity.nbt, "storedBurn"),
        i32::from(flag(&entity.nbt, ASSEMBLED)),
    ];
}
pub(super) fn tick(game: &mut Game<'_>, pos: [i32; 3], entity: &mut ModBlockEntity) {
    let count = if entity.id == GENERATOR { 1 } else { 2 };
    if entity.items.len() < count {
        entity.items.resize(count, None);
    }
    let mut energy = int(&entity.nbt, "energy").max(0);
    let mut progress = int(&entity.nbt, PROGRESS).max(0);
    if entity.id == GENERATOR {
        if !flag(&entity.nbt, "oritech.redstone") {
            if progress == 0 && energy <= 50_000 - 32 {
                if let Some(fuel) = entity.items[0].as_ref() {
                    // Original rejects BucketItem before consulting the fuel registry.
                    // The first port explicitly excludes all vanilla bucket IDs.
                    let bucket =
                        fuel.item.as_ref() == "minecraft:bucket" || fuel.item.ends_with("_bucket");
                    let burn = if bucket {
                        0
                    } else {
                        game.res
                            .providers()
                            .burn_time(game.res.items(), fuel, false)
                    };
                    if burn > 0 {
                        shrink(&mut entity.items[0]);
                        progress = burn;
                        put(&mut entity.nbt, "storedBurn", burn);
                    }
                }
            }
            if progress > 0 && energy <= 50_000 - 32 {
                progress -= 1;
                energy += 32;
            }
            for direction in Direction::ALL {
                let delta = direction.normal();
                let neighbor = std::array::from_fn(|i| pos[i].saturating_add(delta[i]));
                let target = controller(game, neighbor).unwrap_or(neighbor);
                let face = if direction == Direction::Down {
                    Direction::Down
                } else {
                    direction.opposite()
                };
                // Original maxExtract is a limit per API call, not per tick.
                energy -= game.native_energy_insert(target, face, energy.min(256), false);
            }
        }
    } else {
        let valid = controller(game, above(pos)) == Some(pos);
        if flag(&entity.nbt, ASSEMBLED) && !valid {
            entity.nbt.insert(ASSEMBLED.into(), Tag::Byte(0));
        }
        if flag(&entity.nbt, ASSEMBLED) {
            let recipe = entity.items[0]
                .as_ref()
                .and_then(|input| game.res.recipes().cook("minecraft:smelting", input))
                .cloned();
            let recipe = recipe.filter(|r| {
                entity.items[1].as_ref().is_none_or(|out| {
                    // Original compares item ID here, retaining the existing output's components.
                    out.item == r.result.item
                        && out.count.saturating_add(r.result.count) <= max_stack(game, out)
                })
            });
            if let Some(recipe) = recipe {
                if energy >= 32 {
                    energy -= 32;
                    progress += 1;
                    if progress as f64 >= recipe.time as f64 * 0.5 {
                        shrink(&mut entity.items[0]);
                        if let Some(out) = &mut entity.items[1] {
                            out.count += recipe.result.count;
                        } else {
                            entity.items[1] = Some(recipe.result);
                        }
                        progress = 0;
                    }
                }
            } else {
                progress = 0;
            }
        }
    }
    put(&mut entity.nbt, "energy", energy);
    put(&mut entity.nbt, PROGRESS, progress);
    update(entity);
}

pub(super) fn interact(
    game: &mut Game<'_>,
    hit: Option<&crate::game::Hit>,
) -> std::ops::ControlFlow<horizon_client_lib::Result<bool>> {
    let Some(hit) = hit else {
        return std::ops::ControlFlow::Continue(());
    };
    let id = game.native_block(hit.pos);
    if !machine(&id)
        || game.held().is_some()
        || game.hand != horizon_client_lib::first_person::Hand::Main
        || (game.keys.held(crate::game::Mapping::Sneak) && game.offhand.is_some())
    {
        return std::ops::ControlFlow::Continue(());
    }
    let mut canceled = false;
    game.native_right_click_block(hit.pos, hit.face, &mut canceled);
    game.native_right_click_block_v2(hit.pos, hit.face, game.hand, &mut canceled);
    game.use_failed = canceled;
    if !canceled {
        let containers = game.native_containers();
        game.world.block_entities.set_mod_containers(containers);
        let was_assembled = id != FURNACE
            || game
                .native_with_mod_block_entity(hit.pos, |entity| flag(&entity.nbt, ASSEMBLED))
                .unwrap_or(false);
        let assembled = id != FURNACE || assemble(game, hit.pos);
        // Original consumes the first successful assembly click without a menu.
        if assembled && was_assembled {
            game.native_with_mod_block_entity(hit.pos, |entity| update(entity));
            game.open_menu(hit.pos);
        }
        game.swing_arm();
    }
    std::ops::ControlFlow::Break(Ok(true))
}
