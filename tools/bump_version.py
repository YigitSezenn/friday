"""Sürüm numarasını tüm dosyalarda günceller (release.ps1'in sürüm adımının platformdan bağımsız hali).

Kullanım: python tools/bump_version.py 4.10.3
surum.txt'ye DOKUNMAZ: güncelleyici onu görünce indirme başlatır; yalnızca yayın hattı en son yazar.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def version_code(version: str) -> int:
    parts = [int(p) for p in version.split(".")] + [0, 0]
    return parts[0] * 10000 + parts[1] * 100 + parts[2]


def _rewrite(path: Path, edits, bom: bool = False) -> None:
    text = path.read_bytes().decode("utf-8-sig")
    for pattern, repl in edits:
        new = re.sub(pattern, repl, text)
        if new == text and not re.search(pattern, text):
            raise SystemExit(f"{path}: kalıp bulunamadı: {pattern}")
        text = new
    path.write_bytes((b"\xef\xbb\xbf" if bom else b"") + text.encode("utf-8"))


def bump(version: str, root: Path = ROOT) -> None:
    if not re.fullmatch(r"\d+\.\d+(\.\d+)?", version):
        raise SystemExit("Sürüm N.M ya da N.M.P olmalı")
    _rewrite(root / "jarvis" / "__init__.py", [(r'__version__\s*=\s*"[^"]+"', f'__version__ = "{version}"')])
    # Inno Setup UTF-8'i yalnızca BOM ile okur.
    _rewrite(root / "packaging" / "friday.iss", [(r"AppVersion=[\d.]+", f"AppVersion={version}")], bom=True)
    _rewrite(root / "phone-android" / "app" / "build.gradle.kts", [
        (r'versionName\s*=\s*"[^"]+"', f'versionName = "{version}"'),
        (r"versionCode\s*=\s*\d+", f"versionCode = {version_code(version)}"),
    ])
    _rewrite(root / "site" / "index.html", [
        (r"\?v=\d+\.\d+(?:\.\d+)?", f"?v={version}"),
        (r"Sürüm \d+\.\d+(?:\.\d+)?", f"Sürüm {version}"),
    ])


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    bump(sys.argv[1])
    print(f"sürüm {sys.argv[1]} (versionCode {version_code(sys.argv[1])})")
