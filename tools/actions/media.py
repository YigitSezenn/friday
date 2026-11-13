from __future__ import annotations

import json
import os
import re
import subprocess
import time
import urllib.parse
from pathlib import Path

from tools.actions.browser import browser_control

VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3

_ALIASES = {
    "pause": "pause",
    "durdur": "pause",
    "duraklat": "pause",
    "sustur": "pause",
    "resume": "resume",
    "devam": "resume",
    "play": "resume",
    "stop": "stop",
    "kapat": "stop",
    "next": "next",
    "sonraki": "next",
    "previous": "previous",
    "prev": "previous",
    "onceki": "previous",
    "önceki": "previous",
    "play_pause": "play_pause",
}


def _exists(path: Path) -> bool:
    try:
        return path.exists()
    except OSError:
        return False


def spotify_path() -> Path | None:
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    candidates = [
        Path(os.environ.get("APPDATA", "")) / "Spotify" / "Spotify.exe",
        Path(os.environ.get("PROGRAMFILES", "")) / "Spotify" / "Spotify.exe",
        local / "Microsoft" / "WindowsApps" / "Spotify.exe",
    ]
    apps = local / "Microsoft" / "WindowsApps"
    if apps.is_dir():
        candidates.extend(apps.glob("SpotifyAB.SpotifyMusic_*/Spotify.exe"))
    for candidate in candidates:
        if _exists(candidate):
            return candidate
    return None


def spotify_cli_path() -> Path | None:
    local = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WindowsApps"
    candidates = [local / "spotify_cli.exe"]
    if local.is_dir():
        candidates.extend(local.glob("SpotifyAB.SpotifyMusic_*/spotify_cli.exe"))
    for candidate in candidates:
        if _exists(candidate):
            return candidate
    return None


def _press_media(vk: int) -> None:
    import ctypes

    user32 = ctypes.windll.user32
    user32.keybd_event(vk, 0, 0, 0)
    user32.keybd_event(vk, 0, 2, 0)


def play_media(query: str, provider: str = "auto", autoplay: bool = True) -> str:
    if not query or not str(query).strip():
        return "Calinacak icerik belirtilmedi."
    provider = (provider or "auto").strip().lower()
    if provider in {"yt", "youtube music"}:
        provider = "youtube"
    elif provider in {"apple music", "music", "apple_music"}:
        provider = "apple_music"
    if provider == "youtube":
        return browser_control("play_youtube", query=query)
    spotify = spotify_path()
    if provider == "spotify":
        if not spotify:
            return "Spotify yuklu gorunmuyor."
        return _play_spotify(query, spotify)
    if provider == "apple_music":
        if spotify:
            return _play_spotify(query, spotify) + " (Windows'ta Apple Music yerine Spotify kullanildi.)"
        return browser_control("play_youtube", query=query) + " (Windows'ta Apple Music yerine YouTube kullanildi.)"
    if spotify:
        return _play_spotify(query, spotify)
    return browser_control("play_youtube", query=query)


