from __future__ import annotations

from pathlib import Path

from jarvis.config import get_app_config_value
from jarvis.paths import data_path

# Kurulu uygulamanin screen_vision listesi. 2.0-flash kaldirildi; kod 4 sure asimi.
VISION_MODELS = (
    "models/gemini-3.1-flash-lite",
    "models/gemini-flash-lite-latest",
    "models/gemini-3.8-flash",
    "models/gemini-flash-latest",
    "models/gemini-2.5-flash",
)
VISION_MAX_DIMENSION = 1280


def capture_active_window() -> tuple[bool, str, dict | None]:
    try:
        import mss
        from PIL import Image
    except ImportError as exc:
        return False, f"Ekran goruntusu icin paket eksik: {exc}", None
    left = top = 0
    width = height = 0
    title = ""
    owner = ""
    try:
        import win32gui
        import win32process

        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd) or ""
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width, height = max(0, right - left), max(0, bottom - top)
        try:
            import psutil

            _thread, pid = win32process.GetWindowThreadProcessId(hwnd)
            owner = psutil.Process(pid).name()
        except Exception:
            owner = ""
    except Exception:
        width = height = 0
    image_path = data_path("cache", "screen.jpg")
    try:
        with mss.MSS() as grabber:
            if width < 20 or height < 20:
                monitor = grabber.monitors[1]
            else:
                monitor = {"left": left, "top": top, "width": width, "height": height}
            shot = grabber.grab(monitor)
            image = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
            image.thumbnail((VISION_MAX_DIMENSION, VISION_MAX_DIMENSION))
            image.save(image_path, format="JPEG", quality=70)
    except Exception as exc:
        return False, f"Ekran goruntusu alinamadi: {exc}", None
    if not image_path.exists() or image_path.stat().st_size <= 0:
        return False, "Ekran goruntusu bos geldi.", None
    return True, "", {"image_path": str(image_path), "window_title": title, "owner_name": owner}


def analyze_screen(query: str, target: str = "active_window") -> str:
    target = (target or "active_window").strip().lower()
    if target != "active_window":
        return "Screen Vision v1 yalnizca aktif pencere analizini destekliyor."
    api_key = str(get_app_config_value("gemini_api_key", "") or "").strip()
    if not api_key:
        return "Gemini API anahtari eksik oldugu icin ekran analizi yapilamadi."
    ok, detail, payload = capture_active_window()
    if not ok or payload is None:
        return detail
    image_path = Path(payload["image_path"])
    title = str(payload.get("window_title") or "")
    owner = str(payload.get("owner_name") or "")
    try:
        analysis = _analyze(api_key, query or "Ekranda ne var?", image_path, owner, title)
    except Exception as exc:
        prefix = " / ".join(part for part in (owner, title) if part)
        if prefix:
            return f"Ekran goruntusu alindi ({prefix}) ama analiz tamamlanamadi: {exc}"
        return f"Ekran goruntusu alindi ama analiz tamamlanamadi: {exc}"
    label = " / ".join(part for part in (owner, title) if part)
    if label:
        return f"[Aktif pencere: {label}]\n{analysis}"
    return analysis


def explain_vision_error(exc: BaseException | None) -> str:
    if exc is None:
        return "Gemini ekran analizi bos dondu."
    raw = str(exc).strip()
    code = getattr(exc, "code", None)
    message = str(getattr(exc, "message", "") or "")
    blob = f"{code or ''} {raw} {message}".lower()
    if raw == "4" or code == 4 or raw.startswith("4 ") or "deadline" in blob:
        return "Gemini ekran analizi zaman asimina ugradi (kod 4). Goruntu kucultulup baska model denendi; biraz sonra tekrar dene."
    if any(word in blob for word in ("429", "quota", "resource exhausted")):
        return "Gemini vision istegi kota veya hiz limitine takildi. Biraz bekleyip tekrar dene."
    if any(word in blob for word in ("503", "unavailable", "overloaded", "internal error")):
        return "Gemini vision servisi su anda yogun. Biraz sonra tekrar dene."
    detail = message or raw or type(exc).__name__
    return f"Gemini vision istegi basarisiz oldu: {detail[:180]}"


def _model_gone(exc: BaseException) -> bool:
    blob = str(exc).lower()
    return any(word in blob for word in ("no longer available", "not found", "not supported", "shut down", "has been shut"))


def _transient(exc: BaseException) -> bool:
    blob = f"{getattr(exc, 'code', '')} {exc}".lower()
    return str(exc).strip() == "4" or getattr(exc, "code", None) == 4 or any(
        word in blob for word in ("deadline", "timeout", "timed out", "503", "429", "unavailable", "overloaded")
    )


def _jpeg_part(image_path: Path, limit: int):
    import io

    from google.genai import types
    from PIL import Image

    image = Image.open(image_path)
    image.thumbnail((limit, limit))
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=60 if limit < VISION_MAX_DIMENSION else 70)
    return types.Part.from_bytes(data=buffer.getvalue(), mime_type="image/jpeg")


def _response_text(response) -> str:
    try:
        text = getattr(response, "text", "") or ""
    except Exception as exc:
        raise RuntimeError(explain_vision_error(exc)) from exc
    if str(text).strip():
        return str(text).strip()
    candidates = getattr(response, "candidates", None) or []
    if candidates:
        reason = getattr(candidates[0], "finish_reason", None)
        if reason:
            raise RuntimeError(f"Gemini yaniti kesti: {reason}")
    raise RuntimeError("Gemini bos yanit verdi.")


def _analyze(api_key: str, query: str, image_path: Path, owner: str, title: str) -> str:
    from google import genai
    from google.genai import types

    prompt = (
        "Ekran goruntusundeki gorunen seyi Turkce, kisa ve dogrudan anlat. "
        "Uydurma. Kullaniciya 'Yep' deme. "
        f"Pencere: {owner} / {title}. Soru: {query}"
    )
    client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta", "timeout": 30000})
    last_error: Exception | None = None
    for limit in (VISION_MAX_DIMENSION, 720):
        image = _jpeg_part(image_path, limit)
        for model_name in VISION_MODELS:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[image, types.Part.from_text(text=prompt)],
                    config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=512),
                )
                return _response_text(response)
            except Exception as exc:
                last_error = exc
                if _transient(exc) or _model_gone(exc):
                    continue
                break
        if last_error and not _transient(last_error):
            break
    raise RuntimeError(explain_vision_error(last_error))
