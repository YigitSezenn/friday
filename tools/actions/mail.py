"""Gmail ile e-posta gönderme (OAuth, yalnızca gmail.send izni) ve açma."""
from __future__ import annotations

import base64
import hashlib
import http.server
import json
import re
import secrets
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from email.message import EmailMessage

from jarvis.memory_store import load_memory, update_memory
from jarvis.paths import data_path
from tools.actions import confirm

SCOPE = "https://www.googleapis.com/auth/gmail.send"
SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
EMAIL_RE = re.compile(r"^[^@\s,;<>]+@[^@\s,;<>]+\.[^@\s,;<>]+$")


def _client_file():
    """Beklenen dosya; Windows gizli uzantı yüzünden .json.json ya da Google'ın
    indirdiği client_secret_*.json adıyla da kaydedilmiş olabilir."""
    wanted = data_path("gmail_client_secret.json")
    if wanted.exists():
        return wanted
    for pattern in ("gmail_client_secret.json.json", "client_secret*.json"):
        for found in sorted(wanted.parent.glob(pattern)):
            return found
    return wanted


def _token_file():
    return data_path("memory", "gmail_token.json")


def _read_json(path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _client() -> dict:
    raw = _read_json(_client_file())
    return raw.get("installed") or raw.get("web") or {}


def _post(url: str, data: dict, timeout: float = 20.0) -> dict:
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def gmail_connected() -> bool:
    return bool(_read_json(_token_file()).get("refresh_token"))


def connect_gmail() -> str:
    client = _client()
    if not client.get("client_id"):
        return (
            "Gmail kurulumu icin once Google Cloud'da 'Masaustu uygulamasi' turunde bir OAuth istemcisi olusturup "
            f"indirdigin JSON dosyasini su adla kaydet: {_client_file()} . Sonra bana 'Gmail'i bagla' de."
        )
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    result: dict = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if query.get("state", [""])[0] == state and query.get("code"):
                result["code"] = query["code"][0]
                text = "FRIDAY Gmail baglandi. Bu sekmeyi kapatabilirsin."
            else:
                text = "Baglanti reddedildi veya gecersiz."
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(text.encode("utf-8"))

        def log_message(self, *_args):
            return

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    redirect = f"http://127.0.0.1:{port}"
    params = {
        "client_id": client["client_id"], "redirect_uri": redirect, "response_type": "code", "scope": SCOPE,
        "access_type": "offline", "prompt": "consent", "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256",
    }
    url = client.get("auth_uri", "https://accounts.google.com/o/oauth2/v2/auth") + "?" + urllib.parse.urlencode(params)

    def finish() -> None:
        server.timeout = 240
        server.handle_request()
        server.server_close()
        if not result.get("code"):
            return
        try:
            token = _post(client.get("token_uri", "https://oauth2.googleapis.com/token"), {
                "client_id": client["client_id"], "client_secret": client.get("client_secret", ""),
                "code": result["code"], "code_verifier": verifier, "grant_type": "authorization_code", "redirect_uri": redirect,
            })
            if token.get("refresh_token"):
                _token_file().write_text(json.dumps({"refresh_token": token["refresh_token"]}), encoding="utf-8")
        except Exception:
            pass

    threading.Thread(target=finish, name="gmail-oauth", daemon=True).start()
    webbrowser.open(url)
    return "Tarayicida Google izin ekrani acildi. Yalnizca e-posta GONDERME izni istenir; okuma izni yoktur. Izni verince 'Gmail'i bagla' demen yeterli degil, otomatik baglanir."


def _access_token() -> str:
    refresh = _read_json(_token_file()).get("refresh_token")
    client = _client()
    if not refresh or not client.get("client_id"):
        raise RuntimeError("Gmail bagli degil. Once 'Gmail'i bagla' de.")
    token = _post(client.get("token_uri", "https://oauth2.googleapis.com/token"), {
        "client_id": client["client_id"], "client_secret": client.get("client_secret", ""),
        "refresh_token": refresh, "grant_type": "refresh_token",
    })
    if not token.get("access_token"):
        raise RuntimeError("Gmail yetkisi yenilenemedi.")
    return token["access_token"]


def build_message(to: str, subject: str, body: str) -> EmailMessage:
    msg = EmailMessage()
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    return msg


def save_email_contact(display_name: str, email: str, aliases: str = "") -> str:
    if not display_name.strip():
        return "Kisi adi bos olamaz."
    if not EMAIL_RE.match(email.strip()):
        return "Gecersiz e-posta adresi."
    from tools.actions.whatsapp import contact_key

    alias_list = [a.strip() for a in aliases.split(",") if a.strip()]
    update_memory({"email_contacts": {contact_key(display_name): {"value": email.strip(), "display_name": display_name.strip(), "aliases": alias_list}}})
    return f"{display_name.strip()} e-posta kisilerine kaydedildi."


def _lookup(name: str) -> dict | None:
    from tools.actions.whatsapp import _match_score, _normalize_lookup

    needle = _normalize_lookup(name)
    best, score = None, 0
    for key, entry in (load_memory().get("email_contacts") or {}).items():
        if not isinstance(entry, dict):
            continue
        names = [entry.get("display_name", ""), key, *[str(a) for a in entry.get("aliases", []) if isinstance(entry.get("aliases"), list)]]
        for n in names:
            s = _match_score(needle, str(n))
            if s > score:
                best, score = entry, s
    return best if score else None


def send_email(to: str = "", subject: str = "", body: str = "", recipient_name: str = "", confirm_send: bool = False) -> str:
    address = (to or "").strip()
    label = address
    if not address and recipient_name.strip():
        contact = _lookup(recipient_name)
        if not contact:
            return f"'{recipient_name}' icin kayitli e-posta bulamadim. Adresi soyle veya kisiyi kaydet."
        address = str(contact.get("value", "")).strip()
        label = str(contact.get("display_name", recipient_name))
    if not EMAIL_RE.match(address):
        return "Gecersiz veya eksik e-posta adresi."
    if re.search(r"[\r\n]", subject or "") or re.search(r"[\r\n]", address):
        return "Gecersiz konu veya adres."
    if not (body or "").strip():
        return "E-posta metni bos olamaz."
    if not gmail_connected():
        return "Gmail bagli degil. Once 'Gmail'i bagla' de."
    parts = (address.lower(), subject, body)
    if confirm.required():
        if not confirm_send:
            return confirm.ask("mail", parts, f"E-posta taslagi — Kime: {label} <{address}>, Konu: {subject or '(konusuz)'}, Metin: {body.strip()[:300]}.")
        problem = confirm.check("mail", parts)
        if problem:
            return problem
    try:
        raw = base64.urlsafe_b64encode(build_message(address, subject, body).as_bytes()).decode()
        req = urllib.request.Request(
            SEND_URL, data=json.dumps({"raw": raw}).encode(),
            headers={"Authorization": f"Bearer {_access_token()}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return f"E-posta gonderilemedi: {exc}"
    return f"E-posta {label} kisisine gonderildi."


def open_mail() -> str:
    webbrowser.open("https://mail.google.com/mail/u/0/#inbox")
    return "Gmail gelen kutusu tarayicida acildi."
