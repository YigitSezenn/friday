from __future__ import annotations

import os
import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent


def frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_root() -> Path:
    if frozen():
        return Path(sys.executable).resolve().parent
    return PROJECT_ROOT


def data_root() -> Path:
    override = os.environ.get("JARVIS_DATA_DIR", "").strip()
    root = Path(override) if override else app_root() / "data"
    root.mkdir(parents=True, exist_ok=True)
    return root


def data_path(*parts: str) -> Path:
    path = data_root().joinpath(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def resource_path(*parts: str) -> Path:
    if frozen():
        return Path(getattr(sys, "_MEIPASS")) / "jarvis" / Path(*parts)
    return PACKAGE_ROOT.joinpath(*parts)
