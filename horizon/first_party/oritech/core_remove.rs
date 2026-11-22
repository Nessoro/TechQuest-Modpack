// Core/controller lifecycle: Rearth, CC0-1.0; LICENSE-ORITECH.
fn release_foundry_cores(
    level: &mut crate::game::GameLevel<'_>,
    pos: horizon_core::position::BlockPos,
) {
    crate::game::techquest_oritech::release_at(
        &mut level.world.block_entities,
        [pos.x, pos.y, pos.z],
    );
    for (key, entity) in level.world.block_entities.iter() {
        if matches!(entity, horizon_client_lib::containers::BlockEntity::Mod(e) if e.id == "oritech:machine_core_1")
        {
            crate::game::techquest_oritech_cables::mark(
                level.dimension.key().id(),
                [key.0, key.1, key.2],
                0,
            );
        }
    }
}
