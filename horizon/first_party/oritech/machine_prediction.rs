// Original MachineBlock block-before-item result: Rearth, CC0-1.0.
// Pinned Horizon remote prediction boundary: MIT; retained license files.
fn predict_machine_use(
    game: &crate::game::Game<'_>,
    hit: &crate::game::Hit,
) -> std::ops::ControlFlow<(InteractionResult, DryUse)> {
    let hands_full = game.stack_in(game.selected).is_some() || game.offhand.is_some();
    if crate::game::techquest_oritech::machine(&game.native_block(hit.pos))
        && !(game.remote_shift_down() && hands_full)
    {
        // The server consumes even an unsuccessful assembly click. Predict
        // only the result: no inventory, energy or assembly mutations here.
        // This prevents an extra UseItem packet after the menu's UseItemOn.
        std::ops::ControlFlow::Break((
            horizon_world::level::InteractionResult::Success,
            DryUse::default(),
        ))
    } else {
        std::ops::ControlFlow::Continue(())
    }
}
