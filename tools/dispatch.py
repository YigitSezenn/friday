"""Arac bildirimleri ve cagri girisi. Isleyiciler tools/handlers.py icindedir."""

from __future__ import annotations

from tools.handlers import HANDLERS, ToolContext

TOOL_DECLARATIONS = [
    {"name": "open_app", "description": "Windows'ta bir uygulamayi açar.", "parameters": {"type": "OBJECT", "properties": {"app_name": {"type": "STRING"}}, "required": ["app_name"]}},
    {"name": "sys_info", "description": "Pil, CPU, RAM, disk, saat, tarih veya ag bilgisi.", "parameters": {"type": "OBJECT", "properties": {"query": {"type": "STRING", "description": "battery|cpu|ram|disk|time|date|network|all"}}, "required": ["query"]}},
    {"name": "get_weather", "description": "Anlik hava durumu. Konum boş ise bulunan şehir kullanilir.", "parameters": {"type": "OBJECT", "properties": {"location": {"type": "STRING"}}}},
    {"name": "get_calendar_events", "description": "Takvimi okur. Outlook aciksa Outlook, değilse JARVIS yerel takvimi.", "parameters": {"type": "OBJECT", "properties": {"query": {"type": "STRING"}, "limit": {"type": "NUMBER"}}, "required": ["query"]}},
    {"name": "add_calendar_event", "description": "Takvime etkinlik ekler.", "parameters": {"type": "OBJECT", "properties": {"title": {"type": "STRING"}, "start_iso": {"type": "STRING"}, "end_iso": {"type": "STRING"}, "location": {"type": "STRING"}, "notes": {"type": "STRING"}, "calendar_name": {"type": "STRING"}, "all_day": {"type": "BOOLEAN"}}, "required": ["title", "start_iso"]}},
    {"name": "delete_calendar_event", "description": "Takvimden etkinlik siler.", "parameters": {"type": "OBJECT", "properties": {"title": {"type": "STRING"}, "start_iso": {"type": "STRING"}, "calendar_name": {"type": "STRING"}, "delete_all_matches": {"type": "BOOLEAN"}}, "required": ["title"]}},
    {"name": "get_reminders", "description": "Animsaticilari okur.", "parameters": {"type": "OBJECT", "properties": {"query": {"type": "STRING"}, "limit": {"type": "NUMBER"}, "list_name": {"type": "STRING"}}, "required": ["query"]}},
    {"name": "add_reminder", "description": "Anımsatıcı ekler. 'N dakika/saat sonra' denince saati kendin hesaplama: after_minutes ver (1 saat = 60). Tek istek için yalnızca bir kez çağır.", "parameters": {"type": "OBJECT", "properties": {"title": {"type": "STRING"}, "due_iso": {"type": "STRING"}, "notes": {"type": "STRING"}, "list_name": {"type": "STRING"}, "priority": {"type": "STRING"}, "all_day": {"type": "BOOLEAN"}, "after_minutes": {"type": "NUMBER"}}, "required": ["title"]}},
    {"name": "complete_reminder", "description": "Anımsatıcıyı tamamlandi olarak isaretler.", "parameters": {"type": "OBJECT", "properties": {"title": {"type": "STRING"}, "id": {"type": "STRING"}}}},
    {"name": "delete_reminder", "description": "Anımsatıcıyı siler.", "parameters": {"type": "OBJECT", "properties": {"title": {"type": "STRING"}, "id": {"type": "STRING"}}}},
    {"name": "browser_control", "description": "URL açar, Google'da arar veya YouTube videosu açar.", "parameters": {"type": "OBJECT", "properties": {"action": {"type": "STRING"}, "url": {"type": "STRING"}, "query": {"type": "STRING"}}, "required": ["action"]}},
    {"name": "shell_run", "description": "Güvenlik filtreli PowerShell komutu calistirir. Okuma disindaki komutlar önce ONAY GEREKLİ doner; kullanıcı evet derse confirm=true ile tekrar çağır. Çıktıyı kendin okuyup söylersin. Kullanıcı komut istemi/terminal PENCERESİNDE görmek veya orada çalıştırmak isterse visible=true ver; pencere açılır ve komut orada çalışır. Boş terminal açıp kullanıcıdan komut yazmasını isteme. winget/pip/npm gibi uzun süren komutlar otomatik olarak görünür pencerede çalışır.", "parameters": {"type": "OBJECT", "properties": {"command": {"type": "STRING"}, "confirm": {"type": "BOOLEAN"}, "visible": {"type": "BOOLEAN"}}, "required": ["command"]}},
    {"name": "toggle_webcam", "description": "Kamerayi açar veya kapatir.", "parameters": {"type": "OBJECT", "properties": {"action": {"type": "STRING"}}, "required": ["action"]}},
    {"name": "home_control", "description": "Evdeki kızılötesi (IR) cihazları (klima, masa ledi) Broadlink köprüsüyle yönetir. action: send (kayıtlı kodu gönder: 'salon klima aç' → device='salon klima', command='aç'), learn (kullanıcı kumandaya basınca kodu öğren), list (kayıtlı cihaz ve komutlar), add (cihaz ekle; host boşsa köprü ağda otomatik bulunur), remove (cihazı ya da verilen komutun kodunu sil). Onay istemez. Kullanıcı hangi cihazı kastettiğini söylemediyse önce list ile bak.", "parameters": {"type": "OBJECT", "properties": {"action": {"type": "STRING"}, "device": {"type": "STRING"}, "command": {"type": "STRING"}, "host": {"type": "STRING"}}, "required": ["action"]}},
    {"name": "file_access", "description": "Kullanıcının izin verdiği klasörlerde (Belgeler, İndirilenler, Masaüstü) dosya listeler, arar, okur, yazar, taşır, siler. action: list|find|read|write|move|delete. write/delete önce onay ister; move (taşıma) onay istemez, hemen yap: kullanıcıya sesli sor, evet derse aynı bilgilerle confirm=true ile tekrar çağır. Silme çöpe taşır. Birden çok dosyayı taşırken path içine yolları | ile ayırarak yaz; tek onay yeter, destination klasör olur (yoksa oluşturulur).", "parameters": {"type": "OBJECT", "properties": {"action": {"type": "STRING"}, "path": {"type": "STRING"}, "destination": {"type": "STRING"}, "content": {"type": "STRING"}, "query": {"type": "STRING"}, "confirm": {"type": "BOOLEAN"}}, "required": ["action"]}},
    {"name": "play_media", "description": "Spotify veya YouTube'da içerik açar.", "parameters": {"type": "OBJECT", "properties": {"query": {"type": "STRING"}, "provider": {"type": "STRING"}, "autoplay": {"type": "BOOLEAN"}}, "required": ["query"]}},
    {"name": "notes_list", "description": "Kullanıcının notlarini numarali okur. 'Notlarimi oku', 'notlarimda ne var' gibi isteklerde.", "parameters": {"type": "OBJECT", "properties": {}}},
    {"name": "note_add", "description": "Not ekler ('not al: ...').", "parameters": {"type": "OBJECT", "properties": {"text": {"type": "STRING"}}, "required": ["text"]}},
    {"name": "note_delete", "description": "Notu siler. target: notun numarası (1'den) ya da içinden bir kelime.", "parameters": {"type": "OBJECT", "properties": {"target": {"type": "STRING"}}, "required": ["target"]}},
    {"name": "note_edit", "description": "Notu değiştirir. target: numara ya da içinden kelime; text: yeni metin.", "parameters": {"type": "OBJECT", "properties": {"target": {"type": "STRING"}, "text": {"type": "STRING"}}, "required": ["target", "text"]}},
    {"name": "timer_set", "description": "Geri sayim zamanlayıcısı kurar (önceki varsa değiştirir). Süre dolunca alarm calar ve haber verilir.", "parameters": {"type": "OBJECT", "properties": {"minutes": {"type": "NUMBER"}, "seconds": {"type": "NUMBER"}, "label": {"type": "STRING", "description": "ornek: makarna, mola"}}}},
    {"name": "timer_add", "description": "Çalışan zamanlayıcıya süre ekler (negatif: kisaltir). 'Bes dakika daha ekle'.", "parameters": {"type": "OBJECT", "properties": {"minutes": {"type": "NUMBER"}, "seconds": {"type": "NUMBER"}}}},
    {"name": "timer_cancel", "description": "Zamanlayiciyi iptal eder.", "parameters": {"type": "OBJECT", "properties": {}}},
    {"name": "timer_status", "description": "Zamanlayicida ne kadar kaldigini ve kronometreyi soyler.", "parameters": {"type": "OBJECT", "properties": {}}},
    {"name": "stopwatch", "description": "Kronometre: action start|stop|reset|toggle.", "parameters": {"type": "OBJECT", "properties": {"action": {"type": "STRING"}}}},
    {"name": "sleep_mode", "description": "FRIDAY'i uyku moduna alir (mikrofon dinlemeyi birakir). Kullanici tek basina 'uyu', 'uyku moduna gec', 'git uyu', 'iyi geceler', 'sus', 'sessize gec', 'biraz dinlen', 'dinlemeyi birak' dediginde HEMEN asleep=true ile cagir; onay isteme. 'Uyan' dediginde asleep=false.", "parameters": {"type": "OBJECT", "properties": {"asleep": {"type": "BOOLEAN"}}}},
    {"name": "app_window", "description": "FRIDAY penceresinin kendisi. 'Kucul', 'kendini kucult', 'arka plana gec' -> action=minimize. 'Kendini kapat', 'kapan', 'uygulamayi kapat' -> action=close (veda et). Geri getirmek icin restore. Baska pencereler icin desktop_action kullan.", "parameters": {"type": "OBJECT", "properties": {"action": {"type": "STRING"}}, "required": ["action"]}},
    {"name": "desktop_action", "description": "Masaustu komutu. action: show_desktop (masaustunu goster), minimize_all (hepsini kucult), restore_all (geri getir), task_view, maximize/minimize (aktif pencere), lock (ekrani kilitle), screenshot (ekran goruntusu kaydet).", "parameters": {"type": "OBJECT", "properties": {"action": {"type": "STRING"}}, "required": ["action"]}},
    {"name": "set_volume", "description": "Bir uygulamanin (spotify, youtube/tarayıcı, discord...) ya da bilgisayarın genel sesini ayarlar. level: 0-100 kesin deger; change: +10/-10 gibi goreli; mute: sessize al/aç.", "parameters": {"type": "OBJECT", "properties": {"target": {"type": "STRING", "description": "spotify|youtube|system|uygulama adı"}, "level": {"type": "NUMBER"}, "change": {"type": "NUMBER"}, "mute": {"type": "BOOLEAN"}}, "required": ["target"]}},
    {"name": "control_media", "description": "Çalan medyayi durdurur, devam ettirir veya parça değiştirir.", "parameters": {"type": "OBJECT", "properties": {"action": {"type": "STRING"}}, "required": ["action"]}},
    {"name": "get_youtube_channel_report", "description": "YouTube kanal istatistiklerini raporlar.", "parameters": {"type": "OBJECT", "properties": {"query": {"type": "STRING"}, "handle": {"type": "STRING"}, "video_limit": {"type": "NUMBER"}}}},
    {"name": "analyze_screen", "description": "Aktif pencerenin goruntusunu okur.", "parameters": {"type": "OBJECT", "properties": {"query": {"type": "STRING"}, "target": {"type": "STRING"}}}},
    {"name": "save_memory", "description": "Kalıcı hafızaya kaydeder.", "parameters": {"type": "OBJECT", "properties": {"category": {"type": "STRING"}, "key": {"type": "STRING"}, "value": {"type": "STRING"}}, "required": ["category", "key", "value"]}},
    {"name": "delete_memory", "description": "Kalıcı hafızadan kayıt siler.", "parameters": {"type": "OBJECT", "properties": {"category": {"type": "STRING"}, "key": {"type": "STRING"}, "match_text": {"type": "STRING"}}}},
    {"name": "send_whatsapp_message", "description": "WhatsApp mesaji hazırlar veya gondermeye çalışır.", "parameters": {"type": "OBJECT", "properties": {"message": {"type": "STRING"}, "phone_number": {"type": "STRING"}, "recipient_name": {"type": "STRING"}, "send_now": {"type": "BOOLEAN"}, "app_target": {"type": "STRING"}, "confirm": {"type": "BOOLEAN", "description": "Kullanıcı 'gönder' onayini verdikten sonra true"}}, "required": ["message"]}},
    {"name": "send_email", "description": "E-posta gonderir: Gmail API bagliysa Gmail, değilse klasik Outlook, o da yoksa tarayıcıdaki Gmail'den gonderir (doldurur, onaydan sonra kendisi Gönder'e basar). Gonderimde ilk cagri onay ister; kullanıcı evet derse confirm=true ile tekrar çağır.", "parameters": {"type": "OBJECT", "properties": {"to": {"type": "STRING"}, "recipient_name": {"type": "STRING"}, "subject": {"type": "STRING"}, "body": {"type": "STRING"}, "confirm": {"type": "BOOLEAN"}, "provider": {"type": "STRING", "description": "auto|gmail|outlook|taslak (outlook: klasik yoksa tarayıcıdaki Outlook)"}}, "required": ["body"]}},
    {"name": "save_email_contact", "description": "E-posta kişisi kaydeder.", "parameters": {"type": "OBJECT", "properties": {"display_name": {"type": "STRING"}, "email": {"type": "STRING"}, "aliases": {"type": "STRING"}}, "required": ["display_name", "email"]}},
    {"name": "connect_gmail", "description": "Gmail API bağlantısı kurar (Google izin ekranı açar). YALNIZCA kullanıcı açıkça 'Gmail'i bağla' derse çağır; mail göndermek için GEREKMEZ (send_email tarayıcıdaki Gmail ile gönderir).", "parameters": {"type": "OBJECT", "properties": {}}},
    {"name": "open_mail", "description": "Gelen kutusunu açar (Gmail ya da Outlook).", "parameters": {"type": "OBJECT", "properties": {"provider": {"type": "STRING", "description": "auto|gmail|outlook"}}}},
    {"name": "save_whatsapp_contact", "description": "WhatsApp kişisi kaydeder.", "parameters": {"type": "OBJECT", "properties": {"display_name": {"type": "STRING"}, "phone_number": {"type": "STRING"}, "aliases": {"type": "STRING"}}, "required": ["display_name", "phone_number"]}},
    {"name": "web_search", "description": "Internette kısa bir özet arar.", "parameters": {"type": "OBJECT", "properties": {"query": {"type": "STRING"}}, "required": ["query"]}},
    {"name": "list_files", "description": "Masaüstü, Belgeler veya Indirilenler klasorunu listeler.", "parameters": {"type": "OBJECT", "properties": {"folder": {"type": "STRING"}}, "required": ["folder"]}},
    {"name": "set_location", "description": "Kalıcı konumu değiştirir (hava ve harita da gecer). Kullanıcı \"Konumum artik Izmir\" veya \"Kadikoy'deyim\" derse çağır. auto=true ise konum yeniden internetten bulunur.", "parameters": {"type": "OBJECT", "properties": {"location": {"type": "STRING"}, "auto": {"type": "BOOLEAN"}}}},
]

ERROR_MARKERS = (
    "hata", "error", "alinamadi", "alınamadı", "bulunamadi", "bulunamadı",
    "acilamadi", "açılamadı", "tamamlanamadi", "tamamlanamadı", "gecersiz",
    "geçersiz", "izin gerekiyor", "izin gerekli", "baglanti", "bağlantı", "gerekli.",
)


def looks_like_error(result) -> bool:
    text = str(result or "").strip().lower()
    return bool(text) and any(marker in text for marker in ERROR_MARKERS)


def execute_tool(name: str, args: dict, webcam=None, ui=None) -> str:
    return _run_tool(name, args, webcam, ui)


def _run_tool(name: str, args: dict, webcam=None, ui=None) -> str:
    handler = HANDLERS.get(name)
    if handler is None:
        return f"Bilinmeyen araç: {name}"
    return handler(args or {}, ToolContext(webcam=webcam, ui=ui))
