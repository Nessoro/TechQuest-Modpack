package dev.techquest.hybrid;

import net.minecraft.core.HolderLookup;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.crafting.CraftingBookCategory;
import net.minecraft.world.item.crafting.CraftingInput;
import net.minecraft.world.item.crafting.CustomRecipe;
import net.minecraft.world.item.crafting.RecipeSerializer;
import net.minecraft.world.level.Level;

/**
 * Shapeless crafting grid: one genuine vanilla elytra and one powered
 * chestplate, regardless of the armor's mod namespace. The returned item is
 * the very same chestplate preserving all components, upgrades, donor charge,
 * name, enchantments and damage. Never attach to ordinary armor.
 */
public final class PoweredElytraRecipe extends CustomRecipe {
    public PoweredElytraRecipe(CraftingBookCategory category) {
        super(category);
    }

    private static ItemStack[] find(CraftingInput input) {
        ItemStack chest = ItemStack.EMPTY;
        ItemStack wings = ItemStack.EMPTY;
        for (int i = 0; i < input.size(); i++) {
            ItemStack stack = input.getItem(i);
            if (stack.isEmpty()) continue;
            if (stack.is(Items.ELYTRA) && wings.isEmpty()) {
                wings = stack;
            } else if (PoweredElytraEnergy.isPoweredChest(stack) && chest.isEmpty()) {
                chest = stack;
            } else {
                return new ItemStack[] {ItemStack.EMPTY, ItemStack.EMPTY};
            }
        }
        return new ItemStack[] {chest, wings};
    }

    @Override
    public boolean matches(CraftingInput input, Level level) {
        ItemStack[] found = find(input);
        return !found[0].isEmpty() && PoweredElytra.canAttach(found[0], found[1]);
    }

    @Override
    public ItemStack assemble(CraftingInput input, HolderLookup.Provider registries) {
        ItemStack[] found = find(input);
        if (found[0].isEmpty() || !PoweredElytra.canAttach(found[0], found[1])) {
            return ItemStack.EMPTY;
        }
        ItemStack result = found[0].copyWithCount(1);
        // Store the exact elytra stack with its enchantments and existing
        // damage; flight will never mutate its damage value.
        result.set(HybridWarfareMod.ELYTRA_ATTACHMENT, found[1].copyWithCount(1));
        return result;
    }

    @Override
    public boolean canCraftInDimensions(int width, int height) {
        return width * height >= 2;
    }

    @Override
    public RecipeSerializer<?> getSerializer() {
        return HybridWarfareMod.ELYTRA_SERIALIZER.get();
    }
}
