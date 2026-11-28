// Biome-context lookup adapted from Horizon c78187d, game/creatures.rs (MIT).
// Copyright (c) 2026 Ludovic Marie and the Horizon contributors
// See LICENSE-HORIZON. Prime only wolf selection from cached world tags;
// the original biome_facts body runs unchanged after this HEAD hook.
fn world_biome_tags(game: &crate::game::Game<'_>, x: i32, y: i32, z: i32) {
    use horizon_client::techquest_terralith_wolf_context as context;
    context::clear();
    let Some(tags) = game.world_tables.as_ref()
        .and_then(|tables| tables.pack_tags.get("worldgen/biome")) else { return; };
    if !tags.contains_key("c:has_wolf_variant/pale") { return; }
    let Some(chunk) = game.world.chunks.get(&(x >> 4, z >> 4)) else {
        return;
    };
    let b = world_biomes!(game).get(chunk.biome(x, y, z));
    let has = |tag: &str| tags.get(tag).is_some_and(|members| members.contains(&b.name));
    let any = ["pale", "spotted", "snowy", "black", "ashen", "rusty", "woods", "chestnut", "striped"]
        .iter().any(|name| has(&format!("c:has_wolf_variant/{name}")));
    let wolf = if any { horizon_client::mobs::tame::wolf_variant_for(&b.name, &has) } else { 0 };
    context::stage(&b.name, wolf);
}
