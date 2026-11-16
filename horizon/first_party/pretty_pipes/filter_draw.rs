fn draw(
    game: &crate::game::Game<'_>,
    block: &str,
    data: &[i32],
    batch: &mut crate::hud::HudBatch,
    origin: [f32; 2],
) {
    crate::game::techquest_pretty_pipes_ui::draw(game, block, data, batch, origin);
}
