package org.techquest.ci;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.client.event.ClientTickEvent;

/** CI-only observer. Never included in the player pack; changes no game behaviour. */
@Mod(value = "techquest_runtime_probe", dist = Dist.CLIENT)
public final class TechQuestRuntimeProbe {
    private int stableTicks;
    private boolean recorded;
    private final Path report = Path.of(System.getProperty("techquest.probe.dir"));

    public TechQuestRuntimeProbe() {
        NeoForge.EVENT_BUS.addListener(this::onTick);
    }

    private void onTick(ClientTickEvent.Post event) {
        try {
            Class<?> type = Class.forName("net.minecraft.client.Minecraft");
            Object game = type.getMethod("getInstance").invoke(null);
            Object screen = type.getField("screen").get(game);
            boolean title = Class.forName("net.minecraft.client.gui.screens.TitleScreen").isInstance(screen);
            boolean overlay = type.getMethod("getOverlay").invoke(game) != null;
            stableTicks = title && !overlay ? stableTicks + 1 : 0;
            if (!recorded && stableTicks >= 40) {
                Files.writeString(report.resolve("ready.tmp"),
                    "{\"screen\":\"TitleScreen\",\"overlay\":false,\"stable_ticks\":40,"
                    + "\"world_loaded\":false,\"scope\":\"client main menu only\"}\n");
                Files.move(report.resolve("ready.tmp"), report.resolve("ready.json"), StandardCopyOption.ATOMIC_MOVE);
                recorded = true;
            }
            if (recorded && Files.exists(report.resolve("stop"))) {
                type.getMethod("stop").invoke(game);
            }
        } catch (ReflectiveOperationException | java.io.IOException failure) {
            throw new IllegalStateException("TechQuest CI runtime observer failed", failure);
        }
    }
}
