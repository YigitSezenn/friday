"""Kapıyı sunucuya kurar. Şifreyi ve anahtarı yazdırmaz, bitince siler."""

from __future__ import annotations

import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOST = "friday-kapi.duckdns.org"
USER = "Administrator"


def _redact(text: str, password: str, key: str, token: str = "") -> str:
    cleaned = text or ""
    for secret in (password, key, token):
        if secret:
            cleaned = cleaned.replace(secret, "[gizli]")
    return cleaned


def load_named(name: str) -> str:
    path = Path(os.environ["LOCALAPPDATA"]) / "FRIDAY" / name
    if not path.exists():
        return ""
    import win32crypt

    try:
        _desc, blob = win32crypt.CryptUnprotectData(path.read_bytes(), None, None, None, 0)
    except Exception:
        return ""
    return blob.decode("utf-8").strip()


def secret_path() -> Path:
    return Path(os.environ["LOCALAPPDATA"]) / "FRIDAY" / "server-login.bin"


def load_saved() -> str:
    path = secret_path()
    if not path.exists():
        return ""
    import win32crypt

    try:
        _desc, blob = win32crypt.CryptUnprotectData(path.read_bytes(), None, None, None, 0)
    except Exception:
        return ""
    return blob.decode("utf-8")


def save_secret(password: str) -> None:
    import win32crypt

    path = secret_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(win32crypt.CryptProtectData(password.encode("utf-8"), "friday-server"))


def ask_password() -> str:
    import tkinter as tk

    box: dict[str, str] = {}
    root = tk.Tk()
    root.title("FRIDAY sunucu")
    root.geometry("440x200")
    tk.Label(root, text=f"{HOST}\nKullanıcı: Administrator\nBu kayıt bu bilgisayarda kalır. Bir daha sorulmaz.").pack(pady=12)
    entry = tk.Entry(root, show="*", width=32)
    entry.pack()
    entry.focus_set()

    def ok() -> None:
        box["value"] = entry.get()
        root.destroy()

    def cancel() -> None:
        root.destroy()

    tk.Button(root, text="Bağlan", command=ok).pack(pady=12)
    root.protocol("WM_DELETE_WINDOW", cancel)
    root.bind("<Return>", lambda _event: ok())
    root.mainloop()
    return box.get("value", "")


