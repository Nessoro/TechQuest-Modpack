fn tick(
    game: &mut crate::game::Game<'_>,
    pos: [i32; 3],
    entity: &mut horizon_client_lib::containers::ModBlockEntity,
) {
    if crate::game::techquest_oritech::machine(&entity.id) {
        crate::game::techquest_oritech::tick(game, pos, entity);
    }
}
