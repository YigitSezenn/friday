from __future__ import annotations

import json

from jarvis.paths import data_path

ACHIEVEMENTS = (
    ("screen", "İlk bakış", "Ekranı bir kez okut."),
    ("weather", "Gökyüzü", "Hava durumunu sor."),
    ("calendar", "Gün", "Takvime bak."),
    ("phone", "Bağ", "Telefonu aynı Wi-Fi'da eşle."),
    ("memory", "Anı", "Bir şeyi hatırlamasını iste."),
    ("search", "İz", "Bir arama yaptır."),
)
HINTS = {
    "screen": "Ekranda ne var, diye sor.",
    "weather": "Hava nasıl, diye sor.",
    "calendar": "Bugün takvimde ne var, diye sor.",
    "phone": "Ayarlar › Telefon'dan QR'ı okut.",
    "memory": "Bunu hatırla, de.",
    "search": "Bir şeyi internetten baktırmayı dene.",
}
TOOL_MARK = {
    "analyze_screen": "screen",
    "get_weather": "weather",
    "get_calendar_events": "calendar",
    "add_calendar_event": "calendar",
    "save_memory": "memory",
    "web_search": "search",
}


def _path():
    return data_path("config", "story.json")


def _load() -> dict:
    try:
        raw = json.loads(_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raw = {}
    got = raw.get("got") if isinstance(raw, dict) else {}
    if not isinstance(got, dict):
        got = {}
    ending = str(raw.get("ending") or "") if isinstance(raw, dict) else ""
    if ending not in {"", "surdur", "kapat"}:
        ending = ""
    return {"got": {key: bool(got.get(key)) for key, _title, _hint in ACHIEVEMENTS}, "ending": ending}


def _save(state: dict) -> None:
    _path().write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def enabled() -> bool:
    from jarvis.config import get_app_config_value

    return bool(get_app_config_value("story_enabled", False))


def note_tool(name: str, result: str) -> None:
    if not enabled():
        return
    text = str(result or "").lower()
    if any(word in text for word in ("hata", "tamamlanamadi", "yapilamadi", "bulunamadi")):
        return
    key = TOOL_MARK.get(name)
    if not key:
        return
    state = _load()
    if state["got"].get(key):
        return
    state["got"][key] = True
    _save(state)


def note_phone() -> None:
    if not enabled():
        return
    state = _load()
    state["got"]["phone"] = True
    _save(state)


def choose(ending: str) -> str:
    if not enabled():
        return "Hikaye kapali."
    ending = ending if ending in {"surdur", "kapat"} else ""
    if not ending:
        return "Secim gecersiz."
    state = _load()
    state["ending"] = ending
    _save(state)
    if ending == "surdur":
        return "Hikaye suruyor. Basarimlar duruyor."
    return "Hikaye burada kapandi. Basarimlar saklandi."


def view() -> dict:
    state = _load()
    rows = []
    missing = []
    for key, title, detail in ACHIEVEMENTS:
        got = bool(state["got"].get(key))
        rows.append({"key": key, "title": title, "detail": detail, "got": got})
        if not got:
            missing.append(HINTS[key])
    return {
        "enabled": enabled(),
        "ending": state["ending"],
        "achievements": rows,
        "hints": missing[:2] if enabled() and not state["ending"] else [],
    }


def prompt_block() -> str:
    if not enabled():
        return ""
    state = view()
    done = [row["title"] for row in state["achievements"] if row["got"]]
    pending = state["hints"]
    ending = state["ending"]
    lines = [
        "\nHİKÂYE MODU AÇIK:",
        "- Kısa bir gizli iz sürüyorsun. Başarımları ve ipuçlarını uydurma; yalnızca aşağıdakileri kullan.",
        "- İptal edilirse hikâye susar, kayıt silinmez.",
    ]
    if done:
        lines.append("- Açılanlar: " + ", ".join(done) + ".")
    if pending and not ending:
        lines.append("- Sıradaki ipucu, kullanıcı sorarsa: " + pending[0])
    if ending == "kapat":
        lines.append("- Son karar verildi: hikâye kapandı. Yeni ipucu verme.")
    elif ending == "surdur":
        lines.append("- Son karar: hikâye sürüyor.")
    return "\n".join(lines) + "\n"
