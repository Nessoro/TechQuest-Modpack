package dev.techquest.hybrid.gui;

import dev.techquest.hybrid.PoweredElytra;
import net.minecraft.client.model.PlayerModel;
import net.minecraft.client.model.geom.EntityModelSet;
import net.minecraft.client.player.AbstractClientPlayer;
import net.minecraft.client.renderer.entity.RenderLayerParent;
import net.minecraft.client.renderer.entity.layers.ElytraLayer;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemStack;

/** Uses vanilla's original elytra wing geometry and texture. */
public final class PoweredElytraLayer extends ElytraLayer<AbstractClientPlayer, PlayerModel<AbstractClientPlayer>> {
    private static final ResourceLocation VANILLA_WINGS =
            ResourceLocation.withDefaultNamespace("textures/entity/elytra.png");

    public PoweredElytraLayer(RenderLayerParent<AbstractClientPlayer, PlayerModel<AbstractClientPlayer>> parent,
                              EntityModelSet modelSet) {
        super(parent, modelSet);
    }

    @Override
    public boolean shouldRender(ItemStack stack, AbstractClientPlayer player) {
        return PoweredElytra.hasElytra(stack);
    }

    @Override
    public ResourceLocation getElytraTexture(ItemStack stack, AbstractClientPlayer player) {
        return VANILLA_WINGS;
    }
}
