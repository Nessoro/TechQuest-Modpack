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

Pretty Pipes 0.4 extraction filters adapt the MIT `ItemFilter`, `FilterSlot`,
`DirectionSelector` and default `ItemEquality` behavior from the same pinned
Ellpeck source. Original component IDs, basic filter/direction codec fields,
English labels and the available Russian labels are reused with the complete
MIT notice in the content module and native source bundle. The compact Horizon
controls and native transport integration are first-party code. The original
runtime/Data.CODEC oracle is distinct from the observed stale cached component
serialization; see `PRETTY_PIPES_FILTER_RESULT.json`.

Pretty Pipes 0.5 destination-capacity and in-flight count policy follows the
MIT `PipeBlockEntity.getAvailableDestination` and `PipeNetwork.getItemsOnTheWay`
from the same pinned Pretty Pipes source. The read-only insertion view adapts
MIT Horizon `game/machines.rs` container rules; see the retained
`LICENSE-HORIZON`. No Java source from NeoForge or LGPL/GPL dependencies was
read or decompiled; the original reference runs binary dependencies only.

Pretty Pipes 0.8 adapts the same pin's MIT `RedstoneModuleItem`, mutual module
compatibility in `PipeBlockEntity.modules`, and the distinction between
`canWork`/new destination selection and direct `store` for an in-flight item.
Its sixth source recipe, redstone-module texture and translated name are staged
privately with the retained complete MIT notice. Power reads use Horizon's
pinned MIT native neighbor-signal API; no dependency Java source is used.

## Oritech energy and quartz-processing subset

The Oritech 1.2.13 reference is [Rearth/Oritech at
4069b6dd14b05dfe0c80126618739b64054630ea](https://github.com/Rearth/Oritech/tree/4069b6dd14b05dfe0c80126618739b64054630ea).
Its pinned `LICENSE.md` dedicates the work under CC0-1.0; that complete text is
retained in `first_party/oritech/LICENSE-ORITECH`. The pinned NeoForge JAR also
declares CC0-1.0. Current Modrinth project metadata instead says CC BY 4.0;
this port relies on the verified dedication at the exact source commit,
not on the current project's metadata. Headers of the consulted own Java files
have no separate license override.

`first_party/oritech/logic.rs` adapts the default Basic Generator, Powered Furnace
and single Machine Core behavior from `BasicGeneratorEntity`,
`UpgradableGeneratorBlockEntity`, `MachineBlockEntity`,
`UpgradableMachineBlockEntity`, `PoweredFurnaceBlockEntity`, `PulverizerBlockEntity`,
`MultiblockMachineEntity`, `MultiblockMachine`, `MultiblockMachineController`,
`MachineCoreEntity`, `MachineCoreBlock`, `DynamicEnergyStorage` and `EnergyApi`.
The same pin's `OritechConfig`, `BlockContent`, `BlockEntitiesContent` and
`BasicGeneratorBlock`/`PoweredFurnaceBlock` were consulted. The integration and
compact menu are first-party Rust; hand-use ordering and the native energy
contract follow Horizon's pinned MIT implementation, with `LICENSE-HORIZON`
retained. Java exists only in the developer oracle.

Private content staging uses the pinned JAR's CC0 core texture and three block
names from each of its English/Russian language JSON files. Simplified machine
models reference installed vanilla textures; GeckoLib animations are not copied.
Architectury, GeckoLib and NeoForge are run as binary reference dependencies;
their Java sources are neither read nor decompiled. Fluidic Tanks is All Rights
Reserved; its source has not been read or used.

Oritech content 0.2 additionally stages the same pinned CC0 JAR's ten source
recipes, ore loot/models/textures, material models/textures, labels and ore
worldgen/biome-modifier JSON. Horizon's MIT `carry::upgrade_recipe`,
`carry::upgrade_loot` and datapack upgrader perform the format changes. Source
common item tags are resolved from public JSON in the pinned Oritech and
NeoForge universal JARs; no dependency Java source is read.

Content 0.3 adds five ordinary recipes, the original quartz Pulverizer recipe,
four material assets and labels from that same CC0 JAR. Native 0.2 adapts the
no-addon quartz processing path and transient recipe-cache behavior. The own
`PulverizerBlockEntity.java` at the same pin has no separate license header;
its SHA-256 is `3d240c40254a4b05805e7ca7212592e8e5843808553c47e19700eab11e43fa4a`.

Content 0.4 adds two ordinary recipes, coal pulverization, three Foundry alloys
and two material assets/labels from the same CC0 JAR. Native 0.3 adapts the own
Foundry class, multiblock lifecycle, horizontal placement and geometry helpers
at the same pin. Their headers contain no separate override. Consulted source
SHA-256 values are recorded in `ORITECH_FOUNDRY_RESULT.json`; dependency Java
source was not read. At the Foundry milestone the own CC0 Assembler class was
consulted for planning only. Pretty Pipes 0.9 only extends
its native endpoint allowlist and optional connection tag to the new Foundry.

Content 0.5/native 0.4 now adapts the same pin's own Assembler class for the
selected coils/motors recipes, four input slots and shared three-core lifecycle.
`AssemblerBlockEntity.java` SHA-256 is
`435944fab5c9130a6119c27ffedec58f751d1afaace0ef6bf54994755a28f031`;
it has no separate license override. The controller's chunk-residency guard uses
the pinned MIT Horizon world API and audited streaming installation order; the
complete MIT notice remains in `first_party/oritech/LICENSE-HORIZON`.
Pretty Pipes 0.10 adds the new native endpoint and optional connection tag;
its six original recipe payloads and transport/module semantics are unchanged.

`first_party/biome_modifiers/merged-biomes.patch` adapts Horizon's MIT
`mod_content.rs` at the existing pinned Horizon commit. It registers declared
biome files before tag filtering and applies modifiers to the merged registry.
The original and resulting source SHA-256 and the exact diff SHA-256 are pinned
in `horizon-core-patch.json`; the complete MIT notice is retained in that folder.
This is a separately declared core correction in a generated private build,
not an SDK native source bundle. The public source and prepared resources stay
unchanged. The developer probes use the same pinned Rust content/recipe/loot
APIs and original binary oracles; no Java is added to the player runtime.

`first_party/biome_world_packs/world-packs.patch` additionally adapts the same
MIT Horizon pin's `mod_content.rs` and `game/world_loading.rs` so feature
modifiers run after enabled world packs. `world_features.rs` uses that pin's
biome modifier/tag APIs. The folder retains the full MIT notice and pins both
source results, the diff and the helper. No dependency Java source is used.
