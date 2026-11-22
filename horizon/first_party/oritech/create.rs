fn create(block: &str, entity: &mut Option<(String, horizon_world::nbt::Compound)>) {
    if block == "oritech:energy_pipe_connection" && entity.is_none() {
        *entity = Some((
            block.into(),
            [("energy".into(), horizon_world::nbt::Tag::Int(0))].into(),
        ));
        return;
    }
    if matches!(
        block,
        "oritech:basic_generator_block"
            | "oritech:powered_furnace_block"
            | "oritech:pulverizer_block"
            | "oritech:foundry_block"
            | "oritech:assembler_block"
            | "oritech:machine_core_1"
    ) && entity.is_none()
    {
        *entity = Some((
            block.into(),
            [
                ("energy".into(), horizon_world::nbt::Tag::Int(0)),
                (
                    "oritech.machine_progress".into(),
                    horizon_world::nbt::Tag::Int(0),
                ),
                ("storedBurn".into(), horizon_world::nbt::Tag::Int(0)),
                (
                    "techquest_assembled".into(),
                    horizon_world::nbt::Tag::Byte(0),
                ),
                (
                    "techquest_core_used".into(),
                    horizon_world::nbt::Tag::Byte(0),
                ),
            ]
            .into(),
        ));
    }
}
