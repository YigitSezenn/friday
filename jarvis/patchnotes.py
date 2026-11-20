"""Yenilikler (patch notes). Tek kaynak: site/public/indir/yenilikler.json.

Uygulamanın içine de konur; sitedeki kopya daha yeni sürümleri de taşıyabilir.
"""

from __future__ import annotations

import json

from jarvis.paths import PROJECT_ROOT, resource_path
from jarvis.updater import SITE, version_parts

NOTES_URL = f"{SITE}/indir/yenilikler.json"


def parse(raw: str) -> list[dict]:
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return []
    items = data.get("surumler") if isinstance(data, dict) else None
    entries: list[dict] = []
    for item in items or []:
        if not isinstance(item, dict) or not version_parts(item.get("surum", "")):
            continue
        entries.append(
            {
                "surum": str(item["surum"]).strip(),
                "tarih": str(item.get("tarih", ""))[:10],
                "baslik": str(item.get("baslik", ""))[:80],
                "maddeler": [str(line)[:200] for line in (item.get("maddeler") or [])[:12] if str(line).strip()],
            }
        )
    return entries


def merge(*lists: list[dict]) -> list[dict]:
    """Aynı sürüm varsa önce gelen liste kazanır; sonuç yeniden eskiye sıralanır."""
    seen: dict[tuple[int, ...], dict] = {}
    for entries in lists:
        for entry in entries:
            seen.setdefault(version_parts(entry["surum"]), entry)
    return [seen[key] for key in sorted(seen, reverse=True)]


def load_local() -> list[dict]:
    for path in (resource_path("yenilikler.json"), PROJECT_ROOT / "site" / "public" / "indir" / "yenilikler.json"):
        try:
            return parse(path.read_text(encoding="utf-8"))
        except OSError:
            continue
    return []


def fetch_remote(timeout: float = 8.0) -> list[dict]:
    import urllib.request

    request = urllib.request.Request(NOTES_URL, headers={"User-Agent": "FRIDAY"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return parse(response.read(200_000).decode("utf-8", errors="replace"))
