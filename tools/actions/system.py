from __future__ import annotations

import datetime
import socket
import subprocess


def sys_info(query: str) -> str:
    query = (query or "").lower().strip()
    results = []
    if query in ("battery", "pil", "all"):
        results.append(_battery())
    if query in ("cpu", "işlemci", "islemci", "all"):
        results.append(_cpu())
    if query in ("ram", "bellek", "memory", "all"):
        results.append(_ram())
    if query in ("disk", "depolama", "all"):
        results.append(_disk())
    if query in ("time", "saat", "zaman", "all"):
        now = datetime.datetime.now()
        results.append(f"Saat: {now.strftime('%H:%M:%S')}")
    if query in ("date", "tarih", "all"):
        now = datetime.datetime.now()
        results.append(f"Tarih: {now.strftime('%d %B %Y, %A')}")
    if query in ("network", "ağ", "ag", "wifi", "all"):
        results.append(_network())
    if not results:
        return "Bilinmeyen sorgu: " + query + ". battery/cpu/ram/disk/time/date/network/all kullanin."
    return "\n".join(results)


def _psutil():
    import psutil

    return psutil


def _battery() -> str:
    try:
        bat = _psutil().sensors_battery()
    except Exception:
        bat = None
    if bat:
        status = "Sarj oluyor" if bat.power_plugged else "Pilde"
        extra = ""
        if not bat.power_plugged and bat.secsleft and bat.secsleft > 0:
            hours, remainder = divmod(int(bat.secsleft), 3600)
            extra = f", ~{hours}s {remainder // 60}dk kaldi"
        return f"Pil: %{bat.percent:.0f} — {status}{extra}"
    return "Pil bulunamadi (masaustu bilgisayar olabilir)."


def _cpu() -> str:
    psutil = _psutil()
    usage = psutil.cpu_percent(interval=0.2)
    count = psutil.cpu_count(logical=True)
    return f"CPU: %{usage:.1f} kullanim — {count} cekirdek"


def _ram() -> str:
    vm = _psutil().virtual_memory()
    return (
        f"RAM: {vm.used / (1024 ** 3):.1f}GB / {vm.total / (1024 ** 3):.1f}GB "
        f"kullanimda (%{vm.percent:.0f})"
    )


def _disk() -> str:
    du = _psutil().disk_usage("C:\\")
    return (
        f"Disk (C:): {du.used / (1024 ** 3):.1f}GB kullanildi, "
        f"{du.free / (1024 ** 3):.1f}GB bos (toplam {du.total / (1024 ** 3):.1f}GB)"
    )


def _network() -> str:
    ip = _local_ip()
    try:
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "(Get-NetConnectionProfile | Select-Object -First 1).Name",
            ],
            capture_output=True,
            text=True,
            timeout=8,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        name = (result.stdout or "").strip().splitlines()
        if name and name[0]:
            suffix = f" — IP {ip}" if ip else ""
            return f"Ag: {name[0]} bagli{suffix}"
    except (OSError, subprocess.TimeoutExpired):
        pass
    if ip:
        return f"Ag: IP {ip}"
    return "Ag baglantisi bulunamadi."


def _local_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.4)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except OSError:
        return ""
