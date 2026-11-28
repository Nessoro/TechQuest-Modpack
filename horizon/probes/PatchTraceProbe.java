// First-party reflection probe for the hash-pinned official 1.21.1 server bundle.
// Executes the real patch loop with a recording predicate, no server or world.
package techquest.probes;

import com.google.gson.*;
import java.lang.reflect.*;
import java.nio.file.*;
import java.util.*;

public class PatchTraceProbe {
    public static void main(String[] args) throws Exception {
        Class.forName("ab").getMethod("a").invoke(null);
        Class.forName("akt").getMethod("a").invoke(null);
        Class<?> holder = Class.forName("jm"), feature = Class.forName("ece");
        Class<?> config = Class.forName("eei"), pos = Class.forName("jd");
        Class<?> level = Class.forName("dds"), generator = Class.forName("duz");
        Class<?> random = Class.forName("ayw"), context = Class.forName("ecg");
        Class<?> predicate = Class.forName("eaf"), integer = Class.forName("bpw");
        Method direct = holder.getMethod("a", Object.class);
        Object noop = Class.forName("ebq").getConstructor(feature, config).newInstance(
            feature.getField("e").get(null), Class.forName("eep").getField("b").get(null));
        Object noopHolder = direct.invoke(null, noop);
        Object registry = Class.forName("lt").getField("O").get(null);
        Method parse = Class.forName("akr").getMethod("a", String.class);
        Method get = Class.forName("jz").getMethod("a", Class.forName("akr"));
        // FlatLevelSource's generation bounds are constants. Bypass its resource-
        // loading constructor; assert bounds and reject unexpected world access.
        Class<?> unsafeClass = Class.forName("sun.misc.Unsafe");
        Field unsafeField = unsafeClass.getDeclaredField("theUnsafe");
        unsafeField.setAccessible(true);
        Object flat = unsafeClass.getMethod("allocateInstance", Class.class).invoke(
            unsafeField.get(null), Class.forName("dyt"));
        Object minimum = generator.getMethod("g").invoke(flat);
        Object depth = generator.getMethod("e").invoke(flat);
        if (!minimum.equals(0) || !depth.equals(384))
            throw new AssertionError("unexpected flat generator bounds: " + minimum + ", " + depth);
        Object world = Proxy.newProxyInstance(level.getClassLoader(), new Class<?>[]{level}, (p, m, a) -> {
            return switch (m.getName()) {
                case "I_" -> -64;
                case "J_" -> 384;
                case "f_" -> true;
                default -> throw new AssertionError("unexpected world query: " + m);
            };
        });
        JsonArray cases = JsonParser.parseString(Files.readString(Path.of(args[0]))).getAsJsonArray();
        JsonArray output = new JsonArray();
        for (JsonElement element : cases) {
            JsonObject row = element.getAsJsonObject();
            JsonArray trace = new JsonArray();
            boolean accept = row.get("accept_alternate").getAsBoolean();
            Object recorder = Proxy.newProxyInstance(predicate.getClassLoader(), new Class<?>[]{predicate},
                (p, m, a) -> {
                    if (!m.getName().equals("test")) throw new AssertionError("unexpected predicate call: " + m);
                    JsonArray xyz = new JsonArray();
                    for (String axis : List.of("u", "v", "w"))
                        xyz.add((Integer) pos.getMethod(axis).invoke(a[1]));
                    trace.add(xyz);
                    return accept && trace.size() % 2 == 0;
                });
            Object filter = Class.forName("eij").getMethod("a", predicate).invoke(null, recorder);
            List<Object> modifiers = new ArrayList<>();
            if (row.get("child_offset").getAsBoolean()) {
                Method uniform = Class.forName("bqc").getMethod("a", int.class, int.class);
                modifiers.add(Class.forName("eja").getMethod("a", integer, integer).invoke(null,
                    uniform.invoke(null, -2, 2), uniform.invoke(null, -1, 1)));
            }
            modifiers.add(filter);
            Object placed = Class.forName("eiv").getConstructor(holder, List.class)
                .newInstance(noopHolder, modifiers);
            Object patchConfig = Class.forName("eev").getConstructor(int.class, int.class, int.class, holder)
                .newInstance(row.get("tries").getAsInt(), row.get("xz_spread").getAsInt(),
                    row.get("y_spread").getAsInt(), direct.invoke(null, placed));
            Object rng = Class.forName("dyz").getConstructor(long.class).newInstance(row.get("seed").getAsLong());
            Object at = pos.getConstructor(int.class, int.class, int.class).newInstance(-17, 80, 31);
            Object ctx = context.getConstructor(Optional.class, level, generator, random, pos, config)
                .newInstance(Optional.empty(), world, flat, rng, at, patchConfig);
            Object patch = get.invoke(registry, parse.invoke(null, "minecraft:" + row.get("kind").getAsString()));
            Object result = feature.getMethod("a", context).invoke(patch, ctx);
            JsonObject answer = new JsonObject();
            answer.add("positions", trace);
            answer.addProperty("result", (Boolean) result);
            answer.addProperty("tail", (Integer) random.getMethod("a", int.class).invoke(rng, 1000000007));
            output.add(answer);
        }
        Files.writeString(Path.of(args[1]), output.toString());
        System.out.println("Reference patch traces: " + output.size());
    }
}
