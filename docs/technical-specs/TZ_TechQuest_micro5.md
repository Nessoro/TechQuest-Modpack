# Technical Specification No. 3 — TechQuest 0.3.3-micro5

## Integrate Iskander Rocket Mod 2.0.1

**Revision:** November 14, 2026  
**Repository:** https://github.com/Nessoro/TechQuest-Modpack  
**Implementation PR:** https://github.com/Nessoro/TechQuest-Modpack/pull/34 (draft)  
**Implementation branch:** `feat/micro5-iskander-rocket-033`  
**Base:** micro4 — `feat/techquest-trash-pipes-reactor-micro4`  
**Target platform:** Minecraft Java 1.21.1, NeoForge 21.1.264, Java 21.

### Objective
Include the **original Iskander Rocket Mod 2.0.1** in both TechQuest client and dedicated-server packages, with a verifiable official download and a controlled in-game test, without replacing Incoming or Superb Warfare.

### Exact mod version
- **Author:** rcatlab. **Official page:** https://modrinth.com/mod/iskander-rocket-mod.
- **Modrinth project ID:** `XUogRnhj`; **version ID:** `M1b2lYax`.
- **Version:** `2.0.1+mc1.21-1.21.1-neoforge`.
- **Filename:** `iskander-2.0.1+mc1.21-1.21.1-neoforge.jar`.
- **SHA-512:** `539ea44461455b3af6e799e17c59d8284300c06b81f6012f687fe8031452c5e60fa0a93d8e59229d4717d0032e53408f80ad7670a681a932acf736a574a7a07c`.
- According to the verified Modrinth metadata: **MIT license**, both client and server, and no declared mandatory dependencies. These metadata **do not replace runtime tests**.
- **Iskander Rocket** and **Iskandert's Library** are separate projects; the rocket has no declared dependency on that library.

### Functional requirements
1. Include the official JAR in the client and dedicated-server distributions. The `.mrpack` and Windows GUI installation path must use the verified download URL and SHA-512. **Never commit a copied third-party JAR into the source repository, modify it or repackage it.**
2. Preserve Incoming: Air Strikes & Nukes 3.10.4, Superb Warfare and all other approved mods. Iskander must work **independently**. Do not claim automatic integration with Incoming or the Broken Arrow bridge in this patch.
3. Test the missile launcher, X/Z coordinate controller, gameplay behavior and JEI recipes. The author describes a **3×3 placement footprint**, **9 blocks of overhead clearance** and **64–10,000 blocks** of range; validate these claims against the selected release rather than assuming them to be verified in TechQuest.
4. Check missile arrival, crater formation and blast/shockwave behavior. The author's stated effects reaching up to **150 blocks** are **not an independently measured TechQuest result**.
5. Preserve a **Russian-language in-game Patchouli page** documenting controls, destructive effects, backups and safe testing.
6. Preserve IC2: Nostalgia, TechQuest Compatibility 1.0.0, Trash Cans and Pretty Pipes. Do not reintroduce RPG Core, PMMO, Colossal Reactors or Iskandert's Library.

### Safety and performance requirements
- Carry out destructive tests **only in a new Creative Mode test world**, away from any valuable builds. Make a backup before testing an existing world.
- Start with **one missile launch**, then verify the world after saving and reloading. Multi-missile salvos are not part of initial acceptance.
- Record real client FPS, dedicated-server TPS, approximate numbers of destroyed blocks, world-save delays and post-reload state, with Spark profiles and reproducible test configuration.
- Test crossing chunk boundaries and behavior when the player moves away from the target. **Do not guarantee success through unloaded chunks until demonstrated.**
- Investigate whether server-admin controls or launch permissions exist. If they do not, document that fact; do not invent commands or configuration options.

### Files and components to update

| File/component | Required change |
|---|---|
| `modlist.json`, `modrinth_lock` | Pin project/version IDs, filename, SHA-512 and client/server sides |
| `scripts/inspect_iskander_rocket.py` | Verify official source, release metadata and declared dependencies |
| `.github/workflows/build-alpha.yml` | Assert the correct JAR on both sides, `.mrpack` entry and hash |
| `tests/test_iskander_rocket.py` | Add composition regression checks and exclusions |
| `scripts/guide_assets.py` | Add a Russian-language Patchouli guide for Iskander |
| `scripts/sync_site_mods.py`, `docs/index.html` | Update the public mod catalog |
| `README.md`, `docs/MICROPATCH_MICRO5_ISKANDER_RU.md` | Document installation, safety, limitations and actual results |

### Acceptance criteria
- [ ] Unit tests and full package build pass with SHA-512 verification.
- [ ] Client, dedicated-server package and `.mrpack` contain **exactly the selected Iskander release**; obsolete reactor libraries do not reappear.
- [ ] The Windows EXE builds and passes self-test; users install without Python.
- [ ] A real Minecraft client launches, creates and saves a world; the server reaches `Done` **after explicit EULA consent** and accepts a joining player.
- [ ] A single missile launch and a distant-target test are performed, with documented destruction, FPS/TPS, world integrity and any failures.
- [ ] Coexistence with Incoming is verified without simultaneous large-scale strikes.
- [ ] CI/build/security evidence corresponds to the same commit SHA. Do not label the patch stable without a real game test.

### Out of scope
Developing new missiles or custom ballistics, integrating the Broken Arrow bridge, rewriting explosion mechanics, FTB Industrial, Colossal Reactors, replacing IC2 or publishing without approval.

### Deliverables and Codex handoff
Update the existing PR #34 with the exact file changes, verified manifests, real client/server/missile-test logs, performance results and outstanding risks. Append a dated status entry to `docs/TECHQUEST_033_DEVELOPMENT_JOURNAL_RU.md`. Do not merge or publish automatically.
