# Oritech native subset 0.2 / content 0.3

First-party Rust implementation for Horizon 26.3 at
`c78187dffffb60f31517eadcb87413386e8ce729`, Mixins
`5a64af938ec86b00d53d16a408aabc0038fb3e57`.

This is a limited port of **Basic Generator → quartz Pulverizer / Powered
Furnace + one Machine Core**, with physical inventories, energy, fuel, processing progress, assembly,
menus and saved state. It is not the complete Oritech mod or a survival-ready
TechQuest industrial progression.

Content 0.2 adds the first crafting route while retaining this native 0.1.0
machine implementation. It additionally requires the separately compiled
[merged-biome core correction](../biome_modifiers/README.md). The installer has
an explicit content/native compatibility table and refuses 0.2 with an engine
that does not declare the reviewed core correction. Content 0.3 requires native
0.2 and both biome core corrections. Earlier sealed content 0.1/0.2 profiles
continue to use native 0.1; their artifacts remain unchanged.

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
the fixed menus and requires the explicitly paired `techquest_oritech` version.
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

Remaining original recipes/material progression, other machines, cables, fluids,
upgrades, other core qualities, auto-placement of held cores, original shapes,
orientation, lit-state/animation/particles, core inventory/fluid delegation and
general energy API delegation through cores remain outside this prototype.
The simplified models reference installed vanilla textures; only the core
texture and translated block names are staged from the pinned CC0 JAR.

The current vanilla 26.3 fuel/recipe resources are used. The tested 1.21.1 fuels
and recipes must match the oracle; the entire cross-version registry is not
claimed equivalent. Component-sensitive/oversized-stack cases, allocation
among multiple receivers, exact immediate break/drop semantics, unloaded
chunks and licensed dedicated-server join still require work. The selected
crafting routes and Pretty Pipes endpoints have separate gameplay probes;
general automation beyond the supported machines is not established.

## Content 0.2 starter subset

`stage_oritech.py --progression` adds the original `core1`, `basicgen`,
`electricfurnacealt`, `magnet`, steel/electrum hand-alloy recipes, and nickel/
platinum raw smelting and blasting recipes. It registers four ore blocks and
eight material items. `biosteel_ingot` preserves the original alternate member
of `c:ingots/steel`; its production chain is not included. The furnace route
uses platinum; the default silicon recipe still requires unported processing.

The pinned JAR supplies original ore loot, models/textures, labels and the three
biome modifiers/placed features. Horizon's pinned Rust upgraders convert the
recipe/loot formats and worldgen, rather than replacing the source recipes.
Pass the pinned NeoForge universal JAR as `--neoforge-jar`, the compiled
`oritech_content_tool.rs` probe as `--content-tool` and the pinned
`horizon-port-pack` binary as `--port-pack`. Exact local compiler commands and
artifact hashes are included in the runtime report. Nothing generated belongs
in the repository.

The original binary oracle `OritechContentProbe.java` runs via
`run_oritech_reference.py --oracle content --cases CASES.json` in a fresh work
directory. `oritech_content_cases.py` generates 38 positive and 444 mutated
grids, including mirror/offset/tag variants. Six mutations correctly craft a
vanilla chest; the comparison preserves that result, normalizing the implicit
`minecraft:` namespace only. All 482 grids and 60 whole-table ore rolls
(four ores, ordinary/Silk Touch/Fortune III, five seeds) match the native engines.

`live_oritech_crafting_gui.py` actually crafts three steel ingots, electrum,
four coils and all three machine/core blocks through menu clicks. It checks
every ingredient delta, places the crafted blocks and produces two collected
iron ingots. Vanilla resources and nickel/platinum ingots are fixtures; the
test does not claim a fully gathered survival run.
`live_oritech_ores_gui.py` separately finds/mines natural nickel with Terralith
enabled and natural End platinum, then verifies inventory/broken blocks after
reopen. It gives only a pickaxe, carves access cells and never injects ores,
features or raw items. End platinum is an existing source route. The later
[`--deepslate` check and world-pack correction](../../ORITECH_WORLDPACK_RESULT.json)
also establish natural Overworld nickel/platinum inside Terralith biomes with
physical save/reopen. The correction restores feature modifiers after enabled
world packs; new installations require both reviewed core corrections.
Full worldgen RNG parity remains unverified.

[Content 0.2 results and limitations](../../ORITECH_STARTER_RESULT.json).

## Guided starter chain from mined materials

`live_oritech_gathered_gui.py` connects gathering, vanilla smelting, crafting,
placement and machine operation in one continued Terralith world save. Only an
iron pickaxe is given. Teleports, spectator travel, peaceful difficulty, carved
access, glass access floors/roofs and a work platform, and tick control are
explicit fixtures. All recipe inputs come from survival mining; workstations,
alloys and machines are crafted through real menu packets.

```sh
python3 horizon/probes/live_oritech_gathered_gui.py --server-dir "$TASK_SERVER" \
  --work "$TASK_RUNTIME/oritech-gathered-new"
```

The probe checks ingredient deltas, collected drops, raw inventory after reopening,
an active machine pair after reopening, and final items/state after another
reopen. It handles redstone's first-hit lighting and naturally falling gravel;
a changed block state alone does not count as collected ore. A stopped
`raw-checkpoint` retains the gathered save and cumulative mining actions.
`--resume-from OWN_GATHER_WORK` accepts only a gather-phase action history,
checks content hashes against the sealed profile, and continues that saved
world in a new scratch directory with its action provenance retained.

[Guided run evidence](../../ORITECH_GATHERED_RESULT.json). This does not establish
unassisted progression from spawn, the silicon processing route, automation or
licensed multiplayer. The engine and content versions are unchanged.

## Automated input/output with Pretty Pipes

