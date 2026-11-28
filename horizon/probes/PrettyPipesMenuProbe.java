package techquest.probes;

import com.google.gson.GsonBuilder;
import com.mojang.authlib.GameProfile;
import de.ellpeck.prettypipes.network.PipeItem;
import de.ellpeck.prettypipes.pipe.PipeBlockEntity;
import de.ellpeck.prettypipes.pipe.containers.MainPipeContainer;
import net.minecraft.core.BlockPos;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.inventory.ClickType;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.component.CustomData;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.AABB;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.common.util.FakePlayer;
import net.neoforged.neoforge.common.util.FakePlayerFactory;
import net.neoforged.neoforge.event.server.ServerStartedEvent;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

/** Developer-only original MainPipeContainer oracle; no client login. */
@Mod("techquest_reference_probe")
public final class PrettyPipesMenuProbe {
    private static final BlockPos POS = new BlockPos(256, 210, 128);
    private ServerLevel level;
    private FakePlayer player;
    private PipeBlockEntity pipe;
    private MainPipeContainer menu;
    private final List<Object> steps = new ArrayList<>();

    public PrettyPipesMenuProbe() { NeoForge.EVENT_BUS.addListener(this::started); }

    private static ItemStack stack(String id, int count, int marker) {
        var result = new ItemStack(BuiltInRegistries.ITEM.get(ResourceLocation.parse(id)), count);
        if (marker != 0) {
            var data = new CompoundTag(); data.putInt("tq_marker", marker);
            result.set(DataComponents.CUSTOM_DATA, CustomData.of(data));
        }
        return result;
    }

    private static Object describe(ItemStack stack) {
        if (stack.isEmpty()) return null;
        var data = stack.get(DataComponents.CUSTOM_DATA);
        return Map.of("id", BuiltInRegistries.ITEM.getKey(stack.getItem()).toString(),
                "count", stack.getCount(), "marker", data == null ? 0 : data.copyTag().getInt("tq_marker"));
    }

    private void step(String name, String area, int slot, int button, ClickType mode, String cursor, int count, int marker) {
        Object setup = null;
        if (cursor != null) {
            var stack = stack(cursor, count, marker);
            menu.setCarried(stack);
            setup = describe(stack);
        }
        int index = area.equals("module") ? slot : 3 + (slot < 9 ? 27 + slot : slot - 9);
        menu.clicked(index, button, mode, player);
        var modules = new ArrayList<>();
        for (int i = 0; i < 3; i++) modules.add(describe(pipe.modules.getStackInSlot(i)));
        var inventory = new ArrayList<>();
        for (int i = 0; i < 36; i++) inventory.add(describe(player.getInventory().getItem(i)));
        var dropped = new TreeMap<String, Integer>();
        for (var entity : level.getEntitiesOfClass(ItemEntity.class, new AABB(POS).inflate(6))) {
            var item = entity.getItem();
            dropped.merge(BuiltInRegistries.ITEM.getKey(item.getItem()).toString(), item.getCount(), Integer::sum);
        }
        var result = new LinkedHashMap<String, Object>();
        result.put("name", name); result.put("area", area); result.put("slot", slot);
        result.put("button", button); result.put("mode", mode.name()); result.put("setup_cursor", setup);
        result.put("modules", modules); result.put("inventory", inventory);
        result.put("cursor", describe(menu.getCarried())); result.put("dropped", dropped);
        result.put("queued", pipe.getItems().stream().mapToInt(item -> item.getContent().getCount()).sum());
        steps.add(result);
    }

    private void click(String name, String area, int slot, int button, ClickType mode) {
        step(name, area, slot, button, mode, null, 0, 0);
    }

