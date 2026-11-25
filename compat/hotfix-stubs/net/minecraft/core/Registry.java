package net.minecraft.core;
import net.minecraft.resources.ResourceLocation;
public interface Registry<T> { ResourceLocation getKey(T value); }
