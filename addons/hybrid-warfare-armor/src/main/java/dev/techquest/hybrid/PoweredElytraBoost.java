package dev.techquest.hybrid;

import java.util.HashSet;
import java.util.Set;
import java.util.UUID;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.Vec3;

/** Server-side hold-to-boost control. No other Elytra or IC2 flight is modified. */
public final class PoweredElytraBoost {
    public static final int TOTAL_COST_PER_TICK = 500;
    public static final int EXTRA_COST_PER_TICK =
            TOTAL_COST_PER_TICK - PoweredElytraEnergy.COST_PER_TICK;
    // Approximately 2x normal level-flight speed. 1.4 blocks/tick may be
    // imperceptible while diving. Local client prediction is also essential.
    private static final double CRUISE_SPEED = 2.2D;
    private static final double MAX_SPEED = 2.4D;
    private static final double ACCELERATION = 0.18D;
    private static final Set<UUID> HELD = new HashSet<>();

    private PoweredElytraBoost() {}

    public static void setHeld(ServerPlayer player, boolean held) {
        if (!held) {
            HELD.remove(player.getUUID());
        } else if (player.isFallFlying()
                && PoweredElytra.canFly(player.getItemBySlot(EquipmentSlot.CHEST), player)) {
            HELD.add(player.getUUID());
        }
    }

    public static void clearIfNotFlying(ServerPlayer player) {
        if (!player.isFallFlying()
                || !PoweredElytra.hasElytra(player.getItemBySlot(EquipmentSlot.CHEST))) {
            HELD.remove(player.getUUID());
        }
    }

    public static void clear(ServerPlayer player) {
        HELD.remove(player.getUUID());
    }

    /** Called after the baseline 200-energy flight tick has succeeded. */
    public static void afterFlightTick(ItemStack chest, LivingEntity wearer) {
        if (!(wearer instanceof ServerPlayer player)
                || !HELD.contains(player.getUUID()) || !player.isFallFlying()
                || !PoweredElytra.canFly(chest, player)) return;
        if (!PoweredElytraEnergy.spendExtra(chest, EXTRA_COST_PER_TICK)) return;
        applyAcceleration(player);
    }

    /**
     * Shared motion math for server and owning client. The client predicts
     * velocity for responsive movement; only the server spends energy.
     * No energy, position or velocity is trusted from the network packet.
     */
    public static void applyAcceleration(LivingEntity player) {
        if (!player.isFallFlying()) return;
        Vec3 look = player.getLookAngle();
        Vec3 direction = new Vec3(look.x, 0, look.z);
        if (direction.lengthSqr() < 1.0E-6D) return;
        direction = direction.normalize();

        Vec3 old = player.getDeltaMovement();
        Vec3 horizontal = new Vec3(old.x, 0, old.z);
        if (horizontal.length() >= MAX_SPEED) return;
        // Preserve existing high-speed dives instead of slowing the player.
        double targetSpeed = Math.max(CRUISE_SPEED, Math.min(MAX_SPEED, horizontal.length()));
        Vec3 change = direction.scale(targetSpeed).subtract(horizontal);
        if (change.length() > ACCELERATION) change = change.normalize().scale(ACCELERATION);
        Vec3 next = horizontal.add(change);
        if (next.length() > MAX_SPEED) next = next.normalize().scale(MAX_SPEED);
        player.setDeltaMovement(next.x, old.y, next.z);
        player.hasImpulse = true;
        if (!player.level().isClientSide()) player.hurtMarked = true;
    }
}
