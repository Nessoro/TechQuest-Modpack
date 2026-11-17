package dev.techquest.hybrid;

import com.mojang.serialization.Codec;
import net.minecraft.core.component.DataComponentType;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.codec.ByteBufCodecs;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.tick.PlayerTickEvent;
import net.neoforged.neoforge.registries.DeferredRegister;

import java.util.Map;
import java.util.Set;

/**
 * Apply tech perks to ORIGINAL Superb Warfare armor via a data component.
 * We do not register new armor/items/models/textures: vanilla smithing_transform
 * recipes transmute the same Superb Warfare item and patch just this component.
 * ArmorPlate, damage, enchants and original GeoArmorRenderer are preserved.
 */
@Mod(HybridWarfareMod.MODID)
public final class HybridWarfareMod {
    public static final String MODID = "techquest_hybrid";

    public static final DataComponentType<String> TECHNOLOGY = DataComponentType
            .<String>builder()
            .persistent(Codec.STRING)
            .networkSynchronized(ByteBufCodecs.STRING_UTF8)
            .build();

    private static final DeferredRegister.DataComponents COMPONENTS =
            DeferredRegister.createDataComponents(Registries.DATA_COMPONENT_TYPE, MODID);

    public static final Set<String> MILITARY_ARMOR = Set.of(
            "ru_helmet_6b47", "ru_chest_6b43",
            "us_helmet_pasgt", "us_chest_iotv", "ge_helmet_m_35"
    );

    private static final Set<String> TECHNOLOGIES = Set.of("ic2", "mi", "mek", "oritech");

    static {
        COMPONENTS.register("technology", () -> TECHNOLOGY);
    }

    public HybridWarfareMod(IEventBus bus) {
        COMPONENTS.register(bus);
        NeoForge.EVENT_BUS.addListener(HybridWarfareMod::tickPlayer);
    }

    public static boolean isSuperbWarfareArmor(ItemStack stack) {
        ResourceLocation id = BuiltInRegistries.ITEM.getKey(stack.getItem());
        return "superbwarfare".equals(id.getNamespace()) && MILITARY_ARMOR.contains(id.getPath());
    }

    private static String technology(ItemStack armor) {
        if (!isSuperbWarfareArmor(armor)) return null;
        String value = armor.get(TECHNOLOGY);
        return value != null && TECHNOLOGIES.contains(value) ? value : null;
    }

    private static void tickPlayer(PlayerTickEvent.Post event) {
        Player player = event.getEntity();
        if (player.level().isClientSide() || player.tickCount % 20 != 0) return;

        String chestTech = technology(player.getItemBySlot(EquipmentSlot.CHEST));
        String headTech = technology(player.getItemBySlot(EquipmentSlot.HEAD));
        if (chestTech == null || !chestTech.equals(headTech)) return;

        // Conservative prototype set bonuses; does not copy EU/FE or donor modules.
        switch (chestTech) {
            case "ic2" -> player.addEffect(new MobEffectInstance(MobEffects.FIRE_RESISTANCE, 45, 0, true, false));
            case "mi" -> player.addEffect(new MobEffectInstance(MobEffects.DAMAGE_RESISTANCE, 45, 0, true, false));
            case "mek" -> player.addEffect(new MobEffectInstance(MobEffects.WATER_BREATHING, 45, 0, true, false));
            case "oritech" -> player.addEffect(new MobEffectInstance(MobEffects.MOVEMENT_SPEED, 45, 0, true, false));
            default -> { }
        }
    }
}
