# Merged-biome core correction 0.1

Reviewed MIT source correction for Horizon
`c78187dffffb60f31517eadcb87413386e8ce729`, applied only to a generated Mixins
stage. This is **not** a `.hnmod` or a claim that the SDK implements the fix.
The native tools build records its exact source/patch hashes separately in
`core_patches`; the installer requires and locks those files for Oritech 0.2.

The pinned `mod_content.rs` leaves custom biome files out of the worldgen bundle,
filters their IDs out of tags and applies modifiers to the original vanilla
bundle. Therefore an ore modifier can affect vanilla biomes while skipping the
registered Terralith biomes. `merged-biomes.patch` makes three changes:

1. Include declared biomes in the worldgen bundle.
2. Keep their registered IDs when filtering biome-tag entries. Unknown IDs still
   leave the tag.
3. Apply modifiers to the merged bundle and write changed individual biome files
   back, preserving the existing modifier ordering and duplicate prevention.

The complete upstream source is not vendored. The diff and the retained MIT
license identify the adapted source. `horizon-core-patch.json` pins the original
file, final file and exact diff. Apply after Mixins and before compiling:

```sh
python3 horizon/tools/apply_biome_modifier_patch.py --workspace "$TASK_STAGE"
```

The tool refuses an upstream checkout, a stage without the expected marker,
symlinks and any different source bytes. An exact repeat performs no write.
Mixins 0.6 refuses transformations of these functions because they contain `?`
and closures; that is why this correction uses a separate explicit patch.
Pristine source, prepared resources and older tools/locks are not changed.

`horizon/probes/check_biome_modifiers.py` compares the original and corrected
content builders: the custom biome and its tag survive, one feature is added
once to the vanilla and custom target, an unknown biome is still excluded,
an untargeted desert stays unchanged and a build without mods preserves the
vanilla biome/tag bundles byte for byte. The Oritech/Terralith content build
contains 162 biomes: 67 vanilla and 95 Terralith (including nested cave files).
The original overworld selector reaches 56 vanilla and 90 Terralith biomes;
the other five custom biomes are outside that source tag, so this fix does not
force ores into them.

Game checks remain separate from this content-root proof. The graphical ore
probe enables the actual Terralith datapack, finds naturally generated nickel
in its biome, mines it, visits the End and mines natural platinum, then checks
raw items and broken blocks after reopening. World generation RNG parity and
natural overworld deepslate platinum are not established by those checks.
