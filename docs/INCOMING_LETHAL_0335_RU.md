# TechQuest 0.3.3.5 — lethal Incoming strikes and boss health caps

**Status:** DRAFT. The candidate is built on 0.3.3.4 / PR #66. No Minecraft world or dedicated-server boss combat test has passed yet.

## Rule

Incoming 3.10.4 computes damage itself. A direct GBU-57 bore hit and the GBU-57 blast's crush-zone hit explicitly deliver `Float.MAX_VALUE`, meaning a lethal hit. The pressure / fragment / thermal models can instead calculate **partial** damage (including ~95% HP damage for catastrophic nonfatal injuries). **TechQuest must not change partial injuries into guaranteed kills.**

The Cataclysm base boss class `LLibrary_Boss_Monster.hurt()` clamps incoming damage to `DamageCap()`, before passing it to vanilla health and armor. For Ender Guardian this cap is 22 HP; Ender Golem's default cap is 999999 HP. This makes a lethal GBU-57 hit barely noticeable to Ender Guardian even with `range_cap=256`. New first-party Mixin `IncomingLethalCapMixin` redirects only that `Math.min` call **when the source is one of the 12 officially registered Incoming 3.10.4 damage types**. The original submitted amount then reaches the standard damage pipeline. Incoming-only ranged-strike handling also converts Cataclysm's attacker-to-victim distance to its existing -1 sentinel, because the remote operator can be thousands of blocks from a legitimate bomb impact. Incoming's own physical hit and pressure checks remain required. A second Incoming-only Mixin injection makes Cataclysm ignore **remote operator distance** (using its existing -1 sentinel) after Incoming's own geometry confirmed an actual hit. Normal Minecraft/other-mod range limits are untouched.

The original `cataclysm:bypasses_hurt_time` additive tag already included seven Incoming damage types; this patch adds five remaining Incoming types so Cataclysm's **own** damage bucket does not turn these hits into 0.1 HP. No vanilla `bypasses_invulnerability`, health setter, unconditional boss kill, generic damage cap change, Iskander alteration, or damage changes for Superb Warfare / other mods.

## What counts as lethal and what does not

- **Lethal**: the original Incoming code sends `Float.MAX_VALUE` for a verified physical hit, such as GBU-57 direct bore contact or a live target in the bomb's approximately 10-block crushing zone. If the target is legitimately damageable, generic Cataclysm per-hit caps may no longer stop it dying.
- **Severe but not necessarily fatal**: Incoming sends a finite health loss from blast, fragments, radiation, and other sources. Cataclysm receives that loss without its generic per-hit / DPS throttle; armor, shields, other natural rules, and the mod's actual hit geometry still apply.
- **Not a hit**: merely seeing terrain damage or a nearby explosion does not prove the target received a damage event. If the bomb missed, the target was behind intact cover, or damage wasn't registered, this Mixin cannot fabricate it.
- **Special boss mechanics**: invulnerability requiring a particular tool, opened ritual, crystal/weak-point sequence or a scripted vulnerability window remains in force; number of health phases **alone is not a reason for immunity**. The Aether Slider and Legendary Monsters Obliterator implementations remain untouched. Cataclysm's own scripted immunity checks execute before the base class's damage cap.

**Known limit:** this Mixin fixes Cataclysm's base damage cap; bosses implemented by other mods may have separate caps or scripted filters. No universal compatibility claim without real-world acceptance tests for the complete boss roster.

## Acceptance test: GBU-57 on bedrock

1. Install this test build into a **separate folder**. Back up existing worlds; test in disposable creative/flat world on Normal.
2. Set `config/cataclysm-common.toml` `range_cap = 256.0` for Ender Guardian and Golem (already migrated automatically only for known original defaults). Restart Minecraft.
3. Spawn Ender Guardian. In a controlled test, use `/data merge entity @e[type=cataclysm:ender_guardian,limit=1,sort=nearest] {NoAI:1b}` to halt regeneration; repeat separately with normal AI.
4. Immediately before and after **one** GBU-57 on bedrock, run `/data get entity @e[type=cataclysm:ender_guardian,limit=1,sort=nearest] Health`. Target GBU precisely; wait until all deferred Incoming damage queue stages finish. A missing entity after a valid hit suggests death; check death log, not only the client boss bar.
5. Repeat GBU-57 on ordinary stone, Ender Golem, zombie. For each, measure before/after on fresh target. Compare `incoming:kinetic` and `incoming:shockwave` vs near-miss wave damage.
6. Repeat a deliberately low-intensity Lancet/Grad near miss: it must **not** one-shot unrelated distant entities merely because its damage source is Incoming. Verify Netherite Monstrosity/other Cataclysm phases still work and Aether Slider / Obliterator keep their required mechanics.
7. Repeat on a separately consented NeoForge 21.1.264 dedicated server with the same compatibility JAR and report FPS/TPS/HP/logs; this is not proven by client menu smoke.

**Pass criteria:** a verified original Incoming lethal hit kills normally damageable bosses without silent Cataclysm cap reduction, partial impacts respect Incoming's computed partial damage, all other mod weapons behave as before, and required boss puzzle mechanics are preserved.

Sources: [Incoming 3.10.4 GBU-57 direct collision](https://github.com/zentixua/incoming/blob/v3.10.4/mod/src/main/java/ua/zentix/incoming/entity/BunkerBusterEntity.java), [Incoming 3.10.4 bunker crush zone](https://github.com/zentixua/incoming/blob/v3.10.4/mod/src/main/java/ua/zentix/incoming/warhead/Warheads.java), [Cataclysm boss damage cap](https://github.com/lender544/new1.20.1/blob/1.21/src/main/java/com/github/L_Ender/cataclysm/entity/AnimationMonster/BossMonsters/LLibrary_Boss_Monster.java).
