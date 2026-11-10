package techquest.compat.mixin;

import com.awesomehippo.betterzoom.config.Config;
import net.neoforged.neoforge.client.event.ClientTickEvent;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Better Zoom 3.1.1 may receive ClientTickEvent.Post while its NeoForge CLIENT
 * ModConfigSpec is not yet loaded, then its ConfigValue.get() throws.
 *
 * Skip only those startup ticks; preserve all zoom functionality afterward.
 * Pin tied to Better Zoom NeoForge 1.21.1 3.1.1. No server mixin.
 */
@Mixin(targets = "com.awesomehippo.betterzoom.ZoomHandler", remap = false)
public abstract class BetterZoomEarlyTickMixin {
    @Inject(method = "onClientTick(Lnet/neoforged/neoforge/client/event/ClientTickEvent$Post;)V",
            at = @At("HEAD"), cancellable = true, remap = false)
    private static void techquest$skipUntilConfigLoads(ClientTickEvent.Post event, CallbackInfo ci) {
        if (!Config.SPEC.isLoaded()) {
            ci.cancel();
        }
    }
}
