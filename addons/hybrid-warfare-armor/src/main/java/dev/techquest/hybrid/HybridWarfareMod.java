package dev.techquest.hybrid;

import net.minecraft.core.Holder;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.EquipmentSlotGroup;
import net.minecraft.world.entity.ai.attributes.Attribute;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ArmorItem;
import net.minecraft.world.item.ArmorMaterial;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.component.ItemAttributeModifiers;
import net.minecraft.world.item.crafting.Ingredient;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.tick.PlayerTickEvent;
import net.neoforged.neoforge.registries.DeferredRegister;
import java.util.*;

@Mod(HybridWarfareMod.MODID)
public final class HybridWarfareMod {
    public static final String MODID = "techquest_hybrid";
    private static final DeferredRegister<ArmorMaterial> MATERIALS =
        DeferredRegister.create(Registries.ARMOR_MATERIAL, MODID);
    private static final DeferredRegister<Item> ITEMS =
        DeferredRegister.create(Registries.ITEM, MODID);
    private static final List<String> TECHNOLOGIES = List.of("ic2", "mi", "mek", "oritech");
    private static final Map<String, Base> BASES = new LinkedHashMap<>();
    private record Base(ArmorItem.Type type, double bulletResistance) {}

    static {
        BASES.put("ru_helmet_6b47", new Base(ArmorItem.Type.HELMET, 0.2));
        BASES.put("ru_chest_6b43", new Base(ArmorItem.Type.CHESTPLATE, 0.5));
        BASES.put("us_helmet_pasgt", new Base(ArmorItem.Type.HELMET, 0.2));
        BASES.put("us_chest_iotv", new Base(ArmorItem.Type.CHESTPLATE, 0.5));
        BASES.put("ge_helmet_m_35", new Base(ArmorItem.Type.HELMET, 0.1));
        for (var technology : TECHNOLOGIES) {
            for (var entry : BASES.entrySet()) {
                String id = technology + "_" + entry.getKey();
                Base base = entry.getValue();
                Holder<ArmorMaterial> material = MATERIALS.register(id, () -> new ArmorMaterial(
                    Map.of(ArmorItem.Type.HELMET, 3, ArmorItem.Type.CHESTPLATE, 8,
                           ArmorItem.Type.LEGGINGS, 0, ArmorItem.Type.BOOTS, 0),
                    15, SoundEvents.ARMOR_EQUIP_NETHERITE, () -> Ingredient.EMPTY,
                    List.of(new ArmorMaterial.Layer(ResourceLocation.fromNamespaceAndPath(MODID, id))),
                    4.0F, 0.05F));
                ITEMS.register(id, () -> new HybridItem(material, base.type, base.bulletResistance,
                    technology, new Item.Properties().durability(base.type.getDurability(50))));
            }
        }
    }

    public HybridWarfareMod(IEventBus modBus) {
        MATERIALS.register(modBus);
        ITEMS.register(modBus);
        NeoForge.EVENT_BUS.addListener(HybridWarfareMod::onPlayerTick);
    }

    private static void onPlayerTick(PlayerTickEvent.Post event) {
        Player player = event.getEntity();
        if (player.level().isClientSide() || player.tickCount % 20 != 0) return;
        ItemStack head = player.getItemBySlot(EquipmentSlot.HEAD);
        ItemStack chest = player.getItemBySlot(EquipmentSlot.CHEST);
        if (!(head.getItem() instanceof HybridItem h) || !(chest.getItem() instanceof HybridItem c)) return;
        if (!h.technology.equals(c.technology)) return;
        // Prototype bonuses: no transfer of EU/FE, native modules, or charged donor components.
        switch (h.technology) {
            case "ic2" -> player.addEffect(new MobEffectInstance(MobEffects.FIRE_RESISTANCE, 45, 0, true, false));
            case "mi" -> player.addEffect(new MobEffectInstance(MobEffects.DAMAGE_RESISTANCE, 45, 0, true, false));
            case "mek" -> player.addEffect(new MobEffectInstance(MobEffects.WATER_BREATHING, 45, 0, true, false));
            case "oritech" -> player.addEffect(new MobEffectInstance(MobEffects.MOVEMENT_SPEED, 45, 0, true, false));
            default -> {}
        }
    }

    public static final class HybridItem extends ArmorItem {
        private final double bulletResistance;
        private final String technology;
        public HybridItem(Holder<ArmorMaterial> material, Type type, double bulletResistance,
                          String technology, Properties properties) {
            super(material, type, properties);
            this.bulletResistance = bulletResistance;
            this.technology = technology;
        }

        @Override
        public ItemAttributeModifiers getDefaultAttributeModifiers(ItemStack stack) {
            var original = super.getDefaultAttributeModifiers(stack);
            var entries = new ArrayList<ItemAttributeModifiers.Entry>(original.modifiers());
            ResourceKey<Attribute> key = ResourceKey.create(Registries.ATTRIBUTE,
                ResourceLocation.fromNamespaceAndPath("superbwarfare", "bullet_resistance"));
            BuiltInRegistries.ATTRIBUTE.getHolder(key).ifPresent(holder -> {
                double condition = stack.isDamageableItem()
                    ? Math.max(0.0, 1.0 - (double) stack.getDamageValue() / stack.getMaxDamage()) : 1.0;
                entries.add(new ItemAttributeModifiers.Entry(holder,
                    new AttributeModifier(ResourceLocation.fromNamespaceAndPath(
                        MODID, "bullet_resistance_" + type.getName()),
                        bulletResistance * condition, AttributeModifier.Operation.ADD_VALUE),
                    EquipmentSlotGroup.bySlot(type.getSlot())));
            });
            return new ItemAttributeModifiers(entries, true);
        }
    }
}
