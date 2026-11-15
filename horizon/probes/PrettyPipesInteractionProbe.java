package techquest.probes;

import com.google.gson.GsonBuilder;
import com.google.gson.JsonParser;
import com.mojang.authlib.GameProfile;
import de.ellpeck.prettypipes.pipe.PipeBlockEntity;
import de.ellpeck.prettypipes.network.PipeItem;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.CraftingInput;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.common.util.FakePlayer;
import net.neoforged.neoforge.common.util.FakePlayerFactory;
import net.neoforged.neoforge.event.server.ServerStartedEvent;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/** Developer-only original-server oracle. A synthetic actor is never a logged-in client. */
@Mod("techquest_reference_probe")
public final class PrettyPipesInteractionProbe {
    private static final BlockPos PIPE = new BlockPos(256, 210, 128);

    public PrettyPipesInteractionProbe() {
        NeoForge.EVENT_BUS.addListener(this::started);
    }

    private static ItemStack stack(String id, int count) {
        return new ItemStack(BuiltInRegistries.ITEM.get(ResourceLocation.parse(id)), count);
    }

    private static PipeBlockEntity fixture(ServerLevel level, boolean inventory) {
        level.getChunkAt(PIPE);
        level.setBlockAndUpdate(PIPE, Blocks.AIR.defaultBlockState());
        level.setBlockAndUpdate(PIPE.west(), Blocks.AIR.defaultBlockState());
        var block = BuiltInRegistries.BLOCK.get(ResourceLocation.parse("prettypipes:pipe"));
        level.setBlockAndUpdate(PIPE, block.defaultBlockState());
        if (inventory)
            level.setBlockAndUpdate(PIPE.west(), Blocks.CHEST.defaultBlockState());
        return (PipeBlockEntity) level.getBlockEntity(PIPE);
    }

    private static Map<String, Object> use(ServerLevel level, FakePlayer player, GameType mode, String item) {
        player.gameMode.changeGameModeForPlayer(mode);
        player.setPos(256.5, 210.5, 129.5);
        player.setItemInHand(InteractionHand.MAIN_HAND, stack(item, 2));
        var result = player.gameMode.useItemOn(player, level, player.getMainHandItem(),
                InteractionHand.MAIN_HAND, new BlockHitResult(Vec3.atCenterOf(PIPE), Direction.UP, PIPE, false));
        var tile = (PipeBlockEntity) level.getBlockEntity(PIPE);
        int installed = 0;
        for (int i = 0; i < tile.modules.getSlots(); i++)
            installed += tile.modules.getStackInSlot(i).getCount();
        return Map.of("held", player.getMainHandItem().getCount(), "installed", installed,
                "consumes_action", result.consumesAction());
    }

    private static Map<String, Object> removed(ServerLevel level, FakePlayer player, String mode) {
        fixture(level, true);
        use(level, player, GameType.SURVIVAL, "prettypipes:low_extraction_module");
        var box = new AABB(PIPE).inflate(6);
        for (var item : level.getEntitiesOfClass(ItemEntity.class, box)) item.discard();
        // A synthetic in-flight stack exercises the original onRemove path;
        // routing itself has a separate natural transport/save/reopen oracle.
        var queued = new PipeItem(stack("minecraft:iron_ingot", 8), 0.05F);
        queued.x = PIPE.getX() + 0.5F; queued.y = PIPE.getY() + 0.5F; queued.z = PIPE.getZ() + 0.5F;
        ((PipeBlockEntity) level.getBlockEntity(PIPE)).getItems().add(queued);
        if (mode.equals("replace")) level.setBlockAndUpdate(PIPE, Blocks.AIR.defaultBlockState());
        else if (mode.equals("destroy")) level.destroyBlock(PIPE, true);
        else {
            player.gameMode.changeGameModeForPlayer(GameType.CREATIVE);
            if (!player.gameMode.destroyBlock(PIPE)) throw new IllegalStateException("creative break refused");
        }
        var counts = new LinkedHashMap<String, Integer>();
        for (var entity : level.getEntitiesOfClass(ItemEntity.class, box)) {
            var item = entity.getItem();
            counts.merge(BuiltInRegistries.ITEM.getKey(item.getItem()).toString(), item.getCount(), Integer::sum);
        }
        return Map.of("dropped", counts, "pipe_removed", level.getBlockState(PIPE).isAir());
    }

