package techquest.probes;

import com.google.gson.GsonBuilder;
import com.mojang.authlib.GameProfile;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.MenuProvider;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.common.util.FakePlayer;
import net.neoforged.neoforge.common.util.FakePlayerFactory;
import net.neoforged.neoforge.event.server.ServerStartedEvent;
import rearth.oritech.api.energy.EnergyApi;
import rearth.oritech.block.blocks.pipes.GenericPipeBlock;
import rearth.oritech.item.tools.Wrench;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;
import java.util.function.Consumer;

/** Original server useItemOn/useItem callbacks; synthetic hand driver, no real packets. */
@Mod("techquest_reference_probe")
public final class OritechWrenchDispatchProbe {
    private static final BlockPos POS=new BlockPos(256,210,128), WIRE=POS.west();
    private static final String TOOL="oritech:wrench", PIPE="oritech:energy_pipe";
    private final List<Object> rows=new ArrayList<>();
    private MenuPlayer player;
    private Wrench wrench;
    // NeoForge's base FakePlayer deliberately suppresses menus. Observe the
    // requested provider boundary and construct its original menu without
    // pretending that a real client window or network connection exists.
    private static final class MenuPlayer extends FakePlayer {
        boolean requested;
        MenuPlayer(ServerLevel level,GameProfile profile){super(level,profile);}
        @Override public OptionalInt openMenu(MenuProvider provider){return openMenu(provider,buf->{});}
        @Override public OptionalInt openMenu(MenuProvider provider,Consumer<RegistryFriendlyByteBuf> extra){
            requested=true;var menu=provider.createMenu(1,getInventory(),this);
            if(menu==null)return OptionalInt.empty();containerMenu=menu;return OptionalInt.of(1);
        }
    }
    public OritechWrenchDispatchProbe(){NeoForge.EVENT_BUS.addListener(this::started);}
    private static void require(boolean ok,String message){if(!ok)throw new IllegalStateException(message);}
    private static ItemStack stack(String id){return id.equals("minecraft:air")?ItemStack.EMPTY:new ItemStack(BuiltInRegistries.ITEM.get(ResourceLocation.parse(id)));}
    private static Map<String,Object> node(ServerLevel level,BlockPos pos){
        var state=level.getBlockState(pos);var props=new TreeMap<String,String>();state.getValues().forEach((k,v)->props.put(k.getName(),v.toString()));
        var out=new LinkedHashMap<String,Object>();out.put("block",BuiltInRegistries.BLOCK.getKey(state.getBlock()).toString());out.put("properties",props);
        var energy=EnergyApi.BLOCK.find(level,pos,Direction.UP);out.put("has_energy",energy!=null);if(energy!=null)out.put("energy",energy.getAmount());return out;
    }
    private static Map<String,Object> world(ServerLevel level){return Map.of("machine",node(level,POS),"wire",node(level,WIRE));}
    private void aim(){
        var eye=Vec3.atLowerCornerOf(POS).add(-2.5,.8,.1);var target=Vec3.atLowerCornerOf(POS).add(.5,.8,.1);var delta=target.subtract(eye);
        player.setPos(eye.x,eye.y-player.getEyeHeight(),eye.z);player.setYRot((float)Math.toDegrees(Math.atan2(-delta.x,delta.z)));player.setXRot(0);
        player.setOldPosAndRot();player.setYHeadRot(player.getYRot());player.setYBodyRot(player.getYRot());player.yHeadRotO=player.yRotO=player.getYRot();player.yBodyRotO=player.getYRot();player.xRotO=player.getXRot();
        require(player.getViewVector(0).distanceTo(delta.normalize())<.0002,"camera fixture is not synchronized");
    }
    private void fixture(ServerLevel level,String block,boolean assembled,boolean wet,boolean connected){
        player.closeContainer();player.getInventory().clearContent();player.setShiftKeyDown(false);player.setGameMode(GameType.SURVIVAL);player.getCooldowns().removeCooldown(wrench);
        player.requested=false;
        for(var p:BlockPos.betweenClosed(POS.offset(-3,-1,-2),POS.offset(2,2,2)))level.setBlockAndUpdate(p,Blocks.AIR.defaultBlockState());
        var state=BuiltInRegistries.BLOCK.get(ResourceLocation.parse(block)).defaultBlockState();
        for(var p:state.getProperties())if(p.getName().equals("machine_assembled"))state=state.setValue((net.minecraft.world.level.block.state.properties.BooleanProperty)p,assembled);
        level.setBlockAndUpdate(POS,state);
        level.setBlockAndUpdate(WIRE,wet?Blocks.WATER.defaultBlockState():Blocks.AIR.defaultBlockState());
        var pipe=(GenericPipeBlock)BuiltInRegistries.BLOCK.get(ResourceLocation.parse(PIPE));level.setBlockAndUpdate(WIRE,pipe.addConnectionStates(pipe.defaultBlockState(),level,WIRE,true));
        var wireState=level.getBlockState(WIRE);
        if(!connected&&wireState.getValue(GenericPipeBlock.EAST)!=0)((GenericPipeBlock)wireState.getBlock()).onWrenchUseNeighbor(wireState,level.getBlockState(POS),level,WIRE,POS,Direction.WEST,player,InteractionHand.MAIN_HAND);
        var energy=EnergyApi.BLOCK.find(level,WIRE,Direction.UP);if(energy!=null)energy.setAmount(333);
    }
    private Map<String,Object> click(ServerLevel level){
        var phases=new ArrayList<Object>();var hit=new BlockHitResult(Vec3.atLowerCornerOf(POS).add(0,.8,.1),Direction.WEST,POS,false);
        for(var hand:InteractionHand.values()){
            var held=player.getItemInHand(hand);var used=player.gameMode.useItemOn(player,level,held,hand,hit);
            phases.add(Map.of("phase","useItemOn","hand",hand.toString(),"result",used.toString()));
            if(used.consumesAction()||used==InteractionResult.FAIL)break;
            if(!held.isEmpty()){
                used=player.gameMode.useItem(player,level,held,hand);phases.add(Map.of("phase","useItem","hand",hand.toString(),"result",used.toString()));
                if(used.consumesAction()||used==InteractionResult.FAIL)break;
            }
        }
        var out=new LinkedHashMap<String,Object>();out.put("phases",phases);out.put("menu_requested",player.requested);out.put("original_provider_materialized",player.containerMenu!=player.inventoryMenu);
        out.put("menu_class",player.containerMenu.getClass().getName());out.put("menu_slots",player.containerMenu.slots.size());
        out.put("cooldown",player.getCooldowns().getCooldownPercent(wrench,0));out.put("after",world(level));
        var inv=new ArrayList<Object>();for(int i=0;i<player.getInventory().getContainerSize();i++){var s=player.getInventory().getItem(i);if(!s.isEmpty())inv.add(Map.of("slot",i,"item",BuiltInRegistries.ITEM.getKey(s.getItem()).toString(),"count",s.getCount()));}out.put("inventory",inv);
        return out;
    }
    private void one(ServerLevel level,String block,boolean assembled,boolean wet,boolean connected,boolean creative,boolean shift,String main,String off,boolean cooling){
        fixture(level,block,assembled,wet,connected);player.setGameMode(creative?GameType.CREATIVE:GameType.SURVIVAL);player.setShiftKeyDown(shift);
        player.setItemInHand(InteractionHand.MAIN_HAND,stack(main));player.setItemInHand(InteractionHand.OFF_HAND,stack(off));if(cooling)player.getCooldowns().addCooldown(wrench,8);aim();
        var row=new LinkedHashMap<String,Object>();row.put("name","case_"+rows.size());row.put("block",block);row.put("assembled_fixture",assembled);row.put("wet",wet);row.put("connected",connected);row.put("creative",creative);row.put("shift",shift);row.put("main",main);row.put("off",off);row.put("initial_cooldown",cooling);
        row.put("machine_implements_wrenchable",level.getBlockState(POS).getBlock() instanceof Wrench.Wrenchable);row.put("before",world(level));row.put("click",click(level));rows.add(row);
    }
    private void started(ServerStartedEvent event){
        var server=event.getServer();try{
            var level=server.overworld();server.tickRateManager().setFrozen(true);for(int x=-1;x<=1;x++)for(int z=-1;z<=1;z++)level.getChunkAt(POS.offset(x*16,0,z*16));
            player=new MenuPlayer(level,new GameProfile(UUID.fromString("a2663000-0000-4000-8000-000000000009"),"TQDispatch"));wrench=(Wrench)BuiltInRegistries.ITEM.get(ResourceLocation.parse(TOOL));
            var result=new LinkedHashMap<String,Object>();result.put("schema",1);result.put("original_server_use_item_on_and_use_item_executed",true);
            if(Boolean.getBoolean("techquest.reference.reopen")){
                result.put("before",world(level));player.setShiftKeyDown(true);player.setItemInHand(InteractionHand.MAIN_HAND,stack(TOOL));aim();result.put("click",click(level));
            }else{
                for(String block:new String[]{"oritech:basic_generator_block","oritech:pulverizer_block","oritech:powered_furnace_block","oritech:foundry_block","oritech:assembler_block","minecraft:chest","minecraft:stone"}){
                    for(boolean assembled:new boolean[]{false,true}){
                        if(!assembled&&!block.matches("oritech:(powered_furnace|foundry|assembler)_block"))continue;
                        for(boolean wet:new boolean[]{false,true})for(boolean connected:new boolean[]{false,true})for(boolean creative:new boolean[]{false,true})for(boolean shift:new boolean[]{false,true})for(boolean off:new boolean[]{false,true}){
                            one(level,block,assembled,wet,connected,creative,shift,off?"minecraft:air":TOOL,off?TOOL:"minecraft:air",false);
                        }
                        for(String[] hands:new String[][]{{TOOL,TOOL},{"minecraft:stick",TOOL},{TOOL,"minecraft:stick"},{"minecraft:water_bucket","minecraft:air"},{"minecraft:air","minecraft:air"}}){
                            for(boolean shift:new boolean[]{false,true})one(level,block,assembled,false,true,false,shift,hands[0],hands[1],false);
                        }
                        for(boolean shift:new boolean[]{false,true})one(level,block,assembled,false,true,false,shift,TOOL,"minecraft:air",true);
                    }
                }
                result.put("rows",rows);fixture(level,"oritech:basic_generator_block",true,true,false);result.put("saved",world(level));
            }
            result.put("driver","instrumented FakePlayer records openMenu and materializes the original MenuProvider; main/off hand driver invokes original server useItemOn then useItem when not consumed; not a real client/window or packet ordering proof; assembly flags may be seeded");
            Files.writeString(Path.of(System.getProperty("techquest.reference.result")),new GsonBuilder().setPrettyPrinting().create().toJson(result));
        }catch(Exception e){throw new IllegalStateException("Original wrench dispatch fixture failed",e);}finally{server.halt(false);}
    }
}
