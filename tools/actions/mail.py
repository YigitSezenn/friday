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
    """Kurulu veri klasöründeki istemci dosyası (yoksa beklenen yol)."""
    wanted = data_path("gmail_client_secret.json")
    if wanted.exists():
        return wanted
    for pattern in ("gmail_client_secret.json.json", "client_secret*.json"):
        for found in sorted(wanted.parent.glob(pattern)):
            return found
    return wanted


def _token_file():
    return data_path("memory", "gmail_token.json")


def _search_dirs() -> list:
    from pathlib import Path

    home = Path.home()
    dirs = [home / "Downloads", home / "Desktop", home / "Documents"]
    for base in (home / "Desktop", home / "Downloads"):
        dirs.append(base / "jarvis-rebuild" / "data")
    return dirs


def _valid_client(path) -> bool:
    raw = _read_json(path)
    info = raw.get("installed") or raw.get("web") or {}
    return bool(info.get("client_id")) and bool(info.get("client_secret"))


def import_client_file() -> bool:
    """Kullanıcıyı uğraştırmamak için: istemci JSON'u Downloads/Masaüstü gibi
    yerlerde otomatik bulunur, doğrulanır ve veri klasörüne kopyalanır."""
    import shutil

    target = data_path("gmail_client_secret.json")
    if _valid_client(_client_file()):
        if not target.exists():
            shutil.copyfile(_client_file(), target)
        return True
    patterns = ("client_secret*.json", "gmail_client_secret.json*")
    candidates = []
    for folder in _search_dirs():
        try:
            for pattern in patterns:
                candidates.extend(f for f in folder.glob(pattern) if f.is_file())
        except OSError:
            continue
    for found in sorted(candidates, key=lambda f: f.stat().st_mtime, reverse=True):
        if _valid_client(found):
            shutil.copyfile(found, target)
            return True
    return False


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
    import_client_file()
    client = _client()
    if not client.get("client_id"):
        return (
            "Google Cloud'da 'Masaustu uygulamasi' turunde OAuth istemcisi olusturup JSON'u indir (Downloads klasorune "
            "inmesi yeterli); ben kendim bulurum. Sonra tekrar 'Gmail'i bagla' de."
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


def _web_autosend() -> bool:
    """Onaydan sonra tarayıcıdaki Gmail'den kendisi göndersin mi (varsayılan açık)."""
    import sys

    if sys.platform != "win32":
        return False
    try:
        from jarvis.config import load_app_config

        return bool(load_app_config().get("mail_web_autosend", True))
    except Exception:
        return True


def outlook_available() -> bool:
    """Klasik Outlook gerçekten kullanılabilir mi?

    Yeni Outlook (olk.exe) COM desteklemez. Klasik Outlook kurulu olsa bile kullanıcı
    yeni Outlook'a geçtiyse (UseNewOutlook=1) ya da klasikte hiç profil yoksa
    kullanılmaz; aksi halde boş kurulum sihirbazı açılırdı.
    """
    import sys

    if sys.platform != "win32":
        return False
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"Outlook.Application\CLSID"):
            pass
    except OSError:
        return False
    return _classic_outlook_in_use()


def _classic_outlook_in_use() -> bool:
    import winreg

    base = r"Software\Microsoft\Office\16.0\Outlook"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, base + r"\Preferences") as key:
            value, _kind = winreg.QueryValueEx(key, "UseNewOutlook")
            if int(value) == 1:
                return False
    except (OSError, ValueError):
        pass
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, base + r"\Profiles") as key:
            return winreg.QueryInfoKey(key)[0] > 0
    except OSError:
        return False


def _send_outlook(address: str, subject: str, body: str) -> None:
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    try:
        app = win32com.client.Dispatch("Outlook.Application")
        item = app.CreateItem(0)  # olMailItem
        item.To = address
        item.Subject = subject
        item.Body = body
        item.Send()
        try:
            app.Session.SendAndReceive(False)
        except Exception:
            pass
    finally:
        pythoncom.CoUninitialize()


def gmail_compose_url(address: str, subject: str, body: str) -> str:
    """Tarayıcıda açık Gmail oturumuyla dolu 'Yeni ileti' penceresi (OAuth gerekmez)."""
    query = urllib.parse.urlencode({"view": "cm", "fs": "1", "to": address, "su": subject, "body": body}, quote_via=urllib.parse.quote)
    return f"https://mail.google.com/mail/?{query}"


def _open_gmail_web(address: str, subject: str, body: str) -> None:
    webbrowser.open(gmail_compose_url(address, subject, body))


def _open_draft(address: str, subject: str, body: str) -> None:
    query = urllib.parse.urlencode({"subject": subject, "body": body}, quote_via=urllib.parse.quote)
    webbrowser.open(f"mailto:{urllib.parse.quote(address, safe='@')}?{query}")


