fn replace_pipe_contents(
    game: &mut crate::game::Game<'_>,
    pos: [i32; 3],
    state: horizon_world::registry::BlockStateId,
) {
    crate::game::techquest_pretty_pipes::replace_contents(game, pos, state);
}
