fn machine_screen(block: &str, screen: &mut Option<crate::mod_api::NativeScreen>) {
    if crate::game::techquest_oritech::machine(block) && screen.is_none() {
        let slots = if block == "oritech:basic_generator_block" {
            vec![Some([80.0, 25.0])]
        } else if block == "oritech:foundry_block" {
            vec![Some([38.0, 25.0]), Some([64.0, 25.0]), Some([117.0, 25.0])]
        } else if block == "oritech:pulverizer_block" {
            vec![Some([56.0, 25.0]), Some([116.0, 25.0]), Some([136.0, 25.0])]
        } else {
            vec![Some([56.0, 25.0]), Some([116.0, 25.0])]
        };
        *screen = Some(crate::mod_api::NativeScreen {
            width: 176.0,
            height: 166.0,
            slots,
            inventory_y: 84.0,
            inventory_x: 8.0,
            own_labels: false,
            own_background: false,
        });
    }
}