    private void started(ServerStartedEvent event) {
        var server = event.getServer();
        try {
            var level = server.overworld();
            var player = FakePlayerFactory.get(level, new GameProfile(
                    UUID.fromString("00000000-0000-4000-8000-000000000048"), "TQReference"));
            var checks = new LinkedHashMap<String, Object>();
            fixture(level, true);
            checks.put("survival_install", use(level, player, GameType.SURVIVAL, "prettypipes:low_extraction_module"));
            checks.put("duplicate_rejected", use(level, player, GameType.SURVIVAL, "prettypipes:high_extraction_module"));
            fixture(level, true);
            checks.put("creative_install", use(level, player, GameType.CREATIVE, "prettypipes:low_extraction_module"));
            fixture(level, false);
            checks.put("no_inventory", use(level, player, GameType.SURVIVAL, "prettypipes:low_extraction_module"));
            fixture(level, true);
            checks.put("blank_rejected", use(level, player, GameType.SURVIVAL, "prettypipes:blank_module"));
            var countCases = new LinkedHashMap<String, Object>();
            for (int count : new int[] {-1, 0, 1, 2}) {
                var tile = fixture(level, true);
                var item = new CompoundTag();
                item.putByte("Slot", (byte) 0);
                item.putString("id", "prettypipes:low_extraction_module");
                item.putInt("count", count);
                var items = new ListTag(); items.add(item);
                var modules = new CompoundTag(); modules.putInt("Size", 3); modules.put("Items", items);
                tile.modules.deserializeNBT(level.registryAccess(), modules);
                countCases.put(Integer.toString(count), tile.modules.getStackInSlot(0).getCount());
            }
            checks.put("nbt_counts", countCases);
            var removal = new LinkedHashMap<String, Object>();
            for (var mode : new String[] {"replace", "destroy", "creative"})
                removal.put(mode, removed(level, player, mode));
            checks.put("removal", removal);
            var report = new LinkedHashMap<String, Object>(Map.of("schema", 1, "source_minecraft", "1.21.1", "pretty_pipes", "1.22.0",
                    "synthetic_player", true, "real_client_tested", false, "checks", checks));
            String casesPath = System.getProperty("techquest.reference.crafting_cases");
            if (casesPath != null) {
                var crafting = new ArrayList<Object>();
                var cases = JsonParser.parseString(Files.readString(Path.of(casesPath))).getAsJsonObject();
                for (var element : cases.getAsJsonArray("cases")) {
                    var row = element.getAsJsonObject();
                    var grid = new ArrayList<ItemStack>();
                    for (var item : row.getAsJsonArray("grid"))
                        grid.add(item.isJsonNull() ? ItemStack.EMPTY : stack(item.getAsString(), 1));
                    var input = CraftingInput.of(3, 3, grid);
                    var match = server.getRecipeManager().getRecipeFor(RecipeType.CRAFTING, input, level);
                    var result = new LinkedHashMap<String, Object>();
                    result.put("name", row.get("name").getAsString());
                    result.put("matched", match.isPresent());
                    if (match.isPresent()) {
                        var holder = match.get();
                        var output = holder.value().assemble(input, level.registryAccess());
                        result.put("recipe", holder.id().toString());
                        result.put("item", BuiltInRegistries.ITEM.getKey(output.getItem()).toString());
                        result.put("count", output.getCount());
                    }
                    boolean expected = row.get("valid").getAsBoolean();
                    if (match.isPresent() != expected || (expected &&
                            (!result.get("recipe").equals(row.get("recipe").getAsString()) ||
                             !result.get("item").equals(row.get("item").getAsString()) ||
                             !result.get("count").equals(row.get("count").getAsInt()))))
                        throw new IllegalStateException("Unexpected original craft: " + result);
                    crafting.add(result);
                }
                report.put("crafting", crafting);
            }
            Files.writeString(Path.of(System.getProperty("techquest.reference.result")),
                    new GsonBuilder().setPrettyPrinting().create().toJson(report));
        } catch (Exception exception) {
            throw new IllegalStateException("Pretty Pipes interaction oracle failed", exception);
        } finally {
            server.halt(false);
        }
    }
}
