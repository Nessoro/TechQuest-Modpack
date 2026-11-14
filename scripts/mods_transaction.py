"""Stage and atomically activate verified mod JARs with one rolling backup."""
from pathlib import Path
import shutil

BACKUP = ".techquest-previous-mods"
ROTATION = ".techquest-backup-rotation"

def activate_staged_mods(target: Path, staging: Path, after_activation=None):
    target, staging = Path(target), Path(staging)
    active, backup, rotation = target / "mods", target / BACKUP, target / ROTATION
    if staging.parent.resolve() != target.resolve() or not staging.is_dir():
        raise ValueError("Staged mods must be a directory inside the target profile")
    if rotation.exists():
        raise OSError("Interrupted backup rotation: inspect " + str(rotation))
    if active.exists() and not active.is_dir():
        raise OSError("mods is not a directory")
    if backup.exists() and not backup.is_dir():
        raise OSError("TechQuest backup path is not a directory")
    had_active = active.is_dir() and any(active.iterdir())
    if active.is_dir() and not had_active:
        active.rmdir()
    parked = moved_old = moved_new = False
    try:
        if had_active and backup.exists():
            backup.rename(rotation)
            parked = True
        if had_active:
            active.rename(backup)
            moved_old = True
        staging.rename(active)
        moved_new = True
        if after_activation is not None:
            after_activation()
    except BaseException:
        if moved_new and active.exists():
            active.rename(staging)
        if moved_old:
            backup.rename(active)
        if parked:
            rotation.rename(backup)
        raise
    if parked:
        try:
            shutil.rmtree(rotation)
        except OSError:
            print("WARNING: older backup rotation needs manual inspection:", rotation)
