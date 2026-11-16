# TechQuest 0.3.3 — DimStorage 9.1.1 + EdivadLib 3.0.0

Test branch: feat/033-dimstorage-neoforge on top of the user-tested 0.3.3 integration branch (PR #25). PR #49 is draft. Main, previous installers and game saves are not changed.

## Official NeoForge 1.21.1 pins (verified by Modrinth API on 2026-11-15)

- DimStorage: project 8lnmIJH7; version R7rQFgQh / 9.1.1; DimStorage-1.21.1-9.1.1.jar (179454 bytes); SHA-512 b15b3e7ef7f0d5814d899ee7b9e87b4abf5add8039ad623ae97d77ad29de31dfe6407637c95b5c50b75c9a5698bbd193da45ece34bfabed7a7fa1c9069dae78f; AGPL-3.0-only.
- EdivadLib: required project a8Jk9kpK; version exl6hgWJ / 3.0.0; EdivadLib-1.21-3.0.0.jar (14133 bytes); SHA-512 3cb39fdc7ce4b68bf4681ef7395fb6b81961372b10a68784abedd33e2026d9c3841daa93d29a44f9872ef0287eac276f10ab8640a8543ae67e9ae294f28bd8b6; LGPL-3.0-only.
- Official API declares one mandatory dependency for this DimStorage version: EdivadLib. Both require client and server installation. Third-party JARs are fetched from their original publishers and checked against SHA-512.

## Preserved TechQuest mods

All 77 previously installed mods are retained: Oritech, Fluidic Tanks, Refined Storage + JEI, AE2, Create, Mekanism, IC2, BuildCraft, Open Parties and Claims, Xaero, etc. New total: 79 mod entries. No RPG Core reintroduction.

## Disposable-world test checklist

1. Install in a clean test profile; back up all existing worlds before any migration.
2. Check NeoForge main menu loads without DimStorage/EdivadLib errors.
3. Place two Dimensional Chests on the same and different frequencies. Verify shared inventory isolation and cross-chunk/dimension transfer.
4. Verify ownership, locking, and prohibited access by a second player.
5. Verify Dimensional Tanks and fluid transfer via Create, Mekanism, and Fluidic Tanks, including persistence after save/reload and no fluid duplication/loss.
6. Verify Dimensional Tablet access, multiplayer joins, and server performance.
7. Dedicated server testing requires explicit Minecraft EULA acceptance. A successful menu smoke does not imply successful world or multiplayer testing.

Keep PR draft until in-world acceptance. Existing stable release and main remain untouched.
