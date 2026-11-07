# Draft request — not sent

Hello Voy7 and ChampPG,

We maintain TechQuest: Industrial Frontier, a Minecraft Java 1.21.1 modpack using
NeoForge 21.1.264 and Java 21, and would like to explore adapting McWW3 to this platform.

We inspected the official McWW3 2.1-beta distribution without executing or decompiling it.
Its mod metadata declares All Rights Reserved and targets Forge 47.4.10+ / Minecraft
`[1.20,1.21)`, with an exact Distant Horizons 3.3.3 dependency. The distribution contains
no Java sources or Gradle build project.

Would you be willing to provide:

1. Access to the complete source/build project for 2.1-beta, including its matching
   dependency versions, mappings and any development instructions? Private access is fine.
2. Your permission and conditions for modifying the code for Minecraft 1.21.1 / NeoForge
   21.1.264, and clarification on whether a compiled derivative may be shared with testers
   or later distributed as part of a modpack.
3. Clarification of the terms for the separate core content pack (models, sounds and
   other assets), and whether you already plan an official 1.21.1 / NeoForge release.
4. Guidance on the Distant Horizons API coupling and whether the exact 3.3.3 requirement
   in the JAR is intentional, since the website describes the dependency as 3.3.3 or later.

We have not published your JAR, sources or content assets, and will not present a modified
build as an official McWW3 release. We can contribute changes upstream if that is your
preferred arrangement.

Project: https://github.com/Nessoro/TechQuest-Modpack
Investigation branch: experiment/mcww3-neoforge-21.1.264

Thank you.
