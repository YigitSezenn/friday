import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from deploy_gate import HOST, USER, load_named, load_saved

token = load_named("discord-token.bin")
password = load_saved()
stage = Path(tempfile.mkdtemp(prefix="friday-who-"))
try:
    secret = stage / "p.txt"
    ask = stage / "ask.cmd"
    secret.write_text(password, encoding="utf-8")
    ask.write_text(f'@echo off\r\ntype "{secret}"\r\n', encoding="ascii")
    env = os.environ.copy()
    env["SSH_ASKPASS"] = str(ask)
    env["SSH_ASKPASS_REQUIRE"] = "force"
    env["DISPLAY"] = "localhost:0"
    base = [
        "-o", "PreferredAuthentications=password", "-o", "PubkeyAuthentication=no",
        "-o", "NumberOfPasswordPrompts=1", "-o", "StrictHostKeyChecking=accept-new",
    ]
    local = Path(r"C:\Code\DiscordBot\atrium-kurulum\bots\_friday_who.js")
    subprocess.run(
        ["scp", *base, str(local), f"{USER}@{HOST}:C:/Code/atrium-kurulum/bots/_friday_who.js"],
        env=env, capture_output=True, text=True, check=True,
    )

    def ssh(remote: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["ssh", *base, f"{USER}@{HOST}", "cmd.exe", "/c", remote],
            env=env, capture_output=True, text=True,
        )

    who = ssh("docker exec friday node /app/bots/_friday_who.js")
    logs = ssh("docker logs --tail 80 friday")
    state = ssh("docker inspect friday --format \"{{.State.Status}} {{.State.Running}} {{.RestartCount}}\"")
    sockets = ssh("docker exec friday node -e \"const fs=require('fs'); const rows=[...fs.readFileSync('/proc/net/tcp','utf8').split(/\\n/).slice(1), ...fs.readFileSync('/proc/net/tcp6','utf8').split(/\\n/).slice(1)]; let n=0; for (const row of rows){ const p=row.trim().split(/\\s+/); if(p[3]==='01' && p[2] && p[2].split(':')[1]==='01BB') n++; } process.stdout.write(String(n));\"")
    ssh("del /q C:\\Code\\atrium-kurulum\\bots\\_friday_who.js")

    def redact(text: str) -> str:
        cleaned = text or ""
        if token:
            cleaned = cleaned.replace(token, "[redacted]")
        return re.sub(r"[A-Za-z0-9_\-]{24,}\.[A-Za-z0-9_\-]{6,}\.[A-Za-z0-9_\-]{20,}", "[redacted]", cleaned)

    Path(__file__).with_name("_friday_who_out.txt").write_text(
        "WHO\n" + redact((who.stdout or "") + (who.stderr or ""))
        + f"\nwho_code={who.returncode}\nSTATE\n" + redact((state.stdout or "") + (state.stderr or ""))
        + "\nSOCKETS443\n" + redact((sockets.stdout or "") + (sockets.stderr or ""))
        + "\nLOG\n" + redact((logs.stdout or "") + (logs.stderr or "")),
        encoding="utf-8",
    )
finally:
    shutil.rmtree(stage, ignore_errors=True)
