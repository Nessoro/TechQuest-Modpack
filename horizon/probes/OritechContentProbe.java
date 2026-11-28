package techquest.probes;

import com.google.gson.*;
import com.mojang.serialization.JsonOps;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.resources.RegistryOps;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.CraftingInput;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.item.enchantment.Enchantments;
import net.minecraft.world.level.storage.loot.LootTable;
import net.minecraft.world.level.storage.loot.LootParams;
import net.minecraft.world.level.storage.loot.parameters.LootContextParamSets;
import net.minecraft.world.level.storage.loot.parameters.LootContextParams;
import net.minecraft.world.phys.Vec3;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.server.ServerStartedEvent;
import java.nio.file.*;
import java.util.*;

/** Original binary crafting manager and full ore loot table oracle; no login. */
@Mod("techquest_reference_probe")
public final class OritechContentProbe {
    public OritechContentProbe() { NeoForge.EVENT_BUS.addListener(this::started); }
    private static ItemStack stack(String id) { return new ItemStack(BuiltInRegistries.ITEM.get(ResourceLocation.parse(id))); }
    private void started(ServerStartedEvent event) {
        var server=event.getServer();var level=server.overworld();
        try {
            server.tickRateManager().setFrozen(true);
            var input=JsonParser.parseString(Files.readString(Path.of(System.getProperty("techquest.reference.cases")))).getAsJsonObject();
            var crafting=new ArrayList<Object>();
            for(var element:input.getAsJsonArray("crafting")) {
                var row=element.getAsJsonObject();var grid=new ArrayList<ItemStack>();
                for(var item:row.getAsJsonArray("grid"))grid.add(item.isJsonNull()?ItemStack.EMPTY:stack(item.getAsString()));
                var inventory=CraftingInput.of(3,3,grid);
                var match=server.getRecipeManager().getRecipeFor(RecipeType.CRAFTING,inventory,level);
                var result=new LinkedHashMap<String,Object>();result.put("name",row.get("name").getAsString());result.put("matched",match.isPresent());
                if(match.isPresent()) {
                    var holder=match.get();var output=holder.value().assemble(inventory,level.registryAccess());
                    result.put("recipe",holder.id().toString());result.put("item",BuiltInRegistries.ITEM.getKey(output.getItem()).toString());result.put("count",output.getCount());
                }
                boolean valid=row.get("valid").getAsBoolean();
                boolean target=match.isPresent() && result.get("recipe").equals(row.get("recipe").getAsString());
                if(target!=valid || valid && (!result.get("item").equals(row.get("item").getAsString()) || !result.get("count").equals(row.get("count").getAsInt())))
                    throw new IllegalStateException("Unexpected original crafting result: "+result);
                crafting.add(result);
            }
            var ops=RegistryOps.create(JsonOps.INSTANCE,server.registryAccess());var loot=new ArrayList<Object>();
            for(var entry:input.getAsJsonObject("loot_tables").entrySet()) {
                var state=BuiltInRegistries.BLOCK.get(ResourceLocation.parse("oritech:"+entry.getKey())).defaultBlockState();
                var table=LootTable.DIRECT_CODEC.parse(ops,entry.getValue()).getOrThrow();
                for(var mode:List.of("plain","silk","fortune")) {
                    var tool=stack("minecraft:diamond_pickaxe");
                    if(!mode.equals("plain"))tool.enchant(server.registryAccess().lookupOrThrow(Registries.ENCHANTMENT).getOrThrow(mode.equals("silk")?Enchantments.SILK_TOUCH:Enchantments.FORTUNE),mode.equals("silk")?1:3);
                    var params=new LootParams.Builder(level).withParameter(LootContextParams.ORIGIN,new Vec3(0,0,0)).withParameter(LootContextParams.BLOCK_STATE,state).withParameter(LootContextParams.TOOL,tool).create(LootContextParamSets.BLOCK);
                    for(var seed:input.getAsJsonArray("seeds")) {
                        var stacks=new ArrayList<Object>();
                        for(var item:table.getRandomItems(params,seed.getAsLong()))stacks.add(Map.of("item",BuiltInRegistries.ITEM.getKey(item.getItem()).toString(),"count",item.getCount()));
                        loot.add(Map.of("ore",entry.getKey(),"tool",mode,"seed",seed.getAsLong(),"stacks",stacks));
                    }
                }
            }
            Files.writeString(Path.of(System.getProperty("techquest.reference.result")),new GsonBuilder().setPrettyPrinting().create().toJson(Map.of("schema",1,"original_crafting_and_loot_executed",true,"crafting",crafting,"loot",loot,"real_client_tested",false)));
        }catch(Exception e){throw new IllegalStateException("Oritech content oracle failed",e);}
        finally {server.halt(false);}
    }
}