    private void started(ServerStartedEvent event) {
        var server = event.getServer();
        try {
            level = server.overworld(); level.getChunkAt(POS);
            level.setBlockAndUpdate(POS, Blocks.AIR.defaultBlockState());
            level.setBlockAndUpdate(POS.west(), Blocks.CHEST.defaultBlockState());
            level.setBlockAndUpdate(POS, BuiltInRegistries.BLOCK.get(ResourceLocation.parse("prettypipes:pipe")).defaultBlockState());
            pipe = (PipeBlockEntity) level.getBlockEntity(POS);
            for (var entity : level.getEntitiesOfClass(ItemEntity.class, new AABB(POS).inflate(6))) entity.discard();
            var queue = new PipeItem(stack("minecraft:iron_ingot", 8, 0), 0.05F);
            queue.x = 256.5F; queue.y = 210.5F; queue.z = 128.5F;
            pipe.getItems().add(queue);
            player = FakePlayerFactory.get(level, new GameProfile(UUID.fromString("00000000-0000-4000-8000-000000000048"), "TQReference"));
            player.setPos(256.5, 210, 129.5); player.gameMode.changeGameModeForPlayer(GameType.SURVIVAL);
            player.getInventory().clearContent();
            menu = new MainPipeContainer(null, 48, player, POS); player.containerMenu = menu;
            step("place_one", "module", 0, 0, ClickType.PICKUP, "prettypipes:low_extraction_module", 2, 48);
            click("reject_second_extractor", "module", 1, 0, ClickType.PICKUP);
            click("store_remaining_low", "inventory", 0, 0, ClickType.PICKUP);
            click("take_low_right_click", "module", 0, 1, ClickType.PICKUP);
            click("store_removed_low", "inventory", 1, 0, ClickType.PICKUP);
            step("place_medium_right_click", "module", 2, 1, ClickType.PICKUP, "prettypipes:medium_extraction_module", 3, 0);
            click("reject_medium_in_other_slot", "module", 1, 0, ClickType.PICKUP);
            click("store_remaining_medium", "inventory", 2, 0, ClickType.PICKUP);
            click("shift_remove_medium", "module", 2, 0, ClickType.QUICK_MOVE);
            click("shift_install_one_medium", "inventory", 2, 0, ClickType.QUICK_MOVE);
            // Use an existing marked low stack for a number-key swap attempt.
            click("reject_incompatible_hotbar_swap", "module", 0, 0, ClickType.SWAP);
            click("throw_module", "module", 0, 1, ClickType.THROW);
            click("shift_reinstall_medium", "inventory", 2, 0, ClickType.QUICK_MOVE);
            step("reject_diamond", "module", 1, 0, ClickType.PICKUP, "minecraft:diamond", 2, 0);
            click("store_diamonds", "inventory", 4, 0, ClickType.PICKUP);
            click("take_medium_left_click", "module", 0, 0, ClickType.PICKUP);
            click("store_removed_medium", "inventory", 5, 0, ClickType.PICKUP);
            step("reject_blank_material", "module", 0, 0, ClickType.PICKUP, "prettypipes:blank_module", 1, 0);
            click("store_blank", "inventory", 6, 0, ClickType.PICKUP);
            click("shift_reinstall_final", "inventory", 5, 0, ClickType.QUICK_MOVE);
            var report = Map.of("schema", 1, "minecraft", "1.21.1", "pretty_pipes", "1.22.0",
                    "original_menu_engine_executed", true, "synthetic_player", true, "real_client_tested", false,
                    "queue_fixture_injected", true, "steps", steps);
            Files.writeString(Path.of(System.getProperty("techquest.reference.result")),
                    new GsonBuilder().serializeNulls().setPrettyPrinting().create().toJson(report));
            menu.removed(player);
        } catch (Exception exception) { throw new IllegalStateException("Original menu oracle failed", exception); }
        finally {
            // This fixture exercises inventory clicks, not a routable path.
            // Remove its pathless synthetic queue before the world is saved.
            if (pipe != null) pipe.getItems().clear();
            server.halt(false);
        }
    }
}
