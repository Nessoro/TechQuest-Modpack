// Oritech 1.2.13 selected machine semantics: Rearth, CC0-1.0.
// Source pin and scope: README.md; dedication retained in LICENSE-ORITECH.
// Horizon integration adapts MIT Game::use_hand and native energy helpers;
// Copyright (c) 2026 Ludovic Marie and Horizon contributors. LICENSE-HORIZON.
use super::Game;
use horizon_client_lib::{containers::ModBlockEntity, items::ItemStack};
use horizon_core::geometry::Direction;
use horizon_world::nbt::{Compound, Tag};

pub(super) const GENERATOR: &str = "oritech:basic_generator_block";
pub(super) const FURNACE: &str = "oritech:powered_furnace_block";
pub(super) const PULVERIZER: &str = "oritech:pulverizer_block";
pub(super) const FOUNDRY: &str = "oritech:foundry_block";
pub(super) const ASSEMBLER: &str = "oritech:assembler_block";
pub(super) const CORE: &str = "oritech:machine_core_1";
const PROGRESS: &str = "oritech.machine_progress";
const ASSEMBLED: &str = "techquest_assembled";

pub(super) fn machine(id: &str) -> bool {
    matches!(id, GENERATOR | FURNACE | PULVERIZER | FOUNDRY | ASSEMBLER)
}
fn multiblock(id: &str) -> bool {
    matches!(id, FOUNDRY | ASSEMBLER)
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
pub(super) fn controller(game: &Game<'_>, pos: [i32; 3]) -> Option<[i32; 3]> {
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
    ((above(p) == pos && game.native_block(p) == FURNACE)
        || (multiblock(&game.native_block(p)) && multiblock_cores(game, p).contains(&pos)))
    .then_some(p)
}
pub(super) fn assemble(game: &mut Game<'_>, pos: [i32; 3]) -> bool {
    if multiblock(&game.native_block(pos)) {
        return assemble_multiblock(game, pos);
    }
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
/// CC0 Geometry.rotatePosition; Foundry and Assembler use the same three cores.
pub(super) fn multiblock_cores(game: &Game<'_>, pos: [i32; 3]) -> [[i32; 3]; 3] {
    let facing = game
        .native_block_property(pos, "facing")
        .unwrap_or_else(|| "north".into());
    let side = match facing.as_str() {
        "east" => [0, 0, 1],
        "south" => [-1, 0, 0],
        "west" => [0, 0, -1],
        _ => [1, 0, 0],
    };
    [
        std::array::from_fn(|i| pos[i].saturating_add(side[i])),
        above(pos),
        std::array::from_fn(|i| above(pos)[i].saturating_add(side[i])),
    ]
}
fn valid_multiblock(game: &Game<'_>, pos: [i32; 3]) -> bool {
    multiblock_cores(game, pos)
        .iter()
        .all(|p| controller(game, *p) == Some(pos))
}
fn multiblock_loaded(game: &Game<'_>, pos: [i32; 3]) -> bool {
    // An absent neighbour chunk reads as air. On startup the controller may
    // tick before its cores load; that is not a physical core destruction.
    // Streaming installs a chunk's block entities before publishing the chunk.
    multiblock_cores(game, pos)
        .iter()
        .all(|p| game.world.chunks.contains_key(&(p[0] >> 4, p[2] >> 4)))
}
fn assemble_multiblock(game: &mut Game<'_>, pos: [i32; 3]) -> bool {
    let core_positions = multiblock_cores(game, pos);
    let active = game.world.block_entities.get(&(pos[0],pos[1],pos[2])).is_some_and(|e|
        matches!(e,horizon_client_lib::containers::BlockEntity::Mod(e) if flag(&e.nbt, ASSEMBLED)));
    if active {
        return valid_multiblock(game, pos);
    }
    if !core_positions.iter().all(|p| game.native_block(*p) == CORE && game.world.block_entities.get(&(p[0],p[1],p[2])).is_some_and(|e|
        matches!(e,horizon_client_lib::containers::BlockEntity::Mod(e) if !flag(&e.nbt,"techquest_core_used")))) { return false; }
    for p in core_positions {
        let linked = game.native_with_mod_block_entity(p, |core| {
            core.nbt.insert("techquest_core_used".into(), Tag::Byte(1));
            for (i, key) in ["controller_x", "controller_y", "controller_z"]
                .iter()
                .enumerate()
            {
                put(&mut core.nbt, key, pos[i] - p[i]);
            }
        });
        if linked.is_none() {
            return false;
        }
    }
    game.native_with_mod_block_entity(pos, |entity| {
        entity.nbt.insert(ASSEMBLED.into(), Tag::Byte(1))
    })
    .is_some()
}

fn linked_to(nbt: &Compound, pos: [i32; 3]) -> [i32; 3] {
    std::array::from_fn(|i| {
        pos[i].saturating_add(int(
            nbt,
            ["controller_x", "controller_y", "controller_z"][i],
        ))
    })
}
pub(super) fn release_controller(
    entities: &mut horizon_client_lib::block_entities::BlockEntities,
    controller: [i32; 3],
) {
    for (key, value) in entities.iter_mut() {
        let horizon_client_lib::containers::BlockEntity::Mod(entity) = value else {
            continue;
        };
        let pos = [key.0, key.1, key.2];
        if entity.id == CORE
            && flag(&entity.nbt, "techquest_core_used")
            && linked_to(&entity.nbt, pos) == controller
        {
            entity
                .nbt
                .insert("techquest_core_used".into(), Tag::Byte(0));
        }
        if multiblock(&entity.id) && pos == controller {
            entity.nbt.insert(ASSEMBLED.into(), Tag::Byte(0));
            if let Some(assembled) = entity.data.get_mut(3) {
                *assembled = 0;
            }
        }
    }
}
pub(super) fn release_at(
    entities: &mut horizon_client_lib::block_entities::BlockEntities,
    pos: [i32; 3],
) {
    let target = match entities.get(&(pos[0], pos[1], pos[2])) {
        Some(horizon_client_lib::containers::BlockEntity::Mod(entity))
            if multiblock(&entity.id) =>
        {
            pos
        }
        Some(horizon_client_lib::containers::BlockEntity::Mod(entity))
            if entity.id == CORE && flag(&entity.nbt, "techquest_core_used") =>
        {
            linked_to(&entity.nbt, pos)
        }
        _ => return,
    };
    if !matches!(entities.get(&(target[0],target[1],target[2])),Some(horizon_client_lib::containers::BlockEntity::Mod(entity)) if multiblock(&entity.id))
    {
        return;
    }
    release_controller(entities, target);
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
    // data slots are not saved by Horizon. The pulverizer uses the last
    // otherwise-unused field to identify a freshly loaded recipe cache.
    let state = if matches!(&*entity.id, PULVERIZER | FOUNDRY | ASSEMBLER) {
        entity.data.get(4).copied().unwrap_or(0)
    } else {
        i32::from(flag(&entity.nbt, ASSEMBLED))
    };
    entity.data = vec![
        energy & 0xffff,
        (energy >> 16) & 0xffff,
        int(&entity.nbt, PROGRESS),
        if multiblock(&entity.id) {
            i32::from(flag(&entity.nbt, ASSEMBLED))
        } else {
            int(&entity.nbt, "storedBurn")
        },
        state,
    ];
}
pub(super) fn tick(game: &mut Game<'_>, pos: [i32; 3], entity: &mut ModBlockEntity) {
    if matches!(&*entity.id, PULVERIZER | FOUNDRY | ASSEMBLER) {
        if multiblock(&entity.id) && !multiblock_loaded(game, pos) {
            // Retain assembly, links and progress until validation can read
            // the actual neighbouring blocks. Do not process against air.
            update(entity);
            return;
        }
        if multiblock(&entity.id) && flag(&entity.nbt, ASSEMBLED) && !valid_multiblock(game, pos) {
            release_controller(&mut game.world.block_entities, pos);
            entity.nbt.insert(ASSEMBLED.into(), Tag::Byte(0));
        }
        tick_processing(game, entity);
        return;
    }
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

const PULVERIZER_CACHE: &str = "techquest_pulverizer_recipe";

fn processing_matches(
    game: &Game<'_>,
    recipe: &serde_json::Value,
    inputs: &[Option<ItemStack>],
) -> bool {
    let Some(ingredients) = recipe["ingredients"]
        .as_array()
        .filter(|v| v.len() == inputs.len())
    else {
        return false;
    };
    // Original complexMatch greedily consumes copied stacks. Ingredient count
    // is one per occurrence, including repeated ingredients in a shared stack;
    // matching does not require a particular slot order.
    let mut copied = inputs.to_vec();
    for value in ingredients {
        let Some(ingredient) = game.native_recipe_ingredient(value) else {
            return false;
        };
        let Some(slot) = copied.iter_mut().find(|s| {
            s.as_ref()
                .is_some_and(|s| s.count > 0 && ingredient.test(s))
        }) else {
            return false;
        };
        shrink(slot);
    }
    true
}

fn consume_processing_inputs(
    game: &Game<'_>,
    recipe: &serde_json::Value,
    inputs: &mut [Option<ItemStack>],
) {
    let mut offset = 0;
    for value in recipe["ingredients"].as_array().unwrap() {
        let ingredient = game.native_recipe_ingredient(value).unwrap();
        for i in 0..inputs.len() {
            let index = (i + offset) % inputs.len();
            if inputs[index]
                .as_ref()
                .is_some_and(|s| s.count > 0 && ingredient.test(s))
            {
                shrink(&mut inputs[index]);
                offset += 1;
                break;
            }
        }
    }
}

fn tick_processing(game: &Game<'_>, entity: &mut ModBlockEntity) {
    let foundry = entity.id == FOUNDRY;
    let assembler = entity.id == ASSEMBLER;
    let input_count = if assembler {
        4
    } else if foundry {
        2
    } else {
        1
    };
    let slots = if assembler { 5 } else { 3 };
    let energy_cost = if foundry || assembler { 128 } else { 32 };
    let cache_key = if assembler {
        "techquest_assembler_recipe"
    } else if foundry {
        "techquest_foundry_recipe"
    } else {
        PULVERIZER_CACHE
    };
    let recipe_type = if assembler {
        "oritech:assembler"
    } else if foundry {
        "oritech:foundry"
    } else {
        "oritech:pulverizer"
    };
    entity.items.resize(slots, None);
    if entity.data.get(4) != Some(&1) {
        // The original currentRecipe is transient: a loaded machine forgets
        // it, even though progress itself was saved. Keep that observed reset
        // behavior without global entity maps or native pointer identities.
        entity.nbt.remove(&cache_key.into());
        entity.data.resize(5, 0);
        entity.data[4] = 1;
    }
    if flag(&entity.nbt, "oritech.redstone")
        || ((foundry || assembler) && !flag(&entity.nbt, ASSEMBLED))
    {
        update(entity);
        return;
    }
    let mut progress = int(&entity.nbt, PROGRESS);
    let mut energy = int(&entity.nbt, "energy").max(0);
    let cached = entity.nbt.get(&cache_key.into()).and_then(|value| {
        if let Tag::String(text) = value {
            text.to_string()
                .ok()
                .and_then(|text| serde_json::from_str::<serde_json::Value>(&text).ok())
        } else {
            None
        }
    });
    let is_cached = cached
        .as_ref()
        .is_some_and(|value| processing_matches(game, value, &entity.items[..input_count]));
    let recipe = if is_cached {
        cached
    } else {
        game.native_recipes_of_type(recipe_type)
            .iter()
            .find(|recipe| processing_matches(game, &recipe.json, &entity.items[..input_count]))
            .map(|recipe| (*recipe.json).clone())
    };
    if let Some(recipe) = recipe {
        let results = recipe["results"].as_array().and_then(|values| {
            if !(1..=slots - input_count).contains(&values.len()) {
                return None;
            }
            values
                .iter()
                .map(|value| game.native_recipe_result(value))
                .collect::<Option<Vec<_>>>()
        });
        let duration = recipe["time"]
            .as_i64()
            .filter(|n| *n > 0 && *n <= i32::MAX as i64);
        let results = results.filter(|results| {
            results.iter().enumerate().all(|(i, result)| {
                entity.items[i + input_count]
                    .as_ref()
                    .is_none_or(|current| {
                        current.item == result.item
                            && current.count.saturating_add(result.count)
                                <= max_stack(game, current)
                    })
            })
        });
        if let (Some(results), Some(duration)) = (results, duration) {
            if !is_cached {
                progress = 0;
            }
            if energy >= energy_cost {
                energy -= energy_cost;
                progress += 1;
                if !is_cached {
                    // The source keeps a matching cached recipe over /reload.
                    // Persisted bytes are ignored on the first load tick above;
                    // no client-visible pointer or unbounded global cache is used.
                    if let Ok(text) = serde_json::to_string(&recipe) {
                        entity
                            .nbt
                            .insert(cache_key.into(), Tag::String(text.as_str().into()));
                    }
                }
                if i64::from(progress) >= duration {
                    consume_processing_inputs(game, &recipe, &mut entity.items[..input_count]);
                    for (i, result) in results.into_iter().enumerate() {
                        if let Some(current) = &mut entity.items[i + input_count] {
                            current.count += result.count;
                        } else {
                            entity.items[i + input_count] = Some(result);
                        }
                    }
                    // Selected recipes have no secondary small-dust compaction
                    // or random result processing.
                    progress = 0;
                }
            }
        } else {
            progress = 0;
        }
    } else {
        entity.nbt.remove(&cache_key.into());
        progress = 0;
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
        let was_assembled = !matches!(&*id, FURNACE | FOUNDRY | ASSEMBLER)
            || game
                .native_with_mod_block_entity(hit.pos, |entity| flag(&entity.nbt, ASSEMBLED))
                .unwrap_or(false);
        let assembled = !matches!(&*id, FURNACE | FOUNDRY | ASSEMBLER) || assemble(game, hit.pos);
        if assembled && !was_assembled {
            super::techquest_oritech_cables::assembled(game, hit.pos);
        }
        // Original consumes the first successful assembly click without a menu.
        if assembled && was_assembled {
            game.native_with_mod_block_entity(hit.pos, |entity| update(entity));
            game.open_menu(hit.pos);
        }
        game.swing_arm();
    }
    std::ops::ControlFlow::Break(Ok(true))
}
