// Developer-side static audit. Reads class files; never loads or executes mod code.
// Requires Java 21 and the pinned ASM library already used by NeoForge.
import org.objectweb.asm.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;

class KeymapAudit {
    record Ref(String name) {}
    record Key(int code, String type) {}
    static final Object UNKNOWN = new Ref("unresolved");
    static final List<String> rows = new ArrayList<>();
    static String json(Object value) {
        if (value == null) return "null";
        if (value instanceof Number) return value.toString();
        return "\"" + value.toString().replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "\\r") + "\"";
    }
    static void inspect(byte[] bytes, String origin) {
        new ClassReader(bytes).accept(new ClassVisitor(Opcodes.ASM9) {
            String className;
            public void visit(int v, int a, String n, String s, String p, String[] i) { className = n; }
            public MethodVisitor visitMethod(int access, String name, String descriptor, String signature, String[] exceptions) {
                return new MethodVisitor(Opcodes.ASM9) {
                    final List<Object> stack = new ArrayList<>();
                    Object pop() { return stack.isEmpty() ? UNKNOWN : stack.remove(stack.size() - 1); }
                    void push(Object o) { stack.add(o); }
                    public void visitLdcInsn(Object value) { push(value); }
                    public void visitIntInsn(int op, int operand) { push(op == Opcodes.BIPUSH || op == Opcodes.SIPUSH ? operand : UNKNOWN); }
                    public void visitVarInsn(int op, int local) {
                        if (op >= Opcodes.ILOAD && op <= Opcodes.ALOAD) push(UNKNOWN); else pop();
                    }
                    public void visitTypeInsn(int op, String type) {
                        if (op == Opcodes.NEW) push(UNKNOWN);
                        else if (op != Opcodes.CHECKCAST) { pop(); push(UNKNOWN); }
                    }
                    public void visitFieldInsn(int op, String owner, String field, String desc) {
                        if (op == Opcodes.GETSTATIC) push(owner.equals("com/mojang/blaze3d/platform/InputConstants") && field.equals("UNKNOWN")
                            ? new Key(-1, "KEYSYM") : new Ref(owner + "." + field));
                        else if (op == Opcodes.PUTSTATIC) pop();
                        else if (op == Opcodes.GETFIELD) { pop(); push(UNKNOWN); }
                        else { pop(); pop(); }
                    }
                    public void visitInsn(int op) {
                        if (op >= Opcodes.ICONST_M1 && op <= Opcodes.ICONST_5) push(op - Opcodes.ICONST_0);
                        else if (op == Opcodes.DUP) { Object o = pop(); push(o); push(o); }
                        else if (op == Opcodes.POP) pop();
                        else if (op == Opcodes.ACONST_NULL) push(UNKNOWN);
                        else if (op != Opcodes.NOP) stack.clear();
                    }
                    public void visitJumpInsn(int op, Label label) { stack.clear(); }
                    public void visitMethodInsn(int op, String owner, String method, String desc, boolean iface) {
                        Type[] types = Type.getArgumentTypes(desc);
                        Object[] values = new Object[types.length];
                        for (int i = types.length - 1; i >= 0; i--) values[i] = pop();
                        Object receiver = op != Opcodes.INVOKESTATIC ? pop() : UNKNOWN;
                        if (owner.equals("net/minecraft/client/KeyMapping") && method.equals("<init>")) {
                            Object id = null, code = null, category = null, modifier = null, context = null, input = null;
                            boolean firstString = true;
                            for (int i = 0; i < types.length; i++) {
                                if (types[i].equals(Type.getType(String.class))) {
                                    if (firstString) { id = values[i] instanceof String ? values[i] : null; firstString = false; }
                                    else category = values[i] instanceof String ? values[i] : null;
                                }
                                if (types[i].getSort() == Type.INT && values[i] instanceof Integer) code = values[i];
                                if (values[i] instanceof Key k) { code = k.code; input = k.type; }
                                if (values[i] instanceof Ref r) {
                                    if (r.name.contains("KeyModifier.")) modifier = r.name.substring(r.name.lastIndexOf('.') + 1);
                                    if (r.name.contains("KeyConflictContext.")) context = r.name.substring(r.name.lastIndexOf('.') + 1);
                                    if (r.name.contains("InputConstants$Type.")) input = r.name.substring(r.name.lastIndexOf('.') + 1);
                                }
                            }
                            rows.add("{\"id\":" + json(id) + ",\"code\":" + json(code) + ",\"modifier\":" + json(modifier) +
                                ",\"context\":" + json(context) + ",\"input\":" + json(input) + ",\"category\":" + json(category) +
                                ",\"origin\":" + json(origin) + ",\"method\":" + json(className + "." + name) + "}");
                        }
                        if (Type.getReturnType(desc).getSort() != Type.VOID) {
                            if (owner.equals("com/mojang/blaze3d/platform/InputConstants$Type") && method.equals("getOrCreate") &&
                                values.length == 1 && values[0] instanceof Integer code && receiver instanceof Ref r)
                                push(new Key(code, r.name.substring(r.name.lastIndexOf('.') + 1)));
                            // Reviewed TranslationHelper contract for the pinned backpack release.
                            // A different release remains unresolved and the reserved-key guard fails.
                            else if (origin.equals("sophisticatedbackpacks-1.21.1-3.26.20.2244.jar") &&
                                owner.equals("net/p3pp3rf1y/sophisticatedbackpacks/client/gui/SBPTranslationHelper") &&
                                method.equals("translKeybind") && values.length == 1 && values[0] instanceof String suffix)
                                push("key.sophisticatedbackpacks." + suffix);
                            else push(UNKNOWN);
                        }
                    }
                    public void visitInvokeDynamicInsn(String n, String d, Handle b, Object... args) {
                        for (Type ignored : Type.getArgumentTypes(d)) pop();
                        if (Type.getReturnType(d).getSort() != Type.VOID) push(UNKNOWN);
                    }
                };
            }
        }, ClassReader.SKIP_DEBUG | ClassReader.SKIP_FRAMES);
    }
    static void nested(byte[] bytes, String origin, int depth) throws IOException {
        if (depth > 3) throw new IOException("Nested archive limit: " + origin);
        try (var zip = new ZipInputStream(new ByteArrayInputStream(bytes))) {
            ZipEntry e;
            while ((e = zip.getNextEntry()) != null) {
                if (!e.getName().endsWith(".class") && !e.getName().endsWith(".jar")) continue;
                byte[] data = zip.readNBytes(32 * 1024 * 1024 + 1);
                if (data.length > 32 * 1024 * 1024) throw new IOException("Entry too large: " + origin);
                if (e.getName().endsWith(".class")) inspect(data, origin);
                else nested(data, origin + "!/" + e.getName(), depth + 1);
            }
        }
    }
    public static void main(String[] args) throws Exception {
        try (var files = Files.list(Path.of(args[0]))) {
            for (Path path : files.filter(p -> p.toString().endsWith(".jar")).sorted().toList()) {
                try (var zip = new ZipFile(path.toFile())) {
                    var entries = zip.entries();
                    while (entries.hasMoreElements()) {
                        ZipEntry e = entries.nextElement();
                        if (!e.getName().endsWith(".class") && !e.getName().endsWith(".jar")) continue;
                        try (var input = zip.getInputStream(e)) {
                            byte[] data = input.readNBytes(32 * 1024 * 1024 + 1);
                            if (data.length > 32 * 1024 * 1024) throw new IOException("Entry too large: " + e.getName());
                            if (e.getName().endsWith(".class")) inspect(data, path.getFileName().toString());
                            else nested(data, path.getFileName() + "!/" + e.getName(), 1);
                        }
                    }
                }
            }
        }
        System.out.println("[" + String.join(",\n", rows) + "]");
    }
}
