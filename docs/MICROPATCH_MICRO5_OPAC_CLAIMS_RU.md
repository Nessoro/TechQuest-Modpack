# TechQuest 0.3.3 — Open Parties and Claims (OPAC) beta 0.33.0

## Scope and dependencies

**Branch:** `feat/micro5-opac-claims-033`, based on `feat/micro5-refined-storage-033` (PR #41).  
**Request:** [#42](https://github.com/Nessoro/TechQuest-Modpack/issues/42); existing Xaero force-load issue [#39](https://github.com/Nessoro/TechQuest-Modpack/issues/39).  
**Platform:** Minecraft 1.21.1 / NeoForge 21.1.264 / Java 21.  
**Mod:** [official Modrinth version](https://modrinth.com/mod/open-parties-and-claims/version/neoforge-1.21.1-0.33.0), `gF3BGWvG`, `yWmXD7GW`, `open-parties-and-claims-neoforge-1.21.1-0.33.0.jar`, LGPL-3.0-only, beta; required client+server.

Official Modrinth version JSON was queried in GitHub Actions workflow on 2026-11-14. It reports **no required dependencies** (`dependencies=[]`) for this exact NeoForge artifact, SHA-1 `6075cf36ac8d70bd1fd870e0eb9ac84685388df7`, SHA-512 `646fd9796ef2dfd1132e22aacf1a417639233d90fb7eb862a718badfed955d54714c88327b7ddc651f98cd5b7d2a80e8c91233d2232680d4998fdd10ef392ffb`. The existing Xaero Minimap and World Map remain as currently pinned; exact in-game integration needs testing. Forge Config API Port and Fabric API are not added because this particular NeoForge version declares no mandatory dependencies.

**Do not remove** AE2, Refined Storage, IC2 Nostalgia, Create, Mekanism, BuildCraft or other gameplay mods. Do not replace Xaero maps or change worlds.

## New-world defaults

The **new-world-only** config is `compat/opac/openpartiesandclaims-server.toml`. The builder copies it to `defaultconfigs/openpartiesandclaims-server.toml` inside both generated client/server folders and `.mrpack` overrides. The Windows GUI, client and server installers only copy this exact path when it is not already present. They never overwrite an existing `saves/`, `world/`, `config/`, or `world/serverconfig/`.

- `maxPlayerClaims = 64`: claimed chunks; claiming does not imply force-loading.
- `maxPlayerClaimForceloads = 4`: at most four player-selected force-loaded claimed chunks under these default settings.
- `maxPlayerClaimsPermission = ""`, `maxPlayerClaimForceloadsPermission = ""`: stop permission-provider overrides of the default limits. Other administrator/player config bonuses could also affect limits: audit them with the installed version.
- `claimsSynchronization = "ALL"`: synchronize claim borders to clients for Xaero map integration.
- Protection remains as the **mod's own default**, rather than globally disabled or silently overridden. It is NOT proven safe for Incoming/Iskander explosives and fake-player automation. Test in disposable worlds first, then define an explicit protection policy.

These limits are **conservative starting values, not a benchmark**. A shared server with 8 players could have up to 32 forced chunks if all players reach the configured allowance, before any bonuses/privileged mechanics. Monitor TPS/MSPT, especially with energy networks and machine farms.

### Existing saves and dedicated servers

Existing worlds may have `<world>/serverconfig/openpartiesandclaims-server.toml` already, and NeoForge does not re-apply `defaultconfigs` over existing `serverconfig` files. Back up the world. Shut down Minecraft or the dedicated server, edit the *existing* OPAC server config's `[serverConfig.claims]` section using the same keys and values, and restart. If the mod has not created its config yet, launch it once in a disposable copy and then inspect the generated file before making changes. Do not copy a whole config from a different mod version. Consult the [official author guide](https://modrinth.com/mod/open-parties-and-claims) for config structure and operator commands.

### In-game interaction

Open **Xaero's World Map** and right-click/drag-select a chunk to claim or set force-load where permitted; the OPAC menu opens with the apostrophe key by default (rebind if conflicting with the user's controls). OPAC claim commands start with `/oclaims`, party commands with `/oparties`, and player-config commands with `/opac` in 0.33.0. A claim protects or reserves a chunk; it does not generate terrain or automatically force-load it. Choose force-loading explicitly.

## Runtime acceptance checklist (not yet completed)

1. CI: parse `modlist.json`, verify exact Modrinth version/file SHA-512/dependencies, `--resolve-only`; client/server jar set, downloadable archive, Windows GUI self-test, security pipeline.
2. Launch an actual NeoForge 1.21.1 client with both Xaero map mods; test player claim and force-load via map, and see visible boundaries in a new and upgraded disposable world.
3. Launch an actual dedicated NeoForge 21.1.264 server and join as client. Test claimed/force-loaded chunks after leaving the base, logout and restart, accounting for server offline-player behavior.
4. Verify 64/4 limits and absence of unexpected permission overrides or party bonuses. Monitor Spark TPS/MSPT while Create, IC2 Nostalgia, BuildCraft, Mekanism and AE2/Refined Storage networks work; limit claims when needed.
5. Test two friends/parties: ownership, access, claims touching, breaking/placing, pistons, fake players/automation, explosions, Incoming and Iskander Rocket damage. Decide which protections to preserve, without globally disabling them.
6. Test upgrades in the same install directory and confirm all world files, existing OPAC config, Xaero map data and user `options.txt` are unchanged.
7. No merge, release or advertised runtime compatibility before passing the above. Issue #42/#39 remain open pending verified gameplay tests.

## Verification evidence

Static test module: `tests/test_opac_claims.py`. The temporary metadata-probe workflow was used to retrieve the official SHA-512/dependencies and should be removed from the finalized branch. Successful static checks/CI do not prove real client or server startup.
