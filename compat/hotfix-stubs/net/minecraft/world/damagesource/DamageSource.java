package net.minecraft.world.damagesource;
import net.minecraft.resources.ResourceKey;
public class DamageSource {
  private final ResourceKey<DamageType> type;
  public DamageSource(ResourceKey<DamageType> type) { this.type=type; }
  public boolean is(ResourceKey<DamageType> key) { return type.equals(key); }
}
