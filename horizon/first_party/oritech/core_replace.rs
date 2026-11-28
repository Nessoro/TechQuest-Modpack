fn replace_foundry_core(
    game: &mut crate::game::Game<'_>,
    pos: [i32; 3],
    state: horizon_world::registry::BlockStateId,
) {
    if game.native_state_block(state) != Some(game.native_block(pos).as_str()) {
        crate::game::techquest_oritech::release_at(&mut game.world.block_entities, pos);
        for (key, entity) in game.world.block_entities.iter() {
            if matches!(entity, horizon_client_lib::containers::BlockEntity::Mod(e) if e.id == "oritech:machine_core_1")
            {
                crate::game::techquest_oritech_cables::mark(
                    game.dim.id(),
                    [key.0, key.1, key.2],
                    0,
                );
            }
        }
    }
}
