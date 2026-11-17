"""Tactical Blue V2: generate four wearable 3D equipment atlases from cuboid geometry.
The compressed geometry is an artist-authored, original Minecraft-compatible model.
No external Python packages needed. Code and textures are not derived from SBW images.
"""
from pathlib import Path
import base64
import json
import math
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "src/main/resources/assets/techquest_hybrid"
ATLAS = 256
NAMES = {
    "helmet": "mek_ru_helmet_6b47",
    "chest": "mek_ru_chest_6b43",
    "leggings": "mek_ru_leggings",
    "boots": "mek_ru_boots",
}
COLORS = {
    "shell": (32, 39, 55), "fabric": (25, 31, 42), "navy": (46, 59, 81),
    "ceramic": (58, 72, 95), "ceramic_light": (87, 101, 124),
    "edge": (17, 23, 33), "plate": (73, 86, 108), "rubber": (24, 29, 39),
    "webbing": (54, 60, 69), "pouch": (57, 66, 79), "buckle": (123, 134, 146),
    "steel": (116, 132, 153), "blue": (15, 117, 246),
    "bright": (53, 195, 255), "ice": (168, 234, 255),
    "glass": (22, 73, 128),
}

def geometry():
    source = (Path(__file__).with_name("tactical_blue_v2.b85")).read_text()
    data = "".join(s.strip() for s in source.splitlines() if not s.startswith("#"))
    result = json.loads(zlib.decompress(base64.b85decode(data)).decode("utf-8"))
    assert set(result) == set(NAMES), "Missing armor slot in geometry"
    return result

def pack(parts):
    x, y, row = 70, 1, 0
    result = []
    for bone, name, material, px, py, pz, sx, sy, sz in parts:
        width = math.ceil(2 * (sx + sz)) + 2
        height = math.ceil(sy + sz) + 2
        if x + width > ATLAS:
            x, y, row = 70, y + row + 2, 0
        if y + height > ATLAS:
            raise ValueError("3D model UV atlas full: " + name)
        result.append((bone, name, material, px, py, pz, sx, sy, sz, x + 1, y + 1))
        x += width + 1
        row = max(row, height)
    return result

def paint_face(image, u, v, w, h, material, index, face):
    col = COLORS[material]
    if w < 1 or h < 1:
        return
    lighting = {"top": 8, "bottom": -9, "front": 3, "back": -8,
                "left": -3, "right": 2}[face]
    for yy in range(h):
        for xx in range(w):
            jitter = int((((xx * 19 + yy * 13 + index * 23) % 17) - 8) * 0.75)
            edge = xx == 0 or yy == 0 or xx == w - 1 or yy == h - 1
            shade = jitter + lighting - (11 if edge else 0)
            if material in ("fabric", "webbing", "rubber") and (xx + 2*yy + index) % 5 == 0:
                shade -= 6
            if material in ("ceramic", "plate", "navy") and (xx + yy//2 + index) % 13 == 0:
                shade += 10
            if material in ("blue", "bright", "ice"):
                shade = (10 if (xx + yy) % 4 < 2 else -4) + lighting - (17 if edge else 0)
            rgb = tuple(max(0, min(255, value + shade)) for value in col)
            image[(v + yy)*ATLAS + (u + xx)] = (*rgb, 255)
    if material in ("ceramic", "plate", "steel", "navy") and w > 4 and h > 4 and face == "front":
        for rx in (1, w - 2):
            image[(v + 1)*ATLAS + (u + rx)] = (*COLORS["buckle"], 255)
        for xx in range(2, w - 2):
            if xx % 3 != 0:
                image[(v + h - 2)*ATLAS + u + xx] = (*COLORS["edge"], 255)
    if material == "pouch" and w >= 4 and h >= 4 and face == "front":
        for xx in range(1, w - 1):
            image[(v + 1)*ATLAS + u + xx] = (*COLORS["webbing"], 255)

def atlas(parts):
    image = [(*COLORS["edge"], 255)] * (ATLAS * ATLAS)
    for y in range(64):
        for x in range(64):
            rgb = COLORS["fabric"] if (x+y) % 13 < 8 else COLORS["shell"]
            shift = ((x*7 + y*11) % 9) - 4
            image[y*ATLAS + x] = (*tuple(max(0, min(255, k+shift)) for k in rgb), 255)
    used = set()
    for i, (_, name, material, x, y, z, sx, sy, sz, u, v) in enumerate(parts):
        w, h, d = math.ceil(sx), math.ceil(sy), math.ceil(sz)
        faces = [
            ("top", u+d, v, w, d),
            ("bottom", u+d+w, v, w, d),
            ("left", u, v+d, d, h),
            ("front", u+d, v+d, w, h),
            ("right", u+d+w, v+d, d, h),
            ("back", u+2*d+w, v+d, w, h),
        ]
        for face, fx, fy, fw, fh in faces:
            for py in range(fy, fy+fh):
                for px in range(fx, fx+fw):
                    if (px, py) in used:
                        raise ValueError("UV overlap: " + name)
                    if px >= ATLAS or py >= ATLAS:
                        raise ValueError("UV out of bounds: " + name)
                    used.add((px, py))
            paint_face(image, fx, fy, fw, fh, material, i, face)
    return image

def png(path, image):
    pixels = b"".join(
        b"\\0" + b"".join(bytes(image[y*ATLAS + x]) for x in range(ATLAS))
        for y in range(ATLAS)
    )
    def chunk(tag, body):
        return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag+body) & 0xFFFFFFFF)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        b"\\x89PNG\\r\\n\\x1a\\n" +
        chunk(b"IHDR", struct.pack(">2I5B", ATLAS, ATLAS, 8, 6, 0, 0, 0)) +
        chunk(b"IDAT", zlib.compress(pixels, 9)) + chunk(b"IEND", b"")
    )

def generate():
    counts = {}
    for slot, model in geometry().items():
        parts = pack(model)
        item = NAMES[slot]
        lines = []
        for bone, name, mat, x, y, z, w, h, d, u, v in parts:
            lines.append(f"{bone} {name} {u} {v} {x:g} {y:g} {z:g} {w:g} {h:g} {d:g}")
        model_path = ASSET / "models/armor" / (item + ".cuboids")
        model_path.parent.mkdir(parents=True, exist_ok=True)
        model_path.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
        png(ASSET / "textures/models/armor" / (item + "_3d.png"), atlas(parts))
        counts[item] = len(parts)
    return counts

if __name__ == "__main__":
    print("Generated Tactical Blue V2 wearable armor:", generate())
