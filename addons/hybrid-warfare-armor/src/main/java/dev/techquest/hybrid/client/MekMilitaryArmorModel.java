package dev.techquest.hybrid.client;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import net.minecraft.client.model.HumanoidModel;
import net.minecraft.client.model.geom.PartPose;
import net.minecraft.client.model.geom.builders.CubeDeformation;
import net.minecraft.client.model.geom.builders.CubeListBuilder;
import net.minecraft.client.model.geom.builders.LayerDefinition;
import net.minecraft.client.model.geom.builders.MeshDefinition;
import net.minecraft.client.model.geom.builders.PartDefinition;

/**
 * 4-piece Tactical Blue V2 3D voxel armor, built from packaged .cuboids resources.
 *
 * Every protrusion is attached to the appropriate vanilla humanoid bone, so it
 * moves with the player. The base head cuboid is removed for the helmet, allowing
 * the player's actual face/skin to remain visible beneath the open-face helmet.
 * All geometry and texture palettes are original works for TechQuest.
 */
public final class MekMilitaryArmorModel {
    private MekMilitaryArmorModel() {}

    public static LayerDefinition create(String itemName) {
        MeshDefinition mesh = HumanoidModel.createMesh(CubeDeformation.NONE, 0.0F);
        if (itemName.equals("mek_ru_helmet_6b47")) {
            mesh.getRoot().addOrReplaceChild("head", CubeListBuilder.create(), PartPose.ZERO);
        }
        String path = "/assets/techquest_hybrid/models/armor/" + itemName + ".cuboids";
        var stream = MekMilitaryArmorModel.class.getResourceAsStream(path);
        if (stream == null) {
            throw new IllegalStateException("Missing TechQuest Tactical Blue V2 model " + path);
        }
        int parts = 0;
        try (BufferedReader reader =
                new BufferedReader(new InputStreamReader(stream, StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                if (line.isBlank() || line.startsWith("#")) continue;
                String[] v = line.strip().split("\\s+");
                if (v.length != 10) {
                    throw new IllegalStateException("Invalid cuboid: " + itemName + " / " + line);
                }
                PartDefinition bone = mesh.getRoot().getChild(v[0]);
                bone.addOrReplaceChild(v[1], CubeListBuilder.create()
                        .texOffs(Integer.parseInt(v[2]), Integer.parseInt(v[3]))
                        .addBox(
                            Float.parseFloat(v[4]), Float.parseFloat(v[5]), Float.parseFloat(v[6]),
                            Float.parseFloat(v[7]), Float.parseFloat(v[8]), Float.parseFloat(v[9])),
                    PartPose.ZERO);
                parts++;
            }
        } catch (IOException error) {
            throw new IllegalStateException("Could not read armor model " + path, error);
        }
        if (parts == 0) throw new IllegalStateException("Empty armor model " + path);
        return LayerDefinition.create(mesh, 256, 256);
    }
}
