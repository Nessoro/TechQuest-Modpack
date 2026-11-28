// First-party reflection oracle for the official, hash-pinned Minecraft 1.21.1 jar.
// Inputs are synthetic-palette test cases; no game/client/world is started.
package techquest.probes;

import com.google.gson.*;
import java.lang.reflect.*;
import java.nio.file.*;
import java.util.*;

public class NoiseStateProbe {
    static Class<?> random, params, state;
    static Object registry;
    static Method parse, getBlock, defaultState;

    static Object block(String name) throws Exception {
        return defaultState.invoke(getBlock.invoke(registry, parse.invoke(null, name)));
    }

    static List<Object> blocks(JsonArray names) throws Exception {
        List<Object> out = new ArrayList<>();
        for (JsonElement value : names) out.add(block(value.getAsString()));
        return out;
    }

    static Object parameters(JsonObject spec) throws Exception {
        List<Double> amplitudes = new ArrayList<>();
        for (JsonElement value : spec.getAsJsonArray("amplitudes")) amplitudes.add(value.getAsDouble());
        var constructor = params.getDeclaredConstructor(int.class, List.class);
        constructor.setAccessible(true);
        return constructor.newInstance(spec.get("firstOctave").getAsInt(), amplitudes);
    }

    public static void main(String[] args) throws Exception {
        Class.forName("ab").getMethod("a").invoke(null);
        Class.forName("akt").getMethod("a").invoke(null);
        random = Class.forName("ayw");
        params = Class.forName("eoh$a");
        state = Class.forName("dtc");
        Class<?> position = Class.forName("jd"), location = Class.forName("akr");
        registry = Class.forName("lt").getField("e").get(null);
        parse = location.getMethod("a", String.class);
        getBlock = Class.forName("jz").getMethod("a", location);
        defaultState = Class.forName("dfy").getMethod("o");
        List<String> names = List.of("minecraft:stone", "minecraft:dirt", "minecraft:clay", "minecraft:grass_block");
        List<Object> palette = new ArrayList<>();
        for (String name : names) palette.add(block(name));
        JsonArray output = new JsonArray();
        JsonArray cases = JsonParser.parseString(Files.readString(Path.of(args[0]))).getAsJsonArray();
        for (JsonElement item : cases) {
            JsonObject row = item.getAsJsonObject(), old = row.getAsJsonObject("legacy");
            long seed = old.get("seed").getAsLong();
            float scale = old.get("scale").getAsFloat();
            Object noise = parameters(old.getAsJsonObject("noise")), provider;
            Class<?> type;
            switch (row.get("kind").getAsString()) {
                case "noise_provider" -> {
                    type = Class.forName("egn");
                    var constructor = type.getDeclaredConstructor(long.class, params, float.class, List.class);
                    constructor.setAccessible(true);
                    provider = constructor.newInstance(seed, noise, scale, blocks(old.getAsJsonArray("states")));
                }
                case "dual_noise_provider" -> {
                    type = Class.forName("egl");
                    Class<?> inclusive = Class.forName("ayg");
                    JsonObject range = old.getAsJsonObject("variety");
                    Object variety = inclusive.getConstructor(Comparable.class, Comparable.class).newInstance(
                        range.get("min_inclusive").getAsInt(), range.get("max_inclusive").getAsInt());
                    var constructor = type.getDeclaredConstructor(inclusive, params, float.class, long.class,
                                                                  params, float.class, List.class);
                    constructor.setAccessible(true);
                    provider = constructor.newInstance(variety, parameters(old.getAsJsonObject("slow_noise")),
                        old.get("slow_scale").getAsFloat(), seed, noise, scale, blocks(old.getAsJsonArray("states")));
                }
                case "noise_threshold_provider" -> {
                    type = Class.forName("ego");
                    var constructor = type.getDeclaredConstructor(long.class, params, float.class, float.class,
                                                                  float.class, state, List.class, List.class);
                    constructor.setAccessible(true);
                    provider = constructor.newInstance(seed, noise, scale, old.get("threshold").getAsFloat(),
                        old.get("high_chance").getAsFloat(), block(old.get("default_state").getAsString()),
                        blocks(old.getAsJsonArray("low_states")), blocks(old.getAsJsonArray("high_states")));
                }
                default -> throw new IllegalArgumentException("unknown provider type");
            }
            JsonArray xyz = row.getAsJsonArray("position");
            Object at = position.getConstructor(int.class, int.class, int.class).newInstance(
                xyz.get(0).getAsInt(), xyz.get(1).getAsInt(), xyz.get(2).getAsInt());
            Object rng = Class.forName("dyz").getConstructor(long.class).newInstance(row.get("random_seed").getAsLong());
            Object selected = type.getMethod("a", random, position).invoke(provider, rng, at);
            int index = palette.indexOf(selected);
            if (index < 0) throw new AssertionError("unexpected block outside synthetic palette");
            output.add(names.get(index));
        }
        Files.writeString(Path.of(args[1]), output.toString());
        System.out.println("Provider reference cases: " + output.size());
    }
}
