"""Targeted Modern Industrialization book-on-respawn migration.

Only modern_industrialization-server.toml is touched, only the single
respawnWithGuideBook key is changed, and original bytes are backed up once.
Minecraft must be closed during any configuration migration.
"""
from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

MI_FILE = "modern_industrialization-server.toml"
MI_BACKUP = MI_FILE + ".techquest-original.bak"
_RESPAWN = re.compile(
    rb"(?m)^([ \t]*respawnWithGuideBook[ \t]*=[ \t]*)(true|false)([ \t]*(?:\#[^\r\n]*)?\r?)$",
    re.IGNORECASE,
)


def patch_mi_guide_config(path: Path) -> bool:
    """Turn off respawn guide in an existing file, preserving its other bytes.

    Return True only when an existing file was changed. Do not create a server
    config in a world where the mod has not generated it yet.
    """
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        return False
    original = path.read_bytes()
    if b"\x00" in original:
        return False
    match = _RESPAWN.search(original)
    if match:
        if match.group(2).lower() == b"false":
            return False
        updated = original[:match.start(2)] + b"false" + original[match.end(2):]
    else:
        # A config from an older MI version may not yet contain this option.
        # Insert it at TOML root (before any [section]), never inside recipes.
        if b"respawnWithGuideBook" in original:
            return False  # unexpected syntax; never overwrite a dubious config
        bom = b"\xef\xbb\xbf" if original.startswith(b"\xef\xbb\xbf") else b""
        body = original[len(bom):]
        updated = bom + b"respawnWithGuideBook = false\n" + body
    backup = path.with_name(MI_BACKUP)
    if backup.exists() and (backup.is_symlink() or not backup.is_file()):
        raise OSError("Unsafe MI guide backup path: " + str(backup))
    if not backup.exists():
        backup.write_bytes(original)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".techquest-mi-guide-", delete=False) as out:
        staged = Path(out.name)
        out.write(updated)
    try:
        os.replace(staged, path)
    finally:
        staged.unlink(missing_ok=True)
    return True


def patch_existing_mi_worlds(root: Path, *, dedicated_server: bool = False) -> list[Path]:
    """Apply the one-key change to existing MI server configs only.

    Only immediate singleplayer saves or the configured dedicated server world
    are inspected. Symlinked files/directories and traversal are excluded.
    """
    root = Path(root).resolve()
    candidates = [root / "config" / MI_FILE]  # legacy/server-root MI configs
    if dedicated_server:
        world_name = "world"
        properties = root / "server.properties"
        if properties.is_file() and not properties.is_symlink():
            for line in properties.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("level-name="):
                    name = line.partition("=")[2].strip()
                    if name and name not in (".", "..") and "/" not in name and "\\" not in name:
                        world_name = name
                    break
        candidates.append(root / world_name / "serverconfig" / MI_FILE)
    else:
        saves = root / "saves"
        if saves.is_dir() and not saves.is_symlink():
            candidates.extend(
                save / "serverconfig" / MI_FILE
                for save in saves.iterdir()
                if save.is_dir() and not save.is_symlink()
            )
    changed = []
    for path in candidates:
        if patch_mi_guide_config(path):
            changed.append(path)
    return changed
