package techquest.compat.mixin;

import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.EntityType;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Only these registered Cataclysm boss entity types are tracked for 14 chunks.
 * 14 chunks = 224 blocks at most, bounded by the server/client view distance.
 * Ordinary mobs, bosses from other mods, attacks and boss immunity are unchanged.
 */
@Mixin(EntityType.class)
public abstract class BossTrackingRangeMixin {
    private static final int TECHQUEST_BOSS_TRACKING_CHUNKS = 14;

    @Inject(method = "clientTrackingRange()I", at = @At("RETURN"), cancellable = true)
    private void techquest$bossTrackingRange(CallbackInfoReturnable<Integer> cir) {
        EntityType<?> type = (EntityType<?>) (Object) this;
        ResourceLocation id = BuiltInRegistries.ENTITY_TYPE.getKey(type);
        if (id == null || !"cataclysm".equals(id.getNamespace())) {
            return;
        }
        switch (id.getPath()) {
            case "ender_golem", "ender_guardian", "netherite_monstrosity",
                 "ignis", "the_harbinger", "the_leviathan", "ancient_remnant",
                 "scylla", "clawdian", "maledictus", "the_prowler" ->
                    cir.setReturnValue(Math.max(cir.getReturnValueI(), TECHQUEST_BOSS_TRACKING_CHUNKS));
            default -> { } // No tracking changes for minions or projectiles.
        }
    }
}
