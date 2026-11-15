fn install_from_hand(
    game: &mut crate::game::Game<'_>,
    stack: &horizon_client_lib::items::ItemStack,
    pos: [i32; 3],
    claimed: &mut bool,
) {
    if !*claimed {
        *claimed = crate::game::techquest_pretty_pipes::use_module(game, stack, pos);
    }
}
