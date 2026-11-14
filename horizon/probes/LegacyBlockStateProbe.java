// First-party codec check; official hash-pinned 1.21.1 bundle, no world started.
package techquest.probes;

import com.google.gson.*;
import com.mojang.serialization.*;
import java.nio.file.*;

public class LegacyBlockStateProbe {
    @SuppressWarnings("unchecked")
    public static void main(String[] args) throws Exception {
        Class.forName("ab").getMethod("a").invoke(null);
        Class.forName("akt").getMethod("a").invoke(null);
        JsonObject source = JsonParser.parseString(Files.readString(Path.of(args[0]))).getAsJsonObject();
        JsonObject target = source.getAsJsonObject("config").getAsJsonObject("target");
        Codec<Object> codec = (Codec<Object>) Class.forName("dtc").getField("b").get(null);
        Object decoded = codec.parse(JsonOps.INSTANCE, target).getOrThrow();
        JsonElement encoded = codec.encodeStart(JsonOps.INSTANCE, decoded).getOrThrow();
        Object blocks = Class.forName("lt").getField("e").get(null);
        Object location = Class.forName("akr").getMethod("a", String.class).invoke(null, "minecraft:basalt");
        Object basalt = Class.forName("jz").getMethod("a", Class.forName("akr")).invoke(blocks, location);
        Object defaultBasalt = Class.forName("dfy").getMethod("o").invoke(basalt);
        JsonObject proof = new JsonObject();
        proof.addProperty("equals_default_basalt", decoded.equals(defaultBasalt));
        proof.addProperty("source_has_misspelled_Properites", target.has("Properites"));
        proof.add("encoded_state", encoded);
        if (!decoded.equals(defaultBasalt)) throw new AssertionError("not the default basalt state");
        Files.writeString(Path.of(args[1]), proof.toString());
        System.out.println(proof);
    }
}
