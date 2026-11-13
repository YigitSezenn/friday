from __future__ import annotations

from pathlib import Path

FOLDERS = {
    "desktop": "Desktop",
    "masaüstü": "Desktop",
    "masaustu": "Desktop",
    "documents": "Documents",
    "belgeler": "Documents",
    "downloads": "Downloads",
    "indirilenler": "Downloads",
}


def list_user_files(folder: str, root: Path | None = None) -> str:
    base = (root or Path.home()).resolve()
    raw = str(folder or "desktop").strip()
    name = FOLDERS.get(raw.casefold(), raw)
    target = (base / name).resolve()
    if target != base and base not in target.parents:
        return "Bu klasore bakamam."
    if not target.is_dir():
        return "Klasor bulunamadi."
    names = []
    for path in sorted(target.iterdir(), key=lambda item: item.name.lower()):
        if path.name.startswith(".") or path.name.lower() in {"api_keys.json", ".env"}:
            continue
        names.append(path.name + ("/" if path.is_dir() else ""))
        if len(names) >= 30:
            break
    if not names:
        return "Klasor bos."
    return target.name + ":\n" + "\n".join("- " + item for item in names)
