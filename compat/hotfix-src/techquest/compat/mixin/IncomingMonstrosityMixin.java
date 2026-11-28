package techquest.compat.mixin;

import java.util.Set;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.damagesource.DamageType;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;
import org.spongepowered.asm.mixin.injection.ModifyVariable;

/** Scoped bridge for the separate Cataclysm 3.33 internal-animation boss hierarchy. */
@Mixin(targets = "com.github.L_Ender.cataclysm.entity.InternalAnimationMonster.IABossMonsters.IABoss_monster")
public abstract class IncomingMonstrosityMixin {
    @Shadow(remap = false)
    public abstract int getAttackState();

    private boolean techquest$isVulnerableMonstrosityIncoming(DamageSource source) {
        return getClass().getName().equals("com.github.L_Ender.cataclysm.entity.InternalAnimationMonster.IABossMonsters.NewNetherite_Monstrosity.Netherite_Monstrosity_Entity")
                && getAttackState() != 4 && techquest$isIncoming(source);
    }

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
        return techquest$isVulnerableMonstrosityIncoming(source) ? -1.0 : squaredDistance;
    }

    // Only redirects the clamp in IABoss_monster.hurt, not the boss' own
    // hurt guard or the vanilla LivingEntity.hurt damage pipeline.
    @Redirect(
            method = "hurt(Lnet/minecraft/world/damagesource/DamageSource;F)Z",
            at = @At(value = "INVOKE", target = "Ljava/lang/Math;min(FF)F"))
    private float techquest$incomingOriginalDamage(float perHitCap, float damage,
                                                    DamageSource source, float initialDamage) {
        if (damage > perHitCap && techquest$isVulnerableMonstrosityIncoming(source)) return damage;
        return Math.min(perHitCap, damage);
    }
}
