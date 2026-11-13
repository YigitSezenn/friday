from __future__ import annotations


def due_nudges(now: float, state: dict, config: dict, paused: bool = False) -> list[str]:
    if paused or not config.get("proactive_enabled"):
        return []
    notes = []
    quiet = int(config.get("quiet_minutes") or 20)
    quiet = quiet if quiet in {10, 20, 40} else 20
    last_heard = float(state.get("heard") or now)
    if now - last_heard >= quiet * 60 and now - float(state.get("silence") or 0) >= quiet * 60:
        state["silence"] = now
        notes.append("Uzun sessizlik oldu. Bir kez, kisa ve israr etmeden soz al.")
    if config.get("water_enabled") and now - float(state.get("water") or 0) >= 3600:
        state["water"] = now
        notes.append("Su hatirlatmasi: kisa bir yudum oner.")
    if config.get("break_enabled") and now - float(state.get("break") or 0) >= 50 * 60:
        state["break"] = now
        notes.append("Mola hatirlatmasi: kalkip gerinmeyi kisa oner.")
    if config.get("event_alerts"):
        notes.extend(_event_note(now, state))
    return notes


def _event_note(now: float, state: dict) -> list[str]:
    if now - float(state.get("event") or 0) < 600:
        return []
    try:
        from tools.actions.calendar import get_calendar_events

        text = get_calendar_events("today")
    except Exception:
        return []
    if "etkinlik yok" in text.lower() or not text.strip():
        return []
    state["event"] = now
    first = next((line for line in text.splitlines() if line.startswith("- ")), "")
    if not first:
        return []
    return [f"Yaklasan takvim: {first[2:]} Bir kez haber ver."]
