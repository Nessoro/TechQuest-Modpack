package techquest.probes;

import com.google.gson.GsonBuilder;
import com.mojang.authlib.GameProfile;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.common.util.FakePlayer;
import net.neoforged.neoforge.common.util.FakePlayerFactory;
import net.neoforged.neoforge.event.server.ServerStartedEvent;
import rearth.oritech.api.energy.EnergyApi;
import rearth.oritech.block.blocks.pipes.GenericPipeBlock;
import rearth.oritech.init.OritechStartupConfig;
import rearth.oritech.item.tools.Wrench;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

/** Developer fixture: original CC0 wrench/use/shape calls, binary dependency APIs only. */
@Mod("techquest_reference_probe")
public final class OritechWrenchProbe {
    private static final BlockPos POS=new BlockPos(256,210,128);
    private static final String WIRE="oritech:energy_pipe", ENDPOINT="oritech:energy_pipe_connection";
    private static final Direction[] SHAPE_ORDER={Direction.NORTH,Direction.EAST,Direction.SOUTH,Direction.WEST,Direction.UP,Direction.DOWN};
    private final List<BlockPos> placed=new ArrayList<>();
    private final List<Object> geometry=new ArrayList<>(), callbacks=new ArrayList<>(), uses=new ArrayList<>(), removals=new ArrayList<>();
    private FakePlayer player;
    private Wrench wrench;
    private Method select;
    private static final class ItemAccess extends Wrench {
        ItemAccess(){super(new net.minecraft.world.item.Item.Properties());}
        static net.minecraft.world.phys.BlockHitResult pov(ServerLevel level,FakePlayer player){
            return getPlayerPOVHitResult(level,player,ClipContext.Fluid.NONE);
        }
    }
    public OritechWrenchProbe(){NeoForge.EVENT_BUS.addListener(this::started);}
    private static void require(boolean condition,String message){if(!condition)throw new IllegalStateException(message);}
    private void put(ServerLevel level,BlockPos pos,String id){
        level.getChunkAt(pos);if(!placed.contains(pos))placed.add(pos);
        var state=BuiltInRegistries.BLOCK.get(ResourceLocation.parse(id)).defaultBlockState();
        if(id.equals(WIRE))state=((GenericPipeBlock)state.getBlock()).addConnectionStates(state,level,pos,true);
        level.setBlockAndUpdate(pos,state);
    }
    private void clear(ServerLevel level){
        for(var p:placed)level.setBlockAndUpdate(p,Blocks.AIR.defaultBlockState());
        placed.clear();
        for(var drop:level.getEntitiesOfClass(ItemEntity.class,new AABB(POS).inflate(8)))drop.discard();
        player.setShiftKeyDown(false);player.setGameMode(GameType.SURVIVAL);
        player.getCooldowns().removeCooldown(wrench);
        player.setItemInHand(InteractionHand.MAIN_HAND,ItemStack.EMPTY);player.setItemInHand(InteractionHand.OFF_HAND,ItemStack.EMPTY);
    }
    private static Vec3 center(BlockPos pos){return Vec3.atCenterOf(pos);}
    private void aim(Vec3 eye,Vec3 toward){
        var delta=toward.subtract(eye);
        player.setPos(eye.x,eye.y-player.getEyeHeight(),eye.z);
        player.setYRot((float)Math.toDegrees(Math.atan2(-delta.x,delta.z)));
        player.setXRot((float)Math.toDegrees(Math.atan2(-delta.y,Math.hypot(delta.x,delta.z))));
        player.setOldPosAndRot();
        // FakePlayer has no normal client look packet updating head rotation.
        // Item's POV and LivingEntity.getViewVector must see the same camera.
        player.setYHeadRot(player.getYRot());player.setYBodyRot(player.getYRot());
        player.yHeadRotO=player.getYRot();player.yBodyRotO=player.getYRot();
        player.yRotO=player.getYRot();player.xRotO=player.getXRot();
        require(player.getViewVector(0f).distanceTo(delta.normalize())<.0002,"fixture head/view did not follow camera");
    }
    private Vec3 diagonalEye(Direction side){
        int axis=side.getAxis().ordinal();
        double[] values={.5,.5,.5};values[axis]=side.getAxisDirection()==Direction.AxisDirection.POSITIVE?1.2:-.2;
        values[(axis+1)%3]=.9;
        return new Vec3(POS.getX()+values[0],POS.getY()+values[1],POS.getZ()+values[2]);
    }
    private static Map<String,Object> node(ServerLevel level,BlockPos pos){
        var state=level.getBlockState(pos);var props=new TreeMap<String,String>();
        state.getValues().forEach((key,value)->props.put(key.getName(),value.toString()));
        var result=new LinkedHashMap<String,Object>();
        result.put("block",BuiltInRegistries.BLOCK.getKey(state.getBlock()).toString());result.put("properties",props);
        result.put("has_block_entity",level.getBlockEntity(pos)!=null);
        var buffer=EnergyApi.BLOCK.find(level,pos,Direction.UP);result.put("has_energy_api",buffer!=null);
        if(buffer!=null){result.put("energy",buffer.getAmount());result.put("capacity",buffer.getCapacity());}
        return result;
    }
    private static Map<String,Object> pair(ServerLevel level,Direction side){return Map.of("self",node(level,POS),"neighbor",node(level,POS.relative(side)));}
    private void setup(ServerLevel level,Direction side,boolean machine){
        clear(level);put(level,POS.relative(side),machine?"oritech:basic_generator_block":WIRE);put(level,POS,WIRE);
        require(level.getBlockState(POS).getBlock() instanceof GenericPipeBlock,"pipe fixture missing");
    }
    private void geometry(ServerLevel level)throws Exception{
        var block=(GenericPipeBlock)BuiltInRegistries.BLOCK.get(ResourceLocation.parse(WIRE));
        var fractions=new double[]{.2,.375,.5,.625,.8};
        for(int mask=0;mask<64;mask++){
            BlockState state=block.defaultBlockState();
            for(int bit=0;bit<6;bit++)state=state.setValue(block.directionToProperty(SHAPE_ORDER[bit]),(mask>>bit)&1);
            state=block.addStraightState(state);
            for(var side:Direction.values())for(double a:fractions)for(double b:fractions){
                int axis=side.getAxis().ordinal();double[] eye={0,0,0},target={.5,.5,.5};
                eye[axis]=side.getAxisDirection()==Direction.AxisDirection.POSITIVE?3.5:-2.5;
                eye[(axis+1)%3]=a;eye[(axis+2)%3]=b;
                target[(axis+1)%3]=a;target[(axis+2)%3]=b;
                aim(new Vec3(POS.getX()+eye[0],POS.getY()+eye[1],POS.getZ()+eye[2]),new Vec3(POS.getX()+target[0],POS.getY()+target[1],POS.getZ()+target[2]));
                var start=player.getEyePosition(0f);var end=start.add(player.getViewVector(0f).scale(5));
                var hit=state.getShape(level,POS).clip(start,end,POS);
                var row=new LinkedHashMap<String,Object>();row.put("mask",mask);row.put("view_side",side.getName());
                row.put("fraction_a",a);row.put("fraction_b",b);row.put("eye",List.of(start.x-POS.getX(),start.y-POS.getY(),start.z-POS.getZ()));
                row.put("end",List.of(end.x-POS.getX(),end.y-POS.getY(),end.z-POS.getZ()));row.put("block_shape_hit",hit!=null);
                if(hit!=null)row.put("selected_side",((Direction)select.invoke(block,state,POS,player)).getName());
                geometry.add(row);
            }
        }
        require(geometry.size()==9600,"geometry case count changed");
    }
    private void callbacks(ServerLevel level){
        for(var side:Direction.values())for(boolean machine:new boolean[]{false,true}){
            setup(level,side,machine);var before=pair(level,side);
            if(machine)EnergyApi.BLOCK.find(level,POS,side).setAmount(333);
            var block=(GenericPipeBlock)level.getBlockState(POS).getBlock();
            var off=block.onWrenchUseNeighbor(level.getBlockState(POS),level.getBlockState(POS.relative(side)),level,POS,POS.relative(side),side.getOpposite(),player,InteractionHand.MAIN_HAND);
            var disabled=pair(level,side);block=(GenericPipeBlock)level.getBlockState(POS).getBlock();
            var on=block.onWrenchUseNeighbor(level.getBlockState(POS),level.getBlockState(POS.relative(side)),level,POS,POS.relative(side),side.getOpposite(),player,InteractionHand.OFF_HAND);
            callbacks.add(Map.of("side",side.getName(),"machine_neighbor",machine,"before",before,"disabled",disabled,"enabled",pair(level,side),"off_result",off.toString(),"on_result",on.toString(),"discarded_interface_energy",machine?333:0));
        }
        setup(level,Direction.EAST,false);
        var before=pair(level,Direction.EAST);var block=(GenericPipeBlock)level.getBlockState(POS).getBlock();
        var invalid=block.onWrenchUseNeighbor(level.getBlockState(POS),Blocks.AIR.defaultBlockState(),level,POS,POS.north(),Direction.SOUTH,player,InteractionHand.MAIN_HAND);
        require(pair(level,Direction.EAST).equals(before),"invalid side changed wire");
        callbacks.add(Map.of("kind","invalid_air_target","result",invalid.toString(),"before",before,"after",pair(level,Direction.EAST)));
    }
    private Map<String,Object> use(ServerLevel level,InteractionHand hand)throws Exception{
        var hit=ItemAccess.pov(level,player);var ray=new LinkedHashMap<String,Object>();
        ray.put("type",hit.getType().toString());ray.put("pos",List.of(hit.getBlockPos().getX()-POS.getX(),hit.getBlockPos().getY()-POS.getY(),hit.getBlockPos().getZ()-POS.getZ()));
        ray.put("face",hit.getDirection().getName());
        if(level.getBlockState(hit.getBlockPos()).getBlock() instanceof GenericPipeBlock block)
            ray.put("selected_side",((Direction)select.invoke(block,level.getBlockState(hit.getBlockPos()),hit.getBlockPos(),player)).getName());
        var result=wrench.use(level,player,hand);
        return Map.of("result",result.getResult().toString(),"cooldown",player.getCooldowns().getCooldownPercent(wrench,0f),
            "stack_count",player.getItemInHand(hand).getCount(),"state",node(level,POS),"ray_before_use",ray);
    }
    private void uses(ServerLevel level)throws Exception{
        for(var side:Direction.values())for(var hand:InteractionHand.values()){
            setup(level,side,false);player.setItemInHand(hand,new ItemStack(wrench));aim(diagonalEye(side),center(POS));
            var before=pair(level,side);var states=new ArrayList<Object>();int elapsed=0;
            for(int checkpoint:new int[]{0,1,7,8,9,16}){
                while(elapsed<checkpoint){player.getCooldowns().tick();elapsed++;}
                var action=use(level,hand);
                require(action.get("result").equals(checkpoint%8==0?"SUCCESS":"FAIL"),"unexpected original cooldown result on "+side+" at "+checkpoint);
                require(level.getBlockState(POS).getValue(((GenericPipeBlock)level.getBlockState(POS).getBlock()).directionToProperty(side))==(checkpoint>=8&&checkpoint<16?1:0),"unexpected toggled side on "+side+" at "+checkpoint);
                states.add(Map.of("elapsed",checkpoint,"use",action,"pair",pair(level,side)));
            }
            uses.add(Map.of("side",side.getName(),"hand",hand.toString(),"kind","full_original_use","before",before,"states",states));
        }
        setup(level,Direction.EAST,false);player.setItemInHand(InteractionHand.MAIN_HAND,new ItemStack(wrench));player.setItemInHand(InteractionHand.OFF_HAND,new ItemStack(wrench));
        aim(center(POS).add(0,2.5,0),center(POS).add(0,3.5,0));var miss=use(level,InteractionHand.MAIN_HAND);
        aim(diagonalEye(Direction.EAST),center(POS));var blocked=use(level,InteractionHand.OFF_HAND);
        for(int i=0;i<8;i++)player.getCooldowns().tick();var resumed=use(level,InteractionHand.OFF_HAND);
        require(level.getBlockState(POS).getValue(GenericPipeBlock.EAST)==0,"cooldown release did not toggle east");
        uses.add(Map.of("kind","air_miss_and_cross_hand_shared_cooldown","miss",miss,"blocked_offhand",blocked,"after_eight_ticks",resumed));
    }
    private void removals(ServerLevel level)throws Exception{
        for(boolean machine:new boolean[]{false,true})for(boolean creative:new boolean[]{false,true}){
            setup(level,Direction.EAST,machine);player.setItemInHand(InteractionHand.MAIN_HAND,new ItemStack(wrench));
            if(machine)EnergyApi.BLOCK.find(level,POS,Direction.UP).setAmount(333);
            player.setGameMode(creative?GameType.CREATIVE:GameType.SURVIVAL);player.setShiftKeyDown(true);
            aim(Vec3.atLowerCornerOf(POS).add(.9,.9,-1.5),Vec3.atLowerCornerOf(POS).add(.9,.5,.5));
            var before=node(level,POS);var result=use(level,InteractionHand.MAIN_HAND);
            var drops=new ArrayList<Object>();
            for(var entity:level.getEntitiesOfClass(ItemEntity.class,new AABB(POS).inflate(8)))drops.add(Map.of("item",BuiltInRegistries.ITEM.getKey(entity.getItem().getItem()).toString(),"count",entity.getItem().getCount()));
            require(level.getBlockState(POS).isAir(),"shift wrench did not remove fixture wire");
            removals.add(Map.of("machine_interface",machine,"creative",creative,"before",before,"use",result,"drops",drops,"after",node(level,POS)));
        }
    }
    private void started(ServerStartedEvent event){
        var server=event.getServer();
        try{
            var level=server.overworld();server.tickRateManager().setFrozen(true);
            for(int x=-1;x<=1;x++)for(int z=-1;z<=1;z++)level.getChunkAt(POS.offset(x*16,0,z*16));
            player=FakePlayerFactory.get(level,new GameProfile(UUID.fromString("a2663000-0000-4000-8000-000000000007"),"TQWrenchOracle"));
            wrench=(Wrench)BuiltInRegistries.ITEM.get(ResourceLocation.parse("oritech:wrench"));
            select=GenericPipeBlock.class.getDeclaredMethod("getInteractDirection",BlockState.class,BlockPos.class,net.minecraft.world.entity.player.Player.class);select.setAccessible(true);
            var result=new LinkedHashMap<String,Object>();result.put("schema",1);result.put("original_wrench_callbacks_executed",true);
            result.put("fake_player_head_body_and_previous_rotation_synchronized",true);
            result.put("default_tight_cable_hitboxes",OritechStartupConfig.tightCableHitboxes.get());require(OritechStartupConfig.tightCableHitboxes.get(),"unexpected original selection config");
            if(Boolean.getBoolean("techquest.reference.reopen")){
                result.put("before",pair(level,Direction.WEST));
                player.setItemInHand(InteractionHand.MAIN_HAND,new ItemStack(wrench));aim(diagonalEye(Direction.WEST),center(POS));
                result.put("use_after_reopen",use(level,InteractionHand.MAIN_HAND));result.put("after",pair(level,Direction.WEST));
                require(level.getBlockState(POS).getValue(GenericPipeBlock.WEST)==1,"physical reopen did not reconnect");
            }else{
                geometry(level);callbacks(level);uses(level);removals(level);
                result.put("geometry",geometry);result.put("neighbor_callbacks",callbacks);result.put("uses",uses);result.put("shift_removals",removals);
                setup(level,Direction.WEST,false);
                var block=(GenericPipeBlock)level.getBlockState(POS).getBlock();
                block.onWrenchUseNeighbor(level.getBlockState(POS),level.getBlockState(POS.west()),level,POS,POS.west(),Direction.EAST,player,InteractionHand.MAIN_HAND);
                result.put("saved",pair(level,Direction.WEST));result.put("saved_side","west");result.put("cooldown_ticks",Wrench.ACTION_COOLDOWN);
                result.put("driver","synthetic NeoForge FakePlayer with explicit pose/view and direct original use calls; cooldown clock stepped explicitly; no account or real input packets");
            }
            Files.writeString(Path.of(System.getProperty("techquest.reference.result")),new GsonBuilder().setPrettyPrinting().create().toJson(result));
        }catch(Exception e){throw new IllegalStateException("Original wrench oracle failed",e);}
        finally{server.halt(false);}
    }
}
