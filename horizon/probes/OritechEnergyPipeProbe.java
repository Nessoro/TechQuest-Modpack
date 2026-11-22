package techquest.probes;

import com.google.gson.GsonBuilder;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.block.Blocks;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.server.ServerStartedEvent;
import rearth.oritech.api.energy.EnergyApi;
import rearth.oritech.block.base.entity.MachineBlockEntity;
import rearth.oritech.block.blocks.pipes.GenericPipeBlock;
import rearth.oritech.block.blocks.pipes.energy.EnergyPipeBlock;
import rearth.oritech.block.entity.pipes.EnergyPipeInterfaceEntity;
import rearth.oritech.block.entity.pipes.GenericPipeInterfaceEntity;
import rearth.oritech.block.entity.generators.BasicGeneratorEntity;
import rearth.oritech.block.entity.processing.PoweredFurnaceBlockEntity;
import net.minecraft.world.item.ItemStack;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

/** Developer-only CC0 Oritech callbacks, using dependency binary public APIs. */
@Mod("techquest_reference_probe")
public final class OritechEnergyPipeProbe {
    private static final BlockPos BASE = new BlockPos(256, 210, 128);
    private static final String NORMAL = "oritech:energy_pipe", CONNECTION = "oritech:energy_pipe_connection";
    private static final String GENERATOR = "oritech:basic_generator_block", FURNACE = "oritech:powered_furnace_block";
    private final Set<BlockPos> placed = new LinkedHashSet<>();
    private final List<Object> rows = new ArrayList<>(), apiRows = new ArrayList<>(), layouts = new ArrayList<>();
    private record Line(BlockPos source, BlockPos endpoint, BlockPos target, List<BlockPos> wires) {}

