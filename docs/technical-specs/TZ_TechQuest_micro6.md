# Technical Specification No. 4 — TechQuest 0.3.3-micro6

## Port Advanced Solar Panels to Industrial Craft 2: Nostalgia

**Revision:** November 14, 2026  
**Repository:** https://github.com/Nessoro/TechQuest-Modpack  
**Implementation PR:** https://github.com/Nessoro/TechQuest-Modpack/pull/35 (draft; initial audit phase only)  
**Implementation branch:** `experiment/solar-panels-nostalgia-micro6`  
**Base:** micro5 — `feat/micro5-iskander-rocket-033`  
**Target platform:** Minecraft Java 1.21.1, NeoForge 21.1.264, Java 21.

### Objective
Build a separate **Advanced Solar Panels** add-on compatible with **Industrial Craft 2: Nostalgia 21.1.0-local.26**. Do **not** replace Nostalgia with Refactored or alter the existing `ic2` mod ID and saved worlds. Start with one functional solar-panel prototype; expand to four panel tiers only after the minimum viable prototype works.

### Verified baseline and current blocker
- TechQuest already includes `industrial-craft-2-nostalgia-21.1.0-local.26.jar` in `manual-mods`.
- **TechQuest Compatibility 1.0.0** must remain installed, preserving Create ↔ IC2 recipes and the Better Zoom workaround.
- Reference upstream add-on: **Advanced Solar Panels Refactored 1.1.8**, published for Minecraft 1.21.1 at https://www.curseforge.com/minecraft/mc-mods/advanced-solar-panels-refactored/files/9525863.
- The existing `scripts/audit_solar_nostalgia.py` audit found **48 Java classes** and **19 direct references to `me/halfcooler/ic2r/`**. The add-on expects `modId=ic2r` and references `ic2r:` item/recipe identifiers.
- Under a hypothetical package-name replacement, one class (`me/halfcooler/ic2r/core/IC2R`) has no direct counterpart in Nostalgia. **Similar class names for the remaining references do not prove binary, method, field or semantic compatibility.**
- The add-on page lists a **GPLv3** license. Verify the actual source code, resource rights and exact distribution terms before reusing code or assets.
- **The actual port has not yet been implemented or tested in Minecraft.** A successful static audit is not a successful game launch.

### Phase A — Legal review and API compatibility matrix
1. Locate the source code corresponding to upstream release 1.1.8, or another legally usable code base. Verify permissions for textures, models, localization and other art assets as well as Java sources.
2. Compare the Java APIs of the pinned Nostalgia `local.26` and the referenced IC2 Refactored: block/item registration, EU energy-source and energy-sink interfaces, energy-grid events, cable connections, block entities, save/sync logic, item energy APIs and client/server packets.
3. Produce a **class / method / field compatibility matrix**, identifying actual adapter implementations and blockers. Do not conceal missing behavior with empty placeholder interfaces or dummy methods.
4. Record source revisions, verified checksums, attribution and corresponding-source distribution requirements. Do not ship an unverified third-party binary.

### Phase B — MVP: one Advanced Solar Panel
1. Create an isolated NeoForge/Java 21 add-on with its **own unique mod ID** (proposed: `techquest_solar`). **Do not register another `ic2` mod** or modify Nostalgia's JAR.
2. Implement a placeable **Advanced Solar Panel** block and item with EU generation, integration into Nostalgia's actual energy network, cable output, voltage/output limits and internal energy storage.
3. Account for sky access, daylight, weather/rain, chunk unloading and server/world reloads. Prevent unbounded power generation or duplication after saving/reloading.
4. Supply original or properly licensed textures/models, Russian in-game strings, a JEI recipe and a Patchouli entry. Do not copy protected art without complying with the applicable license.
5. Test EU production over **20, 200 and 1,200 game ticks**, transfer to an IC2 energy-storage block, persistence and output-voltage restrictions.

### Phase C — Expand to four panel tiers

The following figures are **historical reference targets** from Advanced Solar Panels, **not approved balance or verified output values for TechQuest**. Confirm Nostalgia voltage tiers and balance before finalizing them.

