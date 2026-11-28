fn ticking(block: &str, ticks: &mut bool) {
    if crate::game::techquest_oritech::machine(block) || block == "oritech:energy_pipe_connection" {
        *ticks = true;
    }
}
