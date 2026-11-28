package dev.techquest.test;

import com.google.gson.*;
import java.nio.file.*;
import java.util.*;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.*;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.Ingredient;
import net.neoforged.fml.ModList;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.server.ServerStartedEvent;

/** Observer of real server recipe decoding. No crafting, spawning or player simulation. */
@Mod("techquest_dragonrise_probe")
public final class DragonRiseProbe {
    public DragonRiseProbe() {
        NeoForge.EVENT_BUS.addListener(this::onStarted);
    }

    private static boolean containsExact(Tag tag, String expected) {
        if (tag instanceof StringTag value) return value.getAsString().equals(expected);
        if (tag instanceof CompoundTag compound) {
            for (String key : compound.getAllKeys()) {
                if (containsExact(compound.get(key), expected)) return true;
            }
        }
        if (tag instanceof ListTag list) {
            for (Tag child : list) if (containsExact(child, expected)) return true;
        }
        return false;
    }

    private static void addIngredient(Map<String, Integer> counts, Ingredient ingredient, int amount) {
        ItemStack[] options = ingredient.getItems();
        if (options.length != 1 || options[0].isEmpty() || amount <= 0)
            throw new IllegalArgumentException("Invalid or ambiguous decoded ingredient");
        counts.merge(BuiltInRegistries.ITEM.getKey(options[0].getItem()).toString(), amount, Integer::sum);
    }

    // SBW 0.8.9.2 exposes public inputs and count, and getIngredient() in
    // VehicleAssemblingIngredient. Read these from the real decoded object.
    private static Map<String, Integer> decodedIngredients(RecipeHolder<?> holder, String serializer) throws Exception {
        Map<String, Integer> counts = new TreeMap<>();
        if (serializer.equals("superbwarfare:vehicle_assembling")) {
            Object recipe = holder.value();
            for (Object input : (List<?>) recipe.getClass().getField("inputs").get(recipe)) {
                Ingredient ingredient = (Ingredient) input.getClass().getMethod("getIngredient").invoke(input);
                int count = input.getClass().getField("count").getInt(input);
                addIngredient(counts, ingredient, count);
            }
        } else {
            for (Ingredient ingredient : holder.value().getIngredients())
                if (!ingredient.isEmpty()) addIngredient(counts, ingredient, 1);
        }
        return counts;
    }

    private void onStarted(ServerStartedEvent event) {
        try {
            Path expectedFile = Path.of(System.getProperty("techquest.dragonrise.expected"));
            Path reportFile = Path.of(System.getProperty("techquest.dragonrise.report"));
            boolean present = Boolean.parseBoolean(System.getProperty("techquest.dragonrise.present"));
            var server = event.getServer();
            var expected = JsonParser.parseString(Files.readString(expectedFile)).getAsJsonObject();
            var errors = new JsonArray();
            var observations = new JsonObject();
            var recipes = new TreeMap<String, RecipeHolder<?>>();
            var sbw = new TreeSet<String>();
            for (RecipeHolder<?> holder : server.getRecipeManager().getRecipes()) {
                String id = holder.id().toString();
                if (id.startsWith("techquest:dragonrise/")) {
                    if (recipes.put(id, holder) != null) errors.add("Duplicate recipe " + id);
                }
                if (id.startsWith("superbwarfare:")) sbw.add(id);
            }
            if (ModList.get().isLoaded("dragonrise_reforge") != present) errors.add("Unexpected DragonRise presence");
            if (!ModList.get().isLoaded("superbwarfare")) errors.add("Superb Warfare absent");
            if (sbw.isEmpty()) errors.add("No original SBW recipes loaded");
            if (!present && !recipes.isEmpty()) errors.add("Optional DragonRise recipes loaded while absent");
            if (present) {
                for (var row : expected.entrySet()) {
                    String id = row.getKey();
                    var definition = row.getValue().getAsJsonObject();
                    RecipeHolder<?> holder = recipes.get(id);
                    if (holder == null) {
                        errors.add("Missing decoded recipe " + id);
                        continue;
                    }
                    try {
                        String serializer = BuiltInRegistries.RECIPE_SERIALIZER.getKey(holder.value().getSerializer()).toString();
                        String wantSerializer = definition.get("serializer").getAsString();
                        String target = definition.get("target").getAsString();
                        String kind = definition.get("kind").getAsString();
                        if (!serializer.equals(wantSerializer)) errors.add("Wrong serializer " + id + ": " + serializer);
                        Map<String, Integer> expectedCounts = new TreeMap<>();
                        for (var ingredient : definition.getAsJsonObject("ingredients").entrySet()) {
                            String ingredientId = ingredient.getKey();
                            expectedCounts.put(ingredientId, ingredient.getValue().getAsInt());
                            if (!BuiltInRegistries.ITEM.containsKey(ResourceLocation.parse(ingredientId)))
                                errors.add("Unregistered ingredient " + ingredientId + " in " + id);
                        }
                        Map<String, Integer> decoded = decodedIngredients(holder, serializer);
                        if (!decoded.equals(expectedCounts)) errors.add("Decoded ingredient quantities differ " + id + ": " + decoded);
                        ItemStack stack = holder.value().getResultItem(server.registryAccess());
                        if (stack.isEmpty()) {
                            errors.add("Empty output " + id);
                            continue;
                        }
                        if (stack.getCount() != definition.get("count").getAsInt()) errors.add("Wrong output count " + id);
                        String item = BuiltInRegistries.ITEM.getKey(stack.getItem()).toString();
                        if (kind.equals("vehicle")) {
                            if (!BuiltInRegistries.ENTITY_TYPE.containsKey(ResourceLocation.parse(target)))
                                errors.add("Unregistered entity " + target);
                            if (!item.equals("superbwarfare:container") && !item.equals("superbwarfare:small_container"))
                                errors.add("Not an SBW deployment container " + id + ": " + item);
                            if (!containsExact(stack.save(server.registryAccess()), target))
                                errors.add("Wrong or missing deployment entity data " + id);
                        } else if (!item.equals(target)) {
                            errors.add("Wrong output " + id + ": " + item);
                        }
                        var observation = new JsonObject();
                        observation.addProperty("serializer", serializer);
                        observation.addProperty("item", item);
                        observation.addProperty("count", stack.getCount());
                        if (kind.equals("vehicle") && containsExact(stack.save(server.registryAccess()), target))
                            observation.addProperty("deployment_entity", target);
                        observation.add("decoded_ingredients", new Gson().toJsonTree(decoded));
                        observations.add(id, observation);
                    } catch (Exception ex) {
                        errors.add("Exception evaluating " + id + ": " + ex);
                    }
                }
                for (String id : recipes.keySet()) if (!expected.has(id)) errors.add("Unexpected recipe " + id);
            }
            var report = new JsonObject();
            report.addProperty("scope", "dedicated server recipe decoding and registered outputs only");
            report.addProperty("dragonrise_present", present);
            report.addProperty("expected", expected.size());
            report.addProperty("loaded", recipes.size());
            report.add("observations", observations);
            report.add("errors", errors);
            var original = new JsonArray();
            sbw.forEach(original::add);
            report.add("original_sbw_recipe_ids", original);
            Files.writeString(reportFile, new GsonBuilder().setPrettyPrinting().create().toJson(report));
            System.out.println("TECHQUEST_DRAGONRISE_PROBE_COMPLETE errors=" + errors.size());
        } catch (Exception failure) {
            throw new IllegalStateException("DragonRise server observer failed", failure);
        }
    }
}
