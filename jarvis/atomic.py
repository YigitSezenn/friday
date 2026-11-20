"""Güvenli dosya yazımı: önce geçici dosya, sonra tek adımda yer değiştirme.

Yazma ortasında çökme ya da elektrik kesintisi olursa eski dosya bozulmadan kalır.
`LOCK` aynı süreçte iki iş parçacığının oku-değiştir-yaz yarışını önler.
"""
from __future__ import annotations

import os
import tempfile
import threading
from pathlib import Path

LOCK = threading.RLock()


def write_text(path, text: str, encoding: str = "utf-8") -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with LOCK:
        fd, tmp = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent))
        try:
            with os.fdopen(fd, "w", encoding=encoding, newline="") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, target)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
