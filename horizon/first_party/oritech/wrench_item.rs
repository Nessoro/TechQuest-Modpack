fn wrench_item(
    game: &mut crate::game::Game<'_>,
    stack: &horizon_client_lib::items::ItemStack,
    claimed: &mut bool,
) {
    crate::game::techquest_oritech_wrench::item_use(game, stack, claimed);
}
