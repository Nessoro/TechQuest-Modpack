fn declare_slots(block: &str, value: &mut Option<horizon_client_lib::containers::ModContainer>) {
    if block == "prettypipes:pipe" && value.is_none() {
        *value = Some(horizon_client_lib::containers::ModContainer {
            slots: 64,
            faces: std::array::from_fn(|_| Vec::new()),
            inputs: Vec::new(),
            outputs: Vec::new(),
            menu: None,
        });
    }
}
