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


def gesture_options() -> dict:
    """Ayarlardaki hareket anahtarları ve hız (yüzde); yoksa hepsi açık."""
    from jarvis.config import load_app_config

    config = load_app_config()
    options = {name: bool(config.get(f"hand_{name}", True)) for name in ("move", "resize", "maximize", "minimize")}
    options["speed"] = max(0.5, min(2.0, float(config.get("hand_speed", 100) or 100) / 100))
    return options


class HandMover:
    """Kamera karelerini alır, el hareketleriyle öndeki pencereyi taşır/boyutlandırır/büyütür/küçültür."""

    def __init__(self, on_status=None) -> None:
        from jarvis import win32
        from jarvis.gesture import HandGestures

        win = type("Win", (), {
            "foreground": staticmethod(win32.foreground_window),
            "controllable": staticmethod(win32.controllable),
            "maximized": staticmethod(win32.is_maximized),
            "rect": staticmethod(win32.window_rect),
            "move": staticmethod(win32.move_window),
            "resize": staticmethod(win32.resize_window),
            "show": staticmethod(win32.show_window),
            "screen": staticmethod(win32.screen_size),
        })
        self._options, self._options_at = None, 0.0
        self.tracker = HandTracker()
        self.drag = HandGestures(win, self._cached_options, on_status)

    def _cached_options(self) -> dict:
        now = time.monotonic()
        if self._options is None or now - self._options_at > 1.0:
            try:
                self._options = gesture_options()
            except Exception:
                self._options = {}
            self._options_at = now
        return self._options

    def on_frame(self, bgr_frame) -> None:
        try:
            points = self.tracker.points(bgr_frame)
            self.drag.update(points, time.monotonic())
            if points:
                _draw(bgr_frame, points, self.drag.grabbing)
        except Exception:
            self.drag.release()

    def close(self) -> None:
        self.drag.release()
        self.tracker.close()


def _draw(frame, points, grabbing: bool) -> None:
    """Görüntü penceresinde elin noktalarını gösterir (kamera karesi üzerine çizilir)."""
    import cv2

    height, width = frame.shape[:2]
    color = (80, 220, 120) if grabbing else (230, 200, 60)
    for point in points:
        cv2.circle(frame, (int(point.x * width), int(point.y * height)), 3, color, -1)
