package techquest.probes;

import com.google.gson.GsonBuilder;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.level.block.Blocks;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.server.ServerStartedEvent;
import rearth.oritech.block.base.entity.MachineBlockEntity;
import rearth.oritech.block.entity.processing.PulverizerBlockEntity;
import rearth.oritech.init.OritechConfig;
import rearth.oritech.init.recipes.OritechRecipe;

import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

/** Developer-only original serverTick oracle; no dependency Java source used. */
@Mod("techquest_reference_probe")
public final class OritechPulverizerProbe {
    private static final BlockPos POS = new BlockPos(256, 210, 128);
    private final List<Object> rows = new ArrayList<>();
    public OritechPulverizerProbe() { NeoForge.EVENT_BUS.addListener(this::started); }
    private static ItemStack stack(String id, int count) {
        return count == 0 ? ItemStack.EMPTY : new ItemStack(BuiltInRegistries.ITEM.get(ResourceLocation.parse(id)), count);
    }
    private static PulverizerBlockEntity place(ServerLevel level) {
        level.setBlockAndUpdate(POS, Blocks.AIR.defaultBlockState());
        level.setBlockAndUpdate(POS, BuiltInRegistries.BLOCK.get(ResourceLocation.parse("oritech:pulverizer_block")).defaultBlockState());
        return (PulverizerBlockEntity)level.getBlockEntity(POS);
    }
    private static Map<String,Object> snapshot(PulverizerBlockEntity machine) {
        var result = new LinkedHashMap<String,Object>();
        result.put("energy",machine.energyStorage.amount); result.put("progress",machine.progress);
        var items = new ArrayList<Object>();
        for(int i=0;i<machine.inventory.getContainerSize();i++) {
            var item=machine.inventory.getItem(i);
            if(!item.isEmpty())items.add(Map.of("slot",i,"item",BuiltInRegistries.ITEM.getKey(item.getItem()).toString(),"count",item.getCount()));
        }
        result.put("items",items);result.put("burst_ticks",machine.remainingBurstTicks);
        return result;
    }
    private static void tick(ServerLevel level, PulverizerBlockEntity machine) {
        machine.serverTick(level,machine.getBlockPos(),machine.getBlockState(),machine);
    }
    private static void prime(PulverizerBlockEntity machine) throws Exception {
        Method lookup=MachineBlockEntity.class.getDeclaredMethod("getRecipe");lookup.setAccessible(true);
        var result=(Optional<?>)lookup.invoke(machine);
        if(result.isEmpty())throw new IllegalStateException("quartz recipe not loaded");
        machine.setCurrentRecipe((OritechRecipe)((RecipeHolder<?>)result.get()).value());
    }
    private void one(ServerLevel level,String input,int count,String output,int outputCount,long energy,int progress,boolean primed,boolean disabled,boolean secondary) throws Exception {
        var machine=place(level);
        machine.inventory.setItem(0,stack(input,count));machine.inventory.setItem(1,stack(output,outputCount));
        if(secondary)machine.inventory.setItem(2,stack("minecraft:barrier",64));
        machine.energyStorage.amount=energy;machine.progress=progress;
        if(primed)prime(machine);
        machine.onRedstoneEvent(disabled);
        var row=new LinkedHashMap<String,Object>();row.put("name","case_"+rows.size());
        row.put("input",input);row.put("input_count",count);row.put("output",output);row.put("output_count",outputCount);
        row.put("initial_energy",energy);row.put("initial_progress",progress);row.put("recipe_primed",primed);row.put("disabled",disabled);row.put("secondary_blocked",secondary);
        row.put("initial_state",snapshot(machine));
        var states=new ArrayList<Object>();int elapsed=0;
        for(int checkpoint:new int[]{1,2,49,50,99,100,101,200}) {
            while(elapsed<checkpoint){tick(level,machine);elapsed++;}
            states.add(Map.of("ticks",checkpoint,"state",snapshot(machine)));
        }
        row.put("states",states);rows.add(row);
    }
    private void started(ServerStartedEvent event) {
        var server=event.getServer();var level=server.overworld();
        try {
            server.tickRateManager().setFrozen(true);level.getChunkAt(POS);
            var result=new LinkedHashMap<String,Object>();
            result.put("schema",1);result.put("oritech","1.2.13");result.put("original_server_tick_executed",true);
            if(Boolean.getBoolean("techquest.reference.reopen")) {
                var machine=(PulverizerBlockEntity)level.getBlockEntity(POS);
                result.put("before",snapshot(machine));
                var states=new ArrayList<Object>();int elapsed=0;
                for(int n:new int[]{1,100,101,200}) {
                    while(elapsed<n){tick(level,machine);elapsed++;}
                    states.add(Map.of("ticks",n,"state",snapshot(machine)));
                }
                result.put("states",states);
            } else {
                for(boolean disabled:new boolean[]{false,true})
                    for(long energy:new long[]{0,31,32,3199,3200,6400,25000})
                        for(int mode=0;mode<4;mode++)
                            one(level,"minecraft:quartz",2,mode==3?"minecraft:gold_ingot":"oritech:quartz_dust",new int[]{0,63,64,1}[mode],energy,49,true,disabled,false);
                for(long energy:new long[]{0,31,32,3200,25000})
                    one(level,"minecraft:quartz",2,"oritech:quartz_dust",0,energy,49,false,false,false);
                one(level,"minecraft:barrier",2,"oritech:quartz_dust",0,25000,49,false,false,false);
                one(level,"minecraft:quartz",0,"oritech:quartz_dust",0,25000,49,false,false,false);
                one(level,"minecraft:quartz",2,"oritech:quartz_dust",0,6400,0,false,false,true);
                one(level,"minecraft:quartz",1,"oritech:quartz_dust",0,3200,0,true,false,false);
                one(level,"minecraft:quartz",2,"oritech:quartz_dust",0,32,99,true,false,false);
                one(level,"minecraft:quartz",2,"oritech:quartz_dust",0,32,99,false,false,false);
                var machine=place(level);machine.inventory.setItem(0,stack("minecraft:quartz",2));machine.energyStorage.amount=25000;
                for(int i=0;i<45;i++)tick(level,machine);
                result.put("rows",rows);result.put("saved",snapshot(machine));
                var config=OritechConfig.processingMachines.pulverizerData;
                result.put("configured_capacity",config.energyCapacity.get());result.put("configured_max_insertion",config.maxEnergyInsertion.get());result.put("configured_energy_per_tick",config.energyPerTick.get());
            }
            result.put("real_client_tested",false);result.put("addons_installed",false);
            Files.writeString(Path.of(System.getProperty("techquest.reference.result")),new GsonBuilder().setPrettyPrinting().create().toJson(result));
        } catch(Exception e) { throw new IllegalStateException("Oritech pulverizer oracle failed",e); }
        finally { server.halt(false); }
    }
}
