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


def instruction(config: dict | None = None) -> str:
    key = current(config)
    if key == "auto":
        return ""
    _label, _bcp, _speech, word, toward = LANGUAGES[key]
    return (
        f"[KONUŞMA DİLİ: {word.upper()}] Bu kural aşağıdaki bütün dil kurallarından önce gelir. "
        f"Kullanıcı {word} konuşuyor: söylediklerini her zaman {word} olarak anla "
        f"(başka bir dile benzeyen sesleri de {word} sözcükler olarak yorumla) ve her zaman yalnızca {word} yanıt ver. "
        f"Aşağıdaki talimatlar Türkçe yazılmış olsa da konuşman {word} olsun; karakterini, hitaplarını ve esprilerini {toward} uyarla.\n"
    )
