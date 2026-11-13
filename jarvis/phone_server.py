"""Aynı Wi-Fi telefon köprüsü. Jeton loglanmaz. İnternete tünel açılmaz."""

from __future__ import annotations

import queue
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from jarvis.config import load_app_config
from jarvis.paths import data_path

_server: ThreadingHTTPServer | None = None
_thread: threading.Thread | None = None
_bind_host = "127.0.0.1"
_phone_audio: queue.Queue[bytes] = queue.Queue(maxsize=32)
_speaker = bytearray()
_speaker_lock = threading.Lock()
_on_text = None

PHONE_PAGE = """<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>FRIDAY</title>
<style>
body{margin:0;background:#070605;color:#f3e6c8;font-family:Segoe UI,sans-serif}
main{max-width:420px;margin:0 auto;padding:28px 20px 40px}
h1{letter-spacing:.28em;font-weight:500;font-size:18px}
p{color:#b7a98a;line-height:1.45}
button,input{font:inherit}
button{background:#e6c98a;color:#1a140c;border:0;border-radius:999px;padding:14px 18px;letter-spacing:.08em}
input{width:100%;box-sizing:border-box;background:#100e0a;color:#fff;border:1px solid rgba(230,201,138,.35);border-radius:12px;padding:12px;margin:8px 0 14px}
.mic{width:100%;margin:18px 0}
.mic[aria-pressed=true]{background:#8fd6a0}
#heard{min-height:1.2em}
</style>
<main>
<h1>FRIDAY</h1>
<p>Aynı Wi-Fi. Konuşman ve yazdığın komut bu bilgisayarda çalışır. “Bilgisayarda aç” dersen uygulama bilgisayarda açılır.</p>
<button class="mic" id="mic" type="button" aria-pressed="false">MİKROFONU AÇ</button>
<p id="heard">Mikrofon kapalı</p>
<form id="say"><input name="text" placeholder="Bilgisayara yaz" autocomplete="off"><button type="submit">GÖNDER</button></form>
</main>
<script>
const token = new URLSearchParams(location.search).get("token") || "";
const mic = document.getElementById("mic");
const heard = document.getElementById("heard");
let on = false, ctx, node, playAt = 0;
async function micOn(){
  const stream = await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,channelCount:1}});
  ctx = new AudioContext();
  const src = ctx.createMediaStreamSource(stream);
  node = ctx.createScriptProcessor(4096, 1, 1);
  src.connect(node); node.connect(ctx.destination);
  node.onaudioprocess = (ev) => {
    if(!on) return;
    const input = ev.inputBuffer.getChannelData(0);
    const pcm = new Int16Array(input.length);
    for(let i=0;i<input.length;i++) pcm[i] = Math.max(-32768, Math.min(32767, input[i]*32768));
    fetch("/mic?token="+encodeURIComponent(token), {method:"POST", body:pcm.buffer});
  };
  on = true; mic.setAttribute("aria-pressed","true"); heard.textContent = "Dinliyorum, bilgisayara gidiyor";
}
function micOff(){ on = false; mic.setAttribute("aria-pressed","false"); heard.textContent = "Mikrofon kapalı"; try{node.disconnect();}catch(e){} }
mic.onclick = () => on ? micOff() : micOn().catch(() => { heard.textContent = "Mikrofon izni gerekli"; });
document.getElementById("say").onsubmit = async (ev) => {
  ev.preventDefault();
  const text = new FormData(ev.target).get("text");
  await fetch("/command?token="+encodeURIComponent(token), {method:"POST", headers:{"Content-Type":"application/x-www-form-urlencoded"}, body:"text="+encodeURIComponent(text)});
  ev.target.reset();
  heard.textContent = "Bilgisayara iletildi";
};
setInterval(async () => {
  if(!ctx) return;
  const res = await fetch("/speaker?token="+encodeURIComponent(token));
  if(!res.ok) return;
  const buf = await res.arrayBuffer();
  if(buf.byteLength < 2) return;
  const pcm = new Int16Array(buf);
  const audio = ctx.createBuffer(1, pcm.length, 16000);
  const ch = audio.getChannelData(0);
  for(let i=0;i<pcm.length;i++) ch[i] = pcm[i]/32768;
  const src = ctx.createBufferSource();
  src.buffer = audio; src.connect(ctx.destination);
  const now = ctx.currentTime;
  const start = Math.max(now, playAt);
  src.start(start); playAt = start + audio.duration;
}, 250);
</script>
"""

JOIN_PAGE = """<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>FRIDAY telefon</title>
<style>body{margin:0;background:#070605;color:#f3e6c8;font-family:Segoe UI,sans-serif}main{max-width:420px;margin:0 auto;padding:32px 20px}a,button{display:block;text-align:center;margin:12px 0;padding:14px;border-radius:999px;text-decoration:none}a.apk{background:#e6c98a;color:#1a140c}a.go{border:1px solid rgba(230,201,138,.4);color:#f3e6c8}</style>
<main><h1>FRIDAY</h1><p>Android’de uygulamayı indir, kur, sonra bu sayfadaki bağlantıyla aç. Aynı Wi-Fi gerekir.</p>
<a class="apk" href="/friday.apk">UYGULAMAYI İNDİR</a>
<a class="go" id="open" href="/">TARAYICIDA AÇ</a>
<script>const t=new URLSearchParams(location.search).get("token")||"";document.getElementById("open").href="/?token="+encodeURIComponent(t);</script>
</main>
"""


