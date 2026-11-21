package dev.techquest.hybrid;

import ic2.core.IC2;
import ic2.core.Ic2Potion;
import ic2.core.item.ItemTinCan;
import ic2.core.ref.Ic2Items;
import java.util.ArrayList;
import net.minecraft.core.Holder;
import net.minecraft.core.component.DataComponents;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.InteractionResultHolder;
import net.minecraft.world.effect.MobEffect;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.component.CustomData;

/**
 * Quantum Helmet functionality for original Superb Warfare helmets.
 *
 * This is needed because the embedded IC2 Quantum Helmet is an ItemStack data
 * component, not the item equipped in the HEAD slot: IC2's original
 * ItemArmorQuantumSuit.inventoryTick() will never be called on it.
 *
 * All energy-consuming actions use Ic2QuantumChargeManager, forwarding to
 * the real donor's original IC2 battery (MFSU, charge tier and EU storage).
 * The original 6B47/PASGT/M35 3D model, UV, ballistic stats and enchants
 * are unaffected. No new helmet items or texture assets are registered.
 */
public final class Ic2QuantumHelmetCompat {
    private static final String NIGHT_VISION = "techquest_quantum_night_vision";
    private static final String TOGGLE_COOLDOWN = "techquest_quantum_toggle_timer";

    private Ic2QuantumHelmetCompat() {}

    public static void serverTick(Player player, ItemStack helmet) {
        if (player.level().isClientSide() || !Ic2QuantumChargeManager.isQuantumHybrid(helmet)) {
            return;
        }

        // IC2's original mode key combo: Alt + Mode Switch.
        // Store toggle state on the ORIGINAL Superb Warfare item and preserve
        // its other CUSTOM_DATA entries; do not overwrite donor charge.
        CompoundTag previous = helmet.getOrDefault(DataComponents.CUSTOM_DATA, CustomData.EMPTY).copyTag();
        int cooldown = Math.max(0, previous.getInt(TOGGLE_COOLDOWN));
        boolean enabled = previous.getBoolean(NIGHT_VISION);
        boolean toggled = IC2.keyboard.isAltKeyDown(player)
                && IC2.keyboard.isModeSwitchKeyDown(player) && cooldown == 0;
        if (toggled) {
            enabled = !enabled;
            cooldown = 10;
        } else if (cooldown > 0) {
            cooldown--;
        }
        if (toggled || previous.getInt(TOGGLE_COOLDOWN) != cooldown) {
            final boolean newEnabled = enabled;
            final int newCooldown = cooldown;
            CustomData.update(DataComponents.CUSTOM_DATA, helmet, nbt -> {
                nbt.putBoolean(NIGHT_VISION, newEnabled);
                nbt.putInt(TOGGLE_COOLDOWN, newCooldown);
            });
        }

        // Real Quantum Helmet: restore breath in 200-tick increments for 1k EU.
        if (player.getAirSupply() < player.getMaxAirSupply()
                && Ic2QuantumChargeManager.spend(helmet, 1_000)) {
            player.setAirSupply(Math.min(player.getMaxAirSupply(), player.getAirSupply() + 200));
        }

        // Same core status-removal rules as IC2 Quantum Helmet. Never remove a
        // status without first paying the appropriate energy from the donor.
        for (MobEffectInstance effect : new ArrayList<>(player.getActiveEffects())) {
            Holder<MobEffect> type = effect.getEffect();
            int cost;
            if (type.equals(MobEffects.POISON)) {
                cost = 10_000 * (effect.getAmplifier() + 1);
            } else if (type.equals(MobEffects.WITHER)) {
                cost = 25_000 * (effect.getAmplifier() + 1);
            } else if (type.equals(Ic2Potion.radiationHolder())) {
                cost = 10_000 + effect.getAmplifier() * 100;
            } else {
                continue;
            }
            if (Ic2QuantumChargeManager.spend(helmet, Math.max(1, cost))) {
                player.removeEffect(type);
            }
        }

        // Consume IC2's filled food cans with their own native food effect.
        // Do not consume cans if the hybrid has no energy to power the action.
        if (player.getFoodData().needsFood()
                && Ic2QuantumChargeManager.stored(helmet) >= 1_000) {
            for (int i = 0; i < player.getInventory().items.size(); i++) {
                ItemStack food = player.getInventory().items.get(i);
                if (!food.isEmpty() && food.getItem() == Ic2Items.FILLED_TIN_CAN
                        && food.getItem() instanceof ItemTinCan can) {
                    InteractionResultHolder<ItemStack> result = can.onEaten(player, food);
                    if (result.getResult() == InteractionResult.SUCCESS) {
                        player.getInventory().items.set(i, result.getObject());
                        Ic2QuantumChargeManager.spend(helmet, 1_000);
                    }
                    break;
                }
            }
        }

        // Unlike the earlier always-on TechQuest night vision, respect
        // original IC2's toggle state and drain power only while enabled.
        if (enabled && Ic2QuantumChargeManager.spend(helmet, 1)) {
            player.addEffect(new MobEffectInstance(MobEffects.NIGHT_VISION, 65, 0, true, false));
        }
    }
}
