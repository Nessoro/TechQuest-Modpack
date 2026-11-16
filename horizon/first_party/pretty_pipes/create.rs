fn create(block: &str, entity: &mut Option<(String, horizon_world::nbt::Compound)>) {
    if block == "prettypipes:pipe" && entity.is_none() {
        *entity = Some((
            block.into(),
            [(
                "techquest_inventory_schema".into(),
                horizon_world::nbt::Tag::Int(3),
            )]
            .into(),
        ));
    }
}
