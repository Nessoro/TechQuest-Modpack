# TechQuest 0.3.3.3 — military weapon / boss compatibility task brief

## Scope
Continue Nessoro/TechQuest-Modpack from the 0.3.3.2 draft PR, using NeoForge 21.1.264, Java 21, Superb Warfare 0.8.9.2, Incoming v3.10.4 and Iskander 2.0.1. Do not alter established boss phase vulnerability, Aether Slider's pickaxe rule, Legendary Monsters Obliterator's special rules or timed weak points. Do not publish or merge without owner approval.

## Evidence
On the owner's 0.3.3.2 game video, helicopter weapons visually hit the Cataclysm Ender Golem but left HP at 150/150; several Incoming explosions damaged terrain but did not lower HP, although a separate series killed the golem. Iskander killed the golem but not the Obliterator. These observations do not prove a single root cause.

## First candidate
Add only specific missing damage type IDs to `cataclysm:bypasses_hurt_time` via a first-party data resource with `replace:false`. This changes Cataclysm's internal DPS damage bucket, not immunity, vanilla cooldown, hit detection, individual hit cap, or boss phases. It may change combat balance and is not yet verified in-game.

## Next engineering work if still failing
1. Reproduce one projectile or bomb at a time at 20 and 100 blocks with the Ender Golem active and with controlled `NoAI` + `is_Awaken` state.
2. Record server-side HP immediately before and after, plus a nearby zombie as explosion control.
3. Trace the pinned source call paths for Superb Warfare gunfire/vehicle cannon and Incoming 3.10.4 StagedExplosion / BlastBody.harm, including `LivingEntity.hurt` return values, source IDs, direct entity and attacker.
4. If legitimate hits are dropped before reaching `hurt`, implement a narrowly scoped first-party NeoForge integration compiled reproducibly, not a global damage override, `setHealth` write or invulnerability bypass.
5. Verify runtime in a real single-player world and dedicated server, package the same compat resources into both installers, and test preservation of original boss conditions.

## Acceptance criteria
Successful tests must demonstrate legal hits reduce HP, phases and tool restrictions remain intact, Iskander behavior does not regress, client/server builds remain reproducible, and the candidate is not published prematurely. Automated CI by itself is insufficient.
