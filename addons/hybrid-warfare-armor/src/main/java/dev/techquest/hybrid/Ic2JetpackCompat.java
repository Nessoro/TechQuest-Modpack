package dev.techquest.hybrid;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import net.minecraft.core.component.DataComponents;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.component.CustomData;

/**
 * Optional compatibility with IC2R / IC2: Nostalgia electric jetpack attachment.
 *
 * Uses the public IC2 ElectricItem.manager API through reflection so the
 * addon does not ship or compile against IC2's version-pinned local JAR.
 * Matches the attachment marker used by IC2R 1.21.1 JetpackHandler.
 *
 * The MFSU remains the native owner of electricity (charge/discharge tier,
 * transfer limit, sound, flight controls). Do not reimplement jetpack physics
 * or change the original Superb Warfare armor item class.
 */
public final class Ic2JetpackCompat {
    private Ic2JetpackCompat() {}
    private static final String KEY = "hasIC2Jetpack";

    private static Object manager;
    private static Method getChargeMethod;
    private static Method getMaxChargeMethod;
    private static Method chargeMethod;
    private static Method dischargeMethod;

    public static boolean attached(ItemStack stack) {
        return !stack.isEmpty()
                && stack.getOrDefault(DataComponents.CUSTOM_DATA, CustomData.EMPTY)
                        .copyTag().getBoolean(KEY);
    }

    public static void attachIfAbsent(ItemStack chest) {
        if (chest.isEmpty() || attached(chest)) return;
        // Preserve every other NBT entry: ArmorPlate and any Apotheosis data.
        CustomData.update(DataComponents.CUSTOM_DATA, chest, nbt -> nbt.putBoolean(KEY, true));
    }

    private static synchronized boolean prepare() {
        if (manager != null) return true;
        try {
            Class<?> api = Class.forName("ic2.api.item.ElectricItem");
            Field field = api.getField("manager");
            Object candidate = field.get(null);
            if (candidate == null) return false;
            Class<?> type = Class.forName("ic2.api.item.IElectricItemManager");
            getChargeMethod = type.getMethod("getCharge", ItemStack.class);
            getMaxChargeMethod = type.getMethod("getMaxCharge", ItemStack.class);
            chargeMethod = type.getMethod("charge", ItemStack.class,
                    double.class, int.class, boolean.class, boolean.class);
            dischargeMethod = type.getMethod("discharge", ItemStack.class,
                    double.class, int.class, boolean.class, boolean.class, boolean.class);
            manager = candidate;
            return true;
        } catch (ReflectiveOperationException | LinkageError ex) {
            return false; // IC2 not installed or API incompatible: leave original item untouched
        }
    }

    private static double call(Method method, Object... args) {
        if (!prepare()) return 0.0;
        try {
            Object result = method.invoke(manager, args);
            return result instanceof Number number ? number.doubleValue() : 0.0;
        } catch (ReflectiveOperationException | RuntimeException ex) {
            return 0.0;
        }
    }

    public static int current(ItemStack armor) {
        if (!attached(armor)) return 0;
        if (prepare()) return Math.max(0, (int) Math.min(Integer.MAX_VALUE,
                call(getChargeMethod, armor)));
        return Math.max(0, (int) Math.min(Integer.MAX_VALUE, armor
                .getOrDefault(DataComponents.CUSTOM_DATA, CustomData.EMPTY)
                .copyTag().getDouble("charge")));
    }

    public static int capacity(ItemStack armor) {
        if (!attached(armor)) return 0;
        if (!prepare()) return 30_000; // shown by the local.26 jetpack in testing
        return Math.max(0, (int) Math.min(Integer.MAX_VALUE,
                call(getMaxChargeMethod, armor)));
    }

    public static boolean spend(ItemStack armor, int amount) {
        return attached(armor) && amount >= 0 && prepare()
                && call(dischargeMethod, armor, (double) amount, Integer.MAX_VALUE,
                        true, false, false) >= amount;
    }

    public static int receive(ItemStack armor, int request, boolean simulate) {
        if (!attached(armor) || request <= 0 || !prepare()) return 0;
        return Math.max(0, (int) Math.min(request,
                call(chargeMethod, armor, (double) request, Integer.MAX_VALUE,
                        false, simulate)));
    }
}
