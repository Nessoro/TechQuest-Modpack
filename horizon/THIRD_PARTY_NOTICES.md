# Third-party source notices

`first_party/terralith_wolves/world_tags.rs` adapts the biome-context lookup of
`Game::biome_facts` from
[Horizon c78187d](https://github.com/horizon-rust/horizon/blob/c78187dffffb60f31517eadcb87413386e8ce729/crates/horizon-client/src/game/creatures.rs).
Copyright (c) 2026 Ludovic Marie and the Horizon contributors, MIT.
The license is retained in `first_party/terralith_wolves/LICENSE-HORIZON`.
The HEAD hook passes the world's cached wolf selection to a one-shot thread-local
context; the original body and its other calculations are retained. Two HEAD
hooks are used because the pinned horizon-mixins refuses body rewrites over
the original closure and `world_biomes!` macro.
