fn declare_energy(
    block: &str,
    value: &mut Option<horizon_client_lib::containers::ModEnergyBuffer>,
) {
    if crate::game::techquest_oritech::machine(block) && value.is_none() {
        let generator = block == "oritech:basic_generator_block";
        *value = Some(horizon_client_lib::containers::ModEnergyBuffer {
            capacity: match block {
                "oritech:basic_generator_block"
                | "oritech:foundry_block"
                | "oritech:assembler_block" => 50_000,
                "oritech:pulverizer_block" => 25_000,
                _ => 10_000,
            },
            max_insert: if generator {
                0
            } else if matches!(block, "oritech:foundry_block" | "oritech:assembler_block") {
                1024
            } else {
                256
            },
            max_extract: if generator { 256 } else { 0 },
            insert_faces: [!generator; 6],
            extract_faces: [generator; 6],
        });
    }
}
