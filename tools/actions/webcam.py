from __future__ import annotations

import threading
import time


class WebcamStreamer:
    MAX_DIM = 640
    CAPTURE_INTERVAL = 0.05
    OPEN_TIMEOUT = 12.0
    OPEN_TRIES = 3
    OPEN_RETRY_DELAY = 0.7

    def __init__(self):
        self._lock = threading.Lock()
        self._latest: bytes | None = None
        self._active = False
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._opened = threading.Event()  # açma denemesi bitti (başarılı ya da başarısız)
        self.frame_hook = None  # el hareketi gibi yerel işlemler için: hook(bgr_kare)
        self.local_only = False  # True: görüntü Gemini'ye gönderilmez

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
        self._opened.clear()
        self._thread = threading.Thread(target=self._loop, name="jarvis-webcam", daemon=True)
        self._thread.start()
        self._opened.wait(timeout=self.OPEN_TIMEOUT)  # ilk açılış (DirectShow soğuk başlangıç) birkaç saniye sürebilir
        if not self._active:
            self._stop.set()  # açılamadı: yarım kalan deneme arkada sürüp sonradan açılmasın
        return "ok" if self._active else "missing"

    def stop(self) -> None:
        hook, self.frame_hook, self.local_only = self.frame_hook, None, False
        close = getattr(getattr(hook, "__self__", None), "close", None)
        if close:
            close()
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=1.5)
        with self._lock:
            self._active = False
            self._latest = None

    def _open(self, cv2):
        """Kamerayı açar; ilk denemede meşgul/uyanmamış olabilir, bu yüzden birkaç kez dener."""
        for attempt in range(self.OPEN_TRIES):
            for backend in (cv2.CAP_DSHOW, None):
                cap = cv2.VideoCapture(0, backend) if backend is not None else cv2.VideoCapture(0)
                if cap.isOpened():
                    return cap
                cap.release()
            if self._stop.wait(self.OPEN_RETRY_DELAY):
                break
        return None

    def _loop(self) -> None:
        import cv2

        cap = self._open(cv2)
        if cap is None:
            self._stop.set()
            self._opened.set()
            return
        for prop, value in ((cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG")), (cv2.CAP_PROP_FRAME_WIDTH, 640),
                            (cv2.CAP_PROP_FRAME_HEIGHT, 480), (cv2.CAP_PROP_FPS, 30), (cv2.CAP_PROP_BUFFERSIZE, 1)):
            try:  # MJPG + 30 kare/sn: kısa pozlama (daha az hareket bulanıklığı) ve düşük gecikme; kamera desteklemezse yok sayılır
                cap.set(prop, value)
            except Exception:
                pass
        with self._lock:
            self._active = True
        self._opened.set()
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
                hook = self.frame_hook
                if hook:
                    hook(frame)
                encoded, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                if encoded:
                    with self._lock:
                        self._latest = buf.tobytes()
                time.sleep(0.005 if self.frame_hook else self.CAPTURE_INTERVAL)  # el takibinde hızlı hareketi kaçırmamak için tam hızda
        finally:
            cap.release()
            with self._lock:
                self._active = False
                self._latest = None
