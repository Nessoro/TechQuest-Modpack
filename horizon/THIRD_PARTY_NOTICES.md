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

`first_party/pretty_pipes/{logic,modules}.rs` implements extraction tiers and
default module installation/inventory semantics observed
and read in Pretty Pipes 1.22.0, commit
[`1f8ac61`](https://github.com/Ellpeck/PrettyPipes/tree/1f8ac61c6de5b191f3b28da2c23d8040a231047f).
Copyright (c) 2020–2021 Ellpeck, MIT. The original source files read are listed
in `PRETTY_PIPES_REFERENCE_RU.md`; the Rust routing implementation is original.
The MIT text is retained in `first_party/pretty_pipes/LICENSE-PRETTY-PIPES`.
The private content assembler adapts five original recipes, copies a pipe loot
table and five original MIT textures, and embeds
the copyright/permission notice as manifest comments in its output hmod.

The native pipe adapter uses Horizon's MIT container/tick APIs and adapts the
stack-size component fallback of `game/machines.rs` at the same pinned Horizon
revision. Copyright (c) 2026 Ludovic Marie and the Horizon contributors, MIT;
the license is retained in `first_party/pretty_pipes/LICENSE-HORIZON`.

Pretty Pipes recipe glass membership is resolved from the public item-tag JSON
in NeoForge 21.1.264 universal JAR (LGPL 2.1, as declared in its official POM). Only the 18 vanilla item IDs
of the minimal reference are used in a private tag; optional missing legacy
Forge tags and the official artifact SHA-256 are recorded in the build report.
No NeoForge Java source is read or copied. The developer oracle calls its public
binary API on an isolated server.

The 0.3 main menu layout adapts Pretty Pipes `MainPipeContainer` and the
compatibility rule of `PipeBlockEntity.modules`; both are MIT at the pinned tag.
The private content output also includes five names from each of the original
English and Russian language files. The hand-use hook ordering and lazy
container-table preparation follow Horizon `Game::use_hand` and
`game/block_entity_ticks.rs` (same MIT pin and retained license).
