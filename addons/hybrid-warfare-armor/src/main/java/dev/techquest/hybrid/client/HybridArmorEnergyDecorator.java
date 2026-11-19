package dev.techquest.hybrid.client;

import dev.techquest.hybrid.HybridWarfareMod;
import net.minecraft.client.gui.Font;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.IItemDecorator;
import net.neoforged.neoforge.client.event.RegisterItemDecorationsEvent;

/**
 * Extra energy bar under the original Superb Warfare armor item icon.
 * Does NOT alter the normal durability bar or the Superb Warfare ArmorPlate HUD.
 *
 * For undamaged armor, use vanilla bottom slot (y+13); when a vanilla
 * durability bar exists, put energy above it (y+10), so both remain visible.
 */
@EventBusSubscriber(value = Dist.CLIENT, bus = EventBusSubscriber.Bus.MOD, modid = HybridWarfareMod.MODID)
public final class HybridArmorEnergyDecorator {
    private HybridArmorEnergyDecorator() {}

    @SubscribeEvent
    public static void register(RegisterItemDecorationsEvent event) {
        IItemDecorator decorator = HybridArmorEnergyDecorator::render;
        for (String name : new String[]{
                "ru_helmet_6b47", "ru_chest_6b43",
                "us_helmet_pasgt", "us_chest_iotv", "ge_helmet_m_35"
        }) {
            ResourceLocation id = ResourceLocation.fromNamespaceAndPath("superbwarfare", name);
            Item armor = BuiltInRegistries.ITEM.get(id);
            event.register(armor, decorator);
        }
    }

    private static boolean render(GuiGraphics graphics, Font font, ItemStack stack, int x, int y) {
        if (HybridWarfareMod.technology(stack) == null) return false;

        int capacity = HybridWarfareMod.energyCapacity(stack);
        int charge = capacity <= 0 ? 0 :
                Math.max(0, Math.min(capacity, HybridWarfareMod.charge(stack)));
        int width = capacity <= 0 ? 0 : Math.round(13.0F * charge / capacity);
        int barY = stack.isBarVisible() ? y + 10 : y + 13;

        // Same dimensions as a vanilla/IC2 item energy bar, with a cyan fill.
        // Empty bar is intentionally visible, even when battery charge is zero.
        graphics.fill(x + 2, barY, x + 15, barY + 2, 0xFF22272B);
        if (width > 0) {
            graphics.fill(x + 2, barY, x + 2 + width, barY + 1, 0xFF40D8F0);
        }
        return false; // No lasting render state changes; vanilla decorations remain.
    }
}
