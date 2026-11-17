"""Generate 256x256 native Minecraft UV atlases for the 6B47/6B43 3D pilot.
The committed Java humanoid geometry is the authoritative source for UV offsets.
No third-party model or texture assets are copied, and only stdlib is required.
"""
from pathlib import Path
import math
import re
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "src/main/java/dev/techquest/hybrid/client/MekMilitaryArmorModel.java"
TEXTURES = ROOT / "src/main/resources/assets/techquest_hybrid/textures/models/armor"
PATTERN = re.compile(
    r'if \((helmet|!helmet)\) add\(mesh, "(\w+)", "(\w+)", (\d+), (\d+), ([^;]+)\);'
)
PALETTE = {
    "shell": (68, 82, 61),
    "ceramic": (79, 90, 82),
    "steel": (104, 115, 113),
    "undersuit": (36, 44, 45),
    "strap": (125, 117, 86),
    "pouch": (86, 84, 65),
    "cyan": (34, 183, 225),
    "bright": (142, 241, 254),
    "glass": (17, 76, 94),
    "dark": (24, 29, 34),
}

def palette_for(name):
    if "glint" in name or "visor_LED" in name:
        return "bright"
    if "eye" in name or "glass" in name:
        return "glass"
    if any(k in name for k in ("diode", "power_core", "battery_light", "radio_led")):
        return "cyan"
    if "pouch" in name and "tab" not in name:
        return "pouch"
    if any(k in name for k in ("strap", "_tab")):
        return "strap"
    if any(k in name for k in ("rail", "battery", "frame", "latch", "center_rib", "vision_module_center")):
        return "steel"
    if any(k in name for k in ("soft_armor", "chin_guard", "power_core_base", "visor_brow", "radio")):
        return "undersuit"
    if any(k in name for k in ("plate", "guard", "collar", "shoulder")):
        return "ceramic"
    return "shell"

def get_cubes():
    cubes = {"helmet": [], "chest": []}
    for condition, bone, name, u, v, values in PATTERN.findall(MODEL.read_text(encoding="utf-8")):
        numbers = [float(s.strip().rstrip("F")) for s in values.split(",")]
        if len(numbers) != 6:
            raise ValueError("Bad cuboid: " + name)
        part = "helmet" if condition == "helmet" else "chest"
        cubes[part].append((bone, name, int(u), int(v), numbers))
    if len(cubes["helmet"]) != 24 or len(cubes["chest"]) != 35:
        raise ValueError("Expected 24 helmet and 35 vest cuboids; got " +
                         str({k: len(v) for k, v in cubes.items()}))
    return cubes

def png(path, pixels, width=256, height=256):
    raw = b"".join(b"\x00" + b"".join(bytes(pixels[y * width + x]) for x in range(width))
                   for y in range(height))
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
    encoded = (b"\x89PNG\r\n\x1a\n" +
               chunk(b"IHDR", struct.pack(">2I5B", width, height, 8, 6, 0, 0, 0)) +
               chunk(b"IDAT", zlib.compress(raw, level=9)) + chunk(b"IEND", b""))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded)

def make_pixels(armor, cubes):
    width = height = 256
    pixels = [(43, 52, 48, 255)] * (width * height)
    def put(x, y, color):
        if 0 <= x < width and 0 <= y < height:
            pixels[y * width + x] = color + (255,)
    # Default Minecraft humanoid head/body UV, beneath the raised armor.
    base = PALETTE["shell" if armor == "helmet" else "undersuit"]
    for y in range(64):
        for x in range(64):
            shade = (x * 13 + y * 7) % 7 - 3
            put(x, y, tuple(max(0, min(255, c + shade)) for c in base))
    occupied = set()
    for _, name, u, v, (_, _, _, dx, dy, dz) in cubes:
        tw, th = math.ceil(2 * (dx + dz)), math.ceil(dy + dz)
        color = PALETTE[palette_for(name)]
        for oy in range(th):
            for ox in range(tw):
                x, y = u + ox, v + oy
                if not 0 <= x < 256 or not 0 <= y < 256:
                    raise ValueError("Texture extends past atlas: " + name)
                if (x, y) in occupied:
                    raise ValueError("Overlapping UV: " + name)
                occupied.add((x, y))
                shade = (ox * 5 + oy * 3 + len(name) * 7) % 11 - 5
                if "cyan" == palette_for(name) or palette_for(name) == "bright":
                    shade = 4 if (ox + oy) % 5 < 3 else -4
                if ox % max(1, int(math.ceil(dx))) == 0 or oy % max(1, int(math.ceil(dy))) == 0:
                    shade -= 3
                put(x, y, tuple(max(0, min(255, c + shade)) for c in color))
    return pixels

def generate():
    cubes = get_cubes()
    for armor, data in cubes.items():
        item = "mek_ru_helmet_6b47" if armor == "helmet" else "mek_ru_chest_6b43"
        png(TEXTURES / (item + "_3d.png"), make_pixels(armor, data))
    return cubes

if __name__ == "__main__":
    parsed = generate()
    print("3D armor atlas generated", {name: len(v) for name, v in parsed.items()})
