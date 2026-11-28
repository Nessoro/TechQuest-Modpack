# TechQuest 0.3.3.10 — scoped Monstrosity bridge and delivery evidence

Cumulative from PR #74 SHA 93af3dbc56b53b08d942abf3a188194b9b6e876a, inheriting tested PR #73. Version .9 was consumed by run 46140341723.

Cataclysm upstream 3.33 commit 10e21131b8eb2ce92be416409f91925e8c5decf0 establishes the independent IA hierarchy. Netherite_Monstrosity_Entity extends IABoss_monster, whose hurt method clamps and rejects distant sources separately from LLibrary_Boss_Monster. Preserve the concrete boss override (state 4 immunity, awakening, golem modifier) and multipart routing; do not globally alter invulnerability or death. IncomingMonstrosityMixin targets the IA parent but gates both existing-style injections on the exact concrete Monstrosity class name and the twelve existing Incoming types. Verify pinned JAR hashes and bytecode targets in CI; Java stub tests are not runtime proof. Other IA bosses and non-Incoming sources must remain unchanged. Test vulnerable/protected phases, direct/indirect partial/lethal and multipart hits in actual world.

Retain PR #74 selective tracking and safe EntityType.getKey. Audit pinned Legendary Monsters 2.2.4 registry and culling declarations; client render distance remains an open runtime gate. Ender Guardian intermittent zero-health issue not reproduced; preserve its death pipeline.

DragonRise 1.5.1 project 1346094 file 9208025: approved API access and explicit distribution permission are not yet confirmed. The diagnostic probe uses only a configured CURSEFORGE_API_KEY secret and API-returned exact official CDN URL; if authorization/metadata is missing it reports a blocker rather than inferring a URL. Capture size and both hashes; then review compliant delivery and implement required manifest/client/server/GUI changes atomically in a subsequent unique candidate. No silent manual fallback or claim of completion. Preserve PR #71 unmerged; no unreviewed recipes.

Run exact SHA CI, gameplay checks, EULA-gated server test and security audit before owner acceptance. See docs/BOSS_DRAGONRISE_03310_RU.md. No merge or stable release.
