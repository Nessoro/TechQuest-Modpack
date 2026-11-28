package techquest.probes;

import com.google.gson.GsonBuilder;
import com.mojang.authlib.GameProfile;
import de.ellpeck.prettypipes.misc.FilterSlot;
import de.ellpeck.prettypipes.misc.ItemFilter;
import de.ellpeck.prettypipes.misc.DirectionSelector;
import de.ellpeck.prettypipes.pipe.PipeBlockEntity;
import de.ellpeck.prettypipes.pipe.PipeBlock;
import de.ellpeck.prettypipes.pipe.ConnectionType;
import de.ellpeck.prettypipes.pipe.modules.extraction.ExtractionModuleContainer;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtOps;
import net.minecraft.resources.RegistryOps;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.component.CustomData;
import net.minecraft.world.level.block.Blocks;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.common.util.FakePlayerFactory;
import net.neoforged.neoforge.event.server.ServerStartedEvent;
import java.nio.file.*;
import java.util.*;

/** Original MIT filter/ghost slot/direction oracle; synthetic actor, no login. */
@Mod("techquest_reference_probe")
public final class PrettyPipesFilterProbe {
    private static final BlockPos POS = new BlockPos(256, 210, 128);
    public PrettyPipesFilterProbe() { NeoForge.EVENT_BUS.addListener(this::started); }
    private static ItemStack stack(String name, int count, int damage) {
        var item = new ItemStack(BuiltInRegistries.ITEM.get(ResourceLocation.parse(name)), count);
        if (damage != 0) item.setDamageValue(damage);
        return item;
    }
    private static Object row(String name, ItemStack module, ExtractionModuleContainer menu,
                              net.minecraft.server.level.ServerLevel level) {
        menu.filter.save(); menu.directionSelector.save();
        var allowed = new LinkedHashMap<String, Boolean>();
        for (var id : List.of("minecraft:iron_ingot", "minecraft:gold_ingot", "minecraft:iron_sword"))
            allowed.put(id, menu.filter.isAllowed(stack(id, 1, 0), Direction.WEST));
        allowed.put("damaged_sword", menu.filter.isAllowed(stack("minecraft:iron_sword", 1, 30), Direction.WEST));
        var sides = new ArrayList<Boolean>();
        for (var d : Direction.values()) sides.add(menu.directionSelector.has(d));
        var saved = (CompoundTag) module.save(level.registryAccess());
        var direct = saved.copy();
        var ops = RegistryOps.create(NbtOps.INSTANCE,level.registryAccess());
        if (module.has(ItemFilter.Data.TYPE)) direct.getCompound("components").put("prettypipes:item_filter_data",
                ItemFilter.Data.CODEC.encodeStart(ops,module.get(ItemFilter.Data.TYPE)).getOrThrow());
        if (module.has(DirectionSelector.Data.TYPE)) direct.getCompound("components").put("prettypipes:direction_selector_data",
                DirectionSelector.Data.CODEC.encodeStart(ops,module.get(DirectionSelector.Data.TYPE)).getOrThrow());
        return Map.of("name", name, "module_snbt", saved.toString(),
                "direct_component_snbt", direct.toString(), "cached_component_differs",!saved.equals(direct),
                "allowed", allowed, "directions", sides, "cursor_count", menu.getCarried().getCount(),
                "sample_count", menu.filter.content.getStackInSlot(0).getCount());
    }
    private void started(ServerStartedEvent event) {
        var server = event.getServer();
        try {
            var level = server.overworld(); level.getChunkAt(POS);
            var player = FakePlayerFactory.get(level, new GameProfile(
                    UUID.fromString("00000000-0000-4000-8000-000000000048"), "TQReference"));
            var block = BuiltInRegistries.BLOCK.get(ResourceLocation.parse("prettypipes:pipe"));
            var rows = new ArrayList<Object>();
            for (var tier : List.of("low", "medium", "high")) {
                level.setBlockAndUpdate(POS, Blocks.AIR.defaultBlockState());
                level.setBlockAndUpdate(POS.west(), Blocks.CHEST.defaultBlockState());
                level.setBlockAndUpdate(POS.east(), Blocks.CHEST.defaultBlockState());
                level.setBlockAndUpdate(POS, block.defaultBlockState()
                        .setValue(PipeBlock.DIRECTIONS.get(Direction.WEST), ConnectionType.CONNECTED)
                        .setValue(PipeBlock.DIRECTIONS.get(Direction.EAST), ConnectionType.CONNECTED));
                var pipe = (PipeBlockEntity) level.getBlockEntity(POS);
                if (pipe.getItemHandler(Direction.WEST) == null || pipe.getItemHandler(Direction.EAST) == null)
                    throw new IllegalStateException("reference inventories are not connected");
                var module = stack("prettypipes:" + tier + "_extraction_module", 1, 0);
                pipe.modules.setStackInSlot(0, module);
                var menu = new ExtractionModuleContainer(null, 48, player, POS, 0);
                rows.add(row(tier + "_default", module, menu, level));
                var iron = stack("minecraft:iron_ingot", 64, 0);
                var marker = new CompoundTag(); marker.putInt("tq_marker",48);
                iron.set(DataComponents.CUSTOM_DATA, CustomData.of(marker));
                menu.setCarried(iron);
                if (!FilterSlot.checkFilter(menu,0)) throw new IllegalStateException("filter slot absent");
                rows.add(row(tier + "_blacklist_iron", module, menu, level));
                menu.filter.onButtonPacket(menu,0);
                rows.add(row(tier + "_whitelist_iron", module, menu, level));
                menu.setCarried(stack("minecraft:iron_sword",1,70));
                if (!FilterSlot.checkFilter(menu,0)) throw new IllegalStateException("filter slot absent");
                rows.add(row(tier + "_whitelist_sword", module, menu, level));
                menu.setCarried(ItemStack.EMPTY); FilterSlot.checkFilter(menu,0);
                rows.add(row(tier + "_empty_whitelist", module, menu, level));
                menu.filter.onButtonPacket(menu,0);
                rows.add(row(tier + "_empty_blacklist", module, menu, level));
                for (int i=0; i<3; i++) {
                    menu.directionSelector.onButtonPacket();
                    rows.add(row(tier + "_direction_" + i, module, menu, level));
                }
                menu.removed(player);
            }
            Files.writeString(Path.of(System.getProperty("techquest.reference.result")),
                    new GsonBuilder().serializeNulls().setPrettyPrinting().create().toJson(Map.of(
                        "schema",1,"minecraft","1.21.1","pretty_pipes","1.22.0",
                        "original_filter_and_direction_executed",true,"synthetic_actor",true,
                        "real_client_tested",false,"rows",rows)));
        } catch (Exception e) { throw new IllegalStateException("Original filter oracle failed",e); }
        finally { server.halt(false); }
    }
}
