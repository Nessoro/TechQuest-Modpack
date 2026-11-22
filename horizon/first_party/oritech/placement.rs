// MachineBlock.getStateForPlacement: Rearth, CC0-1.0; LICENSE-ORITECH.
fn foundry_placement(
    game: &crate::game::GameLevel<'_>,
    state: horizon_world::registry::BlockStateId,
    context: &horizon_world::level::PlacementContext,
    answer: &mut Option<Option<horizon_world::registry::BlockStateId>>,
) {
    if answer.is_some() || game.native_state_block(state) != Some("oritech:foundry_block") {
        return;
    }
    let index = ((f64::from(context.yaw) / 90.0 + 0.5).floor() as i64).rem_euclid(4) as usize;
    // Opposite of vanilla's South/West/North/East horizontal yaw order.
    let facing = ["north", "east", "south", "west"][index];
    *answer = Some(game.native_state_with_property(state, "facing", facing));
}
