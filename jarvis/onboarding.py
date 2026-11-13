"""İlk açılış: anahtar yokken servis kalkmaz, hazır olunca ekran metni üretilir."""

READY_TEXT = "Her şey çalıştı. FRIDAY ayakta."


def onboarding_view(*, has_key: bool, connected: bool, mic_ok: bool) -> dict:
    ready = bool(has_key and connected and mic_ok)
    return {
        "show_welcome": not has_key,
        "start_services": bool(has_key),
        "steps": {
            "key": bool(has_key),
            "link": bool(connected),
            "mic": bool(mic_ok),
        },
        "ready": ready,
        "message": READY_TEXT if ready else "",
    }
