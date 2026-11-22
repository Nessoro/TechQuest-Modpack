package techquest.probes;

import com.google.gson.GsonBuilder;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.server.ServerStartedEvent;
import rearth.oritech.block.base.block.MultiblockMachine;
import rearth.oritech.block.base.entity.MachineBlockEntity;
import rearth.oritech.block.blocks.processing.MachineCoreBlock;
import rearth.oritech.block.entity.processing.AssemblerBlockEntity;
import rearth.oritech.init.recipes.OritechRecipe;
import rearth.oritech.util.Geometry;
import java.lang.reflect.Method;
import java.nio.file.*;
import java.util.*;

/** Developer-only original CC0 machine calls; binary dependency APIs only. */
@Mod("techquest_reference_probe")
public final class OritechAssemblerProbe {
    private static final BlockPos POS = new BlockPos(256, 210, 128);
    private static final int[] CHECKPOINTS = {1, 2, 13, 47, 48, 49, 96, 144};
    private record Stack(String id, int count) {}
    private record Recipe(String name, String result, int resultCount, List<Stack> inputs) {}
    private static final Stack EMPTY = new Stack("minecraft:air", 0);
    private final List<Object> rows = new ArrayList<>(), geometry = new ArrayList<>();

    public OritechAssemblerProbe() { NeoForge.EVENT_BUS.addListener(this::started); }
    private static ItemStack item(Stack spec) {
        return spec.count == 0 ? ItemStack.EMPTY : new ItemStack(BuiltInRegistries.ITEM.get(ResourceLocation.parse(spec.id)), spec.count);
    }
    private static List<BlockPos> cores(AssemblerBlockEntity entity) {
        return entity.getCorePositions().stream().map(p -> POS.offset(Geometry.rotatePosition(p, entity.getFacingForMultiblock()))).toList();
    }
    private static void clear(ServerLevel level) {
        for (int x = -2; x <= 2; x++) for (int y = 0; y <= 2; y++) for (int z = -2; z <= 2; z++)
            level.setBlockAndUpdate(POS.offset(x, y, z), Blocks.AIR.defaultBlockState());
    }
    private static AssemblerBlockEntity place(ServerLevel level, Direction facing, int missing, boolean used, boolean assemble) {
        clear(level);
        level.setBlockAndUpdate(POS, BuiltInRegistries.BLOCK.get(ResourceLocation.parse("oritech:assembler_block")).defaultBlockState().setValue(BlockStateProperties.HORIZONTAL_FACING, facing));
        var entity = (AssemblerBlockEntity) level.getBlockEntity(POS);
        int i = 0;
        for (var pos : cores(entity)) {
            if (i != missing) level.setBlockAndUpdate(pos, BuiltInRegistries.BLOCK.get(ResourceLocation.parse("oritech:machine_core_1")).defaultBlockState().setValue(MachineCoreBlock.USED, used && i == 0));
            i++;
        }
        if (assemble) {
            if (!entity.initMultiblock(entity.getBlockState())) throw new IllegalStateException("assembly failed");
            entity.initAddons();
        }
        return entity;
    }
    private static Map<String, Object> snapshot(AssemblerBlockEntity entity) {
        var result = new LinkedHashMap<String, Object>();
        result.put("energy", entity.energyStorage.amount);
        result.put("progress", entity.progress);
        result.put("assembled", entity.getBlockState().getValue(MultiblockMachine.ASSEMBLED));
        var items = new ArrayList<Object>();
        for (int slot = 0; slot < 5; slot++) {
            var stack = entity.inventory.getItem(slot);
            if (!stack.isEmpty()) items.add(Map.of("slot", slot, "item", BuiltInRegistries.ITEM.getKey(stack.getItem()).toString(), "count", stack.getCount()));
        }
        result.put("items", items);
        return result;
    }
    private static void tick(ServerLevel level, AssemblerBlockEntity entity) {
        entity.serverTick(level, POS, entity.getBlockState(), entity);
    }
    private static void prime(AssemblerBlockEntity entity) throws Exception {
        Method lookup = MachineBlockEntity.class.getDeclaredMethod("getRecipe");
        lookup.setAccessible(true);
        var candidate = (Optional<?>) lookup.invoke(entity);
        if (candidate.isEmpty()) throw new IllegalStateException("fixture recipe missing");
        entity.setCurrentRecipe((OritechRecipe) ((RecipeHolder<?>) candidate.get()).value());
    }
    private static void inputs(AssemblerBlockEntity entity, List<Stack> values) {
        for (int slot = 0; slot < 4; slot++) entity.inventory.setItem(slot, item(values.get(slot)));
    }
    private static Set<List<Stack>> permutations(List<Stack> values) {
        var result = new LinkedHashSet<List<Stack>>();
        permute(new ArrayList<>(values), 0, result);
        return result;
    }
    private static void permute(List<Stack> values, int at, Set<List<Stack>> output) {
        if (at == values.size()) { output.add(List.copyOf(values)); return; }
        for (int i = at; i < values.size(); i++) {
            Collections.swap(values, at, i); permute(values, at + 1, output); Collections.swap(values, at, i);
        }
    }
    private void one(ServerLevel level, Recipe recipe, List<Stack> layout, long energy, boolean primed, boolean disabled, boolean active, int output, String outputId, String kind) throws Exception {
        var entity = place(level, Direction.NORTH, -1, false, active);
        inputs(entity, layout);
        entity.inventory.setItem(4, item(new Stack(outputId == null ? recipe.result : outputId, output)));
        entity.energyStorage.amount = energy;
        entity.progress = 12;
        if (primed) prime(entity);
        entity.onRedstoneEvent(disabled);
        var row = new LinkedHashMap<String, Object>();
        row.put("name", "case_" + rows.size()); row.put("recipe", recipe.name); row.put("kind", kind);
        row.put("primed", primed); row.put("disabled", disabled); row.put("initial_state", snapshot(entity));
        var states = new ArrayList<Object>(); int elapsed = 0;
        for (int point : CHECKPOINTS) {
            while (elapsed < point) { tick(level, entity); elapsed++; }
            states.add(Map.of("ticks", point, "state", snapshot(entity)));
        }
        row.put("states", states); rows.add(row);
    }
    private void started(ServerStartedEvent event) {
        var server = event.getServer();
        try {
            var level = server.overworld(); level.getChunkAt(POS); server.tickRateManager().setFrozen(true);
            if (Boolean.getBoolean("techquest.reference.reopen")) {
                var entity = (AssemblerBlockEntity) level.getBlockEntity(POS);
                var before = snapshot(entity); var states = new ArrayList<Object>(); int elapsed = 0;
                for (int point : new int[]{1, 48, 49, 96}) {
                    while (elapsed < point) { tick(level, entity); elapsed++; }
                    states.add(Map.of("ticks", point, "state", snapshot(entity)));
                }
                Files.writeString(Path.of(System.getProperty("techquest.reference.result")), new GsonBuilder().setPrettyPrinting().create().toJson(Map.of("schema", 1, "physical_reopen", true, "before", before, "states", states)));
                return;
            }
            for (var facing : List.of(Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST)) for (int variant = -1; variant < 4; variant++) {
                boolean used = variant == 3;
                var entity = place(level, facing, used ? -1 : variant, used, false);
                boolean assembled = entity.initMultiblock(entity.getBlockState());
                var flags = new ArrayList<Boolean>();
                for (var p : cores(entity)) { var state = level.getBlockState(p); flags.add(state.getBlock() instanceof MachineCoreBlock && state.getValue(MachineCoreBlock.USED)); }
                geometry.add(Map.of("name", "geometry_" + geometry.size(), "facing", facing.getName(), "missing", used ? -1 : variant, "used", used,
                    "core_positions", cores(entity).stream().map(p -> List.of(p.getX()-POS.getX(), p.getY()-POS.getY(), p.getZ()-POS.getZ())).toList(), "assembled", assembled, "used_after", flags));
                if (assembled != (variant == -1)) throw new IllegalStateException("assembly fixture differed");
            }
            var recipes = List.of(
                new Recipe("assembler/magnet", "oritech:magnetic_coil", 6, List.of(new Stack("oritech:steel_ingot", 2), new Stack("oritech:nickel_ingot", 2), new Stack("oritech:nickel_ingot", 2), new Stack("minecraft:copper_ingot", 2))),
                new Recipe("assembler/motor", "oritech:motor", 2, List.of(new Stack("oritech:nickel_ingot", 2), new Stack("oritech:steel_ingot", 2), new Stack("oritech:magnetic_coil", 2), new Stack("oritech:magnetic_coil", 2))));
            for (var recipe : recipes) {
                for (var layout : permutations(recipe.inputs)) for (long energy : new long[]{0, 127, 128, 50000}) for (boolean primed : new boolean[]{false, true})
                    one(level, recipe, layout, energy, primed, false, true, 0, null, "distributed_permutation");
                var merged = new LinkedHashMap<String, Integer>();
                for (var input : recipe.inputs) merged.merge(input.id, input.count, Integer::sum);
                var compact = new ArrayList<Stack>(); merged.forEach((id, count) -> compact.add(new Stack(id, count))); compact.add(EMPTY);
                for (var layout : permutations(compact)) one(level, recipe, layout, 50000, false, false, true, 0, null, "compacted_permutation");
                for (int output : new int[]{64-recipe.resultCount, 65-recipe.resultCount, 64})
                    one(level, recipe, recipe.inputs, 50000, true, false, true, output, null, "output_capacity");
                one(level, recipe, recipe.inputs, 50000, true, false, true, 1, "minecraft:barrier", "wrong_output");
                for (boolean primed : new boolean[]{false, true}) {
                    one(level, recipe, recipe.inputs, 50000, primed, true, true, 0, null, "redstone_disabled");
                    one(level, recipe, recipe.inputs, 50000, primed, false, false, 0, null, "inactive");
                }
                var missing = new ArrayList<>(recipe.inputs); missing.set(0, EMPTY);
                one(level, recipe, missing, 50000, false, false, true, 0, null, "missing_unique_input");
                var shortDuplicate = new ArrayList<>(compact);
                String duplicate = recipe.inputs.get(2).id;
                for (int i = 0; i < shortDuplicate.size(); i++) if (shortDuplicate.get(i).id.equals(duplicate)) shortDuplicate.set(i, new Stack(duplicate, 1));
                one(level, recipe, shortDuplicate, 50000, false, false, true, 0, null, "insufficient_repeated_ingredient");
                one(level, recipe, List.of(EMPTY, EMPTY, EMPTY, EMPTY), 50000, false, false, true, 0, null, "empty");
            }
            if (rows.size() != 262) throw new IllegalStateException("unexpected case count " + rows.size());
            var machine = place(level, Direction.NORTH, -1, false, true); inputs(machine, recipes.get(1).inputs); machine.energyStorage.amount = 50000;
            for (int i = 0; i < 13; i++) tick(level, machine);
            var beforeBroken = snapshot(machine); var broken = cores(machine).get(0);
            level.getBlockState(broken).getBlock().destroy(level, broken, level.getBlockState(broken));
            level.setBlockAndUpdate(broken, Blocks.AIR.defaultBlockState()); var afterBroken = snapshot(machine);
            for (int i = 0; i < 10; i++) tick(level, machine); var paused = snapshot(machine);
            level.setBlockAndUpdate(broken, BuiltInRegistries.BLOCK.get(ResourceLocation.parse("oritech:machine_core_1")).defaultBlockState());
            boolean reassembled = machine.initMultiblock(machine.getBlockState()); machine.initAddons(); tick(level, machine); var resumed = snapshot(machine);
            if ((boolean) afterBroken.get("assembled") || !paused.equals(afterBroken) || !reassembled || (int) resumed.get("progress") != 14) throw new IllegalStateException("core lifecycle differed");
            var lifecycle = Map.of("before_broken", beforeBroken, "after_broken", afterBroken, "paused", paused, "resumed", resumed, "original_destroy_callback_executed", true);
            machine = place(level, Direction.NORTH, -1, false, true); inputs(machine, recipes.get(1).inputs); machine.energyStorage.amount = 50000;
            for (int i = 0; i < 13; i++) tick(level, machine);
            var report = new LinkedHashMap<String, Object>(); report.put("schema", 1); report.put("original_server_tick_executed", true);
            report.put("rows", rows); report.put("geometry", geometry); report.put("core_lifecycle", lifecycle); report.put("saved", snapshot(machine));
            report.put("capacity", machine.getDefaultCapacity()); report.put("max_insertion", machine.getDefaultInsertRate());
            report.put("speed", machine.getSpeedMultiplier()); report.put("efficiency", machine.getEfficiencyMultiplier()); report.put("core_quality", machine.getCoreQuality());
            Files.writeString(Path.of(System.getProperty("techquest.reference.result")), new GsonBuilder().setPrettyPrinting().create().toJson(report));
        } catch (Exception e) { throw new IllegalStateException("Assembler original oracle failed", e); }
        finally { server.halt(false); }
    }
}
