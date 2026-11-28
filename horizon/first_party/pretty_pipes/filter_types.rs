fn register_types(types: &mut Vec<String>) {
    for name in [
        "prettypipes:item_filter_data",
        "prettypipes:direction_selector_data",
    ] {
        if !types.iter().any(|s| s == name) {
            types.push(name.into());
        }
    }
}
