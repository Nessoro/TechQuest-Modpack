package dev.techquest.hybrid.client;

import dev.techquest.hybrid.HybridWarfareMod;
import net.minecraft.client.model.HumanoidModel;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.neoforged.neoforge.client.extensions.common.IClientItemExtensions;
import net.neoforged.neoforge.client.extensions.common.RegisterClientExtensionsEvent;

/**
 * Client-only 3D humanoid armor: the models animate with head turns and arm motion.
 * These original cubes are not derived from Superb Warfare's copyrighted Bedrock geometry.
 */
public final class MekMilitaryArmorClient {
    private MekMilitaryArmorClient() {}

    private static final IClientItemExtensions HELMET = new IClientItemExtensions() {
        private HumanoidModel<LivingEntity> model;

        @Override
        public HumanoidModel<?> getHumanoidArmorModel(LivingEntity living, ItemStack stack,
                                                       EquipmentSlot slot, HumanoidModel<?> original) {
            if (model == null) model = new HumanoidModel<>(MekMilitaryArmorModel.create(true).bakeRoot());
            return model;
        }
    };

    private static final IClientItemExtensions CHEST = new IClientItemExtensions() {
        private HumanoidModel<LivingEntity> model;

        @Override
        public HumanoidModel<?> getHumanoidArmorModel(LivingEntity living, ItemStack stack,
                                                       EquipmentSlot slot, HumanoidModel<?> original) {
            if (model == null) model = new HumanoidModel<>(MekMilitaryArmorModel.create(false).bakeRoot());
            return model;
        }
    };

    public static void register(RegisterClientExtensionsEvent event) {
        Item helmet = BuiltInRegistries.ITEM.get(ResourceLocation.fromNamespaceAndPath(
            HybridWarfareMod.MODID, "mek_ru_helmet_6b47"));
        Item vest = BuiltInRegistries.ITEM.get(ResourceLocation.fromNamespaceAndPath(
            HybridWarfareMod.MODID, "mek_ru_chest_6b43"));
        event.registerItem(HELMET, helmet);
        event.registerItem(CHEST, vest);
    }
}