def _spotify_run(args: list[str], timeout: int = 25):
    cli = spotify_cli_path()
    if cli is None:
        raise FileNotFoundError("spotify_cli")
    result = subprocess.run(
        [str(cli), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    raw = (result.stdout or "").strip() or (result.stderr or "").strip()
    if raw.startswith("{") or raw.startswith("["):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    if result.returncode != 0:
        return {"error": raw or f"cikis {result.returncode}"}
    return {"text": raw}


def _spotify_ready() -> bool:
    state = _spotify_run(["status", "--format", "json"], timeout=8)
    if isinstance(state, dict) and state.get("running") and state.get("logged_in", True):
        return True
    _spotify_run(["open"], timeout=20)
    deadline = time.time() + 20
    while time.time() < deadline:
        time.sleep(1)
        state = _spotify_run(["status", "--format", "json"], timeout=8)
        if isinstance(state, dict) and state.get("running") and state.get("logged_in", True):
            return True
    return False


_FOLD = str.maketrans({
    "ı": "i", "İ": "i", "I": "i",
    "ş": "s", "Ş": "s",
    "ğ": "g", "Ğ": "g",
    "ü": "u", "Ü": "u",
    "ö": "o", "Ö": "o",
    "ç": "c", "Ç": "c",
})
_COLLECTION_DROP = {
    "profil", "profilim", "profilimde", "profilimdeki", "profilindeki", "profilinde",
    "kutuphane", "kutuphanem", "kutuphanemde", "kutuphanemdeki", "kutuphanendeki",
    "kitaplik", "kitapligim", "kitapligimdaki",
    "album", "albumu", "albumun", "albumunu", "albumum", "albumumu", "albumune",
    "playlist", "playlisti", "playlistini", "calmalistesi", "calma",
    "listesi", "listesini", "listeyi", "liste",
    "ki", "de", "da", "ve", "bir", "benim", "bana", "ac", "cal", "oynat", "lutfen",
    "spotify", "spotifymde", "spotifymdeki", "acik", "acarmisin",
}


def _fold_name(text: str) -> str:
    folded = (text or "").casefold().translate(_FOLD)
    return re.sub(r"[^a-z0-9]+", " ", folded).strip()


def collection_name(query: str) -> str | None:
    """Profil veya albüm/çalma listesi isteğinden kayıt adını çıkarır. Düz şarkı araması None döner."""
    words = _fold_name(query).split()
    if not words:
        return None
    marked = any(
        word.startswith("profil") or word.startswith("album") or word.startswith("playlist")
        or word.startswith("kutuphan") or word.startswith("kitaplik") or word in {"calmalistesi", "liste", "listesi"}
        for word in words
    )
    if not marked:
        return None
    kept = [
        word for word in words
        if word not in _COLLECTION_DROP
        and not word.startswith("profil")
        and not word.startswith("album")
        and not word.startswith("playlist")
        and not word.startswith("kutuphan")
        and not word.startswith("kitaplik")
    ]
    name = " ".join(kept).strip()
    return name or None


def pick_library_item(items: list, name: str) -> dict | None:
    target = _fold_name(name)
    exact = []
    partial = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        label = _fold_name(str(item.get("name") or ""))
        if not label or not str(item.get("uri") or "").startswith("spotify:"):
            continue
        if label == target:
            exact.append(item)
        elif target and (target in label or label in target):
            partial.append(item)
    chosen = exact or partial
    return chosen[0] if chosen else None


def _library_items(payload) -> list:
    if isinstance(payload, dict):
        items = payload.get("items")
        return items if isinstance(items, list) else []
    return payload if isinstance(payload, list) else []


def play_saved_collection(query: str, run=None) -> str | None:
    """Kullanıcının kendi Spotify kitaplığındaki albümü veya çalma listesini açar."""
    name = collection_name(query)
    if name is None:
        return None
    runner = run or _spotify_run
    if run is None and spotify_cli_path() is None:
        return "Spotify komut araci yok. Profildeki album acilamadi."
    albums = _library_items(runner(["library", "list", "--type", "album", "--limit", "50", "--format", "json"]))
    playlists = _library_items(runner(["library", "list", "--type", "playlist", "--limit", "50", "--format", "json"]))
    album = pick_library_item(albums, name)
    playlist = pick_library_item(playlists, name)
    folded = _fold_name(query)
    wants_album = "album" in folded
    wants_list = "playlist" in folded or "liste" in folded
    if album and playlist:
        if wants_album and not wants_list:
            chosen = album
        elif wants_list and not wants_album:
            chosen = playlist
        else:
            chosen = album
    else:
        chosen = album or playlist
    if not chosen:
        return f"Spotify profilinde '{name}' adinda album veya calma listesi yok."
    uri = str(chosen.get("uri") or "")
    played = runner(["play", uri], timeout=20)
    if isinstance(played, dict) and played.get("error"):
        return f"Spotify profilindeki kayit acilamadi: {str(played['error'])[:160]}"
    title = str(chosen.get("name") or name)
    return f"Spotify profilinde acildi: {title} ({uri})"


def spotify_now() -> dict:
    payload = _spotify_run(["now-playing", "--format", "json"], timeout=15)
    if not isinstance(payload, dict):
        return {}
    current = payload.get("currently_playing") or {}
    return current if isinstance(current, dict) else {}


def _play_spotify(query: str, spotify: Path) -> str:
    if spotify_cli_path() is None:
        return _open_spotify_search(query, spotify)
    try:
        if not _spotify_ready():
            return "Spotify acildi ama oturum hazir olmadi. Uygulamada giris yapildigini kontrol et."
        saved = play_saved_collection(query)
        if saved:
            return saved
        found = _spotify_run(["search", query.strip(), "--type", "track", "--limit", "5", "--format", "json"])
        tracks = found.get("tracks") if isinstance(found, dict) else None
        if not tracks:
            detail = found.get("error") if isinstance(found, dict) else ""
            return f"Spotify'da '{query}' icin parca bulunamadi.{(' ' + detail) if detail else ''}"
        track = tracks[0]
        uri = str(track.get("uri") or "")
        if not uri.startswith("spotify:track:"):
            return f"Spotify sonucu bir parca degil: {query}"
        played = _spotify_run(["play", uri], timeout=20)
        if isinstance(played, dict) and played.get("error"):
            return f"Spotify'da acilamadi: {str(played['error'])[:160]}"
        current = {}
        for _ in range(4):
            time.sleep(0.8)
            current = spotify_now()
            if current.get("uri") == uri and current.get("is_playing"):
                break
        if current.get("uri") != uri or not current.get("is_playing"):
            return f"Spotify'da '{query}' arandi ama parca acilmadi."
        return f"Spotify'da caliyor: {current.get('description') or track.get('name') or query} ({uri})"
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        return f"Spotify'da calinamadi: {exc}"


def _open_spotify_search(query: str, spotify: Path) -> str:
    encoded = urllib.parse.quote(query.strip())
    uri = f"spotify:search:{encoded}"
    try:
        os.startfile(str(spotify))  # type: ignore[attr-defined]
    except OSError as exc:
        return f"Spotify acilamadi: {exc}"
    try:
        os.startfile(uri)  # type: ignore[attr-defined]
    except OSError:
        import webbrowser

        webbrowser.open(f"https://open.spotify.com/search/{encoded}")
        return f"Spotify aramasi tarayicida acildi: {query}"
    return f"Spotify'da arandi ama parca acilmadi: {query}. Komut araci yok."


def control_media(action: str = "pause") -> str:
    key = _ALIASES.get((action or "").strip().lower())
    if key is None:
        return f"Bilinmeyen medya eylemi: {action}. Kullanilabilir: durdur, devam et, sonraki, onceki."
    mapping = {
        "pause": (VK_MEDIA_PLAY_PAUSE, "duraklatildi"),
        "resume": (VK_MEDIA_PLAY_PAUSE, "devam ettirildi"),
        "stop": (VK_MEDIA_STOP, "durduruldu"),
        "next": (VK_MEDIA_NEXT_TRACK, "sonraki parcaya gecildi"),
        "previous": (VK_MEDIA_PREV_TRACK, "onceki parcaya gecildi"),
        "play_pause": (VK_MEDIA_PLAY_PAUSE, "oynat/duraklat gonderildi"),
    }
    vk, label = mapping[key]
    cli_command = {"pause": "pause", "resume": "resume", "stop": "pause", "next": "next", "previous": "previous", "play_pause": "play"}[key]
    if spotify_cli_path() is not None:
        try:
            outcome = _spotify_run([cli_command], timeout=15)
            if not (isinstance(outcome, dict) and outcome.get("error")):
                return f"Medya {label} (Spotify komutu gonderildi)."
        except (OSError, subprocess.TimeoutExpired):
            pass
    try:
        _press_media(vk)
    except OSError as exc:
        return f"Medya tusu gonderilemedi: {exc}"
    return f"Medya {label} (calan uygulamaya komut gonderildi)."
