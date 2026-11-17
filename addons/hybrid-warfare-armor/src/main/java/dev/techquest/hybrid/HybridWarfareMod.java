package dev.techquest.hybrid;

import com.mojang.serialization.Codec;
import net.minecraft.ChatFormatting;
import net.minecraft.core.component.DataComponentType;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.codec.ByteBufCodecs;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.armortrim.ArmorTrim;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.capabilities.Capabilities;
import net.neoforged.neoforge.capabilities.RegisterCapabilitiesEvent;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.energy.IEnergyStorage;
import net.neoforged.neoforge.event.entity.player.ItemTooltipEvent;
import net.neoforged.neoforge.event.tick.PlayerTickEvent;
import net.neoforged.neoforge.registries.DeferredRegister;

import java.util.Set;

/**
 * Add tech upgrades and energy storage to ORIGINAL Superb Warfare armor.
 * No item replacement, model overrides or generated textures. Upgrades are
 * stored as stack components, so they survive inventory save/load and sync.
 */
@Mod(HybridWarfareMod.MODID)
public final class HybridWarfareMod {
    public static final String MODID = "techquest_hybrid";
    public static final int ENERGY_CAPACITY = 500_000; // NeoForge FE, not native IC2 EU
    public static final int MAX_RECEIVE = 8_000;

    public static final DataComponentType<String> TECHNOLOGY = DataComponentType
            .<String>builder().persistent(Codec.STRING)
            .networkSynchronized(ByteBufCodecs.STRING_UTF8).build();

    public static final DataComponentType<Integer> ENERGY = DataComponentType
            .<Integer>builder().persistent(Codec.INT)
            .networkSynchronized(ByteBufCodecs.VAR_INT).build();

    private static final DeferredRegister.DataComponents COMPONENTS =
            DeferredRegister.createDataComponents(Registries.DATA_COMPONENT_TYPE, MODID);

    private static final Set<String> MILITARY_ARMOR = Set.of(
            "ru_helmet_6b47", "ru_chest_6b43",
            "us_helmet_pasgt", "us_chest_iotv", "ge_helmet_m_35"
    );
    private static final Set<String> TECHNOLOGIES = Set.of("ic2", "mi", "mek", "oritech");

    static {
        COMPONENTS.register("technology", () -> TECHNOLOGY);
        COMPONENTS.register("energy", () -> ENERGY);
    }

    public HybridWarfareMod(IEventBus bus) {
        COMPONENTS.register(bus);
        bus.addListener(HybridWarfareMod::registerCapabilities);
        NeoForge.EVENT_BUS.addListener(HybridWarfareMod::tickPlayer);
        NeoForge.EVENT_BUS.addListener(HybridWarfareMod::tooltip);
    }

    public static boolean isSuperbWarfareArmor(ItemStack stack) {
        ResourceLocation id = BuiltInRegistries.ITEM.getKey(stack.getItem());
        return "superbwarfare".equals(id.getNamespace()) && MILITARY_ARMOR.contains(id.getPath());
    }

    public static String technology(ItemStack armor) {
        if (!isSuperbWarfareArmor(armor)) return null;
        String value = armor.get(TECHNOLOGY);
        return value != null && TECHNOLOGIES.contains(value) ? value : null;
    }

    public static int charge(ItemStack armor) {
        if (technology(armor) == null) return 0;
        return Math.max(0, Math.min(ENERGY_CAPACITY, armor.getOrDefault(ENERGY, 0)));
    }

    private static boolean spend(ItemStack armor, int amount) {
        if (amount <= 0 || charge(armor) < amount) return false;
        armor.set(ENERGY, charge(armor) - amount);
        return true;
    }

    private static void registerCapabilities(RegisterCapabilitiesEvent event) {
        for (String name : MILITARY_ARMOR) {
            Item item = BuiltInRegistries.ITEM.get(ResourceLocation.fromNamespaceAndPath("superbwarfare", name));
            event.registerItem(Capabilities.EnergyStorage.ITEM, (stack, context) ->
                    technology(stack) != null ? new ArmorEnergyStorage(stack) : null, item);
        }
    }

    /** FE transfer bridge; IC2: Nostalgia local.26 has FE/EU converters.
     * No free energy and no donor charge is copied by the current smithing recipes.
     */
    private static final class ArmorEnergyStorage implements IEnergyStorage {
        private final ItemStack stack;

        private ArmorEnergyStorage(ItemStack stack) {
            this.stack = stack;
        }

        @Override
        public int receiveEnergy(int requested, boolean simulate) {
            int accepted = Math.min(Math.min(Math.max(0, requested), MAX_RECEIVE),
                                    ENERGY_CAPACITY - charge(stack));
            if (accepted > 0 && !simulate) stack.set(ENERGY, charge(stack) + accepted);
            return accepted;
        }

