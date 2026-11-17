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
 * Native NeoForge 1.21.1 client 3D armor attachments, one mesh per equipment slot.
 * No client code is registered on dedicated servers.
 */
public final class MekMilitaryArmorClient {
    private MekMilitaryArmorClient() {}

    private static IClientItemExtensions modelFor(String id) {
        return new IClientItemExtensions() {
            private HumanoidModel<LivingEntity> model;

            @Override
            public HumanoidModel<?> getHumanoidArmorModel(LivingEntity living, ItemStack stack,
                    EquipmentSlot slot, HumanoidModel<?> original) {
                if (model == null) {
                    model = new HumanoidModel<>(MekMilitaryArmorModel.create(id).bakeRoot());
                }
                return model;
            }
        };
    }

    public static void register(RegisterClientExtensionsEvent event) {
        for (String id : new String[] {
                "mek_ru_helmet_6b47", "mek_ru_chest_6b43",
                "mek_ru_leggings", "mek_ru_boots" }) {
            Item item = BuiltInRegistries.ITEM.get(
                ResourceLocation.fromNamespaceAndPath(HybridWarfareMod.MODID, id));
            event.registerItem(modelFor(id), item);
        }
    }
}
