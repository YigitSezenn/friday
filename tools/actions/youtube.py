from __future__ import annotations

from jarvis.config import get_app_config_value


def get_youtube_channel_report(query: str = "overview", handle: str = "", video_limit: int = 6) -> str:
    api_key = str(get_app_config_value("youtube_api_key", "") or "").strip()
    if not api_key:
        return (
            "YouTube istatistikleri icin once YouTube API Key gerekli. "
            "Ayarlar icinden YouTube API anahtarini gir."
        )
    channel_ref = (handle or str(get_app_config_value("youtube_channel_handle", "") or "")).strip()
    if not channel_ref:
        return "YouTube kanal adi veya handle gerekli. Ayarlara youtube_channel_handle yazabilirsin."
    try:
        limit = max(1, min(15, int(video_limit or 6)))
    except (TypeError, ValueError):
        limit = 6
    try:
        channel, videos = _fetch(api_key, channel_ref, limit)
    except Exception as exc:
        return f"YouTube raporu alinamadi: {exc}"
    snippet = channel.get("snippet") or {}
    stats = channel.get("statistics") or {}
    title = snippet.get("title", "YouTube kanalin")
    parts = [
        (
            f"Public YouTube verine gore {title} kanalinda "
            f"{int(stats.get('subscriberCount') or 0)} abone, "
            f"{int(stats.get('viewCount') or 0)} toplam goruntulenme ve "
            f"{int(stats.get('videoCount') or 0)} video var."
        )
    ]
    if videos:
        views = [int(video.get("views") or 0) for video in videos]
        average = round(sum(views) / len(views)) if views else 0
        parts.append(f"Son {len(videos)} videonun ortalama izlenmesi {average}.")
        best = max(videos, key=lambda item: int(item.get("views") or 0))
        parts.append(f"En guclu son video '{best.get('title', 'Video')}' - {int(best.get('views') or 0)} izlenme.")
    if query:
        parts.append(f"Sorgu: {query}")
    return " ".join(parts)


def _fetch(api_key: str, channel_ref: str, limit: int) -> tuple[dict, list[dict]]:
    import requests

    params = {"part": "snippet,statistics,contentDetails", "key": api_key}
    if channel_ref.startswith("UC"):
        params["id"] = channel_ref
    else:
        params["forHandle"] = channel_ref if channel_ref.startswith("@") else f"@{channel_ref.lstrip('@')}"
    response = requests.get("https://www.googleapis.com/youtube/v3/channels", params=params, timeout=15)
    response.raise_for_status()
    items = response.json().get("items") or []
    if not items:
        raise RuntimeError("Kanal bulunamadi.")
    channel = items[0]
    uploads = ((channel.get("contentDetails") or {}).get("relatedPlaylists") or {}).get("uploads", "")
    videos: list[dict] = []
    if uploads:
        playlist = requests.get(
            "https://www.googleapis.com/youtube/v3/playlistItems",
            params={"part": "snippet", "playlistId": uploads, "maxResults": limit, "key": api_key},
            timeout=15,
        )
        playlist.raise_for_status()
        ids = []
        titles = {}
        for item in playlist.json().get("items") or []:
            snippet = item.get("snippet") or {}
            video_id = ((snippet.get("resourceId") or {}).get("videoId"))
            if video_id:
                ids.append(video_id)
                titles[video_id] = snippet.get("title", "")
        if ids:
            details = requests.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={"part": "statistics", "id": ",".join(ids), "key": api_key},
                timeout=15,
            )
            details.raise_for_status()
            for item in details.json().get("items") or []:
                stats = item.get("statistics") or {}
                videos.append({"title": titles.get(item.get("id"), ""), "views": stats.get("viewCount", 0)})
    return channel, videos
