from __future__ import annotations

import subprocess

BLOCKED = [
    "mkfs",
    "dd if=",
    ":(){:|:&};:",
    "shutdown",
    "reboot",
    "halt",
    ">:",
    "format ",
    "diskpart",
    "bcdedit",
    "vssadmin delete",
    "cipher /w",
    "del /s",
    "rd /s",
    "rmdir /s",
    "remove-item -recurse",
    "clear-disk",
    "remove-partition",
    "restart-computer",
    "stop-computer",
    "set-executionpolicy",
    "reg delete",
    "sc delete",
]

UNSAFE_PREFIXES = (
    "del ",
    "erase ",
    "rd ",
    "rmdir ",
    "move ",
    "ren ",
    "rename ",
    "icacls ",
    "takeown ",
    "attrib ",
    "runas ",
    "remove-item",
    "move-item",
    "rename-item",
    "set-acl",
)


def shell_refusal(command: str) -> str | None:
    if not command or not command.strip():
        return "Komut belirtilmedi."
    lowered = command.lower()
    stripped = command.strip().lower()
    if stripped.startswith(UNSAFE_PREFIXES):
        return (
            "Guvenlik: Dosya veya yetki degistiren komutlar dogrudan calistirilmiyor. "
            "Daha guvenli ve dar kapsamli bir komut dene."
        )
    for blocked in BLOCKED:
        if blocked in lowered:
            return f"Guvenlik: Bu komut engellendi → {blocked.strip()}"
    return None


def shell_run(command: str, timeout: int = 30) -> str:
    refusal = shell_refusal(command)
    if refusal:
        return refusal
    wrapped = "[Console]::OutputEncoding = [Text.Encoding]::UTF8; " + command
    try:
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                wrapped,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired:
        return f"Komut zaman asimina ugradi ({timeout}s)."
    except OSError as exc:
        return f"Hata: {exc}"
    output = ((result.stdout or "") + (result.stderr or "")).strip()
    if result.returncode not in (0, None) and not output:
        return f"Komut hata kodu {result.returncode} ile bitti."
    if not output:
        return "Komut basariyla calisti (cikti yok)."
    if len(output) > 800:
        output = output[:800] + "\n... (cikti kisaltildi)"
    return output
