package dev.techquest.hybrid.client;

import net.minecraft.client.model.HumanoidModel;
import net.minecraft.client.model.geom.PartPose;
import net.minecraft.client.model.geom.builders.CubeDeformation;
import net.minecraft.client.model.geom.builders.CubeListBuilder;
import net.minecraft.client.model.geom.builders.LayerDefinition;
import net.minecraft.client.model.geom.builders.MeshDefinition;
import net.minecraft.client.model.geom.builders.PartDefinition;

/**
 * 3D wearable 6B47 + 6B43 armor inspired by Superb Warfare, rebuilt from original voxels.
 * Model parts attach to animated humanoid bones. Texture: 256x256 custom UV atlas.
 * This does NOT copy Superb Warfare's original Bedrock model or assets.
 */
public final class MekMilitaryArmorModel {
    private MekMilitaryArmorModel() {}

    public static LayerDefinition create(boolean helmet) {
        MeshDefinition mesh = HumanoidModel.createMesh(CubeDeformation.NONE, 0.0F);
        if (helmet) add(mesh, "head", "top_shell", 73, 2, -4.75F, -8.65F, -4.75F, 9.5F, 2.9F, 9.5F);
        if (helmet) add(mesh, "head", "forehead_plate", 114, 2, -4.8F, -6.3F, -5.28F, 9.6F, 1.4F, 1.2F);
        if (helmet) add(mesh, "head", "helmet_crown_ridge", 139, 2, -1.5F, -9.08F, -4F, 3F, 0.75F, 8F);
        if (helmet) add(mesh, "head", "helmet_left_side", 164, 2, -5.12F, -7.2F, -4.25F, 1.55F, 5.7F, 7.4F);
        if (helmet) add(mesh, "head", "helmet_right_side", 185, 2, 3.58F, -7.2F, -4.25F, 1.55F, 5.7F, 7.4F);
        if (helmet) add(mesh, "head", "left_ear_guard", 206, 2, -5.3F, -3.7F, -1.9F, 1.4F, 3F, 3.9F);
        if (helmet) add(mesh, "head", "right_ear_guard", 220, 2, 3.9F, -3.7F, -1.9F, 1.4F, 3F, 3.9F);
        if (helmet) add(mesh, "head", "helmet_rear_plate", 73, 19, -4.35F, -6.5F, 3.55F, 8.7F, 5.7F, 1.45F);
        if (helmet) add(mesh, "head", "visor_brow", 97, 19, -4.2F, -5.55F, -5.72F, 8.4F, 0.9F, 1.5F);
        if (helmet) add(mesh, "head", "vision_module_center", 120, 19, -1.25F, -7.3F, -6.12F, 2.5F, 2.1F, 1.3F);
        if (helmet) add(mesh, "head", "vision_module_glass", 131, 19, -0.77F, -6.93F, -6.31F, 1.54F, 1F, 0.35F);
        if (helmet) add(mesh, "head", "visor_eye_L", 138, 19, -3.2F, -4.25F, -5.47F, 2.5F, 0.58F, 0.48F);
        if (helmet) add(mesh, "head", "visor_eye_R", 147, 19, 0.7F, -4.25F, -5.47F, 2.5F, 0.58F, 0.48F);
        if (helmet) add(mesh, "head", "visor_LED_L", 156, 19, -3.13F, -4.23F, -5.64F, 2.2F, 0.28F, 0.2F);
        if (helmet) add(mesh, "head", "visor_LED_R", 164, 19, 0.9F, -4.23F, -5.64F, 2.2F, 0.28F, 0.2F);
        if (helmet) add(mesh, "head", "left_side_rail", 172, 19, -5.57F, -6.7F, -3F, 0.62F, 1.2F, 6F);
        if (helmet) add(mesh, "head", "right_side_rail", 189, 19, 4.95F, -6.7F, -3F, 0.62F, 1.2F, 6F);
        if (helmet) add(mesh, "head", "left_radio", 206, 19, -5.88F, -4.9F, -0.1F, 0.92F, 1.55F, 1.8F);
        if (helmet) add(mesh, "head", "left_radio_led", 215, 19, -5.94F, -4.43F, 0.37F, 0.2F, 0.62F, 0.7F);
        if (helmet) add(mesh, "head", "right_radio", 220, 19, 4.93F, -4.9F, -0.1F, 0.95F, 1.55F, 1.8F);
        if (helmet) add(mesh, "head", "right_radio_led", 229, 19, 5.75F, -4.43F, 0.37F, 0.2F, 0.62F, 0.7F);
        if (helmet) add(mesh, "head", "chin_guard", 234, 19, -2.4F, -1.47F, -5.1F, 4.8F, 2F, 1F);
        if (helmet) add(mesh, "head", "rear_battery", 73, 30, -1.9F, -6.5F, 4.85F, 3.8F, 3.6F, 0.85F);
        if (helmet) add(mesh, "head", "rear_battery_light", 86, 30, -1.2F, -5.7F, 5.72F, 2.4F, 0.6F, 0.22F);
        if (!helmet) add(mesh, "body", "base_plate_back", 73, 2, -4.45F, 0.2F, 1.82F, 8.9F, 11.7F, 1.1F);
        if (!helmet) add(mesh, "body", "base_plate_front", 96, 2, -4.85F, 0.3F, -3.45F, 9.7F, 11.35F, 2F);
        if (!helmet) add(mesh, "body", "soft_armor_front", 123, 2, -4.2F, 0.8F, -3.83F, 8.4F, 10.2F, 1F);
        if (!helmet) add(mesh, "body", "upper_chest_plate", 145, 2, -4.5F, 1.4F, -4.56F, 9F, 5.9F, 1.2F);
        if (!helmet) add(mesh, "body", "lower_chest_plate", 169, 2, -4F, 7.25F, -4.68F, 8F, 3.5F, 1.2F);
        if (!helmet) add(mesh, "body", "center_rib", 191, 2, -0.9F, 1.1F, -4.99F, 1.8F, 9.4F, 0.63F);
        if (!helmet) add(mesh, "body", "collar_rear", 199, 2, -4F, -0.73F, 1.9F, 8F, 1.4F, 2F);
        if (!helmet) add(mesh, "body", "collar_front", 222, 2, -3.6F, -0.48F, -4F, 7.2F, 1.7F, 1.5F);
        if (!helmet) add(mesh, "body", "left_shoulder_strap", 243, 2, -4.45F, -0.85F, -3.9F, 1.6F, 7.2F, 0.76F);
        if (!helmet) add(mesh, "body", "right_shoulder_strap", 73, 19, 2.8F, -0.85F, -3.9F, 1.6F, 7.2F, 0.76F);
        if (!helmet) add(mesh, "body", "left_side_panel", 81, 19, -5.15F, 3F, -2F, 1.4F, 7.8F, 4.3F);
        if (!helmet) add(mesh, "body", "right_side_panel", 96, 19, 3.75F, 3F, -2F, 1.4F, 7.8F, 4.3F);
        if (!helmet) add(mesh, "body", "left_side_latch", 111, 19, -5.6F, 6.2F, -1.2F, 0.56F, 1.25F, 2F);
        if (!helmet) add(mesh, "body", "right_side_latch", 120, 19, 5.04F, 6.2F, -1.2F, 0.56F, 1.25F, 2F);
        if (!helmet) add(mesh, "body", "power_frame", 129, 19, -2.2F, 2.5F, -5.31F, 4.4F, 3.8F, 0.76F);
        if (!helmet) add(mesh, "body", "power_core_base", 143, 19, -1.7F, 2.96F, -5.77F, 3.4F, 2.9F, 0.65F);
        if (!helmet) add(mesh, "body", "power_core", 155, 19, -1.14F, 3.42F, -6.25F, 2.28F, 1.95F, 0.54F);
        if (!helmet) add(mesh, "body", "power_core_glint", 164, 19, -0.42F, 3.58F, -6.55F, 0.84F, 0.75F, 0.18F);
        if (!helmet) add(mesh, "body", "pouch_left", 170, 19, -3.77F, 8.02F, -5.35F, 2.35F, 2.9F, 1.3F);
        if (!helmet) add(mesh, "body", "pouch_center", 181, 19, -1.15F, 8.12F, -5.54F, 2.3F, 2.7F, 1.45F);
        if (!helmet) add(mesh, "body", "pouch_right", 192, 19, 1.55F, 8.02F, -5.35F, 2.35F, 2.9F, 1.3F);
        if (!helmet) add(mesh, "body", "pouch_left_tab", 203, 19, -3.18F, 8.05F, -5.71F, 1F, 0.62F, 0.2F);
        if (!helmet) add(mesh, "body", "pouch_right_tab", 209, 19, 2.14F, 8.05F, -5.71F, 1F, 0.62F, 0.2F);
        if (!helmet) add(mesh, "body", "left_back_storage", 215, 19, -3.65F, 4.9F, 2.95F, 2.9F, 5.2F, 1.9F);
        if (!helmet) add(mesh, "body", "right_back_storage", 228, 19, 0.75F, 4.9F, 2.95F, 2.9F, 5.2F, 1.9F);
        if (!helmet) add(mesh, "body", "back_energy_pack", 241, 19, -1.3F, 1.6F, 3.25F, 2.6F, 4.1F, 1.45F);
        if (!helmet) add(mesh, "body", "back_energy_light", 73, 35, -0.86F, 2.28F, 4.65F, 1.72F, 1.95F, 0.22F);
        if (!helmet) add(mesh, "right_arm", "right_upper_shoulder", 80, 35, -4.45F, -2.45F, -2.95F, 4.6F, 5.5F, 5.9F);
        if (!helmet) add(mesh, "right_arm", "right_shoulder_plate", 104, 35, -4.84F, -1.8F, -3.15F, 4.8F, 3.4F, 0.84F);
        if (!helmet) add(mesh, "right_arm", "right_arm_diode", 119, 35, -2.6F, -0.05F, -3.62F, 1.2F, 0.66F, 0.55F);
        if (!helmet) add(mesh, "right_arm", "right_armor_elbow", 126, 35, -3.95F, 5.35F, -2.75F, 4.25F, 2.1F, 5.5F);
        if (!helmet) add(mesh, "left_arm", "left_upper_shoulder", 149, 35, -0.15F, -2.45F, -2.95F, 4.6F, 5.5F, 5.9F);
        if (!helmet) add(mesh, "left_arm", "left_shoulder_plate", 173, 35, 0.05F, -1.8F, -3.15F, 4.8F, 3.4F, 0.84F);
        if (!helmet) add(mesh, "left_arm", "left_arm_diode", 188, 35, 1.5F, -0.05F, -3.62F, 1.2F, 0.66F, 0.55F);
        if (!helmet) add(mesh, "left_arm", "left_armor_elbow", 195, 35, -0.3F, 5.35F, -2.75F, 4.25F, 2.1F, 5.5F);
        return LayerDefinition.create(mesh, 256, 256);
    }

    private static void add(MeshDefinition mesh, String bone, String name, int u, int v,
                            float x, float y, float z, float width, float height, float depth) {
        PartDefinition parent = mesh.getRoot().getChild(bone);
        parent.addOrReplaceChild(name, CubeListBuilder.create()
                .texOffs(u, v).addBox(x, y, z, width, height, depth), PartPose.ZERO);
    }
}
