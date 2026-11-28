package net.minecraft.resources;
public final class ResourceLocation {
  private final String namespace, path;
  private ResourceLocation(String namespace, String path) { this.namespace=namespace; this.path=path; }
  public static ResourceLocation fromNamespaceAndPath(String namespace, String path) { return new ResourceLocation(namespace,path); }
  public String getNamespace() { return namespace; }
  public String getPath() { return path; }
  @Override public boolean equals(Object obj) { return obj instanceof ResourceLocation r && namespace.equals(r.namespace) && path.equals(r.path); }
  @Override public int hashCode() { return java.util.Objects.hash(namespace,path); }
}

