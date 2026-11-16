// Use ordering follows Horizon's MIT Game::use_hand; see LICENSE-HORIZON.
fn interact_pipe(
    game: &mut crate::game::Game<'_>,
    hit: Option<&crate::game::Hit>,
) -> std::ops::ControlFlow<Result<bool>> {
    crate::game::techquest_pretty_pipes::interact(game, hit)
}
