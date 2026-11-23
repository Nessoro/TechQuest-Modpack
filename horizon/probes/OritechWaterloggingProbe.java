package techquest.probes;

import com.google.gson.GsonBuilder;
import com.mojang.authlib.GameProfile;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.SimpleWaterloggedBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import net.minecraft.world.level.material.Fluids;
import net.minecraft.world.level.material.FluidState;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.common.util.FakePlayer;
import net.neoforged.neoforge.common.util.FakePlayerFactory;
import net.neoforged.neoforge.event.server.ServerStartedEvent;
import net.neoforged.neoforge.event.tick.ServerTickEvent;
import rearth.oritech.api.energy.EnergyApi;
import rearth.oritech.block.blocks.pipes.GenericPipeBlock;
import rearth.oritech.item.tools.Wrench;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

/** Calls pinned original CC0 Oritech; dependency public binary APIs only. */
@Mod("techquest_reference_probe")
public final class OritechWaterloggingProbe {
    private static final BlockPos POS=new BlockPos(256,210,128), FLOW=POS.south(32);
    private static final String WIRE="oritech:energy_pipe";
    private final Map<String,Object> result=new LinkedHashMap<>();
    private final List<Object> flow=new ArrayList<>();
    private FakePlayer player;
    private boolean ticking;
    private long start;
    public OritechWaterloggingProbe(){NeoForge.EVENT_BUS.addListener(this::started);NeoForge.EVENT_BUS.addListener(this::tick);}
    private static void require(boolean v,String message){if(!v)throw new IllegalStateException(message);}
    private static BlockState block(String id){return BuiltInRegistries.BLOCK.get(ResourceLocation.parse(id)).defaultBlockState();}
    private static String item(ItemStack stack){return stack.isEmpty()?"minecraft:air":BuiltInRegistries.ITEM.getKey(stack.getItem()).toString();}
    private static Map<String,Object> node(ServerLevel level,BlockPos pos){
        var state=level.getBlockState(pos);var fluid=state.getFluidState();var props=new TreeMap<String,String>();
        state.getValues().forEach((k,v)->props.put(k.getName(),v.toString()));
        var out=new LinkedHashMap<String,Object>();out.put("block",BuiltInRegistries.BLOCK.getKey(state.getBlock()).toString());out.put("properties",props);
        out.put("fluid",BuiltInRegistries.FLUID.getKey(fluid.getType()).toString());out.put("amount",fluid.getAmount());out.put("source",fluid.isSource());out.put("empty",fluid.isEmpty());
        var storage=EnergyApi.BLOCK.find(level,pos,Direction.UP);out.put("has_energy",storage!=null);if(storage!=null)out.put("energy",storage.getAmount());
        return out;
    }
    private static Map<String,Object> scheduled(ServerLevel level,BlockPos pos){return Map.of("water",level.getFluidTicks().hasScheduledTick(pos,Fluids.WATER),"flowing_water",level.getFluidTicks().hasScheduledTick(pos,Fluids.FLOWING_WATER));}
    private void clear(ServerLevel level){
        for(var p:BlockPos.betweenClosed(POS.offset(-3,-1,-3),POS.offset(3,2,3)))level.setBlock(p,Blocks.AIR.defaultBlockState(),3);
        level.getFluidTicks().clearArea(BoundingBox.fromCorners(POS.offset(-4,-2,-4),POS.offset(4,3,4)));
        for(var e:level.getEntitiesOfClass(ItemEntity.class,new AABB(POS).inflate(5)))e.discard();
        player.getInventory().clearContent();player.setShiftKeyDown(false);player.setGameMode(GameType.SURVIVAL);
    }
    private void aim(BlockPos pos){
        var eye=Vec3.atCenterOf(pos).add(0,.2,-2.5);var delta=Vec3.atCenterOf(pos).subtract(eye);
        player.setPos(eye.x,eye.y-player.getEyeHeight(),eye.z);player.setYRot((float)Math.toDegrees(Math.atan2(-delta.x,delta.z)));
        player.setXRot((float)Math.toDegrees(Math.atan2(-delta.y,Math.hypot(delta.x,delta.z))));player.setOldPosAndRot();
        player.setYHeadRot(player.getYRot());player.setYBodyRot(player.getYRot());player.yHeadRotO=player.yRotO=player.getYRot();player.yBodyRotO=player.getYRot();player.xRotO=player.getXRot();
        require(player.getViewVector(0).distanceTo(delta.normalize())<.0002,"unsynchronized camera");
    }
    private void pipe(ServerLevel level,boolean endpoint,boolean wet){
        clear(level);level.setBlockAndUpdate(POS.below(),Blocks.GLASS.defaultBlockState());
        if(endpoint)level.setBlockAndUpdate(POS.east(),block("oritech:basic_generator_block"));
        level.setBlockAndUpdate(POS,wet?Blocks.WATER.defaultBlockState():Blocks.AIR.defaultBlockState());
        var base=(GenericPipeBlock)block(WIRE).getBlock();var state=base.addConnectionStates(base.defaultBlockState(),level,POS,true);
        level.setBlockAndUpdate(POS,state);
        require(level.getBlockState(POS).getValue(BlockStateProperties.WATERLOGGED)==wet,"pipe fixture water");
        if(endpoint){var energy=EnergyApi.BLOCK.find(level,POS,Direction.UP);require(energy!=null,"missing interface");energy.insert(333,false);}
        level.getFluidTicks().clearArea(BoundingBox.fromCorners(POS.offset(-4,-2,-4),POS.offset(4,3,4)));
    }
    private void callbacks(ServerLevel level){
        var placements=new ArrayList<Object>();
        for(boolean endpoint:new boolean[]{false,true})for(int liquid=-1;liquid<16;liquid++){
            clear(level);level.setBlockAndUpdate(POS.below(),Blocks.GLASS.defaultBlockState());
            if(endpoint)level.setBlockAndUpdate(POS.east(),block("oritech:basic_generator_block"));
            level.setBlockAndUpdate(POS,liquid<0?Blocks.AIR.defaultBlockState():Blocks.WATER.defaultBlockState().setValue(BlockStateProperties.LEVEL,liquid));
            var before=node(level,POS);var stack=new ItemStack(BuiltInRegistries.ITEM.get(ResourceLocation.parse(WIRE)),2);player.setItemInHand(InteractionHand.MAIN_HAND,stack);
            var hit=new BlockHitResult(Vec3.atCenterOf(POS.below()).add(0,.5,0),Direction.UP,POS.below(),false);
            var used=stack.useOn(new UseOnContext(player,InteractionHand.MAIN_HAND,hit));
            placements.add(Map.of("endpoint",endpoint,"liquid_level",liquid,"before",before,"result",used.toString(),"after",node(level,POS),"remaining",stack.getCount()));
        }
        result.put("placements",placements);
        var liquids=new ArrayList<Object>();var pickups=new ArrayList<Object>();var updates=new ArrayList<Object>();
        FluidState[] fluids={Fluids.WATER.getSource(false),Fluids.FLOWING_WATER.getFlowing(4,false),Fluids.LAVA.getSource(false),Fluids.EMPTY.defaultFluidState()};
        for(boolean endpoint:new boolean[]{false,true})for(boolean wet:new boolean[]{false,true}){
            for(var fluid:fluids){
                pipe(level,endpoint,wet);var state=level.getBlockState(POS);var access=(SimpleWaterloggedBlock)state.getBlock();
                boolean can=access.canPlaceLiquid(player,level,POS,state,fluid.getType());boolean accepted=access.placeLiquid(level,POS,state,fluid);
                liquids.add(Map.of("endpoint",endpoint,"wet",wet,"fluid",BuiltInRegistries.FLUID.getKey(fluid.getType()).toString(),"can_place",can,"placed",accepted,"after",node(level,POS),"scheduled",scheduled(level,POS)));
            }
            pipe(level,endpoint,wet);var state=level.getBlockState(POS);var got=((SimpleWaterloggedBlock)state.getBlock()).pickupBlock(player,level,POS,state);
            pickups.add(Map.of("endpoint",endpoint,"wet",wet,"item",item(got),"count",got.getCount(),"after",node(level,POS)));
            for(var side:Direction.values()){
                pipe(level,endpoint,wet);state=level.getBlockState(POS);
                var after=state.updateShape(side,level.getBlockState(POS.relative(side)),level,POS,POS.relative(side));
                updates.add(Map.of("endpoint",endpoint,"wet",wet,"side",side.getName(),"same_state",state==after,"scheduled",scheduled(level,POS)));
            }
        }
        result.put("liquid_callbacks",liquids);result.put("pickup_callbacks",pickups);result.put("neighbor_scheduling",updates);
        var buckets=new ArrayList<Object>();var removals=new ArrayList<Object>();
        for(boolean endpoint:new boolean[]{false,true})for(boolean creative:new boolean[]{false,true})for(var hand:InteractionHand.values())for(String action:new String[]{"fill_dry","drain_wet","drain_dry"}){
            pipe(level,endpoint,action.equals("drain_wet"));player.setGameMode(creative?GameType.CREATIVE:GameType.SURVIVAL);aim(POS);
            var held=new ItemStack(action.equals("fill_dry")?Items.WATER_BUCKET:Items.BUCKET);player.setItemInHand(hand,held);
            var use=held.use(level,player,hand);player.setItemInHand(hand,use.getObject());
            var inv=new ArrayList<Object>();for(int i=0;i<player.getInventory().getContainerSize();i++){var s=player.getInventory().getItem(i);if(!s.isEmpty())inv.add(Map.of("slot",i,"item",item(s),"count",s.getCount()));}
            buckets.add(Map.of("endpoint",endpoint,"creative",creative,"hand",hand.toString(),"action",action,"result",use.getResult().toString(),"after",node(level,POS),"inventory",inv));
        }
        for(boolean endpoint:new boolean[]{false,true})for(boolean creative:new boolean[]{false,true})for(boolean wet:new boolean[]{false,true}){
            pipe(level,endpoint,wet);player.setGameMode(creative?GameType.CREATIVE:GameType.SURVIVAL);aim(POS);player.setShiftKeyDown(true);
            var wrench=(Wrench)BuiltInRegistries.ITEM.get(ResourceLocation.parse("oritech:wrench"));player.getCooldowns().removeCooldown(wrench);player.setItemInHand(InteractionHand.MAIN_HAND,new ItemStack(wrench));
            var use=wrench.use(level,player,InteractionHand.MAIN_HAND);var drops=new ArrayList<Object>();for(var e:level.getEntitiesOfClass(ItemEntity.class,new AABB(POS).inflate(2)))drops.add(Map.of("item",item(e.getItem()),"count",e.getItem().getCount()));
            removals.add(Map.of("endpoint",endpoint,"creative",creative,"wet",wet,"result",use.getResult().toString(),"after",node(level,POS),"drops",drops));
        }
        result.put("bucket_uses",buckets);result.put("shift_removals",removals);
        pipe(level,true,true);var lifecycle=new LinkedHashMap<String,Object>();lifecycle.put("before",node(level,POS));
        level.setBlockAndUpdate(POS.east(),Blocks.AIR.defaultBlockState());lifecycle.put("removed_provider",node(level,POS));
        level.setBlockAndUpdate(POS.east(),block("oritech:basic_generator_block"));lifecycle.put("replaced_provider",node(level,POS));result.put("wet_lifecycle",lifecycle);
    }
    private List<Object> flowState(ServerLevel level){
        var cells=new ArrayList<Object>();for(int x=-2;x<=2;x++)for(int z=-2;z<=2;z++)cells.add(Map.of("offset",List.of(x,z),"node",node(level,FLOW.offset(x,0,z))));return cells;
    }
    private void finish(MinecraftServer server)throws Exception{
        var level=server.overworld();server.tickRateManager().setFrozen(true);ticking=false;result.put("flow",flow);
        pipe(level,true,true);var state=level.getBlockState(POS);var block=(GenericPipeBlock)state.getBlock();
        block.onWrenchUseNeighbor(state,level.getBlockState(POS.east()),level,POS,POS.east(),Direction.WEST,player,InteractionHand.MAIN_HAND);
        result.put("saved",node(level,POS));write(server);
    }
    private void write(MinecraftServer server)throws Exception{Files.writeString(Path.of(System.getProperty("techquest.reference.result")),new GsonBuilder().setPrettyPrinting().create().toJson(result));server.halt(false);}
    private void started(ServerStartedEvent event){
        var server=event.getServer();try{
            var level=server.overworld();server.tickRateManager().setFrozen(true);for(int x=-1;x<=1;x++)for(int z=-1;z<=3;z++)level.getChunkAt(POS.offset(x*16,0,z*16));
            player=FakePlayerFactory.get(level,new GameProfile(UUID.fromString("a2663000-0000-4000-8000-000000000008"),"TQWaterOracle"));
            result.put("schema",1);result.put("original_waterlogging_callbacks_executed",true);result.put("driver","synthetic FakePlayer/direct original callbacks plus real server fluid ticks; no account or client packets");
            if(Boolean.getBoolean("techquest.reference.reopen")){result.put("before",node(level,POS));result.put("flow_before",flowState(level));write(server);return;}
            callbacks(level);
            // Loading a chunk alone does not make scheduled fluid ticks run
            // without a real player. Force all four chunks of the flow grid.
            for(int x=(FLOW.getX()-3)>>4;x<=((FLOW.getX()+3)>>4);x++)for(int z=(FLOW.getZ()-3)>>4;z<=((FLOW.getZ()+3)>>4);z++)level.setChunkForced(x,z,true);
            result.put("flow_chunks_forced",true);
            for(var p:BlockPos.betweenClosed(FLOW.offset(-3,-1,-3),FLOW.offset(3,1,3)))level.setBlock(p,p.getY()==FLOW.getY()-1?Blocks.GLASS.defaultBlockState():Blocks.AIR.defaultBlockState(),3);
            level.setBlockAndUpdate(FLOW,Blocks.WATER.defaultBlockState());var block=(GenericPipeBlock)block(WIRE).getBlock();level.setBlockAndUpdate(FLOW,block.addConnectionStates(block.defaultBlockState(),level,FLOW,true));
            level.setBlockAndUpdate(FLOW.east(),block.addConnectionStates(block.defaultBlockState(),level,FLOW.east(),true));
            flow.add(Map.of("elapsed",0,"cells",flowState(level),"scheduled",scheduled(level,FLOW)));start=level.getGameTime();ticking=true;server.tickRateManager().setFrozen(false);
        }catch(Exception e){server.halt(false);throw new IllegalStateException("Original waterlogging fixture failed",e);}
    }
    private void tick(ServerTickEvent.Post event){
        if(!ticking)return;var server=event.getServer();try{
            long elapsed=server.overworld().getGameTime()-start;
            if(List.of(1L,4L,5L,6L,10L).contains(elapsed))flow.add(Map.of("elapsed",elapsed,"cells",flowState(server.overworld())));
            if(elapsed>=10)finish(server);
        }catch(Exception e){server.halt(false);throw new IllegalStateException("Original waterlogging fluid ticks failed",e);}
    }
}
