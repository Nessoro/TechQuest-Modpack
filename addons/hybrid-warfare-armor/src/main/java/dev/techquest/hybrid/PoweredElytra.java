package dev.techquest.hybrid;

import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.ElytraItem;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.gameevent.GameEvent;

/**
 * Powered Elytra attachment on an existing chest armor ItemStack.
 * The embedded elytra is a permanent cosmetic/flight attachment; neither
 * the elytra nor the carrier loses durability during gliding. Only energy
 * is spent. Other vanilla and modded elytras remain completely unchanged.
 */
public final class PoweredElytra {
    private PoweredElytra() {}

    public static boolean hasElytra(ItemStack chest) {
        ItemStack wings = chest.get(HybridWarfareMod.ELYTRA_ATTACHMENT);
        return wings != null && wings.is(Items.ELYTRA);
    }

    public static boolean canAttach(ItemStack chest, ItemStack wings) {
        return wings.is(Items.ELYTRA)
                && ElytraItem.isFlyEnabled(wings)
                && !hasElytra(chest)
                && PoweredElytraEnergy.isPoweredChest(chest);
    }

    public static boolean canFly(ItemStack chest, LivingEntity wearer) {
        // Another mod can supply a copy of the equipped ItemStack during
        // its flight handler. Requiring object identity (==) rejected a valid
        // powered 6B43 even though the Elytra and charge were present.
        ItemStack equipped = wearer.getItemBySlot(EquipmentSlot.CHEST);
        return (chest == equipped || ItemStack.isSameItemSameComponents(chest, equipped))
                && hasElytra(chest) && PoweredElytraEnergy.canSpend(chest);
    }

    public static boolean flightTick(ItemStack chest, LivingEntity wearer, int flightTicks) {
        if (!canFly(chest, wearer)) return false;
        if (!wearer.level().isClientSide() && !PoweredElytraEnergy.spend(chest)) {
            return false;
        }
        if (!wearer.level().isClientSide() && (flightTicks + 1) % 10 == 0) {
            wearer.gameEvent(GameEvent.ELYTRA_GLIDE);
        }
        // No ItemStack#hurtAndBreak: consume energy, never elytra durability.
        return true;
    }
}
