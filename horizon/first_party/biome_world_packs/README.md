# Feature modifiers after world datapacks 0.1

This reviewed MIT correction extends the [merged-biome correction](../biome_modifiers/README.md)
at Horizon `c78187dffffb60f31517eadcb87413386e8ce729`. It is a separate
`core_patches` entry, not a `.hnmod`. All four native source bundles and eight
content modules keep their existing versions and bytes.

The content root contains the Oritech features, but the world's enabled
Terralith datapack subsequently replaces biome JSON. A generator audit found
that 125 of the 146 intended Overworld biomes lost their ore features: 35
vanilla and all 90 targeted Terralith biomes. Finding an ore block alone did
not establish the feature settings of every biome.

The content builder now saves the merged biome bundle before modifiers.
The creation and world-load paths replay only `add_features`/`remove_features`
after resolving enabled world packs. Replay restores the original feature
lists, retains other attributes, merges world biome tags with `replace`
semantics, then uses the existing modifier ordering and duplicate prevention.
Restoring original lists also removes additions from biomes that a replacing
world tag no longer targets. Spawn modifiers are not replayed.

The descriptor pins both source files, the exact diff and the Rust helper.
After Mixins, apply to a disposable generated stage and compile a new engine:

```sh
python3 horizon/tools/apply_worldpack_feature_patch.py --workspace "$TASK_STAGE"
```

The tool validates both inputs before applying the base correction. It refuses
unknown source bytes, source symlinks and an upstream checkout; repeating a
completed application is read-only. Resources, upstream source and existing
tools/installations remain untouched. The resource-cache stamp already includes
the engine's identity, so the new engine builds its own content cache.

New Oritech 0.2 installations require both reviewed core corrections. The
installer validates and locks the descriptor, diff and helper. Historical 02a
locks remain verifiable and are not upgraded in place.

`oritech_worldgen_biomes.rs` audits `GeneratorData` with the actual enabled
Terralith pack: the corrected result has one nickel and platinum feature in
each of the 146 targets; all five End targets remain unchanged.
`worldpack_feature_controls.rs` checks overriding biome data, non-feature
attributes, replacing tags, world-only biomes, add/remove order, idempotence
and the no-modifier control using independent synthetic data. The content
builder control also checks byte-identical vanilla biome/tag bundles.

The graphical ore probe's `--deepslate` mode mines naturally generated nickel
and platinum inside Terralith biomes in the Overworld, then checks inventory
and broken blocks after physically reopening the world. Only an iron pickaxe
and access space are fixtures; ores/features/raw items are not injected.
[Evidence and remaining limits](../../ORITECH_WORLDPACK_RESULT.json).

World-pack feature-modifier JSON overrides, world feature tags, spawn modifier
replay, whole-world RNG parity, a complete gathered survival run and licensed
dedicated client join remain outside this correction's verified scope.
