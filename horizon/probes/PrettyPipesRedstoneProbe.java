package techquest.probes;

import com.google.gson.GsonBuilder;
import com.mojang.authlib.GameProfile;
import de.ellpeck.prettypipes.items.IModule;
import de.ellpeck.prettypipes.pipe.ConnectionType;
import de.ellpeck.prettypipes.pipe.PipeBlock;
import de.ellpeck.prettypipes.pipe.PipeBlockEntity;
import de.ellpeck.prettypipes.pipe.containers.MainPipeContainer;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.Container;
import net.minecraft.world.inventory.ClickType;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.component.CustomData;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.common.util.FakePlayerFactory;
import net.neoforged.neoforge.event.server.ServerStartedEvent;
import java.nio.file.*;
import java.util.*;

/** Developer-only original MIT module/menu/signal oracle; binary dependency APIs only. */
@Mod("techquest_reference_probe")
public final class PrettyPipesRedstoneProbe {
    private static final BlockPos POS=new BlockPos(256,210,128);
    private static final String RED="prettypipes:redstone_module";
    private static final List<String> EXTRACTORS=List.of("prettypipes:low_extraction_module","prettypipes:medium_extraction_module","prettypipes:high_extraction_module");
    private final List<Object> compatibility=new ArrayList<>(),signals=new ArrayList<>();
    public PrettyPipesRedstoneProbe(){NeoForge.EVENT_BUS.addListener(this::started);}
    private static ItemStack stack(String id,int count,int marker){
        var value=new ItemStack(BuiltInRegistries.ITEM.get(ResourceLocation.parse(id)),count);
        if(marker!=0){var tag=new CompoundTag();tag.putInt("tq_marker",marker);value.set(DataComponents.CUSTOM_DATA,CustomData.of(tag));}
        return value;
    }
    private static Object describe(ItemStack stack){
        if(stack.isEmpty())return null;
        var data=stack.get(DataComponents.CUSTOM_DATA);
        return Map.of("item",BuiltInRegistries.ITEM.getKey(stack.getItem()).toString(),"count",stack.getCount(),"marker",data==null?0:data.copyTag().getInt("tq_marker"));
    }
    private static PipeBlockEntity place(ServerLevel level,Direction output){
        level.setBlockAndUpdate(POS,Blocks.AIR.defaultBlockState());
        for(var d:Direction.values())level.setBlockAndUpdate(POS.relative(d),Blocks.AIR.defaultBlockState());
        level.setBlockAndUpdate(POS.relative(output),Blocks.CHEST.defaultBlockState());
        level.setBlockAndUpdate(POS,BuiltInRegistries.BLOCK.get(ResourceLocation.parse("prettypipes:pipe")).defaultBlockState().setValue(PipeBlock.DIRECTIONS.get(output),ConnectionType.CONNECTED));
        return (PipeBlockEntity)level.getBlockEntity(POS);
    }
    private void started(ServerStartedEvent event){
        var server=event.getServer();
        try{
            var level=server.overworld();level.getChunkAt(POS);server.tickRateManager().setFrozen(true);
            var player=FakePlayerFactory.get(level,new GameProfile(UUID.fromString("00000000-0000-4000-8000-000000000058"),"TQRedReference"));
            player.setPos(256.5,210,130.5);player.gameMode.changeGameModeForPlayer(GameType.SURVIVAL);
            var layouts=new ArrayList<List<String>>();layouts.add(List.of());layouts.add(List.of(RED));
            for(var extractor:EXTRACTORS){layouts.add(List.of(extractor));layouts.add(List.of(extractor,RED));layouts.add(List.of(RED,extractor));}
            var candidates=new ArrayList<>(EXTRACTORS);candidates.add(RED);candidates.add("prettypipes:blank_module");candidates.add("minecraft:diamond");
            for(var layout:layouts)for(var candidate:candidates){
                var pipe=place(level,Direction.WEST);player.getInventory().clearContent();
                for(int i=0;i<layout.size();i++)pipe.modules.setStackInSlot(i,stack(layout.get(i),1,10+i));
                var input=stack(candidate,2,48);int slot=layout.size();
                boolean valid=pipe.modules.isItemValid(slot,input);
                var menu=new MainPipeContainer(null,58,player,POS);player.containerMenu=menu;menu.setCarried(input.copy());
                menu.clicked(slot,0,ClickType.PICKUP,player);
                var after=new ArrayList<>();for(int i=0;i<3;i++)after.add(describe(pipe.modules.getStackInSlot(i)));
                var row=new LinkedHashMap<String,Object>();row.put("name","compat_"+compatibility.size());row.put("layout",layout);row.put("candidate",candidate);row.put("slot",slot);row.put("valid",valid);row.put("modules",after);row.put("cursor",describe(menu.getCarried()));
                compatibility.add(row);menu.setCarried(ItemStack.EMPTY);menu.removed(player);
            }
            for(var direction:Direction.values())for(boolean powered:new boolean[]{false,true})for(var layout:List.of(List.<String>of(),List.of(RED),List.of(EXTRACTORS.get(0)),List.of(RED,EXTRACTORS.get(0)))){
                var output=direction==Direction.DOWN?Direction.UP:Direction.DOWN;
                var pipe=place(level,output);
                for(int i=0;i<layout.size();i++)pipe.modules.setStackInSlot(i,stack(layout.get(i),1,0));
                level.setBlockAndUpdate(POS.relative(direction),powered?Blocks.REDSTONE_BLOCK.defaultBlockState():Blocks.STONE.defaultBlockState());
                boolean signal=level.hasNeighborSignal(POS);boolean work=pipe.canWork();
                var available=pipe.getAvailableDestination(new Direction[]{output},stack("minecraft:iron_ingot",8,0),true,false);
                int accepted=available==null?0:available.getRight().getCount();
                // Arrival stores directly: it deliberately does not call canWork.
                var remaining=pipe.store(stack("minecraft:iron_ingot",8,0),output);
                var chest=(Container)level.getBlockEntity(POS.relative(output));int stored=0;
                for(int i=0;i<chest.getContainerSize();i++)stored+=chest.getItem(i).getCount();
                boolean expected=!layout.contains(RED)||!powered;
                if(signal!=powered||work!=expected||accepted!=(expected?8:0)||!remaining.isEmpty()||stored!=8)throw new IllegalStateException("original redstone behavior differed");
                signals.add(Map.of("name","signal_"+signals.size(),"direction",direction.getName(),"powered",powered,"layout",layout,"signal",level.getBestNeighborSignal(POS),"can_work",work,"new_destination_accepted",accepted,"direct_arrival_stored",stored));
            }
            var report=Map.of("schema",1,"minecraft","1.21.1","pretty_pipes","1.22.0","original_module_and_menu_engines_executed",true,"original_destination_and_store_executed",true,"destination_force_flag_for_power_isolation",true,"synthetic_module_cursor_and_input_fixtures",true,"real_client_join_tested",false,"compatibility",compatibility,"signals",signals);
            Files.writeString(Path.of(System.getProperty("techquest.reference.result")),new GsonBuilder().serializeNulls().setPrettyPrinting().create().toJson(report));
        }catch(Exception e){throw new IllegalStateException("Redstone original oracle failed",e);}
        finally{server.halt(false);}
    }
}
