package dev.techquest.hybrid.flightmixin;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import dev.techquest.hybrid.PoweredElytra;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;

/** Attach Elytra functionality to powered chest armor without replacing it. */
@Mixin(Player.class)
public abstract class PoweredElytraPlayerMixin {
    @WrapOperation(method = "tryToStartFallFlying",
            at = @At(value = "INVOKE",
                    target = "Lnet/minecraft/world/item/ItemStack;canElytraFly(Lnet/minecraft/world/entity/LivingEntity;)Z"))
    private boolean techquest$canStartGliding(ItemStack stack, LivingEntity owner,
                                              Operation<Boolean> original) {
        return PoweredElytra.canFly(stack, owner) || original.call(stack, owner);
    }
}
