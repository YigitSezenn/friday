from __future__ import annotations

import re
import urllib.parse
import webbrowser


def open_url(url: str) -> None:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    webbrowser.open(url)


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


def browser_control(action: str, url: str | None = None, query: str | None = None) -> str:
    action = (action or "").strip().lower()
    if action == "open_url":
        if not url:
            return "URL belirtilmedi."
        if not str(url).startswith(("http://", "https://")):
            url = "https://" + str(url)
        open_url(url)
        return f"Acildi: {url}"
    if action == "search":
        if not query:
            return "Arama sorgusu belirtilmedi."
        encoded = urllib.parse.quote(query)
        search_url = f"https://www.google.com/search?q={encoded}"
        open_url(search_url)
        return f"'{query}' icin arama acildi: {search_url}"
    if action in ("play_youtube", "youtube_play", "play_music"):
        if not query:
            return "YouTube icin arama sorgusu belirtilmedi."
        try:
            video_id = _find_first_youtube_video(query)
        except Exception as exc:
            encoded = urllib.parse.quote(query)
            fallback = f"https://www.youtube.com/results?search_query={encoded}"
            open_url(fallback)
            return f"YouTube ilk sonucu alinamadi ({exc}). Arama sonuclari acildi: {query}"
        if not video_id:
            encoded = urllib.parse.quote(query)
            fallback = f"https://www.youtube.com/results?search_query={encoded}"
            open_url(fallback)
            return f"YouTube'da dogrudan video bulunamadi. Arama sonuclari acildi: {query}"
        watch = f"https://www.youtube.com/watch?v={video_id}&autoplay=1"
        open_url(watch)
        return f"YouTube'da oynatiliyor: {watch}"
    return f"Bilinmeyen eylem: {action}"
