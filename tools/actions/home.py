"""Kızılötesi (IR) ev kontrolü: Broadlink köprüsü üzerinden klima/led kumandası.

Kodlar data/ir_codes.json içinde saklanır: {cihaz: {"host": ip, "codes": {komut: base64}}}.
Köprü ilk kullanımda `broadlink` paketiyle konuşur (pip install broadlink).
"""

from __future__ import annotations

import base64
import json
import time

from jarvis.paths import data_path

LEARN_SECONDS = 30


def _file():
    return data_path("ir_codes.json")


def _load() -> dict:
    try:
        return json.loads(_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save(data: dict) -> None:
    _file().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _key(name: str) -> str:
    return " ".join(str(name).lower().split())


def _bridge(host: str):
    """Köprüye bağlanır (testlerde değiştirilir)."""
    import broadlink

    device = broadlink.hello(host)
    device.auth()
    return device


def snapshot() -> dict:
    """Ayarlar ekranı için: {cihaz: {host, codes: [komut adları]}}. Kodların kendisi gönderilmez."""
    return {name: {"host": info.get("host", ""), "codes": list(info.get("codes", {}))} for name, info in _load().items()}


def _discover() -> list[str]:
    """Yerel ağdaki Broadlink köprülerinin IP adresleri (testlerde değiştirilir)."""
    import broadlink

    return [device.host[0] for device in broadlink.discover(timeout=5)]


def run(action: str, device: str = "", command: str = "", host: str = "") -> str:
    action, device, command = action.lower().strip(), _key(device), _key(command)
    data = _load()
    if action == "list":
        if not data:
            return "Kayıtlı cihaz yok. Önce action=add ile cihaz ekle."
        return "; ".join(f"{name}: {', '.join(info['codes']) or 'kod yok'}" for name, info in data.items())
    if not device:
        return "Cihaz adı gerekli."
    if action == "add":
        if not host.strip():
            try:
                found = _discover()
            except ImportError:
                return "Broadlink paketi kurulu değil (pip install broadlink)."
            except Exception as exc:
                return f"Ağda arama yapılamadı: {exc}"
            if not found:
                return "Ağda Broadlink köprüsü bulunamadı. Köprü Wi-Fi'ye bağlı, kilitsiz ve bilgisayarla aynı modemde mi?"
            if len(found) > 1:
                return f"Birden fazla köprü bulundu: {', '.join(found)}. Hangisini eklemek istediğini IP ile belirt."
            host = found[0]
        data.setdefault(device, {"codes": {}})["host"] = host.strip()
        _save(data)
        return f"{device} eklendi ({host.strip()})."
    if action == "remove":
        if device not in data:
            return f"{device} kayıtlı değil."
        if command:
            if data[device]["codes"].pop(command, None) is None:
                return f"{device} için '{command}' kodu yok."
            _save(data)
            return f"{device}: {command} kodu silindi."
        del data[device]
        _save(data)
        return f"{device} silindi."
    info = data.get(device)
    if not info:
        return f"{device} kayıtlı değil. Kayıtlı cihazlar: {', '.join(data) or 'yok'}."
    if not command:
        return "Komut adı gerekli."
    try:
        bridge = _bridge(info["host"])
        if action == "send":
            code = info["codes"].get(command)
            if not code:
                return f"{device} için '{command}' kodu öğrenilmemiş. Kayıtlı: {', '.join(info['codes']) or 'yok'}."
            bridge.send_data(base64.b64decode(code))
            return f"{device}: {command} gönderildi."
        if action == "learn":
            bridge.enter_learning()
            deadline = time.time() + LEARN_SECONDS
            while time.time() < deadline:
                time.sleep(1)
                try:
                    packet = bridge.check_data()
                except Exception:
                    continue  # henüz sinyal gelmedi
                info["codes"][command] = base64.b64encode(packet).decode("ascii")
                _save(data)
                return f"{device}: {command} kodu öğrenildi."
            return f"{LEARN_SECONDS} saniyede sinyal gelmedi. Kumandayı köprüye doğrultup tekrar dene."
    except ImportError:
        return "Broadlink paketi kurulu değil (pip install broadlink)."
    except Exception as exc:
        return f"Köprüye ulaşılamadı: {exc}"
    return f"Bilinmeyen işlem: {action}."
