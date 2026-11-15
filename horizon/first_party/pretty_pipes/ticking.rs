fn ticking(block: &str, ticks: &mut bool) {
    if block == "prettypipes:pipe" {
        *ticks = true;
    }
}
