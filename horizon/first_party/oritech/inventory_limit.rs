// Inventory.add component limit observed through original Oritech tank items.
// Horizon integration: MIT; LICENSE-HORIZON. No dependency Java bodies read.
fn component_inventory_limit(
    inventory: &mut [Option<horizon_client_lib::items::ItemStack>],
    offhand: &mut Option<horizon_client_lib::items::ItemStack>,
    selected: usize,
    maximum: u32,
    stack: &mut horizon_client_lib::items::ItemStack,
) -> std::ops::ControlFlow<bool> {
    let patched = stack.data().and_then(|data| {
        if data.other("!minecraft:max_stack_size").is_some() {
            return None;
        }
        match data.other("minecraft:max_stack_size") {
            Some(horizon_world::nbt::Tag::Int(n)) if (1..=99).contains(n) => Some(*n as u32),
            _ => None,
        }
    });
    if let Some(limit) = patched.filter(|&limit| limit != maximum) {
        // Re-enter the original algorithm once with the effective component
        // limit. Equality ends recursion, retaining slot order and overflow.
        std::ops::ControlFlow::Break(crate::game::inventory_add(
            inventory, offhand, selected, limit, stack,
        ))
    } else {
        std::ops::ControlFlow::Continue(())
    }
}
