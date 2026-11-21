package dev.techquest.hybrid.flightmixin;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import dev.techquest.hybrid.PoweredElytra;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.ItemStack;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;

/**
 * Existing jetpack is left intact; custom flight hooks are only called when
 * our persisted Elytra attachment is present on the equipped chestplate.
 */
@Mixin(LivingEntity.class)
public abstract class PoweredElytraLivingMixin {
    @WrapOperation(method = "updateFallFlying",
            at = @At(value = "INVOKE",
                    target = "Lnet/minecraft/world/item/ItemStack;canElytraFly(Lnet/minecraft/world/entity/LivingEntity;)Z"))
    private boolean techquest$canKeepGliding(ItemStack stack, LivingEntity owner,
                                             Operation<Boolean> original) {
        return PoweredElytra.canFly(stack, owner) || original.call(stack, owner);
    }

    @WrapOperation(method = "updateFallFlying",
            at = @At(value = "INVOKE",
                    target = "Lnet/minecraft/world/item/ItemStack;elytraFlightTick(Lnet/minecraft/world/entity/LivingEntity;I)Z"))
    private boolean techquest$energyFlightTick(ItemStack stack, LivingEntity owner, int ticks,
                                               Operation<Boolean> original) {
        if (PoweredElytra.hasElytra(stack)) {
            return PoweredElytra.flightTick(stack, owner, ticks);
        }
        return original.call(stack, owner, ticks);
    }
}
