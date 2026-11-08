#!/usr/bin/env python3
"""CI-only SDL3 check for an excluded research candidate. No game/device/flight test."""
import ctypes
import hashlib
import io
import json
import os
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    if os.name != "nt" or os.environ.get("GITHUB_ACTIONS") != "true":
        raise SystemExit("This native-library smoke test requires an isolated Windows Actions runner")
    snapshot = json.loads((ROOT / "compat/client-controls/controller-research.json").read_text())
    mod = next(m for m in snapshot["mods"] if m["project"] == "controlify")
    file = mod["file"]
    with urllib.request.urlopen(file["url"], timeout=60) as response:
        data = response.read(file["size"] + 1)
    if len(data) != file["size"]:
        raise ValueError("Controlify size mismatch")
    for algorithm, expected in file["hashes"].items():
        if hashlib.new(algorithm, data).hexdigest() != expected:
            raise ValueError("Controlify " + algorithm + " mismatch")
    with tempfile.TemporaryDirectory(prefix="TechQuest-SDL3-smoke-") as tmp:
        dll = Path(tmp) / "SDL3.dll"
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            dll.write_bytes(archive.read("win32-x86-64/SDL3.dll"))
        sdl = ctypes.CDLL(str(dll))
        initialized = False
        try:
            sdl.SDL_GetVersion.restype = ctypes.c_int
            version = sdl.SDL_GetVersion()
            if version // 1_000_000 != 3:
                raise ValueError("Unexpected SDL major version")
            sdl.SDL_Init.argtypes = [ctypes.c_uint32]
            sdl.SDL_Init.restype = ctypes.c_bool
            sdl.SDL_GetError.restype = ctypes.c_char_p
            if not sdl.SDL_Init(0x00002000):  # SDL_INIT_GAMEPAD, including joystick/events
                raise RuntimeError("SDL3 initialization failed: " + sdl.SDL_GetError().decode())
            initialized = True
            sdl.SDL_GetGamepads.argtypes = [ctypes.POINTER(ctypes.c_int)]
            sdl.SDL_GetGamepads.restype = ctypes.POINTER(ctypes.c_uint32)
            count = ctypes.c_int()
            devices = sdl.SDL_GetGamepads(ctypes.byref(count))
            if devices:
                sdl.SDL_free.argtypes = [ctypes.c_void_p]
                sdl.SDL_free(devices)
            print("PASS: research candidate Windows x64 SDL3 loaded; version", version,
                  "; gamepad subsystem initialized; runner device count", count.value)
            print("No Minecraft, physical Xbox controller, joystick axes or flight integration was tested.")
        finally:
            if initialized:
                sdl.SDL_Quit()
            # ctypes keeps loaded DLLs open; release before TemporaryDirectory cleanup.
            import _ctypes
            _ctypes.FreeLibrary(sdl._handle)


if __name__ == "__main__":
    main()
