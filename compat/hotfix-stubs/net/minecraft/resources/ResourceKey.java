package net.minecraft.resources;
public final class ResourceKey<T> {
  private final ResourceLocation registry, id;
  private ResourceKey(ResourceLocation registry, ResourceLocation id) { this.registry=registry; this.id=id; }
  public static <T> ResourceKey<T> create(ResourceKey<T> registry, ResourceLocation id) { return new ResourceKey<>(registry==null?null:registry.id,id); }
  @Override public boolean equals(Object obj) { return obj instanceof ResourceKey<?> other && java.util.Objects.equals(registry,other.registry) && id.equals(other.id); }
  @Override public int hashCode() { return java.util.Objects.hash(registry,id); }
}
