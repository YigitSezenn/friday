from __future__ import annotations

import re
import urllib.parse
import threading
import time
import webbrowser

_RECENT: dict[str, float] = {}
DEDUPE_SECONDS = 8.0


def _site_key(url: str) -> str:
    host = urllib.parse.urlparse(url).netloc.lower()
    host = host[4:] if host.startswith("www.") else host
    return host.replace("m.", "", 1) if host.startswith("m.") else host


def recently_opened(url: str, now: float | None = None) -> bool:
    """Ayni siteye birkac saniye icinde ikinci pencere acilmasin (model iki arac cagirabilir)."""
    now = time.monotonic() if now is None else now
    key = _site_key(url)
    last = _RECENT.get(key)
    _RECENT[key] = now
    return last is not None and now - last < DEDUPE_SECONDS


_PENDING: dict[str, "threading.Timer"] = {}
WEAK_DELAY = 2.5


def _front_marker(url: str) -> str:
    host = urllib.parse.urlparse(url).hostname or ""
    parts = [part for part in host.split(".") if part not in {"www", "m", "music"}]
    name = parts[-2] if len(parts) >= 2 else (parts[0] if parts else "")
    return "YouTube" if name in {"youtube", "youtu"} else name


def _open_front(url: str) -> None:
    """Sayfayı açar ve tarayıcı arka planda kalmasın diye penceresini öne getirir (en iyi çaba)."""
    webbrowser.open(url)
    try:
        from tools.actions.apps import front_soon

        front_soon(_front_marker(url))
    except Exception:
        pass


def open_url(url: str) -> None:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    # Ayni siteye ait bekleyen "ana sayfa" acilisi varsa iptal et: video/arama zaten acilacak.
    pending = _PENDING.pop(_site_key(url), None)
    if pending is not None:
        pending.cancel()
    if recently_opened(url):
        return
    _open_front(url)


def open_home_soon(url: str) -> None:
    """Sadece 'YouTube'u ac' denince: model ayrica video acarsa bu acilis iptal olur."""
    key = _site_key(url)
    last = _RECENT.get(key)
    if key in _PENDING or (last is not None and time.monotonic() - last < DEDUPE_SECONDS):
        return

    def fire() -> None:
        _PENDING.pop(key, None)
        _RECENT[key] = time.monotonic()
        _open_front(url)

    timer = threading.Timer(WEAK_DELAY, fire)
    timer.daemon = True
    _PENDING[key] = timer
    timer.start()


def _find_first_youtube_video(query: str) -> str | None:
    import requests

    response = requests.get(
        "https://www.youtube.com/results",
        params={"search_query": query},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=10,
    )
    response.raise_for_status()
    seen = set()
    for video_id in re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', response.text):
        if video_id not in seen:
            return video_id
    for video_id in re.findall(r"/watch\?v=([A-Za-z0-9_-]{11})", response.text):
        if video_id not in seen:
            return video_id
    return None


def _stop_current_playback() -> None:
    """Yeni video acilmadan once calan ses (eski sekme, Spotify) duraklatilir."""
    try:
        from tools.actions.playback import pause_playing_sessions

        pause_playing_sessions()
    except Exception:
        pass


def browser_control(action: str, url: str | None = None, query: str | None = None) -> str:
    action = (action or "").strip().lower()
    if action == "open_url":
        if not url:
            return "URL belirtilmedi."
        if not str(url).startswith(("http://", "https://")):
            url = "https://" + str(url)
        open_url(url)
        return f"Açıldı: {url}"
    if action == "search":
        if not query:
            return "Arama sorgusu belirtilmedi."
        encoded = urllib.parse.quote(query)
        search_url = f"https://www.google.com/search?q={encoded}"
        open_url(search_url)
        return f"'{query}' için arama açıldı: {search_url}"
    if action in ("play_youtube", "youtube_play", "play_music"):
        if not query:
            return "YouTube için arama sorgusu belirtilmedi."
        _stop_current_playback()
        try:
            video_id = _find_first_youtube_video(query)
        except Exception as exc:
            encoded = urllib.parse.quote(query)
            fallback = f"https://www.youtube.com/results?search_query={encoded}"
            open_url(fallback)
            return f"YouTube ilk sonucu alınamadı ({exc}). Arama sonuçları açıldı: {query}"
        if not video_id:
            encoded = urllib.parse.quote(query)
            fallback = f"https://www.youtube.com/results?search_query={encoded}"
            open_url(fallback)
            return f"YouTube'da doğrudan video bulunamadı. Arama sonuçları açıldı: {query}"
        watch = f"https://www.youtube.com/watch?v={video_id}&autoplay=1"
        open_url(watch)
        return f"YouTube'da oynatiliyor: {watch}"
    return f"Bilinmeyen eylem: {action}"
