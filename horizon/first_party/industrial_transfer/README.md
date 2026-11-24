# TechQuest Industrial Transfer — native prototype

Original first-party Rust implementation, not copied from BuildCraft or IC2. The first vertical transfer node uses the actual pinned Horizon trait hooks: block entity creation, server ticking, saved NBT cooldown, redstone and transactional item movement. Place a container directly above, another below, and power the node with redstone. It attempts to transfer one item every eight powered ticks. No energy system, pipe network, GUI or full third-party port yet.

The accompanying content module is in `../industrial_content/`; install both the content HMOD and the native bundle on the pinned Horizon revision. Native code requires the player's explicit trust in the official launcher. This is not an executable release. CI checks the native crate against the pinned real upstream workspace, runs the pure Rust unit tests and checks the content module using the official SDK. No Minecraft assets or account data are required for compilation.

See [pinned native API](https://github.com/horizon-rust/horizon/blob/c78187dffffb60f31517eadcb87413386e8ce729/docs/native-mods.md) and the [authoritative movement implementation](https://github.com/horizon-rust/horizon/blob/c78187dffffb60f31517eadcb87413386e8ce729/crates/horizon-client/src/game/machines/native_items.rs).

Acceptance before calling this playable: build and link the trait mod into an engine, install the content module, verify an unpowered node moves nothing, power it and observe rate and direction, check full/absent destination and double-chest cases, check hopper/furnace side rules, save/reopen with the cooldown, confirm dedicated server and licensed client agree, and confirm no item loss/duplication with simultaneous automation. No world test yet. Do not attribute this original mechanic to any existing Java mod or change the official port count.

Next: powered ore processor with input/output/fuel or energy slots, then interoperable energy storage and transfer. Keep state server-owned and persistent.