[Pretty Pipes 0.6](../../ORITECH_PIPES_RESULT.json) adds read-only destination
capacity and visible connections for this prototype's generator/furnace. The
Oritech native/content versions stay 0.1.0/0.2.0. A dedicated server and actual
graphical client feed coal/raw iron, extract the genuine output, preserve cargo
across reopening and pause/resume at a full destination. An extractor leaves
the furnace input alone. Sixteen raw iron and one coal produce sixteen ingots
with zero residual machine energy. Machine/assembly/source-material fixtures
are explicit; this automation world is separate from the gathered starter run.
Other machine handlers, general NeoForge capability parity and licensed
dedicated join remain unverified.

## Content 0.3 quartz and silicon route / native 0.2

`stage_oritech.py --pulverizer` implies `--progression` and adds the original
manual motor recipe, Pulverizer recipe, quartz processing recipe, raw-silicon
hand alloy, raw-silicon smelting, and default silicon furnace recipe. There are
15 ordinary recipes plus one `oritech:pulverizer` recipe, four machine/core
blocks, four ore blocks and twelve material items. Existing platinum crafting
remains available. Original files are taken from the same pinned CC0 JAR.

Without addons the Pulverizer has a 25,000 energy buffer, accepts 256 per call,
uses 32/tick and turns one quartz into one quartz dust in 100 ticks. It works
without a machine core and has one input and two output slots. The source
redstone flag pauses processing; invalid input or blocked output resets progress.
The original cached recipe is transient: progress is saved, but after loading
an active quartz recipe starts from zero on its next processing tick. The port
matches this behavior using Horizon's unsaved entity data to invalidate the
private cached recipe, without a global pointer map.

`OritechPulverizerProbe.java` invokes the original server tick for 67 cases and
536 states, including energy boundaries, primed/fresh recipes, redstone,
invalid input, blocked outputs and a secondary-slot obstacle. A separate
physical save/reopen compares the cache reset and subsequent production.

```sh
python3 horizon/probes/run_oritech_reference.py --runtime "$TASK_RUNTIME" \
  --work "$TASK_RUNTIME/oritech-pulverizer-reference-new" --oracle pulverizer --accept-eula
python3 horizon/probes/run_oritech_reference.py --runtime "$TASK_RUNTIME" \
  --work "$TASK_RUNTIME/oritech-pulverizer-reference-new" --oracle pulverizer --reopen
python3 horizon/probes/live_oritech_pulverizer.py --server-dir "$TASK_SERVER" \
  --work "$TASK_RUNTIME/oritech-pulverizer-new" \
  --original "$TASK_RUNTIME/oritech-pulverizer-reference-new/initial-result.json" \
  --original-reopen "$TASK_RUNTIME/oritech-pulverizer-reference-new/reopen-result.json"
python3 horizon/probes/live_oritech_silicon_gui.py --server-dir "$TASK_SERVER" \
  --work "$TASK_RUNTIME/oritech-silicon-gui-new"
```

The graphical probe mines natural Nether quartz and crafts both motors, the
Pulverizer, generator, silicon and default furnace through real menus. Other
base materials are explicit fixtures, alongside teleports, access cells and
a work platform. It is not an unassisted survival run. The separate dedicated
`live_oritech_pulverizer_pipes.py` uses Pretty Pipes 0.7 input/output endpoints,
saves two genuine dust items in flight, then verifies delivery and another
physical reopen. Run its `prepare`, `verify` and `final` phases with a server
start before each, passing `--prior` for the latter two phases.

Only the quartz Pulverizer recipe is staged. Addons, secondary small-dust
compaction, other Pulverizer recipes and full source geometry/animation remain
outside this subset.

## Guided silicon route with all ingredients gathered

`live_oritech_gathered_silicon_gui.py` runs the content 0.3 route in a single
continued Terralith world without the base-material gifts used by the smaller
silicon GUI probe. Only an iron pickaxe is given. The player mines nickel,
iron, gold, redstone, copper, coal, stone, wood, sand and Nether quartz, then
uses real crafting/smelting menus for workstations, alloys, coils, motors,
Pulverizer, generator, silicon, furnace and core. Four physical reopens check
the raw inventory, active Pulverizer, active furnace and final inventory/state.

```sh
python3 horizon/probes/live_oritech_gathered_silicon_gui.py \
  --server-dir "$TASK_SERVER" --work "$TASK_RUNTIME/oritech-gathered-silicon-new"
# Only an own prior gather-phase save/checkpoint can be resumed:
python3 horizon/probes/live_oritech_gathered_silicon_gui.py \
  --server-dir "$TASK_SERVER" --work "$TASK_RUNTIME/oritech-gathered-silicon-resumed" \
  --resume-from "$TASK_RUNTIME/oritech-gathered-silicon-new/raw-checkpoint"
```

Resume checks module hashes, preserves all earlier actions and refuses a save
that has entered crafting. Nearby block searches use radius 16 first and the
original radius 64 as fallback. Nickel eligibility still requires a Terralith
biome; exhausted or ineligible search results cause scouting of nearby natural
areas. A failed initial aim can widen the air/glass approach and retry from
one block away without replacing the ore; mining/drop/menu assertions remain
fatal. Teleports,
spectator travel, carved access, glass supports/platform, peaceful difficulty,
platform forceload and tick control are explicit fixtures. This is a guided
material-progression check, not unassisted survival from spawn or multiplayer.

[Checked gathered silicon route](../../ORITECH_GATHERED_SILICON_RESULT.json):
138 mining actions, 34 crafts, 71 smelted ingots, two collected processing-output
iron ingots and four verified physical reopens. Inventory comparisons cover
item IDs/counts; native machine comparisons cover energy, progress and Items
NBT. General item-component round trips are not established by this probe.
