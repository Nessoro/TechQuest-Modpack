package dev.techquest.hybrid;

import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.Ingredient;
import net.minecraft.world.item.crafting.RecipeSerializer;
import net.minecraft.world.item.crafting.SmithingRecipe;
import net.minecraft.world.item.crafting.SmithingRecipeInput;
import net.minecraft.world.level.Level;

import java.util.stream.Stream;

/**
 * Smithing fusion that retains BOTH sides without replacing the Superb Warfare item.
 *
 * Vanilla smithing_transform copies only the left/base item and discards the
 * technical armor in the addition slot. We still deliberately keep the original
 * Superb Warfare item type, but embed an immutable-copy donor ItemStack as a
 * persistent data component. This retains donor-specific components, upgrades,
 * stored power and module settings for a future native adapter.
 *
 * IMPORTANT: an embedded donor is not the same thing as wearing that donor.
 * This recipe alone does not activate class-specific IC2/Mekanism hooks.
 */
public final class HybridFusionRecipe implements SmithingRecipe {
    private final Ingredient template;
    private final Ingredient base;
    private final Ingredient addition;
    private final ItemStack result;

    public HybridFusionRecipe(Ingredient template, Ingredient base, Ingredient addition, ItemStack result) {
        this.template = template;
        this.base = base;
        this.addition = addition;
        this.result = result;
    }

    @Override
    public boolean matches(SmithingRecipeInput input, Level level) {
        return template.test(input.template())
                && base.test(input.base())
                && addition.test(input.addition())
                && HybridWarfareMod.technology(input.base()) == null;
    }

    @Override
    public ItemStack assemble(SmithingRecipeInput input, HolderLookup.Provider registries) {
        if (input.base().isEmpty() || input.addition().isEmpty()
                || HybridWarfareMod.technology(input.base()) != null) {
            return ItemStack.EMPTY;
        }
        // Same item ID and all original components, including Apotheosis
        // affixes/sockets, enchantments, trim, jetpack attachment, ArmorPlate.
        ItemStack combined = input.base().copyWithCount(1);
        // Set only the technology result patch; never replace base components.
        combined.applyComponents(result.getComponentsPatch());
        combined.set(HybridWarfareMod.DONOR, input.addition().copyWithCount(1));
        // IC2 quantum chestplate includes a jetpack. IC2 already supports
        // attaching an electric jetpack to arbitrary chest armor. Enable its
        // ORIGINAL attachment mechanic on the 6B43/IOTV instead of inventing
        // a new flying model or fake potion effect. Its MFSU charger handles
        // the charge through ElectricItem.manager. Existing attachments stay.
        ResourceLocation sourceId = BuiltInRegistries.ITEM.getKey(input.addition().getItem());
        ResourceLocation baseId = BuiltInRegistries.ITEM.getKey(input.base().getItem());
        if ("ic2".equals(combined.get(HybridWarfareMod.TECHNOLOGY))
                && sourceId.equals(ResourceLocation.fromNamespaceAndPath("ic2", "quantum_chestplate"))
                && (baseId.getPath().equals("ru_chest_6b43") || baseId.getPath().equals("us_chest_iotv"))) {
            Ic2JetpackCompat.attachIfAbsent(combined);
        }
        return combined;
    }

    @Override
    public ItemStack getResultItem(HolderLookup.Provider registries) {
        return result.copy();
    }

    @Override
    public boolean isTemplateIngredient(ItemStack item) {
        return template.test(item);
    }

    @Override
    public boolean isBaseIngredient(ItemStack item) {
        return base.test(item);
    }

    @Override
    public boolean isAdditionIngredient(ItemStack item) {
        return addition.test(item);
    }

    @Override
    public RecipeSerializer<?> getSerializer() {
        return HybridWarfareMod.FUSION_SERIALIZER.get();
    }

    @Override
    public boolean isIncomplete() {
        return Stream.of(template, base, addition).anyMatch(Ingredient::isEmpty);
    }

    public static final class Serializer implements RecipeSerializer<HybridFusionRecipe> {
        private static final MapCodec<HybridFusionRecipe> CODEC = RecordCodecBuilder.mapCodec(instance ->
                instance.group(
                    Ingredient.CODEC.fieldOf("template").forGetter(r -> r.template),
                    Ingredient.CODEC.fieldOf("base").forGetter(r -> r.base),
                    Ingredient.CODEC.fieldOf("addition").forGetter(r -> r.addition),
                    ItemStack.STRICT_CODEC.fieldOf("result").forGetter(r -> r.result)
                ).apply(instance, HybridFusionRecipe::new));

        private static final StreamCodec<RegistryFriendlyByteBuf, HybridFusionRecipe> STREAM_CODEC =
                StreamCodec.of(Serializer::encode, Serializer::decode);

        @Override
        public MapCodec<HybridFusionRecipe> codec() {
            return CODEC;
        }

        @Override
        public StreamCodec<RegistryFriendlyByteBuf, HybridFusionRecipe> streamCodec() {
            return STREAM_CODEC;
        }

        private static HybridFusionRecipe decode(RegistryFriendlyByteBuf buf) {
            Ingredient template = Ingredient.CONTENTS_STREAM_CODEC.decode(buf);
            Ingredient base = Ingredient.CONTENTS_STREAM_CODEC.decode(buf);
            Ingredient addition = Ingredient.CONTENTS_STREAM_CODEC.decode(buf);
            ItemStack result = ItemStack.STREAM_CODEC.decode(buf);
            return new HybridFusionRecipe(template, base, addition, result);
        }

        private static void encode(RegistryFriendlyByteBuf buf, HybridFusionRecipe recipe) {
            Ingredient.CONTENTS_STREAM_CODEC.encode(buf, recipe.template);
            Ingredient.CONTENTS_STREAM_CODEC.encode(buf, recipe.base);
            Ingredient.CONTENTS_STREAM_CODEC.encode(buf, recipe.addition);
            ItemStack.STREAM_CODEC.encode(buf, recipe.result);
        }
    }
}
