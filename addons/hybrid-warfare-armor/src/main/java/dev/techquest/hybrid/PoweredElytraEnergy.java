package dev.techquest.hybrid;

import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.ItemStack;
import net.neoforged.fml.ModList;
import net.neoforged.neoforge.capabilities.Capabilities;
import net.neoforged.neoforge.energy.IEnergyStorage;

/**
 * Never create a synthetic battery for flight. Drain the REAL chestpiece energy.
 *
 * Supports an upgraded Superb Warfare chestpiece (whose battery may be the
 * original embedded IC2 quantum donor), native IC2 electric chestpieces, or
 * other powered armor exposing a writable energy capability for extraction.
 * An unpowered vanilla chestplate is not an eligible elytra carrier.
 */
public final class PoweredElytraEnergy {
    /** Energy paid for every tick of fall-flying. 200 per tick = 4k/s. */
    public static final int COST_PER_TICK = 200;

    private PoweredElytraEnergy() {}

    public static boolean isPoweredChest(ItemStack stack) {
        if (stack.isEmpty() || LivingEntity.getEquipmentSlotForItem(stack) != EquipmentSlot.CHEST) {
            return false;
        }
        if (HybridWarfareMod.technology(stack) != null) {
            return HybridWarfareMod.energyCapacity(stack) > 0;
        }
        ResourceLocation id = BuiltInRegistries.ITEM.getKey(stack.getItem());
        if ("ic2".equals(id.getNamespace()) && ModList.get().isLoaded("ic2")) {
            return Ic2ElytraEnergy.capacity(stack) > 0;
        }
        IEnergyStorage power = stack.getCapability(Capabilities.EnergyStorage.ITEM);
        return power != null && power.getMaxEnergyStored() >= COST_PER_TICK
                && power.canExtract();
    }

    public static boolean canSpend(ItemStack stack) {
        if (!isPoweredChest(stack)) return false;
        if (HybridWarfareMod.technology(stack) != null) {
            return HybridWarfareMod.charge(stack) >= COST_PER_TICK;
        }
        ResourceLocation id = BuiltInRegistries.ITEM.getKey(stack.getItem());
        if ("ic2".equals(id.getNamespace()) && ModList.get().isLoaded("ic2")) {
            return Ic2ElytraEnergy.canSpend(stack, COST_PER_TICK);
        }
        IEnergyStorage power = stack.getCapability(Capabilities.EnergyStorage.ITEM);
        return power != null && power.canExtract()
                && power.extractEnergy(COST_PER_TICK, true) >= COST_PER_TICK;
    }

    public static boolean spend(ItemStack stack) {
        if (!canSpend(stack)) return false;
        if (HybridWarfareMod.technology(stack) != null) {
            return HybridWarfareMod.spend(stack, COST_PER_TICK);
        }
        ResourceLocation id = BuiltInRegistries.ITEM.getKey(stack.getItem());
        if ("ic2".equals(id.getNamespace()) && ModList.get().isLoaded("ic2")) {
            return Ic2ElytraEnergy.spend(stack, COST_PER_TICK);
        }
        IEnergyStorage power = stack.getCapability(Capabilities.EnergyStorage.ITEM);
        return power != null && power.extractEnergy(COST_PER_TICK, false) == COST_PER_TICK;
    }
}
