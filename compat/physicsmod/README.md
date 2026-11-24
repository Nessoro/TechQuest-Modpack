# Physics Mod Lite 3.0.35 — client preset

Applies only to Modrinth version `wudTG1nk` (NeoForge 1.21.1). The original JAR is downloaded by URL and verified against the author's SHA512/SHA1; it is not modified or embedded here. See [the inspection snapshot](../../experiments/destruction/candidates.json).

The two JSON files are TechQuest settings, not copies of third-party code. Their paths, serialized property names and value types were inspected in the exact downloaded JAR using the JDK class-file inspector:

- `net.diebuddies.config.ConfigClient`: `reload` / `createConfig`, including `quickSetupNormalComplete`, `quickSetupProCompleteV2`, `firePhysicsRigidBodiesV2`, `blockSettings` and `mobSettings`. Public Java field names alone do not always match JSON keys.
- `net.diebuddies.config.ConfigServer`: default `collapse=true`; our singleplayer setting is `false`. Other fields retain their original defaults.
- `BlockSetting`, `MobSetting`, their physics-type enums and `AdjustableUtil`: nested keys are annotation IDs; enum values are serialized as ordinals. Blocky is `1`; mobs Off is `4`; no animation is `-1`.

`build_pack.client_config_overrides` includes these files only with the reviewed version and `client_only=true`. It rejects a version/side change until the preset is reviewed. The generated client and `.mrpack` use identical bytes. The Windows GUI and Python client bootstrap allow only these exact config paths and preserve existing files. Dedicated-server installers do not extract them.

Although one file is named `physics_server_config.json`, it is installed **only in the client profile** to disable additional collapse in the integrated singleplayer server. Never infer dedicated-server support from that filename.

Settings intentionally bound the first experiment to Blocky debris: 128 objects, 16-block activation range, Lifetime 2.0 with no variance, one physics worker, and other configurable visual physics disabled. The normal quick-setup wizard is marked complete to avoid replacing the preset. Incoming's own settings remain unchanged.

These are statically reviewed settings, **not a verified game configuration**. The first game test must inspect Physics Settings, block debris, persistence, Create/Sodium rendering, each explosion source and performance. [Russian test route](../../docs/PHYSICS_TESTING_RU.md).

Real client startup exposed the second quick-setup wizard. Both completion flags are now set; the exact serialized Pro-stage key is `quickSetupProCompleteV2`, not the Java field name. This skips setup only: ocean/liquid/wind physics stay off. The observer checks actual runtime limits and disabled effects; it never clicks a preset. Existing player files remain preserved.