| Panel tier | Reference daytime generation | Reference night/rain generation | Internal capacity | Maximum output |
|---|---:|---:|---:|---:|
| Advanced | 8 EU/t | 1 EU/t | 32,000 EU | 32 EU/t |
| Hybrid | 64 EU/t | 8 EU/t | 100,000 EU | 128 EU/t |
| Ultimate Hybrid | 512 EU/t | 64 EU/t | 1,000,000 EU | 512 EU/t |
| Quantum | 4,096 EU/t | 2,048 EU/t | 10,000,000 EU | 8,192 EU/t |

1. Implement all four tiers **only after the MVP is validated**, including proper storage, generation, cable interfaces and safety limits.
2. Validate existing Nostalgia voltage tiers and the effect on industrial progression. Confirm materials, craft balance and recipe compatibility with JEI.
3. Replace `ic2r:*` ingredients with the real `ic2:*` identifiers or agreed common item tags. Do not quietly invent missing items.
4. Solar helmets, Molecular Transformer, additional materials and other machines are a **separate second-stage enhancement**; they are not required to accept the four-panel MVP.

### Phase D — Runtime validation and packaging
- Implement automated EU-network tests, generation tests under different daylight/weather conditions, storage-overflow handling, output-voltage restrictions and save/reload behavior.
- Launch a real Minecraft client with IC2 Nostalgia, TechQuest Compatibility, Create, Mekanism, AE2 and JEI. Verify recipe visibility, actual EU measurements and no Better Zoom regression.
- Boot a real dedicated server to `Done` **after explicit Minecraft EULA consent** and join from the client. Verify there are no `NoClassDefFoundError`, `NoSuchMethodError` or client/server synchronization errors.
- Profile **1 / 16 / 64 solar panels** using Spark; report actual FPS and TPS compared with a control test without the panels. Do not invent performance figures.
- Test save/reload, chunk unload/load, energy retention and preservation of existing IC2 machines/world data.
- **Only after runtime tests pass**, include the legally distributable compiled add-on with verified URLs, checksums and side metadata in `modlist.json`, `.mrpack`, Windows GUI and the server distribution. Verify upgrades, rollback, source availability and licensing compliance.

### Non-negotiable restrictions
- Do not replace IC2 Nostalgia or require IC2 Refactored in the final modpack.
- Do not install two competing mods with the same `ic2` ID.
- Do not add an untested experimental solar JAR to the regular distribution merely to obtain a green CI build.
- Do not distribute source, modified JARs, textures or other assets without checking licenses, authorship and attribution.
- Do not modify existing player worlds, `main` or the published micro2 preview without explicit owner approval.

### Research-phase acceptance (current PR #35)
- [ ] A concrete API matrix including class, method and field signatures has been documented; legal rights and remaining blockers are identified.
- [ ] The static audit and offline unit tests are reproducible against pinned binaries and verified hashes.
- [ ] If no functioning port exists yet, the report explicitly states **"not tested by launching Minecraft"**.

### Playable micro6 acceptance (future)
- [ ] All four panels generate and deliver **real EU to IC2 Nostalgia** in both single-player and dedicated-server worlds, with no second IC2 implementation.
- [ ] Generation/storage are measured numerically and daylight/weather behavior follows the agreed specification.
- [ ] Recipes, Russian localization, JEI and Patchouli work; Create ↔ IC2 and Better Zoom remain functional.
- [ ] Worlds survive save/reload; there are no network-sync errors; FPS/TPS results are documented.
- [ ] Source/license reviews are complete; the binary can be audited; GUI, `.mrpack` and CI all use the same validated commit SHA.

### Deliverables and Codex handoff
Provide the add-on source project or a legally compliant port, the **Refactored → Nostalgia API compatibility matrix**, tested solar-panel implementation, documentation, logs and updated PR #35 (or a follow-up implementation PR if needed). Append dated evidence to `docs/TECHQUEST_033_DEVELOPMENT_JOURNAL_RU.md`. Until a real, tested in-game port exists, **micro6 remains an experiment, not a player-facing update**.
