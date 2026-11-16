// Pretty Pipes onRemove drops modules and queue for replacement and creative
// too. MIT semantics: Copyright (c) 2020-2021 Ellpeck, LICENSE-PRETTY-PIPES.
fn spill_pipe_contents(
    level: &mut crate::game::GameLevel<'_>,
    pos: horizon_core::position::BlockPos,
) {
    let key = (pos.x, pos.y, pos.z);
    let Some(horizon_client_lib::containers::BlockEntity::Mod(entity)) =
        level.world.block_entities.get_mut(&key)
    else {
        return;
    };
    if entity.id != "prettypipes:pipe" {
        return;
    }
    // Take ownership before the engine's usual container removal, so that a
    // destructive break cannot drop the in-flight queue a second time.
    let fields: &mut horizon_client_lib::containers::ModBlockEntityFields = entity;
    let Some(contents) = horizon_client_lib::techquest_pretty_pipes_modules::take_inventory(
        &mut fields.nbt,
        &mut fields.items,
    ) else {
        return;
    };
    for stack in contents.into_iter().flatten() {
        level.drop_item_stack(pos, Some(stack));
    }
}
