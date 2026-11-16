package techquest.probes;

import com.google.gson.*;
import com.mojang.serialization.JsonOps;
import net.minecraft.resources.RegistryOps;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.storage.loot.LootParams;
import net.minecraft.world.level.storage.loot.LootTable;
import net.minecraft.world.level.storage.loot.parameters.LootContextParamSets;
import net.minecraft.world.level.storage.loot.parameters.LootContextParams;
import net.minecraft.world.phys.Vec3;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.server.ServerStartedEvent;
import java.nio.file.*;
import java.util.*;

/** Developer-only original public loot codec/function oracle. No player login. */
@Mod("techquest_reference_probe")
public final class YungLootModifierProbe {
    public YungLootModifierProbe() { NeoForge.EVENT_BUS.addListener(this::started); }

    private static Object describe(ItemStack stack) {
        var result = new LinkedHashMap<String, Object>();
        result.put("item", BuiltInRegistries.ITEM.getKey(stack.getItem()).toString());
        result.put("count", stack.getCount()); result.put("damage", stack.getDamageValue());
        var enchantments = new TreeMap<String, Integer>();
        for (var component : List.of(DataComponents.ENCHANTMENTS, DataComponents.STORED_ENCHANTMENTS)) {
            var value = stack.get(component);
            if (value != null) for (var entry : value.entrySet())
                enchantments.put(entry.getKey().unwrapKey().orElseThrow().location().toString(), entry.getIntValue());
        }
        result.put("enchantments", enchantments);
        var potion = stack.get(DataComponents.POTION_CONTENTS);
        result.put("potion", potion == null ? null : potion.potion().map(
                holder -> holder.unwrapKey().orElseThrow().location().toString()).orElse(null));
        return result;
    }

    private void started(ServerStartedEvent event) {
        var server = event.getServer();
        try {
            var cases = JsonParser.parseString(Files.readString(
                    Path.of(System.getProperty("techquest.reference.cases")))).getAsJsonObject();
            var ops = RegistryOps.create(JsonOps.INSTANCE, server.registryAccess());
            var params = new LootParams.Builder(server.overworld())
                    .withParameter(LootContextParams.ORIGIN, new Vec3(0, 200, 0))
                    .create(LootContextParamSets.CHEST);
            var rows = new ArrayList<Object>();
            for (var element : cases.getAsJsonArray("cases")) {
                var input = element.getAsJsonObject();
                var tableJson = new JsonObject(); tableJson.addProperty("type", "minecraft:chest");
                var pool = new JsonObject(); pool.addProperty("rolls", 1);
                var entries = new JsonArray(); entries.add(input.get("source_entry")); pool.add("entries", entries);
                var pools = new JsonArray(); pools.add(pool); tableJson.add("pools", pools);
                var table = LootTable.DIRECT_CODEC.parse(ops, tableJson).getOrThrow();
                for (var seedValue : cases.getAsJsonArray("seeds")) {
                    long seed = seedValue.getAsLong();
                    var stacks = new ArrayList<Object>();
                    for (var stack : table.getRandomItems(params, seed)) stacks.add(describe(stack));
                    if (stacks.size() != 1) throw new IllegalStateException("expected one forced source entry");
                    rows.add(Map.of("name", input.get("name").getAsString(), "seed", seed, "stacks", stacks));
                }
            }
            Files.writeString(Path.of(System.getProperty("techquest.reference.result")),
                    new GsonBuilder().serializeNulls().setPrettyPrinting().create().toJson(Map.of(
                        "schema", 1, "minecraft", "1.21.1", "original_loot_codec_executed", true,
                        "original_loot_functions_executed", true, "source_entries_isolated", true,
                        "real_client_tested", false, "rows", rows)));
        } catch (Exception exception) { throw new IllegalStateException("Original loot oracle failed", exception); }
        finally { server.halt(false); }
    }
}
