fn clone_item(block: &str, stack: &mut Option<horizon_client_lib::items::ItemStack>) {
    if block == "oritech:energy_pipe_connection" && stack.is_none() {
        *stack = Some(horizon_client_lib::items::ItemStack::new(
            "oritech:energy_pipe",
            1,
        ));
    }
}
