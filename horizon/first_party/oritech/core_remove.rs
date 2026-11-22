// Core/controller lifecycle: Rearth, CC0-1.0; LICENSE-ORITECH.
fn release_foundry_cores(
    level: &mut crate::game::GameLevel<'_>,
    pos: horizon_core::position::BlockPos,
) {
    crate::game::techquest_oritech::release_at(
        &mut level.world.block_entities,
        [pos.x, pos.y, pos.z],
    );
}
