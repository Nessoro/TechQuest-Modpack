// Read-only insertion capacity through the pinned engine's hopper rules.
// Based on Horizon's MIT machines.rs; see LICENSE-HORIZON.
use super::{Game, Kind};
use horizon_client::items::ItemStack;
use horizon_core::geometry::Direction;

/// Support the reviewed vanilla inventories and the two ported Oritech machines.
/// Never simulate by inserting/removing real items: that would fire machine
/// side effects and make failed routes mutate the destination.
pub(in crate::game) fn capacity(
    game: &Game<'_>,
    pos: [i32; 3],
    face: Direction,
    stack: &ItemStack,
) -> Option<u32> {
    let containers = game.containers();
    let view = containers.view((pos[0], pos[1], pos[2]), false)?;
    let vanilla = matches!(
        game.native_block(pos).as_str(),
        "minecraft:chest"
            | "minecraft:trapped_chest"
            | "minecraft:barrel"
            | "minecraft:hopper"
            | "minecraft:furnace"
            | "minecraft:blast_furnace"
            | "minecraft:smoker"
    ) && matches!(view.kind, Kind::Generic | Kind::Hopper | Kind::Furnace);
    let oritech = matches!(
        game.native_block(pos).as_str(),
        "oritech:basic_generator_block" | "oritech:powered_furnace_block"
    ) && view.kind == Kind::Mod;
    if !vanilla && !oritech {
        return None;
    }
    let maximum = containers.max_stack(stack);
    let mut space = 0u32;
    for slot in view.slots_to_add(Some(face)) {
        if !containers.can_place(&view, slot, stack)
            || !game.mod_container_accepts(&view, slot, stack, Some(face))
        {
            continue;
        }
        let available = match containers.get(&view, slot) {
            None => maximum,
            Some(current) if current.same_item_same_components(stack) => {
                maximum.saturating_sub(current.count)
            }
            Some(_) => 0,
        };
        space = space.saturating_add(available);
    }
    Some(space)
}
