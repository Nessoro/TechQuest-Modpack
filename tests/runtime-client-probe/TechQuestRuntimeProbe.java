package org.techquest.ci;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Map;
import java.util.TreeMap;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.client.event.ClientTickEvent;

/** CI-only menu observer and tutorial input, excluded from the player pack. No world/server. */
@Mod(value = "techquest_runtime_probe", dist = Dist.CLIENT)
public final class TechQuestRuntimeProbe {
    private int stableTicks;
    private boolean recorded;
    private boolean skippedGuide;
    private boolean selectedVanilla;
    private String previousState = "";
    private final Path report = Path.of(System.getProperty("techquest.probe.dir"));

    public TechQuestRuntimeProbe() {
        NeoForge.EVENT_BUS.addListener(this::onTick);
    }

    private static String quote(Object value) {
        return "\"" + String.valueOf(value).replace("\\", "\\\\").replace("\"", "\\\"") + "\"";
    }

    private static Object option(Object options, String method) throws ReflectiveOperationException {
        Object instance = options.getClass().getMethod(method).invoke(options);
        return Class.forName("net.minecraft.client.OptionInstance").getMethod("get").invoke(instance);
    }

    private static int geometry(Object screen, String name) throws ReflectiveOperationException {
        var field = screen.getClass().getDeclaredField(name);
        field.setAccessible(true);
        return field.getInt(screen);
    }

    private void clickRectangle(Object screen, String x, String y, String width, String height, String action)
            throws ReflectiveOperationException, java.io.IOException {
        double px = geometry(screen, x) + geometry(screen, width) / 2.0;
        double py = geometry(screen, y) + geometry(screen, height) / 2.0;
        Object accepted = screen.getClass().getMethod("mouseClicked", double.class, double.class, int.class)
            .invoke(screen, px, py, 0);
        if (!Boolean.TRUE.equals(accepted)) throw new IllegalStateException("CI tutorial input was not accepted: " + action);
        Files.writeString(report.resolve("ui-actions.log"), action + "\n", StandardOpenOption.CREATE, StandardOpenOption.APPEND);
    }

    private void onTick(ClientTickEvent.Post event) {
        try {
            Class<?> type = Class.forName("net.minecraft.client.Minecraft");
            Object game = type.getMethod("getInstance").invoke(null);
            Object screen = type.getField("screen").get(game);
            boolean title = Class.forName("net.minecraft.client.gui.screens.TitleScreen").isInstance(screen);
            boolean overlay = type.getMethod("getOverlay").invoke(game) != null;
            String state = (screen == null ? "null" : screen.getClass().getName()) + ":overlay=" + overlay;
            if (!state.equals(previousState)) {
                Files.writeString(report.resolve("screen-state.txt"), state + "\n");
                System.out.println("TechQuest CI screen: " + state);
                previousState = state;
            }
            // Known non-license tutorial only, in the disposable CI profile. Geometry
            // was inspected in the hash-pinned Explosion Overhaul 0.2.3.0 JAR.
            if (!overlay && screen != null && screen.getClass().getName().equals("com.vinlanx.explosionoverhaul.client.GuideSlidesScreen")) {
                if (!skippedGuide && Files.exists(report.resolve("guide-before.png"))) {
                    clickRectangle(screen, "continueButtonX", "continueButtonY", "continueButtonWidth", "continueButtonHeight", "Explosion Overhaul: Skip Guide");
                    skippedGuide = true;
                }
                return;
            }
            if (!overlay && screen != null && screen.getClass().getName().equals("com.vinlanx.explosionoverhaul.client.FirstTimeScreen")) {
                if (!selectedVanilla && Files.exists(report.resolve("mode-before.png"))) {
                    clickRectangle(screen, "rightBoxX", "rightBoxY", "rightBoxW", "rightBoxH", "Explosion Overhaul: Vanilla-like (existing default, CI only)");
                    selectedVanilla = true;
                }
                return;
            }
            stableTicks = title && !overlay ? stableTicks + 1 : 0;
            if (!recorded && stableTicks >= 40) {
                Object options = type.getField("options").get(game);
                Class<?> keyMapping = Class.forName("net.minecraft.client.KeyMapping");
                var wanted = new HashSet<>(Arrays.asList(System.getProperty("techquest.probe.bindings").split(",")));
                var bindings = new TreeMap<String, String>();
                var modifiers = new TreeMap<String, String>();
                for (Object mapping : (Object[]) options.getClass().getField("keyMappings").get(options)) {
                    String name = (String) keyMapping.getMethod("getName").invoke(mapping);
                    if (wanted.contains(name)) {
                        Object key = keyMapping.getMethod("getKey").invoke(mapping);
                        bindings.put(name, (String) key.getClass().getMethod("getName").invoke(key));
                        modifiers.put(name, ((Enum<?>) keyMapping.getMethod("getKeyModifier").invoke(mapping)).name());
                    }
                }
                var entries = new StringBuilder();
                for (Map.Entry<String, String> entry : bindings.entrySet()) {
                    if (!entries.isEmpty()) entries.append(',');
                    entries.append(quote(entry.getKey())).append(':').append(quote(entry.getValue()));
                }
                var modifierEntries = new StringBuilder();
                for (Map.Entry<String, String> entry : modifiers.entrySet()) {
                    if (!modifierEntries.isEmpty()) modifierEntries.append(',');
                    modifierEntries.append(quote(entry.getKey())).append(':').append(quote(entry.getValue()));
                }
                String settings = "{\"renderDistance\":" + option(options, "renderDistance")
                    + ",\"simulationDistance\":" + option(options, "simulationDistance")
                    + ",\"maxFps\":" + option(options, "framerateLimit")
                    + ",\"graphics\":" + quote(option(options, "graphicsMode")) + "}";
                Class<?> physics = Class.forName("net.diebuddies.config.ConfigClient");
                String physicsSettings = "{\"maxPhysicsObjects\":" + physics.getField("maxPhysicsObjects").get(null)
                    + ",\"blockPhysicsRange\":" + physics.getField("blockPhysicsRange").get(null)
                    + ",\"cpuThreads\":" + physics.getField("cpuThreads").get(null)
                    + ",\"oceanPhysics\":" + physics.getField("oceanPhysics").get(null)
                    + ",\"liquidPhysics\":" + physics.getField("liquidPhysics").get(null)
                    + ",\"windPhysics\":" + physics.getField("windPhysics").get(null)
                    + ",\"showSetup\":" + physics.getMethod("shouldShowQuickSetup").invoke(null) + "}";
                Files.writeString(report.resolve("ready.tmp"),
                    "{\"screen\":\"TitleScreen\",\"overlay\":false,\"stable_ticks\":40,"
                    + "\"world_loaded\":false,\"scope\":\"client main menu only\","
                    + "\"options\":" + settings + ",\"bindings\":{" + entries
                    + "},\"modifiers\":{" + modifierEntries + "},\"physics\":" + physicsSettings + "}\n");
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
