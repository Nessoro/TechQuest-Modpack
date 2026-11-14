// First-party codec probe for the official, hash-verified 1.21.1 server bundle.
package techquest.probes;

import com.google.gson.*;
import com.mojang.serialization.*;
import java.lang.reflect.*;
import java.nio.file.*;
import java.util.*;

public class MultifaceDefaultsProbe {
    static Codec<?> codec;
    static DynamicOps<JsonElement> ops;
    static Object blocks;
    static Method name;
    static JsonArray output = new JsonArray();

    static void walk(JsonElement value, String path) throws Exception {
        if (value.isJsonArray()) {
            for (JsonElement child : value.getAsJsonArray()) walk(child, path);
        } else if (value.isJsonObject()) {
            JsonObject row = value.getAsJsonObject();
            if (row.has("type") && row.get("type").isJsonPrimitive()
                    && row.get("type").getAsString().equals("minecraft:multiface_growth")) {
                JsonObject config = row.getAsJsonObject("config");
                if (!config.has("block")) {
                    Object decoded = codec.parse(ops, config).getOrThrow();
                    JsonObject proof = new JsonObject();
                    proof.addProperty("source", path);
                    proof.addProperty("block_omitted", true);
                    proof.addProperty("decoded_block", name.invoke(blocks,
                        Class.forName("een").getField("b").get(decoded)).toString());
                    output.add(proof);
                }
            }
            for (JsonElement child : row.asMap().values()) walk(child, path);
        }
    }

    @SuppressWarnings("unchecked")
    public static void main(String[] args) throws Exception {
        Class.forName("ab").getMethod("a").invoke(null);
        Class.forName("akt").getMethod("a").invoke(null);
        Class<?> registry = Class.forName("jz");
        Object all = Class.forName("lt").getField("aA").get(null);
        Object lookup = Class.forName("ka").getMethod("a", registry).invoke(null, all);
        ops = (DynamicOps<JsonElement>) Class.forName("akp").getMethod(
            "a", DynamicOps.class, Class.forName("jo$a")).invoke(null, JsonOps.INSTANCE, lookup);
        codec = (Codec<?>) Class.forName("een").getField("a").get(null);
        blocks = Class.forName("lt").getField("e").get(null);
        name = registry.getMethod("b", Object.class);
        Path root = Path.of(args[0]).resolve("mods/terralith");
        for (String section : List.of("carry", "outside")) {
            try (var paths = Files.walk(root.resolve(section).resolve("data"))) {
                for (Path path : paths.filter(p -> p.toString().endsWith(".json")).sorted().toList())
                    walk(JsonParser.parseString(Files.readString(path)), root.relativize(path).toString());
            }
        }
        if (output.isEmpty()) throw new AssertionError("no multiface configurations found");
        Files.writeString(Path.of(args[1]), output.toString());
        System.out.println("Multiface configuration cases: " + output.size());
    }
}
