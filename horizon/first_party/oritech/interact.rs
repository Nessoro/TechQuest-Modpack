fn interact(
    game: &mut crate::game::Game<'_>,
    hit: Option<&crate::game::Hit>,
) -> std::ops::ControlFlow<Result<bool>> {
    crate::game::techquest_oritech::interact(game, hit)
}
