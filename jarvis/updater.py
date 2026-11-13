"""Sitedeki sürüm yeni ise kurulum uygulama içinden açılır. Adres ve sürüm yazılır, anahtar yazılmaz."""

from __future__ import annotations

SITE = "https://site-seven-bay-75.vercel.app"
VERSION_URL = f"{SITE}/indir/surum.txt"
INSTALLER_URL = f"{SITE}/indir/FRIDAY-Kurulum.exe"


def version_parts(value: str) -> tuple[int, ...]:
    parts: list[int] = []
    for bit in str(value or "").replace("-", ".").split("."):
        if bit.isdigit():
            parts.append(int(bit))
        elif parts:
            break
    return tuple(parts)


def is_newer(remote: str, local: str) -> bool:
    return version_parts(remote) > version_parts(local)


def available_update(local: str) -> str:
    import urllib.request

    with urllib.request.urlopen(VERSION_URL, timeout=8) as response:
        remote = response.read().decode("utf-8", errors="replace").strip()
    return remote if is_newer(remote, local) else ""


def download_installer(dest) -> None:
    import urllib.request

    request = urllib.request.Request(INSTALLER_URL, headers={"User-Agent": "FRIDAY"})
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read()
    if len(payload) < 1_000_000 or not payload.startswith(b"MZ"):
        raise RuntimeError("kurulum dosyasi olmadi")
    with open(dest, "wb") as handle:
        handle.write(payload)
