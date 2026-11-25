package dev.techquest.hybrid;

import ic2.api.item.ElectricItem;
import net.minecraft.world.item.ItemStack;

/**
 * Optional IC2 bridge. Call only when the ic2 mod is present and only for
 * actual native IC2 items (not the embedded donor of Superb Warfare armor).
 */
public final class Ic2ElytraEnergy {
    private Ic2ElytraEnergy() {}

    public static double capacity(ItemStack stack) {
        return Math.max(0.0D, ElectricItem.manager.getMaxCharge(stack));
    }

    public static boolean canSpend(ItemStack stack, int amount) {
        return amount > 0 && capacity(stack) > 0
                && ElectricItem.manager.discharge(stack, amount, Integer.MAX_VALUE, true,
                        false, true) >= amount;
    }

    public static boolean spend(ItemStack stack, int amount) {
        return canSpend(stack, amount)
                && ElectricItem.manager.discharge(stack, amount, Integer.MAX_VALUE, true,
                        false, false) >= amount;
    }
}
