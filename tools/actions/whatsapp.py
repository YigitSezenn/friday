from __future__ import annotations

import re
import unicodedata
import urllib.parse

from jarvis.memory_store import load_memory, update_memory
from jarvis.paths import data_path


def normalize_phone(phone_number: str) -> str:
    digits = re.sub(r"\D+", "", phone_number or "")
    if len(digits) == 11 and digits.startswith("0"):
        digits = "90" + digits[1:]
    elif len(digits) == 10:
        digits = "90" + digits
    if len(digits) < 8 or len(digits) > 15:
        raise ValueError("Telefon numarasi uluslararasi formatta olmali. Orn: +905551112233")
    return digits


def _normalize_lookup(text: str) -> str:
    text = (text or "").strip().casefold()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("ı", "i")
    return re.sub(r"\s+", " ", text).strip()


def contact_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _normalize_lookup(name)).strip("_") or "contact"


def _phone_book() -> dict:
    path = data_path("memory", "phone_book.json")
    try:
        if path.exists():
            data = __import__("json").loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}
    return {}


def _candidates() -> list[dict]:
    items = []
    sources = (
        ("whatsapp", load_memory().get("whatsapp_contacts", {})),
        ("phone_book", _phone_book()),
    )
    for source_name, source in sources:
        if not isinstance(source, dict):
            continue
        for key, entry in source.items():
            if not isinstance(entry, dict):
                continue
            item = dict(entry)
            item.setdefault("display_name", key)
            item["_source"] = source_name
            item["_key"] = key
            items.append(item)
    return items


def _match_score(needle: str, candidate: str) -> int:
    candidate_norm = _normalize_lookup(candidate)
    if not candidate_norm:
        return 0
    if candidate_norm == needle:
        return 300
    if candidate_norm.startswith(needle) or needle.startswith(candidate_norm):
        return 220
    if needle in candidate_norm:
        return 160
    parts = needle.split()
    if parts and all(part in candidate_norm for part in parts):
        return 120
    return 0


def find_contact(recipient_name: str) -> dict | None:
    needle = _normalize_lookup(recipient_name)
    if not needle:
        return None
    best, best_score = None, 0
    for entry in _candidates():
        names = [entry.get("display_name", ""), entry.get("_key", "")]
        aliases = entry.get("aliases", [])
        if isinstance(aliases, list):
            names.extend(str(alias) for alias in aliases)
        for name in names:
            score = _match_score(needle, str(name))
            if score > best_score:
                best, best_score = entry, score
    return best if best_score else None


def save_whatsapp_contact(display_name: str, phone_number: str, aliases: str = "") -> str:
    if not display_name or not display_name.strip():
        return "Kisi adi bos olamaz."
    try:
        normalized = normalize_phone(phone_number)
    except ValueError as exc:
        return str(exc)
    alias_list = [part.strip() for part in (aliases or "").split(",") if part.strip()]
    update_memory(
        {
            "whatsapp_contacts": {
                contact_key(display_name): {
                    "value": f"+{normalized}",
                    "display_name": display_name.strip(),
                    "aliases": alias_list,
                }
            }
        }
    )
    if alias_list:
        return f"{display_name.strip()} WhatsApp kisilerine kaydedildi. Takma adlar: {', '.join(alias_list)}"
    return f"{display_name.strip()} WhatsApp kisilerine kaydedildi."


def send_whatsapp_message(
    message: str,
    phone_number: str = "",
    recipient_name: str = "",
    send_now: bool = False,
    app_target: str = "auto",
) -> str:
    if not message or not message.strip():
        return "Mesaj bos olamaz."
    normalized = ""
    if phone_number and phone_number.strip():
        try:
            normalized = normalize_phone(phone_number)
        except ValueError as exc:
            return str(exc)
    resolved = (recipient_name or "").strip()
    contact = find_contact(resolved) if resolved else None
    source = ""
    if contact and not normalized:
        try:
            normalized = normalize_phone(str(contact.get("value", "")))
        except ValueError:
            normalized = ""
        resolved = str(contact.get("display_name", resolved)).strip() or resolved
        source = str(contact.get("_source", ""))
    if not normalized:
        if resolved:
            return f"'{resolved}' icin kayitli bir telefon numarasi bulamadim. Istersen once kisiyi numarasiyla kaydet."
        return "WhatsApp mesaji icin kisi adi veya telefon numarasi gerekli."
    encoded = urllib.parse.quote(message.strip())
    url = f"https://web.whatsapp.com/send?phone={normalized}&text={encoded}"
    desktop = f"whatsapp://send?phone={normalized}&text={encoded}"
    import webbrowser

    opened = "WhatsApp Web"
    target = (app_target or "auto").strip().lower()
    try:
        if target in {"auto", "desktop"}:
            os_start = getattr(__import__("os"), "startfile", None)
            if os_start:
                try:
                    os_start(desktop)
                    opened = "WhatsApp Desktop"
                except OSError:
                    webbrowser.open(url)
            else:
                webbrowser.open(url)
        else:
            webbrowser.open(url)
    except OSError as exc:
        return f"WhatsApp acilamadi: {exc}"
    label = resolved or f"+{normalized}"
    note = " (rehberden bulundu)" if source == "phone_book" else ""
    chosen = desktop if opened == "WhatsApp Desktop" else url
    if not send_now:
        return f"WhatsApp sohbeti {opened} icinde {label}{note} icin taslak mesajla acildi: {chosen}"
    try:
        _press_enter()
    except OSError as exc:
        return (
            f"WhatsApp sohbeti acildi ama otomatik gonderim tamamlanamadi ({exc}). "
            "Sohbet hazir — Enter'a basman yeterli."
        )
    return f"WhatsApp uzerinden {label}{note} kisisine mesaj gonderildi."


def _press_enter() -> None:
    import ctypes
    import time

    time.sleep(1.2)
    user32 = ctypes.windll.user32
    user32.keybd_event(0x0D, 0, 0, 0)
    user32.keybd_event(0x0D, 0, 2, 0)
