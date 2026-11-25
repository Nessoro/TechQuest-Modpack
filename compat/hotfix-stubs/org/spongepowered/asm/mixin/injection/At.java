package org.spongepowered.asm.mixin.injection;
import java.lang.annotation.*;
@Retention(RetentionPolicy.RUNTIME) @Target({ElementType.ANNOTATION_TYPE,ElementType.METHOD})
public @interface At { String value(); }
