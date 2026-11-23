package dev.techquest.hybrid;

import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.item.ItemStack;
import net.neoforged.neoforge.network.handling.IPayloadContext;

/**
 * Dedicated server-authoritative activation for powered Elytra.
 *
 * IC2 Jetpack uses the jump key, so vanilla double-space activation can be
 * swallowed by other flight systems. A separate configurable key sends a
 * request; the server validates the actually worn chest armor and charge.
 * Never trust an ItemStack sent by the client.
 */
public record PoweredElytraGlidePayload() implements CustomPacketPayload {
    public static final Type<PoweredElytraGlidePayload> TYPE =
            new Type<>(ResourceLocation.fromNamespaceAndPath(HybridWarfareMod.MODID, "start_powered_glide"));

    public static final StreamCodec<RegistryFriendlyByteBuf, PoweredElytraGlidePayload> STREAM_CODEC =
            StreamCodec.unit(new PoweredElytraGlidePayload());

    @Override
    public Type<? extends CustomPacketPayload> type() {
        return TYPE;
    }

    public static void handle(PoweredElytraGlidePayload payload, IPayloadContext context) {
        if (!(context.player() instanceof ServerPlayer player)) return;
        ItemStack chest = player.getItemBySlot(EquipmentSlot.CHEST);
        if (!PoweredElytra.hasElytra(chest)) {
            player.displayClientMessage(Component.translatable("message.techquest_hybrid.elytra.missing"), true);
            return;
        }
        if (!PoweredElytraEnergy.isPoweredChest(chest)) {
            player.displayClientMessage(Component.translatable("message.techquest_hybrid.elytra.unpowered"), true);
            return;
        }
        if (!PoweredElytraEnergy.canSpend(chest)) {
            player.displayClientMessage(Component.translatable("message.techquest_hybrid.elytra.empty"), true);
            return;
        }
        if (player.isFallFlying()) return;
        if (player.onGround()) {
            player.displayClientMessage(Component.translatable("message.techquest_hybrid.elytra.jump"), true);
            return;
        }
        if (player.tryToStartFallFlying()) {
            player.displayClientMessage(Component.translatable("message.techquest_hybrid.elytra.started"), true);
        } else {
            player.displayClientMessage(Component.translatable("message.techquest_hybrid.elytra.blocked"), true);
        }
    }
}
