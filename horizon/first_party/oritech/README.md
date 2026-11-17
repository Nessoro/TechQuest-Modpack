# Oritech energy prototype 0.1

First-party Rust implementation for Horizon 26.3 at
`c78187dffffb60f31517eadcb87413386e8ce729`, Mixins
`5a64af938ec86b00d53d16a408aabc0038fb3e57`.

This is a limited port of **Basic Generator → Powered Furnace + one Machine
Core**, with physical inventories, energy, fuel, smelting progress, assembly,
menus and saved state. It is not the complete Oritech mod or a survival-ready
TechQuest industrial progression.

## Source and license

[Rearth/Oritech v1.2.13](https://github.com/Rearth/Oritech/tree/4069b6dd14b05dfe0c80126618739b64054630ea),
commit `4069b6dd14b05dfe0c80126618739b64054630ea`. The pinned `LICENSE.md` is
CC0-1.0, retained in `LICENSE-ORITECH`; the pinned NeoForge JAR also declares
CC0-1.0. Current Modrinth project metadata says CC BY 4.0. This work relies on
the dedication at the exact pinned commit. Consulted own source file headers
contain no separate override. See [notices](../../THIRD_PARTY_NOTICES.md).

The source specifies 50,000 energy capacity, 32 energy/tick and 256 extraction
per API call for the generator. The furnace has 10,000 capacity, accepts 256 per
call and, without upgrades, uses 32/tick for half the ordinary smelting time.
The original machine classes are invoked by the developer oracle rather than
reimplemented as expected-value arithmetic. No Java runs in the Horizon port.

## Native behavior

- Generator fuel is consumed only when a complete production tick fits. The
  first tick both consumes fuel and produces energy. Burning pauses with a full
  buffer, preserving fuel remainder. Vanilla buckets are explicitly refused,
  including lava buckets, following the source's early `BucketItem` check.
- The furnace requires a core directly above. Empty-main-hand interaction
  assembles it; the first successful assembly click is consumed and the next
  opens its menu. Removing the core disables processing on the next tick.
- Energy moves directly to adjacent buffers. This generator can also reach the
  furnace through its linked core. The per-call limit is preserved; no aggregate
  256-per-tick cap is invented.
- Invalid input or blocked output resets furnace progress. Insufficient energy
  preserves it. The original furnace override ignores its redstone-disabled
  flag; the oracle includes this observed behavior.
- Compact native menus expose one generator slot or furnace input/output;
  the output is a result slot. Five data slots carry energy as two 16-bit parts,
  progress, burn duration and assembly status.
- `energy` is the canonical native buffer int, as required by Horizon's energy
  API. Progress uses `oritech.machine_progress`, burn duration `storedBurn`.
  Assembly/link flags use `techquest_assembled`/`techquest_core_used` and relative
  `controller_x/y/z`. Original NeoForge world import is not implemented.

## Build and developer checks

All generated resources, bundles, worlds and logs stay outside the repository.
The existing isolated installer accepts optional `--oritech PATH`, validates
the fixed menus and requires a matching `techquest_oritech` 0.1.0 native bundle.
Older installations and locks remain readable and unchanged.

With existing pinned binaries in `$TASK_RUNTIME/oritech-reference-input`, a
NeoForge 21.1.264 reference under `neoforge-reference/server`, and JDK25:

```sh
python3 horizon/probes/run_oritech_reference.py --runtime "$TASK_RUNTIME" \
  --work "$TASK_RUNTIME/oritech-energy-reference-new" --accept-eula
python3 horizon/probes/run_oritech_reference.py --runtime "$TASK_RUNTIME" \
  --work "$TASK_RUNTIME/oritech-energy-reference-new" --reopen
python3 horizon/tools/stage_oritech.py \
  --jar "$TASK_RUNTIME/oritech-reference-input/oritech-neoforge-1.21.1-1.2.13.jar" \
  --sdk "$TASK_RUNTIME/upstream/target/fast/cargo-horizon-mod" \
  --output "$TASK_RUNTIME/oritech-content-new"
```

Apply all `horizon/first_party` modules with pinned Mixins and rebuild Horizon.
The manifest adds eight HEAD injections and one support module. Package the
`.rs`, manifest and both license files in `mixins/techquest_oritech/`, with
`horizon-native.json` at the `.hnmod` root, then run the SDK checker. Content
alone does not execute the machines.

Against a new sealed installation:

```sh
python3 horizon/probes/live_oritech_energy.py --server-dir "$TASK_SERVER" \
  --work "$TASK_RUNTIME/oritech-native-check-new" \
  --original "$TASK_RUNTIME/oritech-energy-reference-new/initial-result.json"
# Requires an X11 display and Vulkan, e.g. the isolated Xvfb/software driver.
python3 horizon/probes/live_oritech_energy_gui.py --server-dir "$TASK_SERVER" \
  --work "$TASK_RUNTIME/oritech-gui-check-new"
```

The original oracle has 63 cases and 414 snapshots: six fuel/invalid-item types,
capacity boundaries, empty input, remaining burn, redstone flags, assembly,
three furnace inputs, energy thresholds and blocked output. Calls run on the
original server thread with explicit time advancement; particle RNG/working
animations are outside the comparison. A separate real world restart resumes a
partially working pair. The native comparison injects initial state fixtures;
the graphical probe separately uses interaction/menu packets and real generated
energy/output, saving and reopening its own physical world.

## Remaining work

Original recipes/material progression, other machines, cables, fluids,
upgrades, other core qualities, auto-placement of held cores, original shapes,
orientation, lit-state/animation/particles, core inventory/fluid delegation and
general energy API delegation through cores remain outside this prototype.
The simplified models reference installed vanilla textures; only the core
texture and translated block names are staged from the pinned CC0 JAR.

The current vanilla 26.3 fuel/recipe resources are used. The tested 1.21.1 fuels
and recipes must match the oracle; the entire cross-version registry is not
claimed equivalent. Component-sensitive/oversized-stack cases, allocation
among multiple receivers, exact immediate break/drop semantics, unloaded
chunks, general automation, normal crafting and licensed dedicated-server join
still require work. Pretty Pipes 0.5 has not yet gained Oritech endpoints.
