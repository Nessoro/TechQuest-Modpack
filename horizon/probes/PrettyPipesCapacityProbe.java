package techquest.probes;

import com.google.gson.GsonBuilder;
import de.ellpeck.prettypipes.network.PipeItem;
import de.ellpeck.prettypipes.network.PipeNetwork;
import de.ellpeck.prettypipes.pipe.ConnectionType;
import de.ellpeck.prettypipes.pipe.PipeBlock;
import de.ellpeck.prettypipes.pipe.PipeBlockEntity;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.Container;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.component.CustomData;
import net.minecraft.world.level.block.Blocks;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.server.ServerStartedEvent;
import java.nio.file.*;
import java.util.*;

/** Original MIT destination-capacity oracle. Synthetic queues, no player login. */
@Mod("techquest_reference_probe")
public final class PrettyPipesCapacityProbe {
    private static final BlockPos PIPE = new BlockPos(256,210,128), DEST = PIPE.east();
    private final List<Object> rows = new ArrayList<>();
    public PrettyPipesCapacityProbe(){NeoForge.EVENT_BUS.addListener(this::started);}
    private static ItemStack stack(String id,int count,int marker) {
        var result = new ItemStack(BuiltInRegistries.ITEM.get(ResourceLocation.parse(id)),count);
        if (marker != 0) { var data = new CompoundTag();data.putInt("tq_marker",marker);
            result.set(DataComponents.CUSTOM_DATA,CustomData.of(data)); }
        return result;
    }
    private void run(net.minecraft.server.level.ServerLevel level,String tier,String block,int slot,
                     String existing,int existingCount,int destinationMarker,String input,int inputMarker,
                     int reserved,String reservedItem) {
        var network = PipeNetwork.get(level); network.getItemsInPipe(PIPE).clear();
        level.setBlockAndUpdate(PIPE,Blocks.AIR.defaultBlockState());
        level.setBlockAndUpdate(DEST,Blocks.AIR.defaultBlockState());
        level.setBlockAndUpdate(DEST,BuiltInRegistries.BLOCK.get(ResourceLocation.parse(block)).defaultBlockState());
        var container = (Container) level.getBlockEntity(DEST);
        for (int i=0;i<container.getContainerSize();i++) container.setItem(i,stack("minecraft:cobblestone",64,0));
        container.setItem(slot,existingCount==0?ItemStack.EMPTY:stack(existing,existingCount,destinationMarker));
        level.setBlockAndUpdate(PIPE,BuiltInRegistries.BLOCK.get(ResourceLocation.parse("prettypipes:pipe"))
                .defaultBlockState().setValue(PipeBlock.DIRECTIONS.get(Direction.EAST),ConnectionType.CONNECTED));
        var pipe=(PipeBlockEntity)level.getBlockEntity(PIPE);
        if (pipe.getItemHandler(Direction.EAST)==null) throw new IllegalStateException("inventory disconnected");
        try {
            if (reserved>0) pipe.getItems().add(new PipeItem(stack(reservedItem,reserved,0),0.05F) {
                @Override public BlockPos getDestInventory(){return DEST;}
            });
            int requested=switch(tier){case "low"->1;case "medium"->8;default->64;};
            var available=pipe.getAvailableDestination(new Direction[]{Direction.EAST},
                    stack(input,requested,inputMarker),false,!tier.equals("low"));
            int count=available==null?0:available.getRight().getCount();
            var row=new LinkedHashMap<String,Object>();
            row.put("name","case_"+rows.size());row.put("tier",tier);row.put("block",block);row.put("slot",slot);
            row.put("existing_item",existing);row.put("existing_count",existingCount);row.put("destination_marker",destinationMarker);
            row.put("input_item",input);row.put("input_marker",inputMarker);row.put("requested",requested);
            row.put("reserved",reserved);row.put("reserved_item",reservedItem);row.put("accepted",count);
            row.put("original_items_on_way",network.getItemsOnTheWay(DEST,null));
            if (network.getItemsOnTheWay(DEST,null)!=reserved) throw new IllegalStateException("queue not counted");
            rows.add(row);
        } finally { pipe.getItems().clear(); }
    }
    private void started(ServerStartedEvent event) {
        var server=event.getServer();
        try {
            var level=server.overworld();level.getChunkAt(PIPE);
            for (var tier:List.of("low","medium","high")) {
                for(int space:new int[]{0,1,2,8,64}) for(int reserved:new int[]{0,1,8})
                    for(var pending:List.of("minecraft:iron_ingot","minecraft:gold_ingot"))
                        run(level,tier,"minecraft:chest",0,"minecraft:iron_ingot",64-space,0,"minecraft:iron_ingot",0,reserved,pending);
                for(int space:new int[]{0,1,8}) for(int reserved:new int[]{0,1})
                    run(level,tier,"minecraft:hopper",0,"minecraft:iron_ingot",64-space,0,"minecraft:iron_ingot",0,reserved,"minecraft:iron_ingot");
                for(var input:List.of("minecraft:coal","minecraft:iron_ingot")) for(int reserved:new int[]{0,1})
                    run(level,tier,"minecraft:furnace",1,"minecraft:coal",63,0,input,0,reserved,"minecraft:coal");
                for(int marker:new int[]{0,48})
                    run(level,tier,"minecraft:chest",0,"minecraft:iron_ingot",63,48,"minecraft:iron_ingot",marker,0,"minecraft:iron_ingot");
            }
            Files.writeString(Path.of(System.getProperty("techquest.reference.result")),
                new GsonBuilder().serializeNulls().setPrettyPrinting().create().toJson(Map.of(
                    "schema",1,"minecraft","1.21.1","pretty_pipes","1.22.0",
                    "original_destination_capacity_executed",true,"synthetic_queues",true,
                    "real_client_tested",false,"rows",rows)));
        } catch(Exception e){throw new IllegalStateException("Capacity oracle failed",e);}
        finally { PipeNetwork.get(server.overworld()).getItemsInPipe(PIPE).clear();server.halt(false); }
    }
}
