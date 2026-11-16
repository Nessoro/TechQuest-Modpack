fn open_modules(
    game: &mut crate::game::Game<'_>,
    key: (i32, i32, i32),
) -> std::ops::ControlFlow<bool> {
    let pos = [key.0, key.1, key.2];
    if game.native_block(pos) == "prettypipes:pipe"
        && !crate::game::techquest_pretty_pipes::allow_open(game, pos)
    {
        return std::ops::ControlFlow::Break(false);
    }
    std::ops::ControlFlow::Continue(())
}
