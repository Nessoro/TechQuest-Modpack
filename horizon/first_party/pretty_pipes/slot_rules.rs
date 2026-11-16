fn module_slot_rules(
    menu: &crate::menu::Menu,
    slot: usize,
    stack: &horizon_items::items::ItemStack,
    mut value: (bool, u32),
) -> (bool, u32) {
    if matches!(menu.kind, crate::menu::Kind::Mod(kind) if kind.id == "prettypipes:pipe") {
        value.0 &= slot < 3
            && crate::techquest_pretty_pipes_modules::menu_accepts(&menu.containers[MAIN], stack);
        value.1 = value.1.min(1);
    }
    value
}
