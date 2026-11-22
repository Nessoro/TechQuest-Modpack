package techquest.probes;

import com.google.gson.GsonBuilder;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.Vec3i;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.server.ServerStartedEvent;
import rearth.oritech.block.base.block.MultiblockMachine;
import rearth.oritech.block.base.entity.MachineBlockEntity;
import rearth.oritech.block.blocks.processing.MachineCoreBlock;
import rearth.oritech.block.entity.processing.FoundryBlockEntity;
import rearth.oritech.block.entity.processing.PulverizerBlockEntity;
import rearth.oritech.init.recipes.OritechRecipe;
import rearth.oritech.util.Geometry;
import java.lang.reflect.Method;
import java.nio.file.*;
import java.util.*;

/** Developer-only execution of original CC0 machines/multiblock; binary dependency APIs only. */
@Mod("techquest_reference_probe")
public final class OritechFoundryProbe {
    private static final BlockPos POS=new BlockPos(256,210,128);
    private final List<Object> rows=new ArrayList<>(),geometry=new ArrayList<>(),coal=new ArrayList<>();
    public OritechFoundryProbe(){NeoForge.EVENT_BUS.addListener(this::started);}
    private static ItemStack item(String id,int count){return count==0?ItemStack.EMPTY:new ItemStack(BuiltInRegistries.ITEM.get(ResourceLocation.parse(id)),count);}
    private static List<BlockPos> cores(FoundryBlockEntity entity){
        return entity.getCorePositions().stream().map(p->POS.offset(Geometry.rotatePosition(p,entity.getFacingForMultiblock()))).toList();
    }
    private static void clear(ServerLevel level){
        for(int x=-2;x<=2;x++)for(int y=0;y<=2;y++)for(int z=-2;z<=2;z++)level.setBlockAndUpdate(POS.offset(x,y,z),Blocks.AIR.defaultBlockState());
    }
    private static FoundryBlockEntity place(ServerLevel level,Direction facing,int missing,boolean used,boolean assemble){
        clear(level);
        level.setBlockAndUpdate(POS,BuiltInRegistries.BLOCK.get(ResourceLocation.parse("oritech:foundry_block")).defaultBlockState().setValue(BlockStateProperties.HORIZONTAL_FACING,facing));
        var entity=(FoundryBlockEntity)level.getBlockEntity(POS);int slot=0;
        for(var pos:cores(entity)){
            if(slot!=missing)level.setBlockAndUpdate(pos,BuiltInRegistries.BLOCK.get(ResourceLocation.parse("oritech:machine_core_1")).defaultBlockState().setValue(MachineCoreBlock.USED,used&&slot==0));
            slot++;
        }
        if(assemble){
            if(!entity.initMultiblock(entity.getBlockState()))throw new IllegalStateException("complete core1 assembly refused");
            entity.initAddons();
        }
        return entity;
    }
    private static Map<String,Object> snapshot(FoundryBlockEntity entity){
        var result=new LinkedHashMap<String,Object>();result.put("energy",entity.energyStorage.amount);result.put("progress",entity.progress);
        result.put("assembled",entity.getBlockState().getValue(MultiblockMachine.ASSEMBLED));
        var inventory=new ArrayList<Object>();
        for(int slot=0;slot<3;slot++){var stack=entity.inventory.getItem(slot);if(!stack.isEmpty())inventory.add(Map.of("slot",slot,"item",BuiltInRegistries.ITEM.getKey(stack.getItem()).toString(),"count",stack.getCount()));}
        result.put("items",inventory);return result;
    }
    private static void tick(ServerLevel level,FoundryBlockEntity entity){entity.serverTick(level,POS,entity.getBlockState(),entity);}
    private static void prime(FoundryBlockEntity entity)throws Exception{
        Method lookup=MachineBlockEntity.class.getDeclaredMethod("getRecipe");lookup.setAccessible(true);var candidate=(Optional<?>)lookup.invoke(entity);
        if(candidate.isEmpty())throw new IllegalStateException("fixture recipe missing");entity.setCurrentRecipe((OritechRecipe)((RecipeHolder<?>)candidate.get()).value());
    }
    private void one(ServerLevel level,String first,String second,String result,boolean swap,long energy,int progress,boolean primed,boolean disabled,boolean active,int output,String outputItem)throws Exception{
        var entity=place(level,Direction.NORTH,-1,false,active);
        entity.inventory.setItem(0,item(swap?second:first,first.equals("minecraft:air")?0:2));
        entity.inventory.setItem(1,item(swap?first:second,second.equals("minecraft:air")?0:2));
        entity.inventory.setItem(2,item(outputItem==null?result:outputItem,output));entity.energyStorage.amount=energy;entity.progress=progress;
        if(primed)prime(entity);entity.onRedstoneEvent(disabled);
        var row=new LinkedHashMap<String,Object>();row.put("name","case_"+rows.size());row.put("primed",primed);row.put("disabled",disabled);row.put("active",active);row.put("initial_state",snapshot(entity));
        var states=new ArrayList<Object>();int elapsed=0;
        for(int point:new int[]{1,2,13,25,26,27,79,80,81,160}){
            while(elapsed<point){tick(level,entity);elapsed++;}states.add(Map.of("ticks",point,"state",snapshot(entity)));
        }
        row.put("states",states);rows.add(row);
    }
    private void started(ServerStartedEvent event){
        var server=event.getServer();
        try{
            var level=server.overworld();level.getChunkAt(POS);server.tickRateManager().setFrozen(true);
            if(Boolean.getBoolean("techquest.reference.reopen")){
                var entity=(FoundryBlockEntity)level.getBlockEntity(POS);var before=snapshot(entity);var states=new ArrayList<Object>();int elapsed=0;
                for(int point:new int[]{1,26,27,52}){while(elapsed<point){tick(level,entity);elapsed++;}states.add(Map.of("ticks",point,"state",snapshot(entity)));}
                Files.writeString(Path.of(System.getProperty("techquest.reference.result")),new GsonBuilder().setPrettyPrinting().create().toJson(Map.of("schema",1,"physical_reopen",true,"before",before,"states",states)));return;
            }
            for(var facing:List.of(Direction.NORTH,Direction.EAST,Direction.SOUTH,Direction.WEST))for(int variant=-1;variant<4;variant++){
                boolean used=variant==3;var entity=place(level,facing,used?-1:variant,used,false);boolean assembled=entity.initMultiblock(entity.getBlockState());
                var positions=cores(entity);var flags=new ArrayList<Boolean>();for(var pos:positions){var state=level.getBlockState(pos);flags.add(state.getBlock() instanceof MachineCoreBlock&&state.getValue(MachineCoreBlock.USED));}
                geometry.add(Map.of("name","geometry_"+geometry.size(),"facing",facing.getName(),"missing",used?-1:variant,"used",used,"core_positions",positions.stream().map(p->List.of(p.getX()-POS.getX(),p.getY()-POS.getY(),p.getZ()-POS.getZ())).toList(),"assembled",assembled,"used_after",flags,"connected",entity.getConnectedCores().size()));
                if(assembled!=(variant==-1))throw new IllegalStateException("assembly fixture differed");
            }
            var recipes=List.of(new String[]{"minecraft:iron_ingot","oritech:coal_dust","oritech:steel_ingot"},new String[]{"minecraft:gold_ingot","minecraft:redstone","oritech:electrum_ingot"},new String[]{"minecraft:diamond","oritech:nickel_ingot","oritech:adamant_ingot"});
            for(var recipe:recipes)for(boolean swap:new boolean[]{false,true})for(long energy:new long[]{0,127,128,50000})for(boolean primed:new boolean[]{false,true})one(level,recipe[0],recipe[1],recipe[2],swap,energy,12,primed,false,true,0,null);
            for(var recipe:recipes){
                for(int output:new int[]{63,64})one(level,recipe[0],recipe[1],recipe[2],false,50000,12,true,false,true,output,null);
                one(level,recipe[0],recipe[1],recipe[2],false,50000,12,true,false,true,1,"minecraft:barrier");
                for(boolean primed:new boolean[]{false,true})one(level,recipe[0],recipe[1],recipe[2],false,50000,12,primed,true,true,0,null);
            }
            for(boolean primed:new boolean[]{false,true})one(level,"minecraft:iron_ingot","oritech:coal_dust","oritech:steel_ingot",false,50000,12,primed,false,false,0,null);
            one(level,"minecraft:iron_ingot","minecraft:coal","oritech:steel_ingot",false,50000,12,false,false,true,0,null);
            one(level,"minecraft:iron_ingot","minecraft:air","oritech:steel_ingot",false,50000,12,false,false,true,0,null);
            one(level,"minecraft:air","minecraft:air","oritech:steel_ingot",false,50000,12,false,false,true,0,null);
            var machine=place(level,Direction.NORTH,-1,false,true);
            machine.inventory.setItem(0,item("minecraft:iron_ingot",2));machine.inventory.setItem(1,item("oritech:coal_dust",2));machine.energyStorage.amount=50000;
            for(int i=0;i<13;i++)tick(level,machine);var beforeBroken=snapshot(machine);var broken=cores(machine).get(0);
            // Raw Level.setBlockAndUpdate bypasses the source's destroy
            // callback. Invoke the real public callback before replacement,
            // as a physical break does, rather than treating an editor write
            // as a player break (the first control run retained that behavior).
            level.getBlockState(broken).getBlock().destroy(level,broken,level.getBlockState(broken));
            level.setBlockAndUpdate(broken,Blocks.AIR.defaultBlockState());var afterBroken=snapshot(machine);
            for(int i=0;i<10;i++)tick(level,machine);var paused=snapshot(machine);
            level.setBlockAndUpdate(broken,BuiltInRegistries.BLOCK.get(ResourceLocation.parse("oritech:machine_core_1")).defaultBlockState());
            boolean reassembled=machine.initMultiblock(machine.getBlockState());machine.initAddons();tick(level,machine);var resumed=snapshot(machine);
            var lifecycle=Map.of("before_broken",beforeBroken,"after_broken",afterBroken,"paused",paused,"reassembled",reassembled,"resumed",resumed,"original_destroy_callback_executed",true);
            if((boolean)afterBroken.get("assembled")||!paused.equals(afterBroken)||!reassembled||(int)resumed.get("progress")!=14)throw new IllegalStateException("physical core break semantics differed");
            clear(level);
            for(var fuel:List.of("minecraft:coal","minecraft:charcoal")){
                level.setBlockAndUpdate(POS,BuiltInRegistries.BLOCK.get(ResourceLocation.parse("oritech:pulverizer_block")).defaultBlockState());var pulverizer=(PulverizerBlockEntity)level.getBlockEntity(POS);
                pulverizer.inventory.setItem(0,item(fuel,1));pulverizer.energyStorage.amount=25000;
                for(int i=0;i<100;i++)pulverizer.serverTick(level,POS,pulverizer.getBlockState(),pulverizer);
                coal.add(Map.of("fuel",fuel,"energy",pulverizer.energyStorage.amount,"progress",pulverizer.progress,"dust",pulverizer.inventory.getItem(1).getCount(),"item",BuiltInRegistries.ITEM.getKey(pulverizer.inventory.getItem(1).getItem()).toString()));
                level.setBlockAndUpdate(POS,Blocks.AIR.defaultBlockState());
            }
            machine=place(level,Direction.NORTH,-1,false,true);machine.inventory.setItem(0,item("minecraft:iron_ingot",2));machine.inventory.setItem(1,item("oritech:coal_dust",2));machine.energyStorage.amount=50000;
            for(int i=0;i<13;i++)tick(level,machine);
            var report=new LinkedHashMap<String,Object>();report.put("schema",1);report.put("original_server_tick_executed",true);report.put("geometry",geometry);report.put("rows",rows);report.put("core_lifecycle",lifecycle);report.put("pulverizer_coal",coal);report.put("saved",snapshot(machine));
            report.put("capacity",machine.getDefaultCapacity());report.put("max_insertion",machine.getDefaultInsertRate());report.put("speed",machine.getSpeedMultiplier());report.put("efficiency",machine.getEfficiencyMultiplier());report.put("core_quality",machine.getCoreQuality());
            Files.writeString(Path.of(System.getProperty("techquest.reference.result")),new GsonBuilder().setPrettyPrinting().create().toJson(report));
        }catch(Exception e){throw new IllegalStateException("Foundry original oracle failed",e);}
        finally{server.halt(false);}
    }
}
