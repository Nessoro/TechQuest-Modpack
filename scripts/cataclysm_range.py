"""Safe one-time migration of Cataclysm *default* boss damage ranges.

Do not change custom ranges, damage/DPS caps, phases, unrelated keys or symlinks.
A one-time backup sits beside the original TOML, never overwritten by updates.
"""
from __future__ import annotations

import os
import re
import shutil
import tempfile
from pathlib import Path

ORIGINAL_BOSS_RANGES = {
    "mobs.ender_golem.cap_config": 8.0,
    "mobs.ender_guardian.cap_config": 12.0,
    "mobs.netherite_monstrosity.cap_config": 18.0,
    "mobs.ignis.cap_config": 15.0,
    "mobs.harbinger.cap_config": 35.0,
    "mobs.leviathan.cap_config": 38.0,
    "mobs.ancient_remnant.cap_config": 14.0,
    "mobs.scylla.cap_config": 12.0,
    "mobs.clawdian.cap_config": 12.0,
    "mobs.maledictus.cap_config": 14.0,
    "mobs.prowler": 15.0,
}

RANGE_LINE = re.compile(
    r"^(?P<prefix>[ \t]*range_cap[ \t]*=[ \t]*)(?P<value>[0-9]+(?:\.[0-9]+)?)(?P<tail>[ \t]*(?:#[^\r\n]*)?)(?P<eol>\r?\n?)$"
)


def upgrade_default_ranges(text: str) -> str:
    section = ""
    updated = []
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1]
        match = RANGE_LINE.fullmatch(line)
        if match and section in ORIGINAL_BOSS_RANGES:
            if float(match["value"]) == ORIGINAL_BOSS_RANGES[section]:
                line = match["prefix"] + "256.0" + match["tail"] + match["eol"]
        updated.append(line)
    return "".join(updated)


def migrate_default_boss_ranges(path: Path) -> bool:
    path = Path(path)
    backup = path.with_name(path.name + ".techquest-before-0334.bak")
    if not path.is_file() or path.is_symlink() or backup.exists():
        return False
    original = path.read_bytes()
    text = original.decode("utf-8-sig")
    upgraded = upgrade_default_ranges(text)
    if upgraded == text:
        return False
    # Retain the original byte-for-byte with the exact pre-migration file metadata.
    shutil.copy2(path, backup)
    fd, tmp = tempfile.mkstemp(prefix=".techquest-range-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(upgraded.encode("utf-8"))
        shutil.copymode(path, tmp)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return True
