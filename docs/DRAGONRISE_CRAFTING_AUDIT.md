# DragonRise 1.5.1 crafting integration — audit scaffold (incomplete)

This branch is based on the merged optional-import PR #65. It contains no new
crafting recipes, no JARs, and no changes to the distribution mechanism. Do not
merge as complete: the registry and crafting coverage are still unknown.

## Reproduce the first audit step

Obtain the original NeoForge 1.21.1 [DragonRise release, file 9208025](https://www.curseforge.com/minecraft/mc-mods/sbw-drr/files/9208025)
and the [locked Superb Warfare 0.8.9.2 release](https://modrinth.com/mod/superb-warfare/version/bl7W8fjU).
Keep both outside Git. The audit checks the SBW SHA-512 against modlist.json
and records a local DragonRise fingerprint (not independent authentication).

```sh
python scripts/inspect_dragonrise_recipes.py --dragonrise /path/dragonrise_reforge-1.5.1-release.jar --superb-warfare /path/superbwarfare-0.8.9.2-mc1.21.1-c22d98c2.jar --output /path/dragonrise-evidence.json
```

The optional `--registries /path/registries.json` accepts a Minecraft runtime
registry report with an entries mapping per registry. Confirm that the report
was captured using the same installed JARs. The output is a starting point,
not a complete content inventory: inspect registration code, creative-tab
membership and stack components, cross-namespace registrations, nested JARs,
entity deployment mapping, original recipe conditions, and actual player-facing
obtainability before classifying every entry. Do not infer IDs from names or
translation keys. Keep third-party binaries and raw evidence out of Git.

## Implementation gates

- Inspect actual SBW workstation recipe codec, output/deployment stack format,
  and JEI integration from the pinned version. Validate on the running game.
- Build a reviewed inventory of every actual player-facing item and obtainable
  block, and individually justify technical exclusions. Track creative tabs,
  countries, existing obtainable recipes, new recipe IDs, tier, and method.
- Verify every ingredient against the actual installed mods. Use existing
  TechQuest progression, affordable ammunition and progressively more
  expensive WWII, Cold War, modern vehicles and advanced aircraft.
- Prefer the existing compat/techquest-compat package, with verified NeoForge
  optional-mod conditions and unique TechQuest recipe IDs. Confirm actual
  client, server, mrpack, GUI installer and update propagation before release.
- Add fail-closed coverage, ID, codec, graph, packaging and absence tests;
  verify original recipes are unchanged. Do not treat an empty inventory as
  100% coverage.
- Run client/server survival crafting, JEI and deployment tests on actual game,
  including existing worlds and optional DragonRise absence. Report CI results
  independently from runtime results.

No coverage number is asserted at this stage. The automated tests use synthetic
fixtures only and verify the evidence collector, not game behavior. No version
bump, mod addition/removal, or automatic installation change is included.
