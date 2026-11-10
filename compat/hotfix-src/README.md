# Better Zoom 3.1.1 early client-config hotfix

The normal Better Zoom JAR stays an original SHA-pinned Modrinth download; TechQuest
does **not** distribute a modified third-party Better Zoom binary.

In repeated headless NeoForge 21.1.264 startup tests, Better Zoom 3.1.1
`ZoomHandler.onClientTick` called `Config.HOLD_TO_ZOOM.get()` before NeoForge
loaded the CLIENT config, causing an `IllegalStateException` and blocking
the main menu. The first-party, client-only Mixin skips *only* early ticks until
`Config.SPEC.isLoaded()`; normal zoom behavior runs once loading finishes.

The source is `compat/hotfix-src/techquest/compat/mixin/BetterZoomEarlyTickMixin.java`.
The corresponding Java 21 class was compiled using `javac --release 21 -g:none`
and minimal type-only stubs matching the pinned NeoForge 21.1.264,
Better Zoom 3.1.1, and SpongePowered Mixin APIs. **Only the compiled
`BetterZoomEarlyTickMixin.class` is included in the compatibility JAR;**
compilation stubs are not distributed.

The Mixin is registered in `compat/techquest-compat/META-INF/neoforge.mods.toml`
as `techquest-compat.mixins.json`. Do not update Better Zoom without
revalidating the target method and real client startup. A menu-only
smoke test cannot prove in-game zoom behavior or keyboard conflict freedom.
