"""Kameradan el noktaları (MediaPipe). Model ilk kullanımda, kullanıcı onayından sonra indirilir."""

from __future__ import annotations

import os
import time
import urllib.request
from pathlib import Path

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
MIN_BYTES = 1_000_000


def model_path() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "FRIDAY" / "models" / "hand_landmarker.task"


def model_ready() -> bool:
    path = model_path()
    return path.is_file() and path.stat().st_size >= MIN_BYTES


def ensure_model(timeout: float = 60.0) -> str:
    """'' başarılı, aksi halde Türkçe hata metni."""
    if model_ready():
        return ""
    path = model_path()
    tmp = path.with_suffix(".part")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(MODEL_URL, timeout=timeout) as response, open(tmp, "wb") as out:
            while chunk := response.read(1 << 16):
                out.write(chunk)
        if tmp.stat().st_size < MIN_BYTES:
            raise OSError("model dosyası eksik indi")
        tmp.replace(path)
        return ""
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        return f"El takip modeli indirilemedi ({exc}). İnternet bağlantını kontrol edip tekrar dene."


class HandTracker:
    def __init__(self) -> None:
        import sys
        import types

        try:
            import matplotlib.pyplot  # noqa: F401
        except ImportError:
            # mediapipe yalnızca çizim yardımcıları için içe aktarır; boyutu şişirmesin diye pakete konmaz.
            for name in ("matplotlib", "matplotlib.pyplot"):
                sys.modules.setdefault(name, types.ModuleType(name))
        import mediapipe as mp
        from mediapipe.tasks import python as tasks
        from mediapipe.tasks.python import vision

        self._mp = mp
        options = vision.HandLandmarkerOptions(
            base_options=tasks.BaseOptions(model_asset_path=str(model_path())),
            running_mode=vision.RunningMode.IMAGE,
            num_hands=1,
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)

    def points(self, bgr_frame):
        """İlk elin 21 noktası (x, y: 0-1) ya da None. Kare, ayna çevrilmiş BGR olmalı."""
        rgb = bgr_frame[:, :, ::-1].copy()
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        found = self._landmarker.detect(image).hand_landmarks
        return found[0] if found else None

    def close(self) -> None:
        try:
            self._landmarker.close()
        except Exception:
            pass


class HandMover:
    """Kamera karelerini alır, tutma hareketiyle öndeki pencereyi taşır."""

    def __init__(self) -> None:
        from jarvis import win32
        from jarvis.gesture import PinchDrag

        win = type("Win", (), {
            "foreground": staticmethod(win32.foreground_window),
            "movable": staticmethod(win32.movable),
            "rect": staticmethod(win32.window_rect),
            "move": staticmethod(win32.move_window),
            "screen": staticmethod(win32.screen_size),
        })
        self.tracker = HandTracker()
        self.drag = PinchDrag(win)

    def on_frame(self, bgr_frame) -> None:
        try:
            self.drag.update(self.tracker.points(bgr_frame), time.monotonic())
        except Exception:
            self.drag.release()

    def close(self) -> None:
        self.drag.release()
        self.tracker.close()
