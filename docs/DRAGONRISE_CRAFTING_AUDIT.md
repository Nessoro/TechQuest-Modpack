# DragonRise crafting integration (draft)

Static evidence: [GitHub Actions audit](https://github.com/Nessoro/TechQuest-Modpack/actions/runs/46128787328).
Machine-readable inventory: `compat/dragonrise_inventory.json`.

The original 1.5.1 JAR uses the pre-1.21 plural recipe directory. Its recipes are not assumed loaded. New independent recipe IDs use the singular 1.21 directory in the existing TechQuest compatibility JAR. Vehicle assembly uses the actual Superb Warfare 0.8.9.2 serializer, including its entity-bearing deployment containers. Original third-party JARs and SBW recipes are unchanged. Every new recipe has NeoForge mod-loaded conditions. This is not a change to DragonRise acquisition or installation.

## Static scope

- registered_items: 67
- registered_entities: 185
- registered_blocks: 1
- static_player_facing_targets: 196
- new_recipes: 196
- legacy_recipe_targets: 118
- invalid_legacy_target: 1
- excluded: 57
- review_required: 0
- runtime_verified: false
- obtainable_coverage_percent: unknown

Tier assignments and costs are proposed balance decisions, not measured gameplay balance. All vehicle variants have separate recipe IDs, including Rafale, WWII vehicles, land/air/sea and logistics entries. The source registry has ordinary items as well as entities used as deployment data; these are distinct coverage units. External SBW ammunition recipes remain original. No hidden projectile or administrative spawner receives a recipe.

## Remaining gates

The hidden entries have explicit static scope decisions; review them before release. A real Minecraft client and dedicated-server session must confirm actual registry IDs, serializer decoding, survival crafting, JEI, container deployment, ammunition/repair and conditional absence. A successful static test is not runtime evidence and does not establish 100% obtainable coverage. No release or merge until review and all acceptance checks pass.

## Dedicated-server recipe decoding test

The new [runtime workflow](../.github/workflows/dragonrise-runtime.yml) compiles
a standalone test observer on PRs. Actual server execution is explicitly opt-in
through the Minecraft EULA checkbox, as in the existing server smoke workflow.
It uses the hash-matched original DragonRise JAR only in the disposable test
server, never in distribution, and tests absence followed by installation into
the same existing world and another restart. It checks decoded recipe IDs,
serializers, registered ingredients, item results, deployment-container entity
data and original SBW recipe ID retention. This is not a player crafting, JEI,
network synchronization, or deployment test. Do not use it alone to clear the
full obtainability release gate.

For a draft-only branch, use the already-registered [Smoke-test TechQuest server](https://github.com/Nessoro/TechQuest-Modpack/actions/workflows/smoke-server.yml) workflow, select branch `feat/dragonrise-complete-recipes`, and explicitly accept the EULA in its existing input. The branch workflow calls the additional DragonRise observer. The standard smoke job remains unchanged. Do not accept the EULA programmatically on behalf of another person.

## Review of the seven outstanding registrations

The deeper original JAR audit (https://github.com/Nessoro/TechQuest-Modpack/actions/runs/46139219780) found a dedicated generator item with real survival consumption, fuel handling, and stored-energy extraction. Added a tier 4 generator deployer recipe; its entity is not a separate output. Four hidden vehicles have server data but no audited player-facing deployment path; base Su-24 has only client vehicle data. Each remains excluded individually to avoid accidentally exposing unfinished content. These are conservative static scope decisions, not a declaration that the hidden vehicles can never work. Owner can reconsider them after runtime testing.

Updated static totals: 196 recipes, 57 excluded registry records, zero unclassified records. Runtime coverage remains unknown. The observer also compares actual decoded ingredient counts, output counts, and registry IDs; it does not replace manual survival gameplay/JEI testing.

## How to clear the release gate with real evidence

After the opt-in server workflow, preserve its exact JSON reports (absent,
present_existing_world, present_restart, expected) and recipe-fingerprint.txt
in `compat/dragonrise_runtime_evidence/` in this review branch. Do not commit
game logs containing private data, binaries, or worlds. The verifier rejects
missing/stale/mismatching evidence. The separate manual-acceptance.json must
contain recipe_fingerprint, review, checks, and obtainability. Each review/check
or obtainability entry has result: pass and an evidence reference to the actual
test record. Use the CHECKS set in scripts/dragonrise_acceptance.py and every
recipe ID in the generated expected.json; a representative tier smoke alone
cannot establish full obtainability. The submitted evidence requires human review.
No acceptance file is supplied because no real gameplay or server test has yet run.
