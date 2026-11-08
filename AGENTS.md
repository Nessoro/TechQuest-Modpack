# AGENTS.md — TechQuest: Industrial Frontier

These are persistent instructions for Codex and other coding agents working in this repository. Follow them for every task. Respond to the project owner in **Russian**, while preserving established names of files, symbols, and commands.

## 1. Project identity and source of truth

- Repository: `Nessoro/TechQuest-Modpack`. **Continue the existing project; do not recreate or replace it.**
- Current documented baseline (check the repository before every change): **TechQuest 0.3.2-alpha Optimized**, Minecraft Java **1.21.1**, NeoForge **21.1.264**, Java **21**.
- There is **one unified Optimized client profile**, not separate Lite and Full releases. Preserve gameplay content while improving performance for weaker and stronger PCs.
- Treat `modlist.json` as the configuration source of truth for the pack, its exact version pins, required/optional mods, client-only mods, and download records. The README may describe intentions or unverified functionality; do not treat descriptions as proof of a successful game launch.
- Read before relevant work: `README.md`, `MODPACK_README_RU.md`, `CONTRIBUTING.md`, `modlist.json`, `build_pack.py`, the affected `scripts/`, `windows-installer/`, `tests/`, and `.github/workflows/`.
- Start each task by checking the current branch, recent changes, and affected files. Avoid overwriting unrelated user or contributor changes.

## 2. Product requirements — do not regress

- Core industrial progression: **BuildCraft Community Edition**, **Industrial Craft 2: Nostalgia**, **Create**, **Mekanism**, **Modern Industrialization**, and **Applied Energistics 2**. Preserve the rest of the intended technology, adventure, magic, and exploration experience unless the owner explicitly requests changes.
- Preserve **Incoming: Air Strikes & Nukes 3.10.4**, **Xaero's Minimap / World Map**, **Health Indicator TXF** (numeric health), the Russian **Patchouli** in-game guide and **Open Loader** integration where compatible. Inspect `modlist.json` for precise pins rather than assuming every candidate is resolved.
- The game is intended for multiplayer with friends. Keep client and server mod sets compatible and respect `client_only` entries. Do not put client-only UI mods into dedicated server installations.
- The supported normal-player path on Windows 10/11 is a **graphical `TechQuestInstaller.exe` + official Minecraft Launcher**. Ordinary users must not need to install Python or run PowerShell/terminal commands. Developer-side Python scripts and CI are acceptable.
- Keep `.mrpack` export as an additional supported path, not as a replacement for the official Launcher installation flow. Do not require Prism Launcher.
- Do not silently change game version, NeoForge or Java pin, uninstall core mods, switch loader, split the unified profile, enable shaders by default, or remove GUI support.
- Performance is a product requirement: minimize unnecessary startup/memory/render overhead; distinguish client FPS from server TPS and world-generation load. Prefer profiling, reproducible benchmarks, and low-risk configuration changes over removing gameplay features.

## 3. Change procedure

1. **Inspect first.** Establish the current implementation and the exact issue; reproduce it when possible. Read existing tests and workflow definitions.
2. **Plan small, reviewable changes.** Make only requested or necessary modifications; state significant dependencies, compatibility risks, and assumptions.
3. **Verify source and licenses.** For each new/updated mod verify official origin, Minecraft 1.21.1/NeoForge support, dependencies, client/server side, release version, license/distribution restrictions, and checksums if available. A matching Modrinth tag alone does not prove runtime interoperability.
4. **Preserve integrity.** Keep pinned URLs/checksums and lockfiles coherent. Never replace a hash with an unverified value or quietly weaken download verification. Never insert arbitrary third-party executable binaries or JARs into the repo.
5. **Special case: IC2.** The repository already contains a pinned IC2: Nostalgia JAR in `manual-mods/` and references it from `modlist.json`. Do not duplicate, remove, move, re-upload, or relicense it without reviewing current usage and distribution rights. `scripts/include_industrialcraft.py` is a legacy helper; current builds already refer to IC2.
6. **Protect user data.** Do not overwrite users' existing `.minecraft`, `mods`, `saves`, `config`, or worlds by default. Install into a separate folder; document backups and rollback. Never commit access tokens, cookies, player data, private IPs, or unredacted logs.
7. **Document material changes.** Keep README/user installation instructions, `modlist.json`, tests, and workflows consistent with actual behavior. For new behavior add or adapt relevant automated tests.

## 4. Validation and CI

Use the checks appropriate to the files changed. The existing CI is the baseline:

```bash
python -m unittest discover -s tests -v
python build_pack.py --help
```

Relevant workflows:
- `.github/workflows/validate.yml` — repository validation and unit tests.
- `.github/workflows/audit-mods.yml` — remote mod availability / metadata audit; **not** a runtime compatibility test.
- `.github/workflows/build-alpha.yml` — build artifacts, manifest/download checks, Windows installer; **not** proof Minecraft actually starts.
- `.github/workflows/smoke-server.yml` — opt-in NeoForge dedicated-server boot check; requires the invoking user to explicitly accept the Minecraft EULA through workflow input. **Do not bypass that consent gate or assert success without a successful run.**

When needed and network/environment permits, run `python scripts/audit_modlist.py` and `python build_pack.py`; explain network dependencies and failures. Avoid massive downloads/builds when the task only changes instructions.

Before calling the pack playable or stable, seek evidence of: client reaching the main menu, dedicated server reaching `Done`, player joining with matching client/server versions, and a basic BuildCraft/IC2/Create integration and world-save test. Use logs, lock data, and profiling measurements. If these checks were not performed, explicitly say **"не проверено запуском Minecraft"**.

Do not claim antivirus/hash checks guarantee malware-free binaries or that dependency resolution guarantees mod compatibility. Treat failures as actionable, not as evidence of success.

## 5. Workflows, publishing, and agent behavior

- Prefer a focused branch/PR for substantive code changes; follow the owner's explicit direction for where to commit. Do not rewrite published history or force-push.
- **Do not publish releases, merge PRs, change repository settings, or mark the pack stable without the owner's explicit request.** Routine changes must never silently ship a new public release.
- Do not use external ChatGPT shared-chat links as a required source of project context: these may return HTTP 403 in cloud environments. This file and the actual repository are the persistent context.
- If the environment blocks a service or a command, report the exact blocker and continue with safe checks available locally; do not invent tool access or pretend tests ran.
- At the end of each task report in Russian: **what changed**, **which files**, **tests actually run and their results**, **remaining risks/blockers**, and **the next practical step**.
- Respect `CONTRIBUTING.md` and keep changes reproducible, minimally invasive, and easy to review.
