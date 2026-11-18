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
            "Güvenlik: Dosya veya yetki değiştiren komutlar doğrudan çalıştırılmıyor. "
            "Daha güvenli ve dar kapsamlı bir komut dene."
        )
    for blocked in BLOCKED:
        if blocked in lowered:
            return f"Güvenlik: Bu komut engellendi → {blocked.strip()}"
    return None


# Yalnızca okuyan komutlar onaysız çalışır; geri kalanı kullanıcıya sorulur.
READ_ONLY_HEADS = (
    "get-", "test-", "measure-", "select-", "where-", "sort-", "format-", "out-string", "convertto-",
    "write-output", "write-host", "echo", "dir", "ls", "gci", "gc", "cat", "type", "pwd", "whoami",
    "hostname", "ipconfig", "ping", "tracert", "nslookup", "systeminfo", "tasklist", "ver", "date",
    "resolve-dnsname", "findstr", "where.exe", "netstat", "wmic",
)
_SPLIT = ("|", ";", "&&", "||", "\n")


def is_read_only(command: str) -> bool:
    """Her parça okuma komutuyla başlıyorsa ve yönlendirme/alt ifade yoksa True."""
    text = str(command or "").strip().lower()
    if not text:
        return False
    # Yönlendirme, alt ifade, betik çalıştırma ya da tek '&' (çağrı işleci) varsa okuma sayılmaz.
    if any(mark in text for mark in (">", "$(", "`", "@(", "{", "invoke-", "iex", "start-process")):
        return False
    if "&" in text.replace("&&", ""):
        return False
    parts = [text]
    for sep in _SPLIT:
        parts = [piece for part in parts for piece in part.split(sep)]
    for part in parts:
        head = part.strip().split(" ", 1)[0] if part.strip() else ""
        if not head:
            continue
        if not any(head == h or head.startswith(h) for h in READ_ONLY_HEADS):
            return False
        if head == "wmic" and any(word in part for word in (" call ", " delete", " set ", " create")):
            return False
    return True


def shell_run(command: str, timeout: int = 30, confirm_run: bool = False) -> str:
    refusal = shell_refusal(command)
    if refusal:
        return refusal
    if not is_read_only(command):
        from tools.actions import confirm

        parts = (command.strip(),)
        if not confirm_run:
            return confirm.ask("shell", parts, f"Bu komut bilgisayarda değişiklik yapabilir: `{command.strip()[:200]}`.").replace(
                "Göndereyim mi?", "Çalıştırayım mı?"
            ).replace("Göndermeden", "Çalıştırmadan")
        problem = confirm.check("shell", parts)
        if problem:
            return problem
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
        return f"Komut zaman aşımına uğradı ({timeout}s)."
    except OSError as exc:
        return f"Hata: {exc}"
    output = ((result.stdout or "") + (result.stderr or "")).strip()
    if result.returncode not in (0, None) and not output:
        return f"Komut hata kodu {result.returncode} ile bitti."
    if not output:
        return "Komut başarıyla çalıştı (çıktı yok)."
    if len(output) > 800:
        output = output[:800] + "\n... (çıktı kısaltıldı)"
    return output
