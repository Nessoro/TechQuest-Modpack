// First-party oracle: executes original 1.21.1 forest_rock with a recording world.
package techquest.probes;

import com.google.gson.*;
import java.lang.reflect.*;
import java.nio.file.*;
import java.util.*;

public class ForestRockProbe {
    static Object blocks, rock, config, bedrock;
    static Class<?> registry, location, state, position, world, random, context;
    static Method parse, get, defaultState, isAir, directPlace, posY;

    static Object block(String key) throws Exception {
        return get.invoke(blocks, parse.invoke(null, key));
    }

    static JsonObject run(Object support, String key, long seed) throws Exception {
        JsonArray writes = new JsonArray();
        Object level = Proxy.newProxyInstance(world.getClassLoader(), new Class<?>[]{world}, (p, m, a) -> {
            if (m.getName().equals("I_")) return -64;
            if (m.getName().equals("f_")) return true;
            if (m.getReturnType() == state || m.getName().equals("u")) {
                Object at = a[0];
                int x = (Integer) position.getMethod("u").invoke(at);
                int y = (Integer) posY.invoke(at);
                int z = (Integer) position.getMethod("w").invoke(at);
                Object value = x == 0 && y == 79 && z == 0 ? support : bedrock;
                return m.getName().equals("u") ? isAir.invoke(value) : value;
            }
            if (a != null && a.length == 3 && position.isInstance(a[0]) && state.isInstance(a[1])) {
                JsonArray xyz = new JsonArray();
                for (String axis : List.of("u", "v", "w"))
                    xyz.add((Integer) position.getMethod(axis).invoke(a[0]));
                writes.add(xyz);
                return true;
            }
            throw new AssertionError("unexpected world query " + m);
        });
        Object rng = Class.forName("dyz").getConstructor(long.class).newInstance(seed);
        Object at = position.getConstructor(int.class, int.class, int.class).newInstance(0, 80, 0);
        Object ctx = context.getConstructor(Optional.class, world, Class.forName("duz"), random,
            position, Class.forName("eei")).newInstance(Optional.empty(), level, null, rng, at, config);
        boolean result = (Boolean) directPlace.invoke(rock, ctx);
        JsonObject row = new JsonObject();
        row.addProperty("support", key);
        row.addProperty("seed", seed);
        row.addProperty("result", result);
        row.add("writes", writes);
        row.addProperty("tail", (Integer) random.getMethod("a", int.class).invoke(rng, 1000000007));
        return row;
    }

    public static void main(String[] args) throws Exception {
        Class.forName("ab").getMethod("a").invoke(null);
        Class.forName("akt").getMethod("a").invoke(null);
        registry = Class.forName("jz"); location = Class.forName("akr");
        state = Class.forName("dtc"); position = Class.forName("jd");
        world = Class.forName("dds"); random = Class.forName("ayw"); context = Class.forName("ecg");
        blocks = Class.forName("lt").getField("e").get(null);
        parse = location.getMethod("a", String.class);
        get = registry.getMethod("a", location);
        defaultState = Class.forName("dfy").getMethod("o");
        isAir = state.getMethod("i"); posY = position.getMethod("v");
        Method wrap = registry.getMethod("e", Object.class);
        Object registryKey = registry.getMethod("d").invoke(blocks);
        Class<?> tag = Class.forName("awu");
        Map<Object, List<Object>> tags = new HashMap<>();
        for (String name : List.of("dirt", "base_stone_overworld")) {
            var resource = ForestRockProbe.class.getClassLoader().getResourceAsStream(
                "data/minecraft/tags/block/" + name + ".json");
            JsonObject original = JsonParser.parseReader(new java.io.InputStreamReader(resource)).getAsJsonObject();
            List<String> names = new ArrayList<>();
            for (var value : original.getAsJsonArray("values")) names.add(value.getAsString());
            Path extra = Path.of(args[0]).resolve("mods/terralith/carry/data/minecraft/tags/block/" + name + ".json");
            if (Files.exists(extra)) {
                JsonObject addon = JsonParser.parseString(Files.readString(extra)).getAsJsonObject();
                if (addon.get("replace").getAsBoolean()) throw new AssertionError("review replaced source tag");
                for (var value : addon.getAsJsonArray("values")) names.add(value.getAsString());
            }
            List<Object> members = new ArrayList<>();
            for (String key : new TreeSet<>(names)) {
                if (key.startsWith("#")) throw new AssertionError("review nested ground tag");
                members.add(wrap.invoke(blocks, block(key)));
            }
            tags.put(tag.getMethod("a", registryKey.getClass(), location).invoke(null,
                registryKey, parse.invoke(null, "minecraft:" + name)), members);
        }
        registry.getMethod("a", Map.class).invoke(blocks, tags);
        bedrock = defaultState.invoke(block("minecraft:bedrock"));
        config = Class.forName("eeb").getConstructor(state).newInstance(defaultState.invoke(block("minecraft:mossy_cobblestone")));
        rock = get.invoke(Class.forName("lt").getField("O").get(null), parse.invoke(null, "minecraft:forest_rock"));
        directPlace = Class.forName("ece").getMethod("a", context);
        Method key = registry.getMethod("b", Object.class);
        JsonArray cases = new JsonArray(), accepted = new JsonArray();
        int checked = 0;
        for (Object candidate : (Iterable<?>) blocks) {
            checked++;
            String name = key.invoke(blocks, candidate).toString();
            Object support = defaultState.invoke(candidate);
            JsonObject row = run(support, name, 263);
            cases.add(row);
            if (row.get("result").getAsBoolean()) {
                accepted.add(name);
                for (long seed : new long[]{0, 1, -1, Long.MAX_VALUE}) cases.add(run(support, name, seed));
            }
        }
        JsonObject result = new JsonObject();
        result.addProperty("block_types_checked", checked);
        result.add("accepted_ground", accepted);
        result.add("cases", cases);
        Files.writeString(Path.of(args[1]), result.toString());
        System.out.println("Ground types " + checked + ", cases " + cases.size() + ", accepted " + accepted);
    }
}
