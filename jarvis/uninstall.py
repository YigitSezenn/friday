"""FRIDAY kaldırma. Yalnız adı FRIDAY olan klasörler. Dosya içeriği okunmaz ve yazılmaz."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_ALLOWED_PARENTS = frozenset({"local", "roaming"})


def friday_data_dirs(local_appdata: Path, roaming_appdata: Path) -> tuple[Path, ...]:
    folders = []
    for root in (Path(local_appdata), Path(roaming_appdata)):
        folder = root / "FRIDAY"
        if _is_friday_dir(folder):
            folders.append(folder)
    return tuple(folders)


def _is_friday_dir(folder: Path) -> bool:
    folder = Path(folder)
    return folder.name.casefold() == "friday" and folder.parent.name.casefold() in _ALLOWED_PARENTS


def delete_friday_dir(folder: Path) -> bool:
    """Klasörün adı FRIDAY ve üstü Local ya da Roaming ise siler. İçeriği yazdırmaz."""
    folder = Path(folder)
    if not _is_friday_dir(folder) or not folder.is_dir():
        return False
    if folder.is_symlink() or os.path.isjunction(folder):
        return False
    import shutil

    shutil.rmtree(folder)
    return True


def delete_friday_dirs(folders: list[Path]) -> list[str]:
    removed = []
    for folder in folders:
        if delete_friday_dir(folder):
            removed.append(str(folder))
    return removed


def uninstaller_candidate(executable: Path, frozen: bool) -> Path | None:
    if not frozen:
        return None
    path = Path(executable).resolve().parent / "unins000.exe"
    if path.name.casefold() != "unins000.exe" or path.parent.name.casefold() != "friday":
        return None
    if not path.is_file():
        return None
    return path


def launch_uninstaller(path: Path | None, popen=subprocess.Popen) -> bool:
    if path is None:
        return False
    target = Path(path)
    if target.name.casefold() != "unins000.exe" or target.parent.name.casefold() != "friday":
        return False
    if not target.is_file():
        return False
    flags = {}
    if os.name == "nt":
        flags["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    popen([str(target), "/SILENT"], close_fds=True, **flags)
    return True


def installed_uninstaller() -> Path | None:
    return uninstaller_candidate(Path(sys.executable), bool(getattr(sys, "frozen", False)))