        @Override
        public int extractEnergy(int requested, boolean simulate) {
            // Upgraded armor cannot be used as a battery to power machines.
            return 0;
        }

        @Override
        public int getEnergyStored() {
            return charge(stack);
        }

        @Override
        public int getMaxEnergyStored() {
            return ENERGY_CAPACITY;
        }

        @Override
        public boolean canExtract() {
            return false;
        }

        @Override
        public boolean canReceive() {
            return true;
        }
    }

    private static void tickPlayer(PlayerTickEvent.Post event) {
        Player player = event.getEntity();
        if (player.level().isClientSide() || player.tickCount % 20 != 0) return;

        ItemStack helmet = player.getItemBySlot(EquipmentSlot.HEAD);
        ItemStack chest = player.getItemBySlot(EquipmentSlot.CHEST);
        String headTech = technology(helmet);
        String chestTech = technology(chest);

        // These are real, energy-consuming gameplay upgrades, not passive
        // cosmetic markers. Effects intentionally stop when charge reaches zero.
        if ("ic2".equals(headTech) && spend(helmet, 80)) {
            player.addEffect(new MobEffectInstance(MobEffects.NIGHT_VISION, 240, 0, true, false));
            player.addEffect(new MobEffectInstance(MobEffects.WATER_BREATHING, 60, 0, true, false));
        } else if ("mek".equals(headTech) && spend(helmet, 70)) {
            player.addEffect(new MobEffectInstance(MobEffects.WATER_BREATHING, 60, 0, true, false));
        } else if ("mi".equals(headTech) && spend(helmet, 90)) {
            player.addEffect(new MobEffectInstance(MobEffects.NIGHT_VISION, 240, 0, true, false));
        }

        if ("ic2".equals(chestTech) && spend(chest, 150)) {
            player.addEffect(new MobEffectInstance(MobEffects.DAMAGE_RESISTANCE, 45, 0, true, false));
        } else if ("mi".equals(chestTech) && spend(chest, 130)) {
            player.addEffect(new MobEffectInstance(MobEffects.DAMAGE_RESISTANCE, 45, 0, true, false));
        } else if ("mek".equals(chestTech) && spend(chest, 120)) {
            player.addEffect(new MobEffectInstance(MobEffects.DAMAGE_RESISTANCE, 45, 0, true, false));
        } else if ("oritech".equals(chestTech) && spend(chest, 90)) {
            player.addEffect(new MobEffectInstance(MobEffects.MOVEMENT_SPEED, 45, 0, true, false));
        }

        // Additional two-piece bonus; both pieces must have matching tech and
        // sufficient charge to pay the bonus cost.
        if (headTech != null && headTech.equals(chestTech)
                && charge(helmet) >= 40 && charge(chest) >= 40
                && spend(helmet, 40) && spend(chest, 40)) {
            switch (headTech) {
                case "ic2" -> player.addEffect(new MobEffectInstance(MobEffects.FIRE_RESISTANCE, 45, 0, true, false));
                case "mi" -> player.addEffect(new MobEffectInstance(MobEffects.DAMAGE_RESISTANCE, 45, 1, true, false));
                case "mek" -> player.addEffect(new MobEffectInstance(MobEffects.WATER_BREATHING, 45, 0, true, false));
                case "oritech" -> player.addEffect(new MobEffectInstance(MobEffects.MOVEMENT_SPEED, 45, 1, true, false));
                default -> { }
            }
        }
    }

    private static void tooltip(ItemTooltipEvent event) {
        ItemStack stack = event.getItemStack();
        if (!isSuperbWarfareArmor(stack)) return;
        String tech = technology(stack);
        if (tech != null) {
            event.getToolTip().add(Component.translatable("tooltip.techquest_hybrid.tech",
                    Component.translatable("tooltip.techquest_hybrid.tech." + tech)).withStyle(ChatFormatting.AQUA));
            event.getToolTip().add(Component.translatable("tooltip.techquest_hybrid.energy",
                    charge(stack), ENERGY_CAPACITY).withStyle(ChatFormatting.YELLOW));
            event.getToolTip().add(Component.translatable("tooltip.techquest_hybrid.recharge").withStyle(ChatFormatting.GRAY));
            event.getToolTip().add(Component.translatable("tooltip.techquest_hybrid.effect." + tech)
                    .withStyle(ChatFormatting.DARK_AQUA));
        }

        ArmorTrim trim = stack.get(DataComponents.TRIM);
        if (trim != null) {
            String dye = trim.material().unwrapKey()
                    .map(key -> key.location().getPath()).orElse("unknown");
            event.getToolTip().add(Component.translatable("tooltip.techquest_hybrid.trim",
                    Component.translatable("tooltip.techquest_hybrid.material." + dye))
                    .withStyle(ChatFormatting.LIGHT_PURPLE));
        }
    }
}
