# TechQuest 0.3.3: Refined Storage — Quartz Arsenal (issue #54)

## Status
Included in the test branch `feat/033-refined-storage-quartz-arsenal` and PR #55.
The module must remain in testing until wireless crafting and client/server
behavior have been tested in Minecraft. This is not a new stable release.

## Official source and fixed version
- Source: https://modrinth.com/mod/refined-storage-quartz-arsenal/version/toDdIhGu
- Modrinth project ID: `gnwGOmBf`
- Version ID: `toDdIhGu`, release `1.0.8`
- Minecraft: Java `1.21.1`, loader: NeoForge
- Required environment: client and server
- Filename: `refinedstorage-quartz-arsenal-neoforge-1.0.8.jar`
- File size: 67,115 bytes
- SHA-512:
  `faa6530135978a86b25301dd5a5ec673d9908edde01780e4f7ba72e3ead18a0c142a578c428fe49df650c8cca03ec69cdf7a97012b5852f3514fddd23052c8d9`
- SHA-1: `510c20c2b4531ceaa99f19ba6bc4671650df7a81`
- License: MIT
- Official required dependency: Refined Storage `KDvYkUg3`; an exact dependency version is not imposed by the Modrinth release. TechQuest already pins RS `2.0.9`.
- Check: [GitHub Actions run 44505908861](https://github.com/Nessoro/TechQuest-Modpack/actions/runs/44505908861) downloaded the original Modrinth JAR and independently matched SHA-512 and SHA-1 against official metadata.
- Keep the original JAR as a Modrinth download only; do not commit or redistribute it inside the repository or installer.

## Functionality
Quartz Arsenal provides the **Wireless Crafting Grid**, which must be linked to a
Refined Storage network and charged. The network must have a Wireless Transmitter.
The Creative Wireless Crafting Grid is also provided for creative-mode use.

Interdimensional Wireless Transmitter (issue #52, merged in PR #53) is retained in the
pack. Its dimension/range behavior is **not** a guarantee that unloaded chunks
or an unpowered RS controller keep working.

## Required manual playtest
- [ ] Fresh clean instance: Minecraft 1.21.1, NeoForge 21.1.264, Java 21.
- [ ] Confirm original RS 2.0.9, Quartz Arsenal 1.0.8, IWT and RS-JEI integration
      load together without missing mod errors.
- [ ] Join a test world, craft Wireless Crafting Grid through JEI, bind it to a
      network device and power it.
- [ ] With Wireless Transmitter on the network, open wireless crafting,
      insert/extract items and craft while nearby and farther away.
- [ ] Recheck resource counts, especially duplication regression fixed in 1.0.8.
- [ ] Check charged, uncharged and low-power terminal behavior and RS controller
      energy supply; do not change existing energy settings to mask errors.
- [ ] With IWT, repeat access from Nether and End; check behavior when network
      chunks unload and when the server restarts.
- [ ] Dedicated server + two players: same mods on both sides, same item counts,
      client rejoin, world save and restart, no crashes or client/server desync.
- [ ] Observe FPS/TPS and logs near existing Create/Mekanism/RS setups.
- [ ] Confirm player worlds, configuration and bindings are preserved on update.

## Automation / CI
- `tests/test_quartz_arsenal.py`: exact version, official hash,
  retained parent mods, both sides and Modrinth manifest.
- `.github/workflows/build-alpha.yml`: validate original downloaded
  JAR on client and server, SHA-512 and `.mrpack` manifest entry.
- `.github/workflows/smoke-client.yml`: real client title-screen smoke
  and same JAR hash checks on client/server.
- `docs/index.html`: derived website catalog entry.
