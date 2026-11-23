"""Alkış sayar: 2 alkış = aç/uyandır, 3 alkış = kapat. Yalnızca ses seviyesine bakar; ses kaydedilmez, hiçbir yere gönderilmez."""

from __future__ import annotations

import array

WINDOWS = 8  # 1024 örneklik parça (~64 ms) 8 küçük pencereye bölünür (~8 ms)
SHARP = 1.5  # en güçlü pencerenin RMS'i, ortanca pencerenin en az bu kadar katı (kısa, belirgin patlama)
DECAY = 0.8  # patlama ilk yarıdaysa, parça sonunda RMS bu orana düşmüş olmalı (alkış söner; konuşma/müzik sürer)
BRIGHT = 0.3  # ardışık örnek farkı enerjisi / enerji: yüksek frekans payı (alkış geniş bantlı; vurma/uğultu/ünlüler düşük)
DEBUG_MIN_PEAK = 0.25  # bu seviyenin üstündeki ama alkış sayılmayan sesler tanı günlüğüne yazılır
_last_debug = 0.0


def features(pcm: bytes) -> dict | None:
    """Parçanın alkışla ilgili ölçüleri; ses yoksa None."""
    usable = pcm[: len(pcm) // 2 * 2]
    samples = array.array("h")
    samples.frombytes(usable)
    size = len(samples) // WINDOWS
    if size < 16:
        return None
    energy = [sum(s * s for s in samples[i * size:(i + 1) * size]) / size for i in range(WINDOWS)]
    top = max(range(WINDOWS), key=energy.__getitem__)
    if energy[top] <= 0:
        return None
    median = sorted(energy)[WINDOWS // 2]
    lo, hi = max(top - 1, 0) * size, (min(top + 1, WINDOWS - 1) + 1) * size
    burst = samples[lo:hi]
    total = sum(s * s for s in burst)
    rough = sum((burst[i] - burst[i - 1]) ** 2 for i in range(1, len(burst)))
    return {
        "sharp": (energy[top] / max(median, 1.0)) ** 0.5,
        "decay": (energy[-1] / energy[top]) ** 0.5 if top < WINDOWS - 2 else 0.0,  # sonda patlama: sönüş görülemez
        "bright": rough / total if total > 0 else 0.0,
        "peak": max(abs(s) for s in samples) / 32768.0,
    }


def clap_level(pcm: bytes) -> float:
    """Parça alkış gibi (kısa, keskin, geniş bantlı bir patlama) ise tepe seviyesini, değilse 0 döner.
    Konuşma, müzik, uğultu, kapı gümlemesi gibi sesler yeterince yüksek olsa da alkış sayılmaz."""
    f = features(pcm)
    if f is None or f["sharp"] < SHARP or f["decay"] > DECAY or f["bright"] < BRIGHT:
        return 0.0
    return f["peak"]


def debug_rejected(pcm: bytes, now: float, write=None) -> None:
    """Yeterince yüksek ama alkış sayılmayan sesin ölçülerini bir dosyaya yazar (en çok saniyede bir, dosya küçük kalır)."""
    global _last_debug
    f = features(pcm)
    if f is None or f["peak"] < DEBUG_MIN_PEAK or now - _last_debug < 1.0 or clap_level(pcm) > 0:
        return
    _last_debug = now
    line = "ret sharp={sharp:.2f} decay={decay:.2f} bright={bright:.2f} peak={peak:.2f}".format(**f)
    try:
        if write is not None:
            write(line)
            return
        from jarvis.paths import data_path

        path = data_path("clap_debug.log")
        old = path.read_text(encoding="utf-8")[-8000:] if path.exists() else ""
        path.write_text(old + line + "\n", encoding="utf-8")
    except Exception:
        pass


class ClapDetector:
    BASE_LOUD = 0.20  # %100 hassasiyette bir alkışın ulaşması gereken seviye (0-1)
    RATIO = 5.0  # ortam gürültüsünün en az bu kadar katı olmalı
    MIN_GAP = 0.12  # aynı alkışın kuyruğu ikinci alkış sayılmaz
    SETTLE = 0.7  # son alkıştan sonra bu kadar sessizlik: sayı kesinleşir
    COOLDOWN = 2.0
    MAX_CLAPS = 3  # daha fazlası alkış değil gürültü/kalabalık sayılır

    def __init__(self, sensitivity: float = 1.0) -> None:
        self.floor = 0.0
        self.prev = 0.0
        self.claps: list[float] = []
        self.quiet_until = 0.0
        self.loud = self.BASE_LOUD
        self.set_sensitivity(sensitivity)

    def set_sensitivity(self, sensitivity: float) -> None:
        """1.0 = varsayılan; 2.0 = iki kat hassas (yarı şiddette alkış yeter), 0.5 = yarı hassas."""
        self.loud = self.BASE_LOUD / min(max(float(sensitivity or 1.0), 0.5), 2.0)

    def feed(self, level: float, now: float) -> int:
        """Alkış sayısı kesinleşince 2 ya da 3 döner, aksi halde 0."""
        onset = level >= max(self.loud, self.floor * self.RATIO) and self.prev < level * 0.5
        if level < self.loud:
            self.floor = self.floor * 0.95 + level * 0.05
        self.prev = level
        if now < self.quiet_until:
            self.claps = []
            return 0
        if onset and not (self.claps and now - self.claps[-1] < self.MIN_GAP):
            self.claps.append(now)
            if len(self.claps) > self.MAX_CLAPS:
                self.claps = []
                self.quiet_until = now + self.COOLDOWN
            return 0
        if self.claps and now - self.claps[-1] >= self.SETTLE:
            count, self.claps = len(self.claps), []
            if count >= 2:
                self.quiet_until = now + self.COOLDOWN
                return count
        return 0
