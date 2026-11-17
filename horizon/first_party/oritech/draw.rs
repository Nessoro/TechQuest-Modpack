fn draw(
    game: &crate::game::Game<'_>,
    block: &str,
    data: &[i32],
    batch: &mut crate::hud::HudBatch,
    origin: [f32; 2],
) {
    if !crate::game::techquest_oritech::machine(block) {
        return;
    }
    let [x, y] = origin;
    let energy = u32::from(data.first().copied().unwrap_or(0) as u16)
        | (u32::from(data.get(1).copied().unwrap_or(0) as u16) << 16);
    game.native_text(
        batch,
        &format!("Energy: {energy}"),
        [x + 8.0, y + 49.0],
        0x404040,
        false,
    );
    let progress = data.get(2).copied().unwrap_or(0);
    game.native_text(
        batch,
        &format!(
            "{}: {progress}",
            if block == "oritech:basic_generator_block" {
                "Burn"
            } else {
                "Progress"
            }
        ),
        [x + 8.0, y + 61.0],
        0x404040,
        false,
    );
}
