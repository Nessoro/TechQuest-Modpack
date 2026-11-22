fn replace_foundry_core(
    game: &mut crate::game::Game<'_>,
    pos: [i32; 3],
    state: horizon_world::registry::BlockStateId,
) {
    if game.native_state_block(state) != Some(game.native_block(pos).as_str()) {
        crate::game::techquest_oritech::release_at(&mut game.world.block_entities, pos);
    }
}
