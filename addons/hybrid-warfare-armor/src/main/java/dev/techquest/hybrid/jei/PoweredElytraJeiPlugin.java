package dev.techquest.hybrid.jei;

import dev.techquest.hybrid.HybridWarfareMod;
import dev.techquest.hybrid.PoweredElytraRecipe;
import java.util.ArrayList;
import java.util.List;
import mezz.jei.api.IModPlugin;
import mezz.jei.api.JeiPlugin;
import mezz.jei.api.constants.RecipeTypes;
import mezz.jei.api.registration.IRecipeRegistration;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.core.NonNullList;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.crafting.CraftingBookCategory;
import net.minecraft.world.item.crafting.CraftingRecipe;
import net.minecraft.world.item.crafting.Ingredient;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.item.crafting.ShapelessRecipe;

/**
 * JEI 19.64 integration only. This class is not loaded by NeoForge and
 * JEI is optional: compiled against its APIs, never bundled or required.
 *
 * PoweredElytraRecipe is a special, dynamic Minecraft recipe with no fixed
 * inputs/output: its original input chestplate and components are preserved
 * by CraftingInput. JEI cannot display it automatically. The examples below
 * are display-only ShapelessRecipe instances registered exclusively inside
 * JEI; they do NOT register extra Minecraft crafting recipes.
 *
 * Examples show a REAL powered input (hybrid technology + donor) and the
 * same original chestplate with techquest_hybrid:elytra_attachment on output.
 * JEI transfer is only a visual convenience; the real special recipe remains
 * the sole authority for valid power, installed wings, and item data.
 */
@JeiPlugin
public final class PoweredElytraJeiPlugin implements IModPlugin {
    private static final String[] CHEST_ARMOR = {"ru_chest_6b43", "us_chest_iotv"};
    private static final String[][] TECHNOLOGIES = {
            {"ic2", "ic2:quantum_chestplate"},
            {"mi", "modern_industrialization:quantum_chestplate"},
            {"mek", "mekanism:mekasuit_bodyarmor"},
            {"oritech", "oritech:exo_chestplate"}
    };

    @Override
    public ResourceLocation getPluginUid() {
        return ResourceLocation.fromNamespaceAndPath(HybridWarfareMod.MODID, "powered_elytra_jei");
    }

    @Override
    public void registerRecipes(IRecipeRegistration registration) {
        ClientLevel world = Minecraft.getInstance().level;
        if (world == null) return;

        // Display no examples if a datapack or the server removed the actual
        // recipe. A JEI diagram must never imply a recipe that is unavailable.
        boolean realRecipeLoaded = world.getRecipeManager()
                .getAllRecipesFor(RecipeType.CRAFTING).stream()
                .anyMatch(holder -> holder.value() instanceof PoweredElytraRecipe);
        if (!realRecipeLoaded) return;

        List<RecipeHolder<CraftingRecipe>> examples = new ArrayList<>();
        for (String[] tech : TECHNOLOGIES) {
            ResourceLocation donorId = ResourceLocation.parse(tech[1]);
            if (!BuiltInRegistries.ITEM.containsKey(donorId)) continue;
            Item donor = BuiltInRegistries.ITEM.get(donorId);
            for (String chestId : CHEST_ARMOR) {
                ResourceLocation armorId = ResourceLocation.fromNamespaceAndPath("superbwarfare", chestId);
                if (!BuiltInRegistries.ITEM.containsKey(armorId)) continue;

                ItemStack powered = new ItemStack(BuiltInRegistries.ITEM.get(armorId));
                powered.set(HybridWarfareMod.TECHNOLOGY, tech[0]);
                powered.set(HybridWarfareMod.DONOR, new ItemStack(donor));
                powered.set(DataComponents.CUSTOM_NAME, Component.translatable(
                        "item.techquest_hybrid.fused_name",
                        Component.translatable("item.techquest_hybrid.prefix." + tech[0]),
                        powered.getHoverName()));

                ItemStack result = powered.copyWithCount(1);
                result.set(HybridWarfareMod.ELYTRA_ATTACHMENT, new ItemStack(Items.ELYTRA));

                // The input preview is a tech-upgraded item. The actual
                // shapeless recipe requires real powered armor and does not
                // accept an unmodified Superb Warfare chestplate.
                ShapelessRecipe preview = new ShapelessRecipe(
                        "techquest_hybrid_elytra_jei",
                        CraftingBookCategory.MISC,
                        result,
                        NonNullList.of(Ingredient.EMPTY,
                                Ingredient.of(powered), Ingredient.of(Items.ELYTRA)));
                ResourceLocation previewId = ResourceLocation.fromNamespaceAndPath(
                        HybridWarfareMod.MODID, "jei_preview_elytra_" + tech[0] + "_" + chestId);
                examples.add(new RecipeHolder<>(previewId, preview));
            }
        }

        // Native IC2 Quantum Chestplate is another supported example. The
        // installed Elytra is still an item data component, not a new item ID.
        ResourceLocation quantum = ResourceLocation.fromNamespaceAndPath("ic2", "quantum_chestplate");
        if (BuiltInRegistries.ITEM.containsKey(quantum)) {
            ItemStack chest = new ItemStack(BuiltInRegistries.ITEM.get(quantum));
            ItemStack result = chest.copy();
            result.set(HybridWarfareMod.ELYTRA_ATTACHMENT, new ItemStack(Items.ELYTRA));
            examples.add(new RecipeHolder<>(
                    ResourceLocation.fromNamespaceAndPath(HybridWarfareMod.MODID, "jei_preview_elytra_ic2_native"),
                    new ShapelessRecipe("techquest_hybrid_elytra_jei", CraftingBookCategory.MISC,
                            result, NonNullList.of(Ingredient.EMPTY,
                                    Ingredient.of(chest), Ingredient.of(Items.ELYTRA)))));
        }

        if (!examples.isEmpty()) {
            registration.addRecipes(RecipeTypes.CRAFTING, examples);
        }
        registration.addItemStackInfo(new ItemStack(Items.ELYTRA),
                Component.translatable("tooltip.techquest_hybrid.jei_elytra"));
    }
}
