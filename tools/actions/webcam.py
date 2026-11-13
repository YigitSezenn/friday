from __future__ import annotations

import threading
import time


class WebcamStreamer:
    MAX_DIM = 640
    CAPTURE_INTERVAL = 0.05

    def __init__(self):
        self._lock = threading.Lock()
        self._latest: bytes | None = None
        self._active = False
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    @property
    def is_active(self) -> bool:
        return self._active

    def get_latest_frame(self) -> bytes | None:
        with self._lock:
            return self._latest

    def start(self) -> str:
        if self._active:
            return "already_active"
        try:
            import cv2  # noqa: F401
        except ImportError:
            return "missing"
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="jarvis-webcam", daemon=True)
        self._thread.start()
        for _ in range(20):
            if self._active or self._stop.is_set():
                break
            time.sleep(0.05)
        return "ok" if self._active else "missing"

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=1.5)
        with self._lock:
            self._active = False
            self._latest = None

    def _loop(self) -> None:
        import cv2

        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self._stop.set()
            return
        with self._lock:
            self._active = True
        try:
            while not self._stop.is_set():
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.1)
                    continue
                height, width = frame.shape[:2]
                if max(height, width) > self.MAX_DIM:
                    scale = self.MAX_DIM / max(height, width)
                    frame = cv2.resize(frame, (int(width * scale), int(height * scale)))
                frame = cv2.flip(frame, 1)
                encoded, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                if encoded:
                    with self._lock:
                        self._latest = buf.tobytes()
                time.sleep(self.CAPTURE_INTERVAL)
        finally:
            cap.release()
            with self._lock:
                self._active = False
                self._latest = None
