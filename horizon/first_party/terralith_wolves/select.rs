// Pinned Terralith 2.6.2 selects the existing nine vanilla variants through
// c:has_wolf_variant/* tags. No membership means the vanilla path still runs,
// preserving a game without Terralith. The supported source's unmatched biomes
// must resolve to pale on that path; the registry probe checks this separately.
fn source_biome_tags(biome: &str, has_tag: &dyn Fn(&str) -> bool) -> std::ops::ControlFlow<u8> {
    if let Some(variant) = crate::techquest_terralith_wolf_context::take(biome) {
        return std::ops::ControlFlow::Break(variant);
    }
    // Observed 1.21.1 datapack registry order, distinct from bootstrap order.
    // Values are the pinned native WOLF_VARIANTS indices, not loop positions.
    for (variant, tag) in [
        (4, "c:has_wolf_variant/ashen"),
        (3, "c:has_wolf_variant/black"),
        (7, "c:has_wolf_variant/chestnut"),
        (0, "c:has_wolf_variant/pale"),
        (5, "c:has_wolf_variant/rusty"),
        (2, "c:has_wolf_variant/snowy"),
        (1, "c:has_wolf_variant/spotted"),
        (8, "c:has_wolf_variant/striped"),
        (6, "c:has_wolf_variant/woods"),
    ] {
        if has_tag(tag) {
            return std::ops::ControlFlow::Break(variant);
        }
    }
    std::ops::ControlFlow::Continue(())
}
