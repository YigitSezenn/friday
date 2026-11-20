"""Dosya erişimi: yalnızca kullanıcının izin verdiği klasörlerde, kapalı gelir.

Okuma/arama serbest; yazma, taşıma ve silme onay ister. Silme kalıcı değildir:
dosya FRIDAY çöp klasörüne taşınır, geri alınabilir.
"""
from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

from tools.actions import confirm

MAX_READ = 20000
MAX_LIST = 60
TEXT_SUFFIXES = {".txt", ".md", ".csv", ".json", ".log", ".py", ".js", ".html", ".css", ".ini", ".yaml", ".yml", ".xml", ".srt", ".tex"}


def enabled() -> bool:
    from jarvis.config import load_app_config

    return bool(load_app_config().get("file_access", False))


def roots() -> list[Path]:
    from jarvis.config import load_app_config

    home = Path.home()
    chosen = load_app_config().get("file_roots") or []
    paths = [Path(str(p)).expanduser() for p in chosen if str(p).strip()]
    if not paths:
        paths = [home / "Documents", home / "Downloads", home / "Desktop", home / "Belgelerim", home / "İndirilenler"]
    return [p.resolve() for p in paths if p.exists()]


def trash_dir() -> Path:
    from jarvis.paths import data_root

    folder = Path(data_root()) / "cop"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def resolve(path: str) -> tuple[Path | None, str]:
    """İzinli klasör içindeki gerçek yolu döndürür; değilse nedenini."""
    raw = (path or "").strip().strip('"')
    if not raw:
        return None, "Dosya yolu belirtilmedi."
    allowed = roots()
    if not allowed:
        return None, "İzinli klasör bulunamadı. Ayarlar › İzinler'den klasör seçilebilir."
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = allowed[0] / candidate
    try:
        real = candidate.resolve()
    except OSError:
        return None, "Yol çözülemedi."
    for base in allowed:
        if real == base or base in real.parents:
            return real, ""
    names = ", ".join(p.name for p in allowed)
    return None, f"Bu klasöre erişim iznim yok. İzinli klasörler: {names}."


def _size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n} B"


def _list(target: Path) -> str:
    if not target.is_dir():
        return "Bu bir klasör değil."
    entries = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    lines = []
    for item in entries[:MAX_LIST]:
        if item.is_dir():
            lines.append(f"📁 {item.name}")
        else:
            lines.append(f"{item.name} ({_size(item.stat().st_size)})")
    more = f"\n… ve {len(entries) - MAX_LIST} öğe daha" if len(entries) > MAX_LIST else ""
    return f"{target.name}: {len(entries)} öğe\n" + "\n".join(lines) + more


def _find(target: Path, query: str) -> str:
    needle = (query or "").strip().lower()
    if not needle:
        return "Aranacak ad belirtilmedi."
    hits: list[Path] = []
    scanned = 0
    for base in ([target] if target.is_dir() else roots()):
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if not d.startswith(".") and d.lower() not in {"node_modules", "__pycache__"}]
            for name in dirnames + filenames:
                scanned += 1
                if needle in name.lower():
                    hits.append(Path(dirpath) / name)
            if len(hits) >= MAX_LIST or scanned > 60000:
                break
    if not hits:
        return f"“{query}” ile eşleşen dosya bulunamadı."
    return f"{len(hits)} sonuç:\n" + "\n".join(str(h) for h in hits[:MAX_LIST])


def _read(target: Path) -> str:
    if not target.is_file():
        return "Dosya bulunamadı."
    if target.suffix.lower() not in TEXT_SUFFIXES:
        return f"{target.name} metin dosyası değil ({_size(target.stat().st_size)}). Açmak için open_app kullanılabilir."
    data = target.read_text(encoding="utf-8", errors="replace")
    cut = "\n… (kısaltıldı)" if len(data) > MAX_READ else ""
    return data[:MAX_READ] + cut


def _confirm(kind: str, parts: tuple, summary: str, confirmed: bool) -> str:
    if not confirmed:
        return confirm.ask(kind, parts, summary)
    return confirm.check(kind, parts)


def run(action: str, path: str = "", destination: str = "", content: str = "", query: str = "", confirmed: bool = False) -> str:
    if not enabled():
        return "Dosya erişimi kapalı. Ayarlar › İzinler'den “Dosya erişimi” anahtarını açman gerekiyor."
    action = (action or "").strip().lower()
    if action == "find" and not path:
        return _find(roots()[0] if roots() else Path.home(), query)
    target, why = resolve(path)
    if target is None:
        return why
    try:
        if action == "list":
            return _list(target)
        if action == "find":
            return _find(target, query)
        if action == "read":
            return _read(target)
        if action == "write":
            if not content:
                return "Yazılacak içerik belirtilmedi."
            exists = target.exists()
            gate = _confirm("file_write", (str(target), content), f"Dosya işlemi: {'üzerine yazılacak' if exists else 'oluşturulacak'} — {target}", confirmed)
            if gate:
                return gate
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return f"{target.name} {'güncellendi' if exists else 'oluşturuldu'}."
        if action == "move":
            dest, why = resolve(destination)
            if dest is None:
                return why
            if not target.exists():
                return "Taşınacak dosya bulunamadı."
            if dest.is_dir():
                dest = dest / target.name
            gate = _confirm("file_move", (str(target), str(dest)), f"Dosya işlemi: taşınacak — {target} → {dest}", confirmed)
            if gate:
                return gate
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(target), str(dest))
            return f"{target.name} taşındı: {dest}"
        if action == "delete":
            if not target.exists():
                return "Silinecek dosya bulunamadı."
            if target in roots():
                return "İzinli klasörün kendisi silinemez."
            gate = _confirm("file_delete", (str(target),), f"Dosya işlemi: çöpe taşınacak — {target}", confirmed)
            if gate:
                return gate
            stamp = time.strftime("%Y%m%d-%H%M%S")
            bin_path = trash_dir() / f"{stamp}-{target.name}"
            shutil.move(str(target), str(bin_path))
            return f"{target.name} çöpe taşındı (kalıcı silinmedi, FRIDAY klasöründeki “cop” içinde duruyor)."
    except PermissionError:
        return "Windows bu dosyaya erişimi engelledi."
    except OSError as exc:
        return f"Dosya işlemi yapılamadı: {exc}"
    return f"Bilinmeyen eylem: {action}. Kullanılabilir: list, find, read, write, move, delete."
