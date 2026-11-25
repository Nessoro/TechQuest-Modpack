# TechQuest 0.3.3.5 — Incoming lethal weapon compatibility specification

## Owner decision

**Weapons from pinned Incoming 3.10.4 which calculate genuinely lethal hits must be lethal against ordinarily damageable enemies and bosses.** The presence of two or more health/combat phases alone is not a valid exception. Exceptions are bosses with *specific intentional prerequisites* (required tools or rituals, exposed weak points/crystals, or scripted vulnerability windows); these rules must still be respected.

Do not classify every nearby Incoming explosion as lethal. Preserve damage calculated by Incoming (including strong but nonfatal partial injuries), do not modify third-party JARs, do not globally override Minecraft invulnerability, and do not bypass boss-specific prerequisite logic.

## Proven code path

- Incoming 3.10.4 `BunkerBusterEntity.strike`: `incoming:kinetic`, `Float.MAX_VALUE` on bore-path entity intersection.
- Incoming 3.10.4 `Warheads.BunkerBlast.crushBodies`: `incoming:shockwave`, `Float.MAX_VALUE` within the physical crush radius (roughly 10 blocks for 2423 kg TNT).
- Other Incoming blast/fragment/heat code calculates fraction of max health; a partial hit must remain partial.
- Cataclysm 1.21 `LLibrary_Boss_Monster.hurt`: `Math.min(DamageCap(), amount)` before vanilla `LivingEntity.hurt`; Ender Guardian has a default 22 HP per-hit cap. The damage range issue is independently controlled by `range_cap` and already fixed in the parent branch.

## Initial implementation

Add a source-scoped Mixin to `LLibrary_Boss_Monster.hurt` to keep original submitted damage when the source is one of the 12 pinned Incoming damage IDs. Normal damage stays clamped. Add remaining Incoming damage types to the *additive Cataclysm-only* `bypasses_hurt_time` tag so its internal damage bucket cannot silently cap an otherwise lethal hit. No boss `setHealth`, broad bypass tag, damage override for Superb Warfare, changes to Incoming mod JAR or global entity properties.

Retain all native `hurt()` guards executed by individual bosses and vanilla armor/mitigation. The term 'lethal' in this spec means damage designed lethal by Incoming, not an absolute kill of targets without a legal hurt event.

## Verification

CI: source-scope and tag tests; rebuild committed Java 21 Mixin bytecode from checked-in stubs; Java behavioral unit harness verifies all 12 Incoming sources vs non-Incoming source and low-damage controls; pack and Windows EXE self-test; real client main-menu startup; security audit.

Gameplay: Ender Guardian and Ender Golem, GBU-57 bedrock vs stone, direct crush vs near miss, zombie; damageable Cataclysm bosses with two phases; all special-prerequisite bosses such as Aether Slider and Legendary Monsters Obliterator; single player and dedicated server. Record health immediately after hit and after regeneration. Probe false negatives due to hit detection, delayed work queue, boss animation guard or unavailable chunks, rather than adding global invulnerability bypass.

## Release gate and remaining work

No stable release or merging into main until client *and* dedicated-server boot, real boss combat acceptance and security review. For other boss mods, audit their exact damage caps and add individual narrowly scoped integrations only after reproducible failing traces. Do not claim all boss families solved solely by this Cataclysm patch.
