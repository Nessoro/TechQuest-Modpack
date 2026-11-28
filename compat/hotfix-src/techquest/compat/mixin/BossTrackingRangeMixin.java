package techquest.compat.mixin;

import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.EntityType;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Track selected Cataclysm bosses and the Legendary Monsters Obliterator.
 * 14 chunks = 224 blocks at most, bounded by the server/client view distance.
 * Ordinary mobs, clones, projectiles and boss immunity are unchanged.
 */
@Mixin(EntityType.class)
public abstract class BossTrackingRangeMixin {
    private static final int TECHQUEST_BOSS_TRACKING_CHUNKS = 14;

    @Inject(method = "clientTrackingRange()I", at = @At("RETURN"), cancellable = true)
    private void techquest$bossTrackingRange(CallbackInfoReturnable<Integer> cir) {
        EntityType<?> type = (EntityType<?>) (Object) this;
        ResourceLocation id = EntityType.getKey(type);
        if (id == null) {
            return;
        }
        if ("legendary_monsters".equals(id.getNamespace()) && "the_obliterator".equals(id.getPath())) {
            cir.setReturnValue(Math.max(cir.getReturnValueI(), TECHQUEST_BOSS_TRACKING_CHUNKS));
            return;
        }
        if (!"cataclysm".equals(id.getNamespace())) {
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
