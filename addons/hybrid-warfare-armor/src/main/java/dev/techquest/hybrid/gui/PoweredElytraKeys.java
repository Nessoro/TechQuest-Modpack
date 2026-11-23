package dev.techquest.hybrid.gui;

import com.mojang.blaze3d.platform.InputConstants;
import dev.techquest.hybrid.HybridWarfareMod;
import dev.techquest.hybrid.PoweredElytraGlidePayload;
import dev.techquest.hybrid.PoweredElytraBoostPayload;
import dev.techquest.hybrid.PoweredElytraBoost;
import dev.techquest.hybrid.PoweredElytra;
import dev.techquest.hybrid.PoweredElytraEnergy;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.item.ItemStack;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.ClientTickEvent;
import net.neoforged.neoforge.client.event.RegisterKeyMappingsEvent;
import net.neoforged.neoforge.network.PacketDistributor;
import org.lwjgl.glfw.GLFW;

/**
 * User-configurable "G" fallback independent of IC2 jetpack jump controls.
 * Explicitly client-only; never load on a dedicated server.
 */
public final class PoweredElytraKeys {
    public static final KeyMapping GLIDE = new KeyMapping(
            "key.techquest_hybrid.powered_elytra_glide",
            InputConstants.Type.KEYSYM, GLFW.GLFW_KEY_G,
            "key.categories.techquest_hybrid");

    // H has no vanilla Minecraft binding; other mods may use H, so it is remappable.
    public static final KeyMapping BOOST = new KeyMapping(
            "key.techquest_hybrid.powered_elytra_boost",
            InputConstants.Type.KEYSYM, GLFW.GLFW_KEY_H,
            "key.categories.techquest_hybrid");

    private PoweredElytraKeys() {}

    @EventBusSubscriber(modid = HybridWarfareMod.MODID, bus = EventBusSubscriber.Bus.MOD, value = Dist.CLIENT)
    public static final class Registration {
        private Registration() {}

        @SubscribeEvent
        public static void register(RegisterKeyMappingsEvent event) {
            event.register(GLIDE);
            event.register(BOOST);
        }
    }

    @EventBusSubscriber(modid = HybridWarfareMod.MODID, value = Dist.CLIENT)
    public static final class Input {
        private Input() {}
        private static boolean lastBoostState = false;

        @SubscribeEvent
        public static void onClientTick(ClientTickEvent.Post event) {
            Minecraft minecraft = Minecraft.getInstance();
            // Don't activate the Elytra while typing, in menus, or outside a world.
            boolean available = minecraft.player != null && minecraft.level != null
                    && minecraft.screen == null;
            boolean boostHeld = available && BOOST.isDown()
                    && minecraft.player.isFallFlying();
            if (minecraft.player != null && minecraft.level != null
                    && boostHeld != lastBoostState) {
                PacketDistributor.sendToServer(new PoweredElytraBoostPayload(boostHeld));
            }
            lastBoostState = boostHeld;
            // The local player controls movement; a server-only velocity
            // adjustment is overwritten by the regular client movement loop.
            // Client prediction costs NO energy. Server still pays 200 + 300.
            if (boostHeld) {
                ItemStack chest = minecraft.player.getItemBySlot(EquipmentSlot.CHEST);
                if (PoweredElytra.canFly(chest, minecraft.player)
                        && PoweredElytraEnergy.canSpendAmount(chest,
                                PoweredElytraBoost.TOTAL_COST_PER_TICK)) {
                    PoweredElytraBoost.applyAcceleration(minecraft.player);
                }
            }
            if (!available) {
                while (GLIDE.consumeClick()) {}
                return;
            }
            while (GLIDE.consumeClick()) {
                PacketDistributor.sendToServer(new PoweredElytraGlidePayload());
            }
        }
    }
}
