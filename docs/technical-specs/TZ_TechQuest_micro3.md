# Technical Specification No. 1 — TechQuest 0.3.3-micro3

## Remove RPG Core while preserving TechQuest Compatibility

**Revision:** November 14, 2026  
**Repository:** https://github.com/Nessoro/TechQuest-Modpack  
**Implementation PR:** https://github.com/Nessoro/TechQuest-Modpack/pull/30 (draft)  
**Implementation branch:** `fix/micro3-remove-first-party-mods-033`  
**Base branch:** `feat/micro2-rpg-core-033`  
**Target platform:** Minecraft Java 1.21.1, NeoForge 21.1.264, Java 21.

### Objective
Completely exclude the in-house TechQuest RPG Core 0.1.0 from future client, dedicated-server, Modrinth and Windows distribution packages **without losing TechQuest Compatibility 1.0.0**. Project MMO (PMMO) must not be reintroduced.

### Mandatory requirements
1. Remove `techquest-rpg-core-0.1.0.jar` from the generation pipeline, `output/client/mods`, `output/server/mods`, `.mrpack`, the server bootstrap and the Windows GUI installer.
2. Keep `techquest-compat-1.0.0.jar` wherever required, preserving both functions: **Create ↔ Industrial Craft 2: Nostalgia** compatibility recipes and the client-side **Better Zoom** early-initialization Mixin workaround.
3. Prevent RPG Core and PMMO JARs from reappearing when an existing profile is upgraded.
4. Do not modify unrelated mod selections or configuration, including BuildCraft, Create, IC2, Mekanism, AE2, FTB Ultimine, Physics Mod, Incoming or Patchouli.
5. Preserve a single Optimized profile installed through the official Minecraft Launcher. End users must not need Python, a command line or Prism Launcher.
6. Preserve `saves`, `config`, `options.txt`, maps and Minecraft Launcher data. When upgrading `mods`, implement a predictable backup location and rollback mechanism; avoid creating numerous duplicate backups.
7. Do not modify the already published micro2 preview, merge PRs or publish releases without explicit owner approval.

### Components to inspect and modify

| Component | Required outcome |
|---|---|
| `build_pack.py` | RPG Core JAR is no longer generated; Compatibility JAR is generated and packaged correctly |
| `scripts/install_client.py` | Compatibility extraction remains allowed; RPG Core is not included in the supported installation path |
| `scripts/install_server.py` | Compatibility is installed, RPG Core is not; the Superb Warfare server workaround remains intact |
| `windows-installer/Program.cs` | GUI installs the current Compatibility JAR, never restores RPG Core, and safely replaces the `mods` folder |
| `.github/workflows/build-alpha.yml` | Assert RPG Core/PMMO are absent and Compatibility is present in client, server and `.mrpack` |
| `tests/` | Add positive/negative regression tests, repeat-install coverage and rollback checks |
| `README.md`, `docs/MICROPATCH_MICRO3_RU.md` | Keep installation guidance, limitations and risks accurate |

### Verification plan
- **Unit tests:** run `python -m unittest discover -s tests -v`.
- **Full packaging:** run `python build_pack.py`; verify downloaded hashes and `modrinth.index.json` consistency.
- **Windows GUI:** build `TechQuestInstaller.exe`, run its self-test, complete a clean installation and upgrade a disposable profile containing the legacy RPG Core. Confirm the previous `mods` folder is retained in one backup location and rollback works after an injected or reproducible failure.
- **Runtime:** launch a real Minecraft client to the main menu and create a fresh test world. Validate Create ↔ IC2 recipes and Better Zoom behavior. Bring the dedicated server to `Done` and connect a client **only after explicit acceptance of the Minecraft EULA**.
- **Separate known mining defect:** reproduce mining of a single block with Ultimine inactive, then a vertical column test with Ultimine and Physics Mod. **Removing RPG Core is not, by itself, proof that unexpected upward block destruction is fixed.**

### Acceptance criteria
- [ ] No future distribution contains RPG Core or PMMO.
- [ ] Compatibility exists in client, server, `.mrpack` and the Windows installer; its two functions are verified in the actual game.
- [ ] Client, dedicated server, Windows GUI and repeat installation work correctly.
- [ ] Existing worlds and user settings are preserved; rollback has been tested.
- [ ] Unit tests, full build, installer self-test and auditing are green for the relevant commit SHA, and a real-game test report is attached to PR #30.

### Out of scope
Redesigning FTB Ultimine or Physics Mod, replacing IC2, introducing industrial mods, and publishing a public release. Track the upward-mining defect separately if necessary.

### Deliverables and Codex handoff
Commit only to the existing implementation branch and update PR #30. Provide changed-file inventory, client/server package manifest, reproducible test logs, remaining risks and the next action. Update `docs/TECHQUEST_033_DEVELOPMENT_JOURNAL_RU.md` with dated evidence. Do not claim stability until runtime validation is complete.
