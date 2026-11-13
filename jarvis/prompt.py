from __future__ import annotations

from jarvis.paths import resource_path

WINDOWS_REPLACEMENTS: list[tuple[str, str]] = [
    ("macOS'ta çalışan", "Windows'ta çalışan"),
    ("Apple Calendar takvimini okur", "takvimi okur (Outlook veya JARVIS yerel takvimi)"),
    ("Apple Calendar takvimine yeni etkinlik ekler", "takvime yeni etkinlik ekler"),
    ("Apple Calendar takviminden etkinlik siler", "takvimden etkinlik siler"),
    ("Apple Anımsatıcılar listesini okur", "anımsatıcı listesini okur"),
    ("Apple Anımsatıcılar'a yeni kayıt ekler", "anımsatıcılara yeni kayıt ekler"),
    (
        "play_media: YouTube, Spotify veya Apple Music/Music içinde içerik açar ve mümkünse oynatır",
        "play_media: YouTube veya Spotify içinde içerik açar ve mümkünse oynatır",
    ),
    ("shell_run: Terminal komutu çalıştırır", "shell_run: PowerShell komutu çalıştırır"),
    (
        '- "Masaüstündeki dosyaları listele" → shell_run("ls ~/Desktop")',
        '- "Masaüstündeki dosyaları listele" → shell_run("Get-ChildItem $env:USERPROFILE\\Desktop")',
    ),
    (
        '- "Apple Music\'te Sezen Aksu Gülümse aç" → play_media(query="Sezen Aksu Gülümse", provider="apple_music", autoplay=true)',
        '- "Sezen Aksu Gülümse çal" → play_media(query="Sezen Aksu Gülümse", provider="auto", autoplay=true)',
    ),
]

WINDOWS_NOTE = (
    "\nPLATFORM NOTU (Windows):\n"
    "- Kabuk komutlari PowerShell sozdizimiyle yazilir (ls degil Get-ChildItem, "
    "dosya yollarinda ters bolu).\n"
    "- Takvim ve animsaticilar Outlook yapilandirilmissa Outlook'a, degilse "
    "JARVIS'in kendi yerel takvimine yazilir. Kullanici sormadikca bu ayrimi anlatma.\n"
    "- Apple Music yoktur; muzik istekleri Spotify veya YouTube uzerinden karsilanir.\n"
    "- get_health_data bu Windows surumunde yoktur; saglik orneklerini uygulama.\n"
)

FALLBACK_PROMPT = (
    "Sen JARVIS'sin — Windows'ta çalışan kişisel AI asistanı. "
    "Türkçe konuş. Kısa ve net yanıtlar ver. "
    "Araçları kullanarak görevleri tamamla, asla taklit etme."
)


def adapt_prompt(text: str) -> str:
    for mac_text, win_text in WINDOWS_REPLACEMENTS:
        text = text.replace(mac_text, win_text)
    if "PLATFORM NOTU (Windows)" not in text:
        text += WINDOWS_NOTE
    return text


def load_system_prompt() -> str:
    path = resource_path("prompts", "prompt.txt")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        text = FALLBACK_PROMPT
    else:
        text = adapt_prompt(text)
    from jarvis.config import persona_note
    from jarvis.language import instruction
    from jarvis.story import prompt_block

    return instruction() + text + persona_note() + prompt_block()
