package dev.techquest.hybrid.flightmixin;

import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import com.llamalad7.mixinextras.injector.wrapoperation.WrapOperation;
import dev.techquest.hybrid.PoweredElytra;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/** Attach Elytra functionality to powered chest armor without replacing it. */
@Mixin(Player.class)
public abstract class PoweredElytraPlayerMixin {
    /**
     * Use the vanilla flight start state transition directly for a valid
     * attached Elytra. This is limited to charged, worn chestpieces; it does
     * not modify normal elytras, IC2 jetpack flight or any other armor.
     *
     * An explicit HEAD injection avoids reliance on the fragile item-method
     * invocation, which some jetpack/flight mods wrap or replace.
     */
    @Inject(method = "tryToStartFallFlying", at = @At("HEAD"), cancellable = true)
    private void techquest$tryPoweredGlide(CallbackInfoReturnable<Boolean> cir) {
        Player player = (Player) (Object) this;
        ItemStack chest = player.getItemBySlot(EquipmentSlot.CHEST);
        if (!PoweredElytra.hasElytra(chest)) return;
        if (!player.onGround() && !player.isFallFlying() && !player.isInWater()
                && !player.hasEffect(MobEffects.LEVITATION) && PoweredElytra.canFly(chest, player)) {
            player.startFallFlying();
            cir.setReturnValue(true);
        }
    }

    @WrapOperation(method = "tryToStartFallFlying",
            at = @At(value = "INVOKE",
                    target = "Lnet/minecraft/world/item/ItemStack;canElytraFly(Lnet/minecraft/world/entity/LivingEntity;)Z"))
    private boolean techquest$canStartGliding(ItemStack stack, LivingEntity owner,
                                              Operation<Boolean> original) {
        return PoweredElytra.canFly(stack, owner) || original.call(stack, owner);
    }
}
