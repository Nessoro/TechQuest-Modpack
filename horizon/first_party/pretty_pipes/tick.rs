fn tick(
    game: &mut crate::game::Game<'_>,
    pos: [i32; 3],
    entity: &mut horizon_client_lib::containers::ModBlockEntity,
) {
    if entity.id == "prettypipes:pipe" {
        crate::game::techquest_pretty_pipes::tick(game, pos, entity);
    }
}
