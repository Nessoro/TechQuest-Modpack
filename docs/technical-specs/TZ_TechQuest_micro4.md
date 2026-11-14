# Technical Specification No. 2 — TechQuest 0.3.3-micro4

## Trash Cans and Pretty Pipes: disposal and engine-free item logistics

**Revision:** November 14, 2026  
**Repository:** https://github.com/Nessoro/TechQuest-Modpack  
**Implementation PR:** https://github.com/Nessoro/TechQuest-Modpack/pull/31 (draft)  
**Implementation branch:** `feat/techquest-trash-pipes-reactor-micro4`  
**Base:** micro3 — `fix/micro3-remove-first-party-mods-033`  
**Target platform:** Minecraft Java 1.21.1, NeoForge 21.1.264, Java 21.

### Objective
Add item/fluid/energy disposal and **item** transportation without BuildCraft engines, while preserving existing factories, IC2: Nostalgia, dedicated-server compatibility and TechQuest Compatibility.

### Pinned versions

| Mod | Modrinth project ID | Version ID | Sides |
|---|---|---|---|
| Trash Cans | `4QrnfueM` | `lSKYKJdm` | Client and server |
| Pretty Pipes | `XExdLWCQ` | `lrhbGGSe` | Client and server |
| SuperMartijn642's Config Lib 1.1.8 | `LN9BxssP` | `qKL9jM75` | As required by verified dependency metadata |
| SuperMartijn642's Core Lib 1.1.26a | `rOUBggPv` | `sLRKmslC` | Client and server |

The authoritative download URLs, JAR filenames, side metadata and SHA-512 checksums are defined in the implementation branch's `modlist.json` and `modrinth_lock`. Do not silently upgrade to unverified latest releases or disable integrity verification.

### Functional requirements
1. Install the author's item, fluid and energy Trash Cans variants correctly. Verify all features and filters actually supported by the selected release.
2. Pretty Pipes must transport **items**, including block items, between inventories/chests/machines without engines or an external power network. **Do not claim it transports placed blocks in the world, fluids or energy.**
3. Test the following routes: **chest → Pretty Pipes → chest** and **chest → Pretty Pipes → Trash Cans**. Configure extraction modules and filters wherever the mod requires them.
4. Prevent unintended disposal when no explicit disposal connection is set up. In a test scenario, confirm filtering protects valuable items.
5. Verify standard inventory compatibility and basic interactions with Sophisticated Storage, Iron Chests, Create and BuildCraft. Do not claim that unsupported adapters work without testing.
6. Retain the single Optimized profile, Patchouli guide, Windows GUI, dedicated server, existing saves and settings.

### Explicit exclusions
- Do **not** add Colossal Reactors, Iskandert's Library or Fusion, which were mistakenly included in an early micro4 candidate.
- Do **not** add FTB Industrial Contraptions or substitute a different reactor. The owner canceled this direction.
- Do **not** replace IC2: Nostalgia with Refactored. Advanced solar panels belong to micro6.
- Do **not** restore RPG Core or PMMO. Preserve TechQuest Compatibility 1.0.0.

### Implementation scope
- `modlist.json`: exact versions, identifiers, SHA-512 checksums and installation sides for both mods and required libraries.
- `build_pack.py`: use the normal verified resolver/download pipeline; do not repack third-party JARs.
- `.github/workflows/build-alpha.yml`: assert both mods are present and the mistakenly added reactor's unique dependencies are absent.
- `tests/test_tech_micro4.py` and `tests/test_adventure_rebalance.py`: verify selection, categories, lock entries, client/server output and manifests.
- `scripts/guide_assets.py`: Russian Patchouli pages describing routing, filters and safe disposal practices.
- `docs/index.html` and `scripts/sync_site_mods.py`: keep the website mod catalog synchronized.
- `README.md` and `docs/MICROPATCH_MICRO4_RU.md`: accurate installation instructions, limitations and cautions.

### Verification and acceptance
- [ ] Unit tests, `python build_pack.py`, downloaded file checksums and `.mrpack` validation succeed.
- [ ] Windows GUI installer builds, passes self-test and deploys client/server content without overwriting user settings.
- [ ] Item transport is demonstrated through straight and turning pipe routes, empty/full containers, extraction and filtering.
- [ ] Cobblestone disposal is demonstrated without accidental loss of a valuable item.
- [ ] Fluid and energy trash variants are independently tested with appropriate sources; these capabilities must **not** be attributed to Pretty Pipes.
- [ ] Actual FPS and TPS are measured on small/medium/large networks, with Spark logs and the precise test conditions. Do not invent benchmarks.
- [ ] Worlds save and reload; dedicated server boots after explicit EULA consent; a client can connect; IC2/BuildCraft/Create factories remain intact.
- [ ] Client, server and `.mrpack` do not contain Colossal Reactors, Iskandert's Library, Fusion or FTB Industrial.

### Deliverables and Codex handoff
Update the existing draft PR #31 with real route-testing evidence, known compatibility limitations, logs and pipe/trash configuration guidance. Record the result in `docs/TECHQUEST_033_DEVELOPMENT_JOURNAL_RU.md`. A public release requires explicit owner approval.
