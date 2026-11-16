fn module_screen(block: &str, screen: &mut Option<crate::mod_api::NativeScreen>) {
    if block == "prettypipes:pipe" && screen.is_none() {
        let mut slots = vec![None; 67];
        for (i, slot) in slots.iter_mut().take(3).enumerate() {
            *slot = Some([62.0 + i as f32 * 18.0, 49.0]);
        }
        *screen = Some(crate::mod_api::NativeScreen {
            width: 176.0,
            height: 203.0,
            slots,
            inventory_y: 121.0,
            inventory_x: 8.0,
            own_labels: false,
            own_background: false,
        });
    }
}