def _foreground_title() -> str:
    import ctypes

    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    length = user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def _press_ctrl_enter() -> None:
    import ctypes

    user32 = ctypes.windll.user32
    user32.keybd_event(0x11, 0, 0, 0)  # Ctrl
    user32.keybd_event(0x0D, 0, 0, 0)  # Enter
    user32.keybd_event(0x0D, 0, 2, 0)
    user32.keybd_event(0x11, 0, 2, 0)


def gmail_web_send(address: str, subject: str, body: str, title=None, press=None, sleep=None,
                   wait: float = 15.0, settle: float = 3.0) -> str:
    """Gmail'i tarayıcıda doldurulmuş açar ve Ctrl+Enter ile gönderir.

    Güvenlik: tuş yalnızca öndeki pencerenin başlığında 'Gmail' varken basılır; aksi halde
    hiçbir tuşa basılmaz ve ileti taslak olarak açık bırakılır (başka bir uygulamaya
    yanlışlıkla Ctrl+Enter gitmesin diye).
    """
    title = title or _foreground_title
    press = press or _press_ctrl_enter
    sleep = sleep or time.sleep
    _open_gmail_web(address, subject, body)
    waited = 0.0
    while waited < wait:
        sleep(0.5)
        waited += 0.5
        if "gmail" in str(title() or "").casefold():
            break
    else:
        return "opened"
    sleep(settle)  # yeni ileti alanlarının yüklenmesi için
    before = str(title() or "")
    if "gmail" not in before.casefold():
        return "opened"
    press()
    sleep(2.5)
    after = str(title() or "")
    return "sent" if after != before else "pressed"


def choose_provider(provider: str = "auto") -> str:
    """auto: Gmail bağlıysa Gmail, değilse klasik Outlook, o da yoksa taslak."""
    key = (provider or "auto").strip().casefold()
    if key in {"gmail", "google"}:
        return "gmail" if gmail_connected() else "gmail_web"
    if key in {"outlook", "office", "hotmail"}:
        return "outlook" if outlook_available() else "none-outlook"
    if key in {"taslak", "draft", "mailto"}:
        return "draft"
    if key in {"gmail_web", "web", "tarayici"}:
        return "gmail_web"
    if gmail_connected():
        return "gmail"
    if outlook_available():
        return "outlook"
    return "gmail_web"


def send_email(to: str = "", subject: str = "", body: str = "", recipient_name: str = "", confirm_send: bool = False, provider: str = "auto") -> str:
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
    route = choose_provider(provider)
    if route == "gmail_web" and not _web_autosend():
        try:
            _open_gmail_web(address, subject, body)
        except Exception as exc:
            return f"Gmail tarayicida acilamadi: {exc}"
        return f"Gmail tarayicida {label} icin doldurulmus yeni ileti olarak acildi; kontrol edip Gonder'e bas."
    if route == "none-outlook":
        return "Klasik Outlook kullanilmiyor (yeni Outlook dogrudan gonderimi desteklemiyor). Taslak olarak acayim mi, yoksa Gmail mi baglayalim?"
    if route == "draft":
        try:
            _open_draft(address, subject, body)
        except Exception as exc:
            return f"E-posta taslagi acilamadi: {exc}"
        return f"E-posta taslagi {label} icin mail uygulamasinda acildi; gondermek icin Gonder'e bas."
    parts = (route, address.lower(), subject, body)
    if confirm.required():
        if not confirm_send:
            via = {"gmail": "Gmail", "gmail_web": "Gmail (tarayici)"}.get(route, "Outlook")
            return confirm.ask("mail", parts, f"E-posta taslagi ({via}) — Kime: {label} <{address}>, Konu: {subject or '(konusuz)'}, Metin: {body.strip()[:300]}.")
        problem = confirm.check("mail", parts)
        if problem:
            return problem
    try:
        if route == "gmail_web":
            outcome = gmail_web_send(address, subject, body)
            if outcome == "sent":
                return f"E-posta Gmail (tarayici) ile {label} kisisine gonderildi."
            if outcome == "pressed":
                return f"Gmail'de {label} icin Gonder komutu verildi; sayfa degismedi, Gonderilenler'den kontrol etmeni oneririm."
            return f"Gmail acildi ama pencere one gelmedigi icin otomatik gonderemedim; ileti dolu bekliyor, Gonder'e bas."
        if route == "outlook":
            _send_outlook(address, subject, body)
            return f"E-posta Outlook ile {label} kisisine gonderildi."
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


def open_mail(provider: str = "auto") -> str:
    import os

    key = (provider or "auto").strip().casefold()
    if key in {"outlook", "office"} or (key == "auto" and not gmail_connected() and outlook_available()):
        try:
            os.startfile("outlook.exe")  # type: ignore[attr-defined]
            return "Outlook acildi."
        except OSError:
            pass
    webbrowser.open("https://mail.google.com/mail/u/0/#inbox")
    return "Gmail gelen kutusu tarayicida acildi."
