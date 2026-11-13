from __future__ import annotations

# Installed app jarvis.language: (görünen ad, yazı dili, konuşma kodu, ad, yönelme).
LANGUAGES = {
    "auto": ("OTOMATİK", None, None, "", ""),
    "tr": ("TÜRKÇE", "tr-TR", "tr", "Türkçe", "Türkçeye"),
    "en": ("İNGİLİZCE", "en-US", "en", "İngilizce", "İngilizceye"),
    "fr": ("FRANSIZCA", "fr-FR", "fr", "Fransızca", "Fransızcaya"),
    "ar": ("ARAPÇA", "ar-SA", "ar", "Arapça", "Arapçaya"),
    "az": ("AZERİCE", "az-AZ", "az", "Azerice", "Azericeye"),
}


def current(config: dict | None = None) -> str:
    from jarvis.config import load_app_config

    key = str((config or load_app_config()).get("language") or "auto").strip().lower()
    return key if key in LANGUAGES else "auto"


def choices() -> list[dict[str, str]]:
    return [{"key": key, "name": row[0]} for key, row in LANGUAGES.items()]


def ui_language(config: dict | None = None) -> str:
    key = current(config)
    return "tr" if key == "auto" else key


def speech_language(config: dict | None = None) -> str:
    return LANGUAGES[ui_language(config)][2] or "tr"


def live_speech_code(model: str, config: dict | None = None) -> str | None:
    """Yerel ses modeli 'tr' kodunu reddedip oturumu düşürüyor. O modele kod gönderilmez."""
    if "native-audio" in str(model or ""):
        return None
    return speech_language(config)


def speech_codes(config: dict | None = None) -> list[str]:
    key = current(config)
    if key == "auto":
        return ["tr-TR", "en-US"]
    return [LANGUAGES[key][1]]


def _letter_rule(key: str) -> str:
    if key in {"auto", "tr"}:
        return (
            "[YAZI] Kullanıcının yazdığı ve senin yazdığın metinde ç, ğ, ı, İ, ö, ş, ü harfleri olduğu gibi kalır. "
            "Bunları ascii karşılıklarına çevirme.\n"
        )
    _label, _bcp, _speech, word, _toward = LANGUAGES[key]
    return f"[YAZI] Yanıtını {word} yaz ve o dilin harflerini olduğu gibi bırak.\n"


def instruction(config: dict | None = None) -> str:
    key = current(config)
    letters = _letter_rule(key)
    if key == "auto":
        return letters
    _label, _bcp, _speech, word, toward = LANGUAGES[key]
    return letters + (
        f"[KONUŞMA DİLİ: {word.upper()}] Bu kural aşağıdaki bütün dil kurallarından önce gelir. "
        f"Kullanıcı {word} konuşuyor: söylediklerini her zaman {word} olarak anla "
        f"(başka bir dile benzeyen sesleri de {word} sözcükler olarak yorumla) ve her zaman yalnızca {word} yanıt ver. "
        f"Aşağıdaki talimatlar Türkçe yazılmış olsa da konuşman {word} olsun; karakterini, hitaplarını ve esprilerini {toward} uyarla.\n"
    )
