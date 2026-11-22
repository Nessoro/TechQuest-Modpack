package dev.techquest.hybrid;

import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.item.ArmorItem;
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

    /**
     * NeoForge's ItemStack.getEquipmentSlot() is an optional override only.
     * It normally returns null even for valid ArmorItem chestplates.
     * ArmorItem itself knows the actual vanilla armor slot.
     */
    private static boolean isChestArmor(ItemStack stack) {
        if (stack.isEmpty()) return false;
        EquipmentSlot override = stack.getEquipmentSlot();
        if (override != null) return override == EquipmentSlot.CHEST;
        return stack.getItem() instanceof ArmorItem armor
                && armor.getEquipmentSlot() == EquipmentSlot.CHEST;
    }

    public static boolean isPoweredChest(ItemStack stack) {
        if (stack.isEmpty()) return false;

        // Some Superb Warfare armor subclasses do not expose a reliable
        // ItemStack equipment-slot override in NeoForge. Match only the two
        // exact supported chest item IDs, and demand a real tech upgrade.
        // This must happen BEFORE the generic ArmorItem/slot fallback.
        ResourceLocation itemId = BuiltInRegistries.ITEM.getKey(stack.getItem());
        if ("superbwarfare".equals(itemId.getNamespace())) {
            String name = itemId.getPath();
            return ("ru_chest_6b43".equals(name) || "us_chest_iotv".equals(name))
                    && HybridWarfareMod.technology(stack) != null
                    && HybridWarfareMod.energyCapacity(stack) >= COST_PER_TICK;
        }

        if (!isChestArmor(stack)) return false;
        if (HybridWarfareMod.technology(stack) != null) {
            return HybridWarfareMod.energyCapacity(stack) >= COST_PER_TICK;
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

    /** Extra energy on a boost tick, in addition to the baseline 200. */
    public static boolean spendExtra(ItemStack stack, int amount) {
        if (amount <= 0 || !isPoweredChest(stack)) return false;
        if (HybridWarfareMod.technology(stack) != null) {
            return HybridWarfareMod.spend(stack, amount);
        }
        ResourceLocation id = BuiltInRegistries.ITEM.getKey(stack.getItem());
        if ("ic2".equals(id.getNamespace()) && ModList.get().isLoaded("ic2")) {
            return Ic2ElytraEnergy.canSpend(stack, amount)
                    && Ic2ElytraEnergy.spend(stack, amount);
        }
        IEnergyStorage power = stack.getCapability(Capabilities.EnergyStorage.ITEM);
        return power != null && power.canExtract()
                && power.extractEnergy(amount, true) >= amount
                && power.extractEnergy(amount, false) == amount;
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
