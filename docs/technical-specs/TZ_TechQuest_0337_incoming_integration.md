# TechQuest 0.3.3.7 — cumulative Incoming lethal damage integration

## Root cause in 0.3.3.6
PR #70 contains the Cataclysm entity-tracking crash fix, but forked from `chore/0335-unique-build-version` rather than PR #68. Its compiled pack therefore does not register or distribute the 3 first-party Incoming lethality Mixins. Neither passing GitHub Actions nor changing `range_cap` can restore omitted classes.

## Scope
Use PR #70 HEAD `ea76d901a6f90a0f268dc1b3ff77d543eba11a0e` as the base. Port precisely the first-party `IncomingLethalCapMixin`, `IncomingLegendaryBossMixin`, `IncomingLegendaryMiniBossMixin` from PR #68 and the additive Cataclysm damage-type tag for Incoming 3.10.4. Compile their bytecode with Java21 from repository source when making `techquest-compat-1.0.0.jar`, using 12 corrected minimal type-only stubs, not the two obsolete direct registry stubs.

Preserve `BossTrackingRangeMixin` version 0.3.3.6 with correct `EntityType.getKey(type)` linkage. Neither modify `damage_cap` globally nor bypass boss-scripted protection. Preserve original Incoming damage (partial or `Float.MAX_VALUE`) and normal physical reach; this integration is NOT unconditional instakill on every blast.

## Acceptance criteria
- A unique candidate version `0.3.3.7` in every manifest/installer/site/CI artifact.
- Unit tests verify 3 registered common Mixins, compiled Java classes in the exact compatibility JAR inside .mrpack, Cataclysm tag, preserved safe tracking, original full/partial Incoming amounts and no modifications for other sources.
- Windows EXE resource `--self-test`, client to menu and hash+security audits succeed on final SHA.
- Real world tests: spawn Ender Guardian and Ender Golem; compare `Health` before/after GBU-57 on bedrock and stone at 20 and 100 blocks, controlling regen. Repeat Legendary Monsters, two-phase Cataclysm fights and special-rule bosses outside/inside legitimate attack windows, zombie control and dedicated server. Check logs for Mixin incompatibility, attack geometry, and TPS.
- Keep draft; no automatic merge or release. A menu smoke is not proof that the bomb really kills in a loaded world.
