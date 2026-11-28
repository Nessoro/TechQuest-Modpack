package techquest.probes;

import com.google.gson.GsonBuilder;
import com.mojang.authlib.GameProfile;
import dev.architectury.fluid.FluidStack;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.component.DataComponentPatch;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.MenuProvider;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.material.Fluids;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.common.util.FakePlayer;
import net.neoforged.neoforge.event.server.ServerStartedEvent;
import rearth.oritech.api.fluid.FluidApi;
import rearth.oritech.api.fluid.containers.SimpleFluidStorage;
import rearth.oritech.block.entity.storage.SmallTankEntity;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;
import java.util.function.Consumer;

/** Developer-only original Oritech callbacks; no dependency Java bodies read. */
@Mod("techquest_reference_probe")
public final class OritechFluidTankProbe {
    private static final BlockPos POS=new BlockPos(256,210,128);
    private static final String TANK="oritech:small_tank_block";
    private MenuPlayer player;
    private static final class MenuPlayer extends FakePlayer {
        boolean requested;
        MenuPlayer(ServerLevel level){super(level,new GameProfile(UUID.fromString("a2663000-0000-4000-8000-000000000010"),"TQFluidRef"));}
        @Override public OptionalInt openMenu(MenuProvider p){return openMenu(p,buf->{});}
        @Override public OptionalInt openMenu(MenuProvider p,Consumer<RegistryFriendlyByteBuf> extra){requested=true;var m=p.createMenu(1,getInventory(),this);if(m==null)return OptionalInt.empty();containerMenu=m;return OptionalInt.of(1);}
    }
    public OritechFluidTankProbe(){NeoForge.EVENT_BUS.addListener(this::started);}
    private static ItemStack item(String id,int count){return count==0||id.equals("minecraft:air")?ItemStack.EMPTY:new ItemStack(BuiltInRegistries.ITEM.get(ResourceLocation.parse(id)),count);}
    private static FluidStack fluid(String id,long amount,int variant){
        var f=BuiltInRegistries.FLUID.get(ResourceLocation.parse(id));
        if(variant==0)return FluidStack.create(f,amount);
        return FluidStack.create(f,amount,DataComponentPatch.builder().set(DataComponents.CUSTOM_NAME,Component.literal("fluid-"+variant)).build());
    }
    private static Map<String,Object> content(FluidStack stack){
        return Map.of("fluid",BuiltInRegistries.FLUID.getKey(stack.getFluid()).toString(),"amount",stack.getAmount(),"empty",stack.isEmpty(),"components",stack.getPatch().toString());
    }
    private static Map<String,Object> stack(ItemStack s){
        var out=new LinkedHashMap<String,Object>();out.put("item",BuiltInRegistries.ITEM.getKey(s.getItem()).toString());out.put("count",s.getCount());out.put("max_stack",s.getMaxStackSize());
        if(s.has(FluidApi.ITEM.getFluidComponent()))out.put("stored_fluid",content(s.get(FluidApi.ITEM.getFluidComponent())));
        return out;
    }
    private static List<Object> inventory(net.minecraft.world.Container inv){
        var out=new ArrayList<Object>();for(int i=0;i<inv.getContainerSize();i++){var s=inv.getItem(i);if(!s.isEmpty()){var row=new LinkedHashMap<String,Object>(stack(s));row.put("slot",i);out.add(row);}}return out;
    }
    private static Map<String,Object> node(SmallTankEntity t){return Map.of("fluid",content(t.fluidStorage.getStack()),"items",inventory(t.inventory),"lit",t.getBlockState().getValue(BlockStateProperties.LIT),"comparator",t.getComparatorOutput());}
    private static void seed(SmallTankEntity t,String kind,long amount){t.fluidStorage.setStack(fluid(kind,amount,0));t.fluidStorage.update();}
    private static SmallTankEntity place(ServerLevel level,BlockPos pos){level.setBlockAndUpdate(pos,Blocks.AIR.defaultBlockState());level.setBlockAndUpdate(pos,BuiltInRegistries.BLOCK.get(ResourceLocation.parse(TANK)).defaultBlockState());return (SmallTankEntity)level.getBlockEntity(pos);}
    private SmallTankEntity fixture(ServerLevel level){
        player.closeContainer();player.getInventory().clearContent();player.setShiftKeyDown(false);player.setGameMode(GameType.SURVIVAL);player.requested=false;
        for(var p:BlockPos.betweenClosed(POS.offset(-1,-2,-1),POS.offset(1,1,1)))level.setBlockAndUpdate(p,Blocks.AIR.defaultBlockState());
        return place(level,POS);
    }
    private static void tick(ServerLevel level,SmallTankEntity t){t.serverTick(level,t.getBlockPos(),t.getBlockState(),t);}
    private static long[] amounts(long cap){return new long[]{0,1,999,1000,1001,cap-1000,cap-1,cap};}
    private List<Object> storage(long cap){
        var rows=new ArrayList<Object>();
        for(String initial:new String[]{"minecraft:water","minecraft:lava"})for(long amount:amounts(cap))for(int storedVariant:new int[]{0,1})
            for(String requested:new String[]{"minecraft:water","minecraft:lava"})for(long count:new long[]{0,1,999,1000,cap+17})for(int requestVariant:new int[]{0,1})for(boolean insert:new boolean[]{false,true})for(boolean simulate:new boolean[]{false,true}){
                var t=new SimpleFluidStorage(cap);t.setStack(fluid(initial,amount,storedVariant));var before=content(t.getStack());var ask=fluid(requested,count,requestVariant);
                long moved=insert?t.insert(ask,simulate):t.extract(ask,simulate);
                rows.add(Map.of("initial",before,"request",content(ask),"insert",insert,"simulate",simulate,"moved",moved,"after",content(t.getStack())));
            }
        return rows;
    }
    private List<Object> processing(ServerLevel level,long cap){
        var rows=new ArrayList<Object>();
        for(String kind:new String[]{"minecraft:water","minecraft:lava"})for(long amount:amounts(cap))for(int slot:new int[]{0,1})
            for(String bucket:new String[]{"minecraft:bucket","minecraft:water_bucket","minecraft:lava_bucket"})for(int count:new int[]{1,2})for(int output:new int[]{0,1,2,3}){
                var t=fixture(level);seed(t,kind,amount);t.inventory.setItem(slot,item(bucket,count));
                if(output!=0)t.inventory.setItem(2,item(output==3?"minecraft:barrier":"minecraft:bucket",output==2?16:1));
                var row=new LinkedHashMap<String,Object>();row.put("name","process_"+rows.size());row.put("initial",node(t));var states=new ArrayList<Object>();
                for(int n=1;n<=4;n++){tick(level,t);states.add(Map.of("tick",n,"state",node(t)));}row.put("states",states);rows.add(row);
            }
        return rows;
    }
    private List<Object> gravity(ServerLevel level,long cap){
        var rows=new ArrayList<Object>();
        for(String upper:new String[]{"minecraft:water","minecraft:lava"})for(long up:new long[]{0,999,1000,cap})for(String lower:new String[]{"minecraft:water","minecraft:lava"})for(long down:new long[]{0,cap-999,cap}){
            var a=fixture(level);var b=place(level,POS.below());seed(a,upper,up);seed(b,lower,down);
            var before=Map.of("upper",node(a),"lower",node(b));tick(level,a);tick(level,b);
            rows.add(Map.of("name","gravity_"+rows.size(),"before",before,"after",Map.of("upper",node(a),"lower",node(b))));
        }
        return rows;
    }
    private Map<String,Object> click(ServerLevel level){
        var hit=new BlockHitResult(Vec3.atLowerCornerOf(POS).add(0,.5,.5),Direction.WEST,POS,false);var phases=new ArrayList<Object>();
        for(var hand:InteractionHand.values()){
            var s=player.getItemInHand(hand);var used=player.gameMode.useItemOn(player,level,s,hand,hit);phases.add(Map.of("hand",hand.toString(),"phase","useItemOn","result",used.toString()));
            if(used.consumesAction()||used==InteractionResult.FAIL)break;
            if(!s.isEmpty()){used=player.gameMode.useItem(player,level,s,hand);phases.add(Map.of("hand",hand.toString(),"phase","useItem","result",used.toString()));if(used.consumesAction()||used==InteractionResult.FAIL)break;}
        }
        return Map.of("phases",phases,"menu_requested",player.requested,"menu_slots",player.containerMenu.slots.size(),"after",node((SmallTankEntity)level.getBlockEntity(POS)),"inventory",inventory(player.getInventory()));
    }
    private List<Object> buckets(ServerLevel level,long cap){
        var rows=new ArrayList<Object>();
        for(String kind:new String[]{"minecraft:water","minecraft:lava"})for(long amount:new long[]{0,999,1000,cap-999,cap})
            for(String bucket:new String[]{"minecraft:bucket","minecraft:water_bucket","minecraft:lava_bucket","oritech:wrench","minecraft:air"})for(boolean off:new boolean[]{false,true})for(boolean creative:new boolean[]{false,true})for(int count:new int[]{1,2}){
                if(count==2&&!bucket.endsWith("bucket"))continue;
                var t=fixture(level);seed(t,kind,amount);player.setGameMode(creative?GameType.CREATIVE:GameType.SURVIVAL);player.setItemInHand(off?InteractionHand.OFF_HAND:InteractionHand.MAIN_HAND,item(bucket,count));
                rows.add(Map.of("name","bucket_"+rows.size(),"initial",node(t),"held",bucket,"count",count,"offhand",off,"creative",creative,"click",click(level)));
            }
        return rows;
    }
    private List<Object> itemData(ServerLevel level){
        var rows=new ArrayList<Object>();
        for(String kind:new String[]{"minecraft:water","minecraft:lava"})for(long amount:new long[]{0,1,999,1000,12345}){
            var t=fixture(level);seed(t,kind,amount);var block=t.getBlockState().getBlock();var clone=block.getCloneItemStack(level,POS,t.getBlockState());
            var cloned=stack(clone);var before=node(t);
            var drops=Block.getDrops(t.getBlockState(),level,POS,t,player,item("minecraft:diamond_pickaxe",1));var dropped=new ArrayList<Object>();for(var s:drops)dropped.add(stack(s));
            var placed=place(level,POS.above());placed.getBlockState().getBlock().setPlacedBy(level,POS.above(),placed.getBlockState(),player,clone);
            rows.add(Map.of("name","item_"+rows.size(),"before",before,"clone",cloned,"drops",dropped,"placed",node(placed)));
        }
        return rows;
    }
    private List<Object> portable(ServerLevel level,long cap){
        var rows=new ArrayList<Object>();
        for(String kind:new String[]{"minecraft:water","minecraft:lava"})for(long amount:new long[]{0,999,1000,64000,cap})for(int slot:new int[]{0,1})for(int mode:new int[]{0,1,2,3}){
            var t=fixture(level);seed(t,kind,amount);var container=item(TANK,1);
            if(mode>0){container.set(FluidApi.ITEM.getFluidComponent(),fluid(mode==2?"minecraft:lava":"minecraft:water",mode==3?cap:1000,0));container.set(DataComponents.MAX_STACK_SIZE,1);}
            t.inventory.setItem(slot,container);var row=new LinkedHashMap<String,Object>();row.put("name","portable_"+rows.size());row.put("initial",node(t));var states=new ArrayList<Object>();
            for(int n=1;n<=5;n++){tick(level,t);states.add(Map.of("tick",n,"state",node(t)));}row.put("states",states);rows.add(row);
        }
        return rows;
    }
    private List<Object> componentLimits(ServerLevel level){
        var rows=new ArrayList<Object>();
        for(String kind:new String[]{"minecraft:water","minecraft:lava"})for(long amount:new long[]{0,1,1000,12345})for(int variant:new int[]{0,1}){
            var t=fixture(level);t.fluidStorage.setStack(fluid(kind,amount,variant));t.fluidStorage.update();
            var clone=t.getBlockState().getBlock().getCloneItemStack(level,POS,t.getBlockState());
            player.getInventory().add(clone.copy());player.getInventory().add(clone.copy());
            rows.add(Map.of("name","limit_"+rows.size(),"clone",stack(clone),"after_giving_two_equal_clones",inventory(player.getInventory())));
        }
        return rows;
    }
    private void started(ServerStartedEvent event){
        var server=event.getServer();var level=server.overworld();try{
            server.tickRateManager().setFrozen(true);level.getChunkAt(POS);player=new MenuPlayer(level);var out=new LinkedHashMap<String,Object>();out.put("schema",1);out.put("original_callbacks_and_server_tick_executed",true);
            if(Boolean.getBoolean("techquest.reference.reopen")){
                var a=(SmallTankEntity)level.getBlockEntity(POS);var b=(SmallTankEntity)level.getBlockEntity(POS.below());out.put("before",Map.of("upper",node(a),"lower",node(b)));
                tick(level,a);tick(level,b);out.put("after",Map.of("upper",node(a),"lower",node(b)));
            }else{
                long cap=fixture(level).fluidStorage.getCapacity();out.put("capacity",cap);out.put("storage",storage(cap));out.put("processing",processing(level,cap));out.put("gravity",gravity(level,cap));out.put("buckets",buckets(level,cap));out.put("item_data",itemData(level));out.put("portable_processing",portable(level,cap));out.put("component_limits",componentLimits(level));
                var a=fixture(level);var b=place(level,POS.below());seed(a,"minecraft:lava",2345);seed(b,"minecraft:lava",cap-1000);a.inventory.setItem(0,item("minecraft:bucket",1));a.inventory.setItem(1,item("minecraft:lava_bucket",1));out.put("saved",Map.of("upper",node(a),"lower",node(b)));
            }
            out.put("driver","Original fluid storage, SmallTankEntity serverTick and server useItemOn/useItem; instrumented FakePlayer materializes requested MenuProvider; initial fluids, inventory and hand driver are fixtures, not real client packets or licensed multiplayer");
            Files.writeString(Path.of(System.getProperty("techquest.reference.result")),new GsonBuilder().setPrettyPrinting().create().toJson(out));
        }catch(Exception e){throw new IllegalStateException("Original fluid tank fixture failed",e);}finally{server.halt(false);}
    }
}
