package techquest.probes;

import com.google.gson.GsonBuilder;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.Blocks;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.server.ServerStartedEvent;
import rearth.oritech.block.base.entity.MachineBlockEntity;
import rearth.oritech.block.entity.generators.BasicGeneratorEntity;
import rearth.oritech.block.entity.processing.PoweredFurnaceBlockEntity;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

/** Developer oracle: invokes the pinned original machines, with no player account. */
@Mod("techquest_reference_probe")
public final class OritechEnergyProbe {
    private static final BlockPos GEN = new BlockPos(256, 210, 128), FURNACE = GEN.east();
    private final List<Object> rows = new ArrayList<>();
    public OritechEnergyProbe() { NeoForge.EVENT_BUS.addListener(this::started); }
    private static ItemStack stack(String id, int count) {
        return count == 0 ? ItemStack.EMPTY : new ItemStack(BuiltInRegistries.ITEM.get(ResourceLocation.parse(id)), count);
    }
    private static MachineBlockEntity place(ServerLevel level, BlockPos pos, String id) {
        level.setBlockAndUpdate(pos, Blocks.AIR.defaultBlockState());
        level.setBlockAndUpdate(pos, BuiltInRegistries.BLOCK.get(ResourceLocation.parse(id)).defaultBlockState());
        return (MachineBlockEntity) level.getBlockEntity(pos);
    }
    private static Map<String,Object> snapshot(MachineBlockEntity machine) {
        var result = new LinkedHashMap<String,Object>();
        result.put("energy", machine.energyStorage.amount); result.put("progress", machine.progress);
        var items = new ArrayList<Object>();
        for (int i=0; i<machine.inventory.getContainerSize(); i++) {
            var item = machine.inventory.getItem(i);
            if (!item.isEmpty()) items.add(Map.of("slot", i, "item", BuiltInRegistries.ITEM.getKey(item.getItem()).toString(), "count", item.getCount()));
        }
        result.put("items", items);
        if (machine instanceof BasicGeneratorEntity generator) result.put("stored_burn", generator.getCurrentMaxBurnTime());
        if (machine instanceof PoweredFurnaceBlockEntity furnace) result.put("assembled", furnace.isActive(furnace.getBlockState()));
        return result;
    }
    private static void tick(ServerLevel level, MachineBlockEntity machine) {
        machine.serverTick(level, machine.getBlockPos(), machine.getBlockState(), machine);
    }
    private void generator(ServerLevel level, String item, int count, long energy, int progress, boolean disabled) {
        level.setBlockAndUpdate(FURNACE, Blocks.AIR.defaultBlockState());
        var machine=(BasicGeneratorEntity)place(level,GEN,"oritech:basic_generator_block");
        machine.inventory.setItem(0,stack(item,count));machine.energyStorage.amount=energy;machine.progress=progress;
        machine.setCurrentMaxBurnTime(progress);machine.onRedstoneEvent(disabled);
        var row=new LinkedHashMap<String,Object>();row.put("kind","generator");row.put("name","case_"+rows.size());
        row.put("fuel",item);row.put("fuel_count",count);row.put("initial_energy",energy);row.put("initial_progress",progress);row.put("disabled",disabled);
        row.put("initial_state",snapshot(machine));
        var states=new ArrayList<Object>();int elapsed=0;
        for(int checkpoint:new int[]{1,2,10,100,1600,1601}) {
            while(elapsed<checkpoint){tick(level,machine);elapsed++;}
            states.add(Map.of("ticks",checkpoint,"state",snapshot(machine)));
        }
        row.put("states",states);rows.add(row);
    }
    private void furnace(ServerLevel level, String item, String output, int outputCount, long energy, int progress, boolean core, boolean disabled) {
        level.setBlockAndUpdate(GEN,Blocks.AIR.defaultBlockState());
        level.setBlockAndUpdate(FURNACE.above(),Blocks.AIR.defaultBlockState());
        var machine=(PoweredFurnaceBlockEntity)place(level,FURNACE,"oritech:powered_furnace_block");
        machine.inventory.setItem(0,stack(item,2));machine.inventory.setItem(1,stack(output,outputCount));
        machine.energyStorage.amount=energy;machine.progress=progress;machine.onRedstoneEvent(disabled);
        if(core)level.setBlockAndUpdate(FURNACE.above(),BuiltInRegistries.BLOCK.get(ResourceLocation.parse("oritech:machine_core_1")).defaultBlockState());
        boolean assembled=machine.initMultiblock(machine.getBlockState());
        if(assembled!=core)throw new IllegalStateException("unexpected assembly result");
        var row=new LinkedHashMap<String,Object>();row.put("kind","furnace");row.put("name","case_"+rows.size());
        row.put("input",item);row.put("output",output);row.put("output_count",outputCount);row.put("initial_energy",energy);row.put("initial_progress",progress);row.put("core",core);row.put("disabled",disabled);
        row.put("initial_state",snapshot(machine));
        var states=new ArrayList<Object>();int elapsed=0;
        for(int checkpoint:new int[]{1,2,50,99,100,101,200}) {
            while(elapsed<checkpoint){tick(level,machine);elapsed++;}
            states.add(Map.of("ticks",checkpoint,"state",snapshot(machine)));
        }
        row.put("states",states);rows.add(row);
    }
    private void started(ServerStartedEvent event) {
        var server=event.getServer();var level=server.overworld();
        try {
            server.tickRateManager().setFrozen(true);level.getChunkAt(GEN);level.getChunkAt(FURNACE);
            if (Boolean.getBoolean("techquest.reference.reopen")) {
                var generator=(BasicGeneratorEntity)level.getBlockEntity(GEN);
                var furnace=(PoweredFurnaceBlockEntity)level.getBlockEntity(FURNACE);
                var result=new LinkedHashMap<String,Object>();
                result.put("before_generator",snapshot(generator));result.put("before_furnace",snapshot(furnace));
                for(int i=0;i<155;i++){tick(level,generator);tick(level,furnace);}
                result.put("after_generator",snapshot(generator));result.put("after_furnace",snapshot(furnace));
                Files.writeString(Path.of(System.getProperty("techquest.reference.result")),new GsonBuilder().setPrettyPrinting().create().toJson(result));
                return;
            }
            for(var fuel:List.of("minecraft:coal","minecraft:oak_planks","minecraft:stick","minecraft:lava_bucket","minecraft:bucket","minecraft:iron_ingot"))
                for(long energy:new long[]{0,49968,49969,50000})generator(level,fuel,2,energy,0,false);
            generator(level,"minecraft:coal",0,0,0,false);
            generator(level,"minecraft:coal",2,0,3,true);
            generator(level,"minecraft:coal",2,49969,3,false);
            for(var item:List.of("minecraft:raw_iron","minecraft:oak_log","minecraft:iron_ingot"))
                for(long energy:new long[]{0,31,32,3200,6400})
                    for(boolean core:new boolean[]{false,true})furnace(level,item,"minecraft:iron_ingot",0,energy,0,core,false);
            for(var output:List.of("minecraft:gold_ingot","minecraft:iron_ingot"))
                for(int count:new int[]{63,64})furnace(level,"minecraft:raw_iron",output,count,6400,49,true,false);
            furnace(level,"minecraft:raw_iron","minecraft:iron_ingot",0,31,49,true,false);
            furnace(level,"minecraft:raw_iron","minecraft:iron_ingot",0,6400,49,true,true);
            // Leave a real partially working pair for a separate server restart.
            level.setBlockAndUpdate(FURNACE.above(),Blocks.AIR.defaultBlockState());
            var furnace=(PoweredFurnaceBlockEntity)place(level,FURNACE,"oritech:powered_furnace_block");
            level.setBlockAndUpdate(FURNACE.above(),BuiltInRegistries.BLOCK.get(ResourceLocation.parse("oritech:machine_core_1")).defaultBlockState());
            if(!furnace.initMultiblock(furnace.getBlockState()))throw new IllegalStateException("chain assembly");
            var generator=(BasicGeneratorEntity)place(level,GEN,"oritech:basic_generator_block");
            generator.inventory.setItem(0,stack("minecraft:coal",2));furnace.inventory.setItem(0,stack("minecraft:raw_iron",2));
            for(int i=0;i<45;i++){tick(level,generator);tick(level,furnace);}
            var result=new LinkedHashMap<String,Object>();result.put("schema",1);result.put("oritech","1.2.13");result.put("original_server_tick_executed",true);
            result.put("tick_method","direct original machine serverTick calls on the server thread; chain order generator then furnace");
            result.put("real_client_tested",false);result.put("rows",rows);result.put("saved_generator",snapshot(generator));result.put("saved_furnace",snapshot(furnace));
            Files.writeString(Path.of(System.getProperty("techquest.reference.result")),new GsonBuilder().setPrettyPrinting().create().toJson(result));
        }catch(Exception e){throw new IllegalStateException("Oritech energy oracle failed",e);}
        finally { server.halt(false); }
    }
}
