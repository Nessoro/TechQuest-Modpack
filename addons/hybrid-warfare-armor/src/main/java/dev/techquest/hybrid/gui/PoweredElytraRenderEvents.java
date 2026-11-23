package dev.techquest.hybrid.gui;

import dev.techquest.hybrid.HybridWarfareMod;
import net.minecraft.client.renderer.entity.player.PlayerRenderer;
import net.minecraft.client.resources.PlayerSkin;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.EntityRenderersEvent;

/** Keep all client UI/render classes OUTSIDE the Mixin-owned packages. */
@EventBusSubscriber(value = Dist.CLIENT, bus = EventBusSubscriber.Bus.MOD, modid = HybridWarfareMod.MODID)
public final class PoweredElytraRenderEvents {
    private PoweredElytraRenderEvents() {}

    @SubscribeEvent
    public static void onAddLayers(EntityRenderersEvent.AddLayers event) {
        for (PlayerSkin.Model skin : event.getSkins()) {
            if (event.getSkin(skin) instanceof PlayerRenderer renderer) {
                renderer.addLayer(new PoweredElytraLayer(renderer, event.getEntityModels()));
            }
        }
    }
}
