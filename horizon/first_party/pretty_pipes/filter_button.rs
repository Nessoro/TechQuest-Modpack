fn button(
    game: &mut crate::game::Game<'_>,
    pos: [i32; 3],
    entity: &mut horizon_client_lib::containers::ModBlockEntity,
    id: i32,
    carried: &mut Option<horizon_client_lib::items::ItemStack>,
) {
    crate::game::techquest_pretty_pipes_ui::button(game, pos, entity, id, carried);
}
