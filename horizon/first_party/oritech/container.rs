fn declare_slots(block: &str, value: &mut Option<horizon_client_lib::containers::ModContainer>) {
    if crate::game::techquest_oritech::machine(block) && value.is_none() {
        let slots = if block == "oritech:basic_generator_block" {
            1
        } else {
            2
        };
        *value = Some(horizon_client_lib::containers::ModContainer {
            slots,
            faces: std::array::from_fn(|_| (0..slots).collect()),
            inputs: vec![0],
            outputs: if slots == 2 { vec![1] } else { vec![] },
            menu: Some(block.into()),
        });
    }
}
