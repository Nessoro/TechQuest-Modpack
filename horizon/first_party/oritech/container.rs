fn declare_slots(block: &str, value: &mut Option<horizon_client_lib::containers::ModContainer>) {
    if crate::game::techquest_oritech::machine(block) && value.is_none() {
        let slots = match block {
            "oritech:basic_generator_block" => 1,
            "oritech:pulverizer_block" | "oritech:foundry_block" => 3,
            "oritech:assembler_block" => 5,
            _ => 2,
        };
        *value = Some(horizon_client_lib::containers::ModContainer {
            slots,
            faces: std::array::from_fn(|_| (0..slots).collect()),
            inputs: if block == "oritech:assembler_block" {
                vec![0, 1, 2, 3]
            } else if block == "oritech:foundry_block" {
                vec![0, 1]
            } else {
                vec![0]
            },
            outputs: (if block == "oritech:assembler_block" {
                4
            } else if block == "oritech:foundry_block" {
                2
            } else {
                1
            }..slots)
                .collect(),
            menu: Some(block.into()),
        });
    }
}