def phone_token() -> str:
    path = data_path("config", "phone_token.txt")
    if path.exists():
        token = path.read_text(encoding="utf-8").strip()
        if token:
            return token
    token = secrets.token_urlsafe(18)
    path.write_text(token, encoding="utf-8")
    return token


def rotate_phone_token() -> str:
    token = secrets.token_urlsafe(18)
    data_path("config", "phone_token.txt").write_text(token, encoding="utf-8")
    return token


def phone_qr_payload(url: str | None = None) -> str:
    return url or phone_join_url()


def phone_qr_data_url(url: str | None = None) -> str:
    import base64
    import io

    import qrcode

    image = qrcode.make(phone_qr_payload(url), box_size=8, border=2)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def phone_url() -> str:
    shown = _shown_host()
    return f"http://{shown}:8766/?token={phone_token()}"


def phone_join_url() -> str:
    shown = _shown_host()
    return f"http://{shown}:8766/join?token={phone_token()}"


def _shown_host() -> str:
    config = load_app_config()
    host = "0.0.0.0" if config.get("web_remote_access") else "127.0.0.1"
    return _lan_ip() if host == "0.0.0.0" else "127.0.0.1"


def _lan_ip() -> str:
    import socket

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except OSError:
        return "127.0.0.1"


def relay_phone_audio(pcm: bytes) -> None:
    if not pcm:
        return
    if _phone_audio.full():
        try:
            _phone_audio.get_nowait()
        except queue.Empty:
            pass
    _phone_audio.put(bytes(pcm))


def take_phone_audio() -> bytes:
    try:
        return _phone_audio.get_nowait()
    except queue.Empty:
        return b""


def publish_speaker(pcm: bytes) -> None:
    if not pcm:
        return
    with _speaker_lock:
        _speaker.extend(pcm)
        if len(_speaker) > 16000 * 2:
            del _speaker[: len(_speaker) - 16000 * 2]


def take_speaker() -> bytes:
    with _speaker_lock:
        data = bytes(_speaker)
        _speaker.clear()
        return data


def phone_command_for_pc(text: str) -> str:
    raw = str(text or "").strip()
    folded = raw.casefold().replace("ı", "i").replace("İ", "i")
    for prefix in ("bilgisayarda ac", "bilgisayara ilet", "bilgisayarda aç"):
        needle = prefix.replace("ı", "i")
        if folded.startswith(needle):
            rest = raw[len(prefix):].strip(" :,-")
            return rest or raw
    return raw


def apk_path() -> Path:
    here = Path(__file__).resolve().parent
    candidates = [
        here.parent / "phone-android" / "FRIDAY.apk",
        here.parent / "dist" / "FRIDAY.apk",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def handle_phone_request(method: str, path: str, body: bytes, on_text) -> tuple[int, bytes, str]:
    parsed = urlparse(path)
    query = parse_qs(parsed.query)
    route = parsed.path
    if route == "/friday.apk":
        path_apk = apk_path()
        if not path_apk.exists():
            return 404, "APK henüz derlenmedi. Sayfayı tarayıcıda aç.".encode("utf-8"), "text/plain; charset=utf-8"
        return 200, path_apk.read_bytes(), "application/vnd.android.package-archive"
    given = (query.get("token") or [""])[0]
    if given != phone_token():
        return 403, "Yetkisiz.".encode("utf-8"), "text/plain; charset=utf-8"
    if route in {"/", "/join"} and method == "GET":
        page = JOIN_PAGE if route == "/join" else PHONE_PAGE
        return 200, page.encode("utf-8"), "text/html; charset=utf-8"
    if route == "/mic" and method == "POST":
        relay_phone_audio(body)
        return 204, b"", "text/plain"
    if route == "/speaker" and method == "GET":
        return 200, take_speaker(), "application/octet-stream"
    if route == "/command" and method == "POST":
        form = parse_qs(body.decode("utf-8", errors="replace"))
        text = phone_command_for_pc((form.get("text") or [""])[0])
        if text and on_text:
            on_text(text)
        return 204, b"", "text/plain"
    return 404, b"", "text/plain"


def start_phone_server(on_text, lan: bool | None = None) -> str:
    global _server, _thread, _bind_host, _on_text
    from jarvis.config import save_app_config

    _on_text = on_text
    if lan is True:
        save_app_config({"web_remote_access": True})
    elif lan is False:
        save_app_config({"web_remote_access": False})
    host = "0.0.0.0" if load_app_config().get("web_remote_access") else "127.0.0.1"
    if _server is not None and _bind_host == host:
        return phone_join_url()
    stop_phone_server()
    _bind_host = host

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:
            return

        def _respond(self) -> None:
            length = int(self.headers.get("Content-Length", "0") or 0)
            body = self.rfile.read(length) if length else b""
            status, payload, content = handle_phone_request(self.command, self.path, body, _on_text)
            self.send_response(status)
            self.send_header("Content-Type", content)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            if payload:
                self.wfile.write(payload)

        def do_GET(self) -> None:
            self._respond()

        def do_POST(self) -> None:
            self._respond()

    _server = ThreadingHTTPServer((host, 8766), Handler)
    _thread = threading.Thread(target=_server.serve_forever, name="jarvis-phone", daemon=True)
    _thread.start()
    return phone_join_url()


def stop_phone_server() -> None:
    global _server
    if _server is not None:
        _server.shutdown()
        _server.server_close()
        _server = None


def phone_status() -> dict:
    return {"running": _server is not None, "url": phone_join_url() if _server else ""}
