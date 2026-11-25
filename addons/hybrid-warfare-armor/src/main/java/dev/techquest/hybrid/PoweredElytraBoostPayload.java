package dev.techquest.hybrid;

import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.neoforged.neoforge.network.handling.IPayloadContext;

/** Only a press/release state; never accept client energy, position or velocity. */
public record PoweredElytraBoostPayload(boolean held) implements CustomPacketPayload {
    public static final Type<PoweredElytraBoostPayload> TYPE = new Type<>(
            ResourceLocation.fromNamespaceAndPath(HybridWarfareMod.MODID, "powered_elytra_boost"));
    public static final StreamCodec<RegistryFriendlyByteBuf, PoweredElytraBoostPayload> STREAM_CODEC =
            StreamCodec.of((buf, payload) -> buf.writeBoolean(payload.held()),
                    buf -> new PoweredElytraBoostPayload(buf.readBoolean()));

    @Override
    public Type<? extends CustomPacketPayload> type() { return TYPE; }

    public static void handle(PoweredElytraBoostPayload payload, IPayloadContext context) {
        if (context.player() instanceof ServerPlayer player) {
            PoweredElytraBoost.setHeld(player, payload.held());
        }
    }
}
