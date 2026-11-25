package techquest.compat.mixin;

import java.util.Set;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.damagesource.DamageType;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;
import org.spongepowered.asm.mixin.injection.ModifyVariable;

/**
 * Cataclysm only: never turn a physically lethal Incoming strike into 22 HP.
 * All other damage and all scripted immunity checks remain in charge.
 * Does not bypass phases, damage-source immunity, or invulnerability tags.
 */
@Mixin(targets = "com.github.L_Ender.cataclysm.entity.AnimationMonster.BossMonsters.LLibrary_Boss_Monster")
public abstract class IncomingLethalCapMixin {
    // Pinned to the damage type IDs in Incoming 3.10.4. These are damage
    // mechanisms, not an unconditional 'kill' action; Incoming computes HP loss.
    private static final Set<ResourceKey<DamageType>> TECHQUEST$INCOMING = Set.of(
            type("strike"), type("shockwave"), type("kinetic"),
            type("nuclear_blast"), type("player_nuclear_blast"),
            type("nuclear_thermal"), type("player_nuclear_thermal"),
            type("radiation"), type("player_radiation"), type("burn_shock"),
            type("debris"), type("fragment"));

    private static ResourceKey<DamageType> type(String id) {
        return ResourceKey.create(Registries.DAMAGE_TYPE, ResourceLocation.fromNamespaceAndPath("incoming", id));
    }

    private static boolean techquest$isIncoming(DamageSource source) {
        for (ResourceKey<DamageType> type : TECHQUEST$INCOMING) {
            if (source.is(type)) return true;
        }
        return false;
    }

    // Incoming projectiles determine hit distance with their own physical model.
    // -1 is Cataclysm's existing sentinel to skip attacker-distance checks.
    @ModifyVariable(method = "hurt(Lnet/minecraft/world/damagesource/DamageSource;F)Z",
            at = @At("STORE"), ordinal = 0)
    private double techquest$incomingNoAttackerRangeCap(double squaredDistance,
                                                         DamageSource source, float initialDamage) {
        return techquest$isIncoming(source) ? -1.0 : squaredDistance;
    }

    // Only redirects the clamp in LLibrary_Boss_Monster.hurt, not the boss' own
    // hurt guard or the vanilla LivingEntity.hurt damage pipeline.
    @Redirect(
            method = "hurt(Lnet/minecraft/world/damagesource/DamageSource;F)Z",
            at = @At(value = "INVOKE", target = "Ljava/lang/Math;min(FF)F"))
    private float techquest$incomingOriginalDamage(float perHitCap, float damage,
                                                    DamageSource source, float initialDamage) {
        if (damage > perHitCap && techquest$isIncoming(source)) return damage;
        return Math.min(perHitCap, damage);
    }
}