    public OritechEnergyPipeProbe() { NeoForge.EVENT_BUS.addListener(this::started); }
    private static void require(boolean condition, String message) {
        if (!condition) throw new IllegalStateException(message);
    }
    private void put(ServerLevel level, BlockPos pos, String id) {
        level.getChunkAt(pos); placed.add(pos);
        var state = BuiltInRegistries.BLOCK.get(ResourceLocation.parse(id)).defaultBlockState();
        if (id.equals(NORMAL)) state = ((GenericPipeBlock) state.getBlock()).addConnectionStates(state, level, pos, true);
        level.setBlockAndUpdate(pos, state);
    }
    private void clear(ServerLevel level) {
        for (var pos : placed) level.setBlockAndUpdate(pos, Blocks.AIR.defaultBlockState());
        placed.clear();
    }
    private Line line(ServerLevel level, Direction direction, String targetId) {
        clear(level);
        var target = BASE.relative(direction, 6);
        put(level, BASE, GENERATOR); put(level, target, targetId);
        var wires = new ArrayList<BlockPos>();
        for (int i = 1; i < 6; i++) { var pos = BASE.relative(direction, i); put(level, pos, NORMAL); wires.add(pos); }
        require(id(level, wires.getFirst()).equals(CONNECTION), "source interface missing");
        require(id(level, wires.getLast()).equals(CONNECTION), "target interface missing");
        for (int i = 1; i < 4; i++) {
            require(id(level, wires.get(i)).equals(NORMAL), "ordinary wire became interface");
            require(level.getBlockEntity(wires.get(i)) == null, "ordinary wire has block entity");
            for (var side : Direction.values()) require(EnergyApi.BLOCK.find(level, wires.get(i), side) == null, "ordinary wire stores energy");
        }
        return new Line(BASE, wires.getFirst(), target, wires);
    }
    private static String id(ServerLevel level, BlockPos pos) {
        return BuiltInRegistries.BLOCK.getKey(level.getBlockState(pos).getBlock()).toString();
    }
    private static EnergyPipeInterfaceEntity endpoint(ServerLevel level, BlockPos pos) {
        return (EnergyPipeInterfaceEntity) level.getBlockEntity(pos);
    }
    private static EnergyApi.EnergyStorage storage(ServerLevel level, BlockPos pos) {
        var result = EnergyApi.BLOCK.find(level, pos, Direction.UP);
        require(result != null, "storage missing at " + pos);
        return result;
    }
    private static void seed(ServerLevel level, BlockPos pos, long amount) {
        var buffer = storage(level, pos); buffer.setAmount(amount); buffer.update();
        level.getBlockEntity(pos).setChanged();
    }
    private static void tick(ServerLevel level, BlockPos pos) {
        var entity = endpoint(level, pos); entity.tick(level, pos, level.getBlockState(pos), entity);
    }
    private static long energy(ServerLevel level, BlockPos pos) { return storage(level, pos).getAmount(); }
    private static List<Integer> coordinates(BlockPos pos) {
        return List.of(pos.getX()-BASE.getX(), pos.getY()-BASE.getY(), pos.getZ()-BASE.getZ());
    }
    private static Map<String,Object> node(ServerLevel level, BlockPos pos) {
        var row = new LinkedHashMap<String,Object>(); row.put("pos", coordinates(pos)); row.put("block", id(level, pos));
        var props = new TreeMap<String,String>();
        level.getBlockState(pos).getValues().forEach((key, value) -> props.put(key.getName(), value.toString()));
        row.put("properties", props); row.put("has_block_entity", level.getBlockEntity(pos) != null);
        var buffer = EnergyApi.BLOCK.find(level, pos, Direction.UP);
        row.put("has_energy_api", buffer != null);
        if (buffer != null) { row.put("energy", buffer.getAmount()); row.put("capacity", buffer.getCapacity()); }
        return row;
    }
    private static Map<String,Object> state(ServerLevel level, Line line) {
        return Map.of("buffer", energy(level,line.endpoint), "source",energy(level,line.source),
            "target", energy(level,line.target), "far_buffer",energy(level,line.wires.getLast()));
    }
    private static List<Object> targets(ServerLevel level, BlockPos endpoint) {
        var data = EnergyPipeBlock.ENERGY_PIPE_DATA.get(level.dimension().location());
        var found = GenericPipeInterfaceEntity.findNetworkTargets(endpoint, data);
        require(found != null, "network target set missing");
        var result = new ArrayList<Object>();
        found.stream().sorted(Comparator.comparing(t -> coordinates(t.getA()).toString() + t.getB().getName()))
            .forEach(t -> result.add(Map.of("pos",coordinates(t.getA()), "face",t.getB().getName())));
        return result;
    }
    private void one(ServerLevel level, Direction direction, String targetId, long buffer, long initialTarget) {
        var line = line(level, direction, targetId);
        seed(level,line.endpoint,buffer); seed(level,line.target,initialTarget);
        var machine = (MachineBlockEntity) level.getBlockEntity(line.target);
        var row = new LinkedHashMap<String,Object>(); row.put("name","case_"+rows.size());
        row.put("direction",direction.getName()); row.put("target_id",targetId);
        row.put("target_capacity",machine.getDefaultCapacity()); row.put("target_max_insert",machine.getDefaultInsertRate());
        row.put("initial",state(level,line));
        var states = new ArrayList<Object>(); int elapsed=0;
        for (int checkpoint : new int[]{1,2,40}) {
            while (elapsed < checkpoint) { tick(level,line.endpoint); elapsed++; }
            var now = state(level,line);
            require(energy(level,line.endpoint)+energy(level,line.target)==buffer+initialTarget,"energy conservation failed");
            require(energy(level,line.wires.getLast())==0,"transfer used destination pipe buffer");
            states.add(Map.of("ticks",checkpoint,"state",now));
        }
        row.put("states",states); rows.add(row);
    }
    private void api(ServerLevel level) {
        var line = line(level,Direction.EAST,FURNACE);
        var buffer = storage(level,line.endpoint);
        require(buffer.getCapacity()==10000,"unexpected default cable capacity");
        for (var side : Direction.values()) require(storage(level,line.endpoint)==EnergyApi.BLOCK.find(level,line.endpoint,side),"sided endpoint storage differs");
        for (var operation : List.of("insert","extract")) for (long initial : new long[]{0,1,9999,10000})
            for (long requested : new long[]{0,1,255,256,9999,10000,10001,Long.MAX_VALUE}) for (boolean simulate : new boolean[]{false,true}) {
                seed(level,line.endpoint,initial);
                long returned = operation.equals("insert") ? buffer.insert(requested,simulate) : buffer.extract(requested,simulate);
                apiRows.add(Map.of("operation",operation,"initial",initial,"requested",requested,"simulate",simulate,"returned",returned,"after",buffer.getAmount()));
            }
    }
    private Map<String,Object> lifecycle(ServerLevel level) {
        var line = line(level,Direction.EAST,FURNACE);
        seed(level,line.endpoint,1000); tick(level,line.endpoint);
        var before=state(level,line);
        put(level,BASE.east(3),"minecraft:air"); tick(level,line.endpoint);
        var broken=state(level,line); var brokenTargets=targets(level,line.endpoint);
        require(before.equals(broken),"energy crossed gap");
        put(level,BASE.east(3),NORMAL); tick(level,line.endpoint); var restored=state(level,line);
        require(energy(level,line.target)==512,"rejoined cable did not transfer");
        seed(level,line.wires.getLast(),333);
        put(level,line.target,"minecraft:air"); var removed=node(level,line.wires.getLast());
        require(id(level,line.wires.getLast()).equals(NORMAL) && level.getBlockEntity(line.wires.getLast())==null,"unused interface survived removal");
        var held=energy(level,line.endpoint); tick(level,line.endpoint);
        require(energy(level,line.endpoint)==held,"empty network consumed energy");
        put(level,line.target,"oritech:foundry_block"); var recreated=node(level,line.wires.getLast());
        require(id(level,line.wires.getLast()).equals(CONNECTION) && energy(level,line.wires.getLast())==0,"recreated interface retained old buffer");
        tick(level,line.endpoint);
        require(energy(level,line.target)==held && energy(level,line.endpoint)==0,"replacement target did not receive buffered energy");
        return Map.of("before_gap",before,"broken",broken,"broken_targets",brokenTargets,"restored",restored,
            "after_target_removed",removed,"after_target_replaced",recreated,"replacement_state",state(level,line),"discarded_removed_interface_energy",333);
    }
    private Map<String,Object> multiTarget(ServerLevel level, long supplied) {
        var line=line(level,Direction.EAST,FURNACE);
        var second=line.target.north(); put(level,second,FURNACE); put(level,line.wires.getLast().north(),NORMAL);
        seed(level,line.endpoint,supplied); tick(level,line.endpoint);
        long a=energy(level,line.target),b=energy(level,second),left=energy(level,line.endpoint);
        require(a+b+left==supplied && a<=256 && b<=256,"multi-target conservation/rate failed");
        if(supplied==100) require((a==100&&b==0)||(a==0&&b==100),"unexpected shuffled allocation");
        if(supplied==1000) require(a==256&&b==256&&left==488,"per-target transfer failed");
        return Map.of("supplied",supplied,"target_a",a,"target_b",b,"remaining",left,"targets",targets(level,line.endpoint),
            "shuffle","original Collections.shuffle; scarce allocation allowed in either order");
    }
    private Map<String,Object> twoFaces(ServerLevel level) {
        var line=line(level,Direction.EAST,FURNACE);
        put(level,line.wires.getLast().north(),NORMAL); put(level,line.target.north(),NORMAL);
        seed(level,line.endpoint,1000); tick(level,line.endpoint);
        require(energy(level,line.target)==512 && energy(level,line.endpoint)==488,"same-machine per-face insertion differs");
        return Map.of("state",state(level,line),"targets",targets(level,line.endpoint));
    }
    private Map<String,Object> twoSources(ServerLevel level) {
        var line=line(level,Direction.EAST,FURNACE);
        var secondEndpoint=BASE.east(2).north();
        put(level,secondEndpoint.north(),GENERATOR); put(level,secondEndpoint,NORMAL);
        seed(level,line.endpoint,1000); seed(level,secondEndpoint,1000);
        tick(level,line.endpoint); tick(level,secondEndpoint);
        require(energy(level,line.target)==512 && energy(level,line.endpoint)==744 && energy(level,secondEndpoint)==744,"per-call insertion was globally capped");
        return Map.of("target",energy(level,line.target),"buffers",List.of(energy(level,line.endpoint),energy(level,secondEndpoint)));
    }
    private Map<String,Object> loop(ServerLevel level) {
        var line=line(level,Direction.EAST,FURNACE);
        for(int x=1;x<=5;x++)put(level,BASE.east(x).south(),NORMAL);
        seed(level,line.endpoint,1000); tick(level,line.endpoint);
        require(energy(level,line.target)==256,"loop duplicated target transfer");
        put(level,BASE.east(3),"minecraft:air"); tick(level,line.endpoint);
        require(energy(level,line.target)==512,"alternative loop path not used");
        put(level,BASE.east(3).south(),"minecraft:air"); tick(level,line.endpoint);
        require(energy(level,line.target)==512,"two broken paths still connected");
        return Map.of("state",state(level,line),"targets_after_both_paths_broken",targets(level,line.endpoint));
    }
    private Map<String,Object> toggle(ServerLevel level) throws Exception {
        var line=line(level,Direction.EAST,FURNACE); var middle=BASE.east(3);
        seed(level,line.endpoint,1000); tick(level,line.endpoint);
        var toggle=GenericPipeBlock.class.getDeclaredMethod("toggleSideConnection",
            net.minecraft.world.level.block.state.BlockState.class,Direction.class,
            net.minecraft.world.level.Level.class,BlockPos.class);
        toggle.setAccessible(true);
        var block=level.getBlockState(middle).getBlock();
        require((boolean)toggle.invoke(block,level.getBlockState(middle),Direction.EAST,level,middle),"disable cable side failed");
        var disabled=List.of(node(level,middle),node(level,middle.east())); tick(level,line.endpoint);
        require(energy(level,line.target)==256 && energy(level,line.endpoint)==744,"disabled side transmitted energy");
        require((boolean)toggle.invoke(block,level.getBlockState(middle),Direction.EAST,level,middle),"enable cable side failed");
        var enabled=List.of(node(level,middle),node(level,middle.east())); tick(level,line.endpoint);
        require(energy(level,line.target)==512 && energy(level,line.endpoint)==488,"enabled side failed transmission");
        return Map.of("disabled",disabled,"enabled",enabled,"state",state(level,line),
            "driver","direct original protected toggle callback; no player/wrench interaction tested");
    }
    private Map<String,Object> core(ServerLevel level) {
        clear(level); var target=BASE.east(6); var controller=target.below();
        put(level,BASE,GENERATOR); put(level,controller,FURNACE); put(level,target,"oritech:machine_core_1");
        for(int x=1;x<=5;x++)put(level,BASE.east(x),NORMAL);
        var before=node(level,BASE.east(5));
        require(id(level,BASE.east(5)).equals(NORMAL),"unused core exposes energy");
        var furnace=(PoweredFurnaceBlockEntity)level.getBlockEntity(controller);
        require(furnace.initMultiblock(furnace.getBlockState()),"core route assembly failed");
        var after=node(level,BASE.east(5));
        require(id(level,BASE.east(5)).equals(CONNECTION),"assembled core did not form cable interface");
        seed(level,BASE.east(),1000); tick(level,BASE.east());
        require(energy(level,controller)==256 && energy(level,BASE.east())==744,"core did not delegate energy");
        return Map.of("before_assembly",before,"after_assembly",after,"controller",energy(level,controller),
            "buffer",energy(level,BASE.east()),"core_capacity",storage(level,target).getCapacity(),"targets",targets(level,BASE.east()));
    }
    private static Map<String,Object> machine(MachineBlockEntity entity) {
        var result=new LinkedHashMap<String,Object>(); result.put("energy",entity.energyStorage.amount); result.put("progress",entity.progress);
        var items=new ArrayList<Object>();
        for(int slot=0;slot<entity.inventory.getContainerSize();slot++) {
            var stack=entity.inventory.getItem(slot);
            if(!stack.isEmpty())items.add(Map.of("slot",slot,"item",BuiltInRegistries.ITEM.getKey(stack.getItem()).toString(),"count",stack.getCount()));
        }
        result.put("items",items); return result;
    }
    private Map<String,Object> fuelChain(ServerLevel level) {
        var line=line(level,Direction.EAST,FURNACE);
        put(level,line.target.above(),"oritech:machine_core_1");
        var generator=(BasicGeneratorEntity)level.getBlockEntity(line.source);
        var furnace=(PoweredFurnaceBlockEntity)level.getBlockEntity(line.target);
        require(furnace.initMultiblock(furnace.getBlockState()),"chain assembly failed");
        generator.inventory.setItem(0,new ItemStack(BuiltInRegistries.ITEM.get(ResourceLocation.parse("minecraft:coal")),1));
        furnace.inventory.setItem(0,new ItemStack(BuiltInRegistries.ITEM.get(ResourceLocation.parse("minecraft:raw_iron")),2));
        var states=new ArrayList<Object>(); int elapsed=0;
        for(int checkpoint:new int[]{1,2,45,100,101,200,201,1600,1601}) {
            while(elapsed<checkpoint) {
                generator.serverTick(level,line.source,generator.getBlockState(),generator);
                tick(level,line.endpoint); tick(level,line.wires.getLast());
                furnace.serverTick(level,line.target,furnace.getBlockState(),furnace); elapsed++;
            }
            states.add(Map.of("ticks",checkpoint,"generator",machine(generator),"furnace",machine(furnace),
                "source_buffer",energy(level,line.endpoint),"far_buffer",energy(level,line.wires.getLast())));
        }
        require(furnace.inventory.getItem(1).getCount()==2 && BuiltInRegistries.ITEM.getKey(furnace.inventory.getItem(1).getItem()).toString().equals("minecraft:iron_ingot"),"remote smelting failed");
        require(generator.energyStorage.amount+furnace.energyStorage.amount+energy(level,line.endpoint)+energy(level,line.wires.getLast())==44800,"fuel chain energy conservation failed");
        return Map.of("states",states,"fixture_inputs",Map.of("minecraft:coal",1,"minecraft:raw_iron",2),
            "machine_inventories_seeded_inputs_only",true,"machine_or_cable_energy_seeded",false,
            "tick_order",List.of("generator","source_interface","far_interface","furnace"),
            "generated",51200,"processing_cost",6400,"remaining",44800);
    }
    private static Map<String,Object> saved(ServerLevel level) {
        var nodes=new ArrayList<Object>();
        for(int i=0;i<=6;i++)nodes.add(node(level,BASE.east(i)));
        return Map.of("nodes",nodes,"targets",targets(level,BASE.east()));
    }
    private void started(ServerStartedEvent event) {
        var server=event.getServer();
        try {
            var level=server.overworld(); server.tickRateManager().setFrozen(true);
            for(int x=-1;x<=1;x++)for(int z=-1;z<=1;z++)level.getChunkAt(BASE.offset(x*16,0,z*16));
            var result=new LinkedHashMap<String,Object>(); result.put("schema",1);
            result.put("original_callbacks_executed",true); result.put("real_client_tested",false);
            if(Boolean.getBoolean("techquest.reference.reopen")) {
                result.put("before",saved(level));
                tick(level,BASE.east()); result.put("after_one",saved(level));
                require(energy(level,BASE.east())==744 && energy(level,BASE.east(6))==9792,"reopened network failed transfer");
                tick(level,BASE.east()); result.put("after_two",saved(level));
                require(energy(level,BASE.east())==536 && energy(level,BASE.east(6))==10000,"reopened target capacity failed");
            } else {
                api(level);
                for(var direction:Direction.values()) {
                    var line=line(level,direction,FURNACE);
                    var nodes=new ArrayList<Object>(); for(var p:line.wires)nodes.add(node(level,p));
                    layouts.add(Map.of("direction",direction.getName(),"nodes",nodes,"targets",targets(level,line.endpoint)));
                }
                for(var targetId:List.of(FURNACE,"oritech:pulverizer_block","oritech:foundry_block","oritech:assembler_block"))
                    for(var direction:Direction.values()) for(long supplied:new long[]{0,1,255,256,257,1024,10000}) {
                        var first=line(level,direction,targetId); long capacity=storage(level,first.target).getCapacity();
                        for(long targetAmount:new long[]{0,capacity-1,capacity})one(level,direction,targetId,supplied,targetAmount);
                    }
                result.put("api_rows",apiRows);result.put("layouts",layouts);result.put("rows",rows);
                result.put("lifecycle",lifecycle(level));result.put("multiple_targets",List.of(multiTarget(level,100),multiTarget(level,1000)));
                result.put("multiple_faces",twoFaces(level));result.put("multiple_sources",twoSources(level));result.put("loop",loop(level));
                result.put("side_toggle",toggle(level));result.put("core_delegation",core(level));result.put("fuel_chain",fuelChain(level));
                var line=line(level,Direction.EAST,FURNACE);
                seed(level,line.endpoint,1000); seed(level,line.target,9536); seed(level,line.wires.getLast(),777);
                result.put("saved",saved(level));
                require(rows.size()==504 && apiRows.size()==128,"oracle case count changed");
            }
            Files.writeString(Path.of(System.getProperty("techquest.reference.result")),new GsonBuilder().setPrettyPrinting().create().toJson(result));
        } catch(Exception e) { throw new IllegalStateException("Energy cable original oracle failed",e); }
        finally { server.halt(false); }
    }
}
