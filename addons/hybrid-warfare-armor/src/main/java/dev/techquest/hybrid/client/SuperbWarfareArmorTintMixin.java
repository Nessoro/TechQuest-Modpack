package dev.techquest.hybrid.client;

import dev.techquest.hybrid.HybridWarfareMod;
import net.minecraft.core.component.DataComponents;
import net.minecraft.util.FastColor;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.armortrim.ArmorTrim;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.ModifyVariable;
import org.jetbrains.annotations.Nullable;

/**
 * Color-grade the ORIGINAL Superb Warfare texture while its Bedrock renderer draws it.
 * No replacement PNGs or new model assets. Vanilla trim template supplies the pattern
 * metadata and the smithing material selects this whole-armor tint.
 *
 * This is a fallback visual interpretation of trims: the original SBW Bedrock UV model
 * does not support projecting vanilla trim patterns onto the 3D mesh.
 */
@Pseudo
@Mixin(targets = "com.github.mcmodderanchor.simplebedrockmodel.v2.client.renderer.GeoArmorRendererV2",
       remap = false)
public abstract class SuperbWarfareArmorTintMixin {
    @Shadow(remap = false) @Nullable protected ItemStack itemStack;

    @ModifyVariable(method = "renderToBuffer(Lcom/mojang/blaze3d/vertex/PoseStack;Lcom/mojang/blaze3d/vertex/VertexConsumer;III)V",
                    at = @At("HEAD"), argsOnly = true, index = 5,
                    remap = false)
    private int techquest$applyTrimTint(int original) {
        ItemStack stack = this.itemStack;
        if (stack == null || !HybridWarfareMod.isSuperbWarfareArmor(stack)) return original;
        ArmorTrim trim = stack.get(DataComponents.TRIM);
        if (trim == null) return original;
        String material = trim.material().unwrapKey().map(key -> key.location().getPath()).orElse("");
        int palette = switch (material) {
            case "quartz" -> 0xF2F0E8;
            case "iron" -> 0xBEC4CD;
            case "copper" -> 0xD0A27B;
            case "gold" -> 0xFFDA8D;
            case "lapis" -> 0x92B6FF;
            case "emerald" -> 0x8FE5B2;
            case "diamond" -> 0x9CE7F0;
            case "redstone" -> 0xFF9292;
            case "amethyst" -> 0xD1A6FF;
            case "netherite" -> 0xB3AABB;
            default -> 0xFFFFFF;
        };
        int r = FastColor.ARGB32.red(original) * ((palette >> 16) & 255) / 255;
        int g = FastColor.ARGB32.green(original) * ((palette >> 8) & 255) / 255;
        int b = FastColor.ARGB32.blue(original) * (palette & 255) / 255;
        return FastColor.ARGB32.color(FastColor.ARGB32.alpha(original), r, g, b);
    }
}
