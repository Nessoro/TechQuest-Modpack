# TechQuest — boss weapon damage (candidate 0.3.3.2)

**Default behavior:** preserve scripted boss mechanics. This is NOT a universal
"always damage" override.

## Cause found in Cataclysm

Cataclysm's upstream NeoForge 1.21 `LLibrary_Boss_Monster.hurt()` rejects
damage when attacker distance is over 1.5 × `RangeLimit()`; published
defaults for many bosses are 12–38 blocks. That can explain distant cannon
shots appearing to hit without changing HP.

`conditions-preserved.toml` changes **only** Cataclysm's `range_cap` to
256.0 blocks for ten bosses and Prowler. Per-hit and DPS caps, special attack
phases and immunity checks remain unchanged. This COMMON config applies to
new singleplayer and dedicated-server installations. Installers preserve
existing `config/cataclysm-common.toml`: manually back up and change just
the `range_cap` keys in older profiles.

No changes are made to Aether Slider's pickaxe-only behavior, Ferrous
Wroughtnaut's vulnerability window, Legendary Monsters, Bosses of Mass
Destruction, or other boss mechanics.

`high-impact-experimental.toml` is an **unbundled reference**, not an
always-damage patch: increased range/damage/DPS caps do NOT override scripted
immunities or missing hit collision. Do not copy it wholesale over customized
config files or deploy to valuable worlds.

**Render:** client 16 chunks, server view 14, simulation 5. Client options
and server.properties from existing profiles are preserved. The server caps
the effective online render distance. On low-end PCs, lower render distance
manually; 16 chunks can markedly increase memory/CPU/GPU load.

## Required in-game validation

On a throwaway world, test actual HP (not only impact VFX) at 20/100/200
blocks with Superb Warfare infantry guns and helicopter cannon, Incoming
strikes and Iskander rocket. Repeat on dedicated NeoForge server. Confirm
Aether Slider remains pickaxe-gated and Ferrous Wroughtnaut damage is
blocked outside his attack window. Other bosses and nonstandard damage
sources may still reject attacks. Report log and exact projectile IDs.

**CI unit tests are not a Minecraft runtime test.** A true optional
always-damage mode requires per-mod, phase-aware source/attack hooks;
it has not been implemented or verified.

Upstream: https://github.com/lender544/new1.20.1/tree/1.21
