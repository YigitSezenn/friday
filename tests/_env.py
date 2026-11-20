"""Ortam gerektiren testler için işaretler.

Varsayılan test koşusu (her ortamda) yalnızca kendi kendine yeten testleri çalıştırır.
- windows_only: PowerShell, os.startfile, Spotify gibi Windows'a özgü işler.
- needs_network: gerçek internet (YouTube, DuckDuckGo, Google). FRIDAY_OFFLINE=1 ile hep atlanır.
- needs_module: isteğe bağlı paket (qrcode, cv2) yoksa atla.
- needs_gate: Kapı sunucu kodu (gate/) bu depoda yoksa atla.
- live_api: gerçek Gemini çağrısı; yalnızca FRIDAY_TEST_GEMINI_KEY verilince.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

windows_only = unittest.skipUnless(sys.platform == "win32", "yalnızca Windows")

_net: bool | None = None


def _online() -> bool:
    global _net
    if _net is None:
        if os.environ.get("FRIDAY_OFFLINE") == "1":
            _net = False
        else:
            try:
                import requests

                requests.head("https://www.google.com", timeout=4)
                _net = True
            except Exception:
                _net = False
    return _net


def needs_network(test):
    def wrapper(self, *args, **kwargs):
        if not _online():
            self.skipTest("internet yok")
        return test(self, *args, **kwargs)

    wrapper.__name__ = test.__name__
    wrapper.__doc__ = test.__doc__
    return wrapper


def needs_module(*names: str):
    missing = [name for name in names if importlib.util.find_spec(name) is None]
    return unittest.skipIf(missing, "eksik paket: " + ", ".join(missing))


needs_gate = unittest.skipUnless((ROOT / "gate" / "logic.py").exists(), "Kapı sunucu kodu (gate/) bu depoda yok")

live_api = unittest.skipUnless(os.environ.get("FRIDAY_TEST_GEMINI_KEY"), "FRIDAY_TEST_GEMINI_KEY verilmedi")



def decode_qr(image) -> str:
    """cv2'nin varsayılan okuyucusu rastgele kodların ~%5'ini okuyamıyor; varsa Aruco okuyucu kullanılır."""
    import cv2
    import numpy as np

    detector = cv2.QRCodeDetectorAruco() if hasattr(cv2, "QRCodeDetectorAruco") else cv2.QRCodeDetector()
    value, _points, _ = detector.detectAndDecode(np.array(image))
    return value
