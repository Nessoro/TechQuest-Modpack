package dev.techquest.hybrid;

import ic2.api.item.ElectricItem;
import ic2.api.item.IBackupElectricItemManager;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.ItemStack;

/**
 * Native IC2: Nostalgia charging adapter for Superb Warfare + QuantumSuit.
 *
 * Instead of duplicating charge into a 500k-FE TechQuest battery, forward IC2's
 * real charge/discharge calls to the preserved QuantumSuit donor ItemStack.
 * The donor's own battery tier, capacity and energy components remain
 * authoritative, including when an MFSU charges the hybrid armor.
 *
 * IC2's existing JetpackHandler detects hasIC2Jetpack on the Superb Warfare
 * chestpiece. When the IC2 electric manager checks the hybrid chestpiece it
 * resolves this backup manager; this makes the jetpack consume the SAME donor
 * battery rather than an unrelated 30k-RF attachment.
 */
public final class Ic2QuantumChargeManager implements IBackupElectricItemManager {
    private static final Ic2QuantumChargeManager INSTANCE = new Ic2QuantumChargeManager();
    private static boolean registered;

    private Ic2QuantumChargeManager() {}

    public static void register() {
        if (!registered) {
            ElectricItem.registerBackupManager(INSTANCE);
            registered = true;
        }
    }

    public static boolean isQuantumHybrid(ItemStack armor) {
        if (!"ic2".equals(HybridWarfareMod.technology(armor))) return false;
        ItemStack embedded = armor.get(HybridWarfareMod.DONOR);
        if (embedded == null || embedded.isEmpty()) return false;
        ResourceLocation id = BuiltInRegistries.ITEM.getKey(embedded.getItem());
        ResourceLocation base = BuiltInRegistries.ITEM.getKey(armor.getItem());
        if (!"ic2".equals(id.getNamespace())) return false;
        return switch (id.getPath()) {
            case "quantum_helmet" -> base.getPath().contains("helmet");
            case "quantum_chestplate" -> base.getPath().contains("chest");
            default -> false;
        };
    }

    private static ItemStack donor(ItemStack armor) {
        ItemStack embedded = armor.get(HybridWarfareMod.DONOR);
        return embedded == null ? ItemStack.EMPTY : embedded.copy();
    }

    private static void save(ItemStack armor, ItemStack donor) {
        armor.set(HybridWarfareMod.DONOR, donor.copyWithCount(1));
    }

    @Override
    public boolean handles(ItemStack armor) {
        return isQuantumHybrid(armor);
    }

    @Override
    public double charge(ItemStack armor, double amount, int tier,
                         boolean ignoreTransferLimit, boolean simulate) {
        if (!handles(armor) || amount <= 0) return 0;
        ItemStack donor = donor(armor);
        double gained = ElectricItem.manager.charge(donor, amount, tier, ignoreTransferLimit, simulate);
        if (gained > 0 && !simulate) save(armor, donor);
        return gained;
    }

    @Override
    public double discharge(ItemStack armor, double amount, int tier,
                            boolean ignoreTransferLimit, boolean externally, boolean simulate) {
        if (!handles(armor) || amount <= 0) return 0;
        ItemStack donor = donor(armor);
        double consumed = ElectricItem.manager.discharge(
                donor, amount, tier, ignoreTransferLimit, externally, simulate);
        if (consumed > 0 && !simulate) save(armor, donor);
        return consumed;
    }

    @Override
    public double getCharge(ItemStack armor) {
        return handles(armor) ? ElectricItem.manager.getCharge(donor(armor)) : 0;
    }

    @Override
    public double getStackCharge(ItemStack armor) {
        return handles(armor) ? ElectricItem.manager.getStackCharge(donor(armor)) : 0;
    }

    @Override
    public double getMaxCharge(ItemStack armor) {
        return handles(armor) ? ElectricItem.manager.getMaxCharge(donor(armor)) : 0;
    }

    @Override
    public boolean canUse(ItemStack armor, double amount) {
        return handles(armor) && ElectricItem.manager.canUse(donor(armor), amount);
    }

    @Override
    public boolean use(ItemStack armor, double amount, LivingEntity entity) {
        if (!handles(armor)) return false;
        ItemStack donor = donor(armor);
        boolean used = ElectricItem.manager.use(donor, amount, entity);
        if (used) save(armor, donor);
        return used;
    }

    @Override
    public void chargeFromArmor(ItemStack armor, LivingEntity entity) {
        if (!handles(armor)) return;
        ItemStack donor = donor(armor);
        double before = ElectricItem.manager.getCharge(donor);
        ElectricItem.manager.chargeFromArmor(donor, entity);
        if (ElectricItem.manager.getCharge(donor) != before) save(armor, donor);
    }

    @Override
    public String getToolTip(ItemStack armor) {
        return handles(armor) ? ElectricItem.manager.getToolTip(donor(armor)) : "";
    }

    @Override
    public int getTier(ItemStack armor) {
        return handles(armor) ? ElectricItem.manager.getTier(donor(armor)) : 0;
    }

    public static int stored(ItemStack armor) {
        return isQuantumHybrid(armor)
                ? (int) Math.max(0, Math.min(Integer.MAX_VALUE, INSTANCE.getCharge(armor))) : 0;
    }

    public static int capacity(ItemStack armor) {
        return isQuantumHybrid(armor)
                ? (int) Math.max(0, Math.min(Integer.MAX_VALUE, INSTANCE.getMaxCharge(armor))) : 0;
    }

    public static boolean spend(ItemStack armor, int amount) {
        if (!isQuantumHybrid(armor) || amount <= 0 || stored(armor) < amount) return false;
        return INSTANCE.discharge(armor, amount, Integer.MAX_VALUE, true, false, false) >= amount;
    }

    public static int receive(ItemStack armor, int amount, boolean simulate) {
        if (!isQuantumHybrid(armor) || amount <= 0) return 0;
        return (int) Math.max(0, Math.min(amount,
                INSTANCE.charge(armor, amount, Integer.MAX_VALUE, false, simulate)));
    }
}
