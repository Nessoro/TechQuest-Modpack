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

/** Preserve Incoming lethal and partial hits on Legendary Monsters minibosses, with special guards intact. */
@Mixin(targets = "net.miauczel.legendary_monsters.entity.AnimatedMonster.OriginClasses.IAnimatedMiniBoss")
public abstract class IncomingLegendaryMiniBossMixin {
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

    @Redirect(method = "hurt(Lnet/minecraft/world/damagesource/DamageSource;F)Z",
            at = @At(value = "INVOKE", target = "Ljava/lang/Math;min(DD)D"))
    private double techquest$incomingUncappedHurt(double limit, double original,
                                                   DamageSource source, float amount) {
        return techquest$isIncoming(source) ? original : Math.min(limit, original);
    }
}
