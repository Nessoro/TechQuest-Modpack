fn tick(
    game: &mut crate::game::Game<'_>,
    pos: [i32; 3],
    entity: &mut horizon_client_lib::containers::ModBlockEntity,
) {
    if entity.id == "oritech:energy_pipe_connection" {
        crate::game::techquest_oritech_cables::tick(game, pos, entity);
        return;
    }
    if crate::game::techquest_oritech::machine(&entity.id) {
        crate::game::techquest_oritech::tick(game, pos, entity);
    }
}
