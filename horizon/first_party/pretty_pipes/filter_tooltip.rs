fn tooltip(
    game: &crate::game::Game<'_>,
    block: &str,
    data: &[i32],
    at: [f32; 2],
    lines: &mut Vec<String>,
) {
    crate::game::techquest_pretty_pipes_ui::tooltip(game, block, data, at, lines);
}
