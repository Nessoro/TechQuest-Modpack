fn wrench_interact(
    game: &mut crate::game::Game<'_>,
    hit: Option<&crate::game::Hit>,
) -> std::ops::ControlFlow<Result<bool>> {
    crate::game::techquest_oritech_wrench::interact(game, hit)
}