def main() -> int:
    setup = ROOT / "dist" / "FRIDAY-Kurulum.exe"
    if not setup.exists():
        print("setup-missing")
        return 1
    data = Path(os.environ["LOCALAPPDATA"]) / "FRIDAY" / "data" / "config"
    data.mkdir(parents=True, exist_ok=True)
    existing = data / "gate_key.txt"
    key = existing.read_text(encoding="utf-8").strip() if existing.exists() else ""
    if not key:
        key = secrets.token_urlsafe(24)
        existing.write_text(key, encoding="utf-8")
    print("local-key-ready")

    password = load_saved()
    if password:
        print("password-reused")
    else:
        password = ask_password()
        if not password:
            print("password-missing")
            return 2
        save_secret(password)
        print("password-saved")

    discord_token = load_named("discord-token.bin")
    stage = Path(tempfile.mkdtemp(prefix="friday-kapi-"))
    secret = stage / "p.txt"
    ask = stage / "ask.cmd"
    try:
        secret.write_text(password, encoding="utf-8")
        ask.write_text(f'@echo off\r\ntype "{secret}"\r\n', encoding="ascii")
        target = stage / "app"
        target.mkdir()
        for name in ("logic.py", "server.py", "requirements.txt", "Dockerfile", "docker-compose.yml"):
            shutil.copy2(ROOT / "gate" / name, target / name)
        public = ROOT / "gate" / "public"
        if public.exists():
            shutil.copytree(public, target / "public")
        discord_owner = load_named("discord-owner.bin")
        (target / ".env").write_text(
            f"GATE_KEY={key}\nDISCORD_TOKEN={discord_token}\nDISCORD_OWNER_ID={discord_owner}\n",
            encoding="utf-8",
        )
        dock = target / "docker-config"
        dock.mkdir()
        (dock / "config.json").write_text('{"auths":{}}\n', encoding="utf-8")
        (target / "probe.cmd").write_text(
            "@echo off\r\n"
            "set DOCKER_CONFIG=C:\\Code\\friday-kapi\\docker-config\r\n"
            "cd /d C:\\Code\\friday-kapi\r\n"
            "where docker > C:\\Code\\friday-kapi\\probe.txt 2>&1\r\n"
            "where docker-compose >> C:\\Code\\friday-kapi\\probe.txt 2>&1\r\n"
            "docker version >> C:\\Code\\friday-kapi\\probe.txt 2>&1\r\n"
            "docker compose version >> C:\\Code\\friday-kapi\\probe.txt 2>&1\r\n"
            "docker-compose version >> C:\\Code\\friday-kapi\\probe.txt 2>&1\r\n",
            encoding="ascii",
        )
        (target / "build-only.cmd").write_text(
            "@echo off\r\n"
            "cd /d C:\\Code\\friday-kapi\r\n"
            "set DOCKER_BUILDKIT=0\r\n"
            "set COMPOSE_BAKE=0\r\n"
            "docker-compose up -d --build > C:\\Code\\friday-kapi\\build.txt 2>&1\r\n"
            "docker ps --filter name=friday-kapi > C:\\Code\\friday-kapi\\ps.txt 2>&1\r\n"
            "docker logs --tail 40 friday-kapi > C:\\Code\\friday-kapi\\bot.txt 2>&1\r\n",
            encoding="ascii",
        )
        (target / "deploy.cmd").write_text(
            "@echo off\r\n"
            "del /q C:\\Code\\friday-kapi\\build.txt C:\\Code\\friday-kapi\\ps.txt >nul 2>&1\r\n"
            "schtasks /Delete /TN FridayGateBuild /F >nul 2>&1\r\n"
            "schtasks /Create /TN FridayGateBuild /TR \"C:\\Code\\friday-kapi\\build-only.cmd\" /SC ONCE /ST 23:59 /F /IT > C:\\Code\\friday-kapi\\task.txt 2>&1\r\n"
            "schtasks /Run /TN FridayGateBuild >> C:\\Code\\friday-kapi\\task.txt 2>&1\r\n",
            encoding="ascii",
        )
        env = os.environ.copy()
        env["SSH_ASKPASS"] = str(ask)
        env["SSH_ASKPASS_REQUIRE"] = "force"
        env["DISPLAY"] = "localhost:0"
        ssh = [
            "ssh",
            "-o", "PreferredAuthentications=password",
            "-o", "PubkeyAuthentication=no",
            "-o", "NumberOfPasswordPrompts=1",
            "-o", "StrictHostKeyChecking=accept-new",
            f"{USER}@{HOST}",
        ]
        made = subprocess.run(ssh + ["if not exist C:\\Code\\friday-kapi\\downloads mkdir C:\\Code\\friday-kapi\\downloads"], env=env, capture_output=True, text=True)
        if made.returncode != 0:
            (ROOT / "tools" / "gate-deploy-status.txt").write_text(_redact((made.stderr or "") + (made.stdout or ""), password, key, discord_token)[-2000:], encoding="utf-8")
            print("ssh-failed")
            return 3
        copied = subprocess.run(
            ["scp", "-o", "PreferredAuthentications=password", "-o", "PubkeyAuthentication=no", "-o", "NumberOfPasswordPrompts=1", "-o", "StrictHostKeyChecking=accept-new", "-r", str(target) + "\\.", f"{USER}@{HOST}:C:/Code/friday-kapi/"],
            env=env,
            capture_output=True,
            text=True,
        )
        if copied.returncode != 0:
            print("scp-failed")
            return 4
        remote = ["cmd.exe", "/c"]
        probed = subprocess.run(ssh + remote + ["C:\\Code\\friday-kapi\\probe.cmd"], env=env, capture_output=True, text=True)
        fetched = subprocess.run(
            ["scp", "-o", "PreferredAuthentications=password", "-o", "PubkeyAuthentication=no", "-o", "NumberOfPasswordPrompts=1", "-o", "StrictHostKeyChecking=accept-new", f"{USER}@{HOST}:C:/Code/friday-kapi/probe.txt", str(stage / "probe.txt")],
            env=env,
            capture_output=True,
            text=True,
        )
        probe_text = (stage / "probe.txt").read_text(encoding="utf-8", errors="replace") if fetched.returncode == 0 and (stage / "probe.txt").exists() else (probed.stderr or "")
        (ROOT / "tools" / "gate-deploy-status.txt").write_text(_redact(probe_text, password, key, discord_token)[-4000:], encoding="utf-8")
        built = subprocess.run(ssh + remote + ["C:\\Code\\friday-kapi\\deploy.cmd"], env=env, capture_output=True, text=True)
        scp_base = ["scp", "-o", "PreferredAuthentications=password", "-o", "PubkeyAuthentication=no", "-o", "NumberOfPasswordPrompts=1", "-o", "StrictHostKeyChecking=accept-new"]
        for _ in range(24):
            time.sleep(10)
            for name in ("task.txt", "build.txt", "ps.txt"):
                subprocess.run(scp_base + [f"{USER}@{HOST}:C:/Code/friday-kapi/{name}", str(stage / name)], env=env, capture_output=True, text=True)
            ps_now = (stage / "ps.txt").read_text(encoding="utf-8", errors="replace") if (stage / "ps.txt").exists() else ""
            build_now = (stage / "build.txt").read_text(encoding="utf-8", errors="replace") if (stage / "build.txt").exists() else ""
            if "friday-kapi" in ps_now and "Up" in ps_now:
                break
            if "failed to solve" in build_now or "ERROR:" in build_now or "is not logged on" in build_now.lower():
                break
        subprocess.run(
            ["scp", "-o", "PreferredAuthentications=password", "-o", "PubkeyAuthentication=no", "-o", "NumberOfPasswordPrompts=1", "-o", "StrictHostKeyChecking=accept-new", f"{USER}@{HOST}:C:/Code/friday-kapi/build.txt", str(stage / "build.txt")],
            env=env,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["scp", "-o", "PreferredAuthentications=password", "-o", "PubkeyAuthentication=no", "-o", "NumberOfPasswordPrompts=1", "-o", "StrictHostKeyChecking=accept-new", f"{USER}@{HOST}:C:/Code/friday-kapi/ps.txt", str(stage / "ps.txt")],
            env=env,
            capture_output=True,
            text=True,
        )
        pieces = [probe_text, built.stdout or "", built.stderr or ""]
        for name in ("task.txt", "build.txt", "ps.txt"):
            path = stage / name
            if path.exists():
                pieces.append(path.read_text(encoding="utf-8", errors="replace"))
        time.sleep(8)
        subprocess.run(ssh + remote + ["docker logs --tail 50 friday-kapi > C:\\Code\\friday-kapi\\bot.txt 2>&1"], env=env, capture_output=True, text=True)
        subprocess.run(scp_base + [f"{USER}@{HOST}:C:/Code/friday-kapi/bot.txt", str(stage / "bot.txt")], env=env, capture_output=True, text=True)
        if (stage / "bot.txt").exists():
            pieces.append((stage / "bot.txt").read_text(encoding="utf-8", errors="replace"))
        report = _redact("\n".join(pieces), password, key, discord_token)
        (ROOT / "tools" / "gate-deploy-status.txt").write_text(report[-5000:], encoding="utf-8")
        ps_text = (stage / "ps.txt").read_text(encoding="utf-8", errors="replace") if (stage / "ps.txt").exists() else ""
        running = "friday-kapi" in ps_text and "Up" in ps_text
        if not running:
            print("compose-failed")
            return 5
        print("deployed")
        bot_text = (stage / "bot.txt").read_text(encoding="utf-8", errors="replace") if (stage / "bot.txt").exists() else ""
        print("bot-online" if "bağlandı" in bot_text else "bot-offline")
        return 0
    finally:
        shutil.rmtree(stage, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
