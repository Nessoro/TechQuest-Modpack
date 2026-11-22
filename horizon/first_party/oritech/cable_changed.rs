fn changed(
    level: &crate::game::GameLevel<'_>,
    pos: horizon_core::position::BlockPos,
    old: horizon_world::registry::BlockStateId,
    new: horizon_world::registry::BlockStateId,
) {
    crate::game::techquest_oritech_cables::changed(level, [pos.x, pos.y, pos.z], old, new);
}
