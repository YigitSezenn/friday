"""Duyulan sesin güvenilir işlenmesi: bozuk dökümü ayıklar, anlaşılmayınca tekrar ister, takılmayı yakalar.

Saf mantık: ses, ağ ve arayüz bilgisi tutmaz, bu yüzden kolayca test edilir.
"""

from __future__ import annotations

import re
import unicodedata

CONTROL_TOKEN_RE = re.compile(r"<ctrl\d+>", re.IGNORECASE)

# Türkçe/İngilizce/Fransızca/Azerice Latin yazar. Ses modeli gürültüyü bazen şu yazılardan birine "çevirir".
_FOREIGN_BLOCKS = (
    (0x0370, 0x03FF),  # Yunan
    (0x0400, 0x052F),  # Kiril
    (0x0590, 0x05FF),  # İbranice
    (0x0900, 0x097F),  # Devanagari
    (0x0E00, 0x0E7F),  # Tay
    (0x1100, 0x11FF),  # Hangul jamo
    (0x3040, 0x30FF),  # Hiragana, Katakana
    (0x3400, 0x4DBF),  # CJK uzantı A
    (0x4E00, 0x9FFF),  # CJK
    (0xAC00, 0xD7AF),  # Hangul
    (0xF900, 0xFAFF),  # CJK uyumluluk
    (0xFF66, 0xFF9F),  # yarım genişlik Katakana
    (0x20000, 0x2A6DF),  # CJK uzantı B
)
_ARABIC = (0x0600, 0x06FF)
REJECT_RATIO = 0.3
VOICE_LEVEL = 0.05
MIN_FRAMES = 8  # ~0,5 sn (1024 örnek / 16 kHz = 64 ms)


def _foreign(char: str, allow_arabic: bool) -> bool:
    code = ord(char)
    if allow_arabic and _ARABIC[0] <= code <= _ARABIC[1]:
        return False
    if _ARABIC[0] <= code <= _ARABIC[1]:
        return True
    return any(low <= code <= high for low, high in _FOREIGN_BLOCKS)


def _invalid(char: str) -> bool:
    if char in "\n\r\t":
        return False
    if char == "\ufffd" or ord(char) < 32:
        return True
    return unicodedata.category(char) in {"Cc", "Cs", "Co", "Cn"}


_WORD_RE = re.compile(r"[^\W\d_]+")
FRAGMENT_RATIO = 0.2


def _fragmented(text: str) -> bool:
    """'Spo tif y 'dan E vergün'i' gibi tek harfli parçalara bölünmüş döküm: gerçek konuşma değil."""
    words = _WORD_RE.findall(text)
    singles = [w for w in words if len(w) == 1 and w.lower() != "o"]
    return len(words) >= 5 and len(singles) >= 2 and len(singles) / len(words) >= FRAGMENT_RATIO


def usable_transcript(text: str, language: str = "tr") -> tuple[str, bool]:
    """(gösterilecek metin, anlaşılmadı mı).

    Kontrol işaretleri ve geçersiz karakterler atılır. Yabancı yazı azsa yalnızca o harfler atılır;
    metnin önemli kısmı yabancı yazıysa (çoğunlukla gürültünün Çince'ye çevrilmesi) tümü reddedilir.
    """
    raw = CONTROL_TOKEN_RE.sub(" ", str(text or ""))
    noisy = raw != str(text or "")
    allow_arabic = language == "ar"
    kept: list[str] = []
    letters = foreign = 0
    for char in raw:
        if _invalid(char):
            noisy = True
            continue
        if char.isalpha():
            letters += 1
            if _foreign(char, allow_arabic):
                foreign += 1
                continue
        kept.append(char)
    cleaned = " ".join("".join(kept).split()).strip()
    if foreign and letters and foreign / letters > REJECT_RATIO:
        return "", True
    if not cleaned and noisy:
        return "", True
    if _fragmented(cleaned):
        return "", True
    return cleaned, False


class RepeatPolicy:
    """Anlaşılmayınca "tekrar eder misin" demeyi sınırlar: ardışık en çok `max_streak`, aralarında `cooldown` sn."""

    def __init__(self, cooldown: float = 12.0, max_streak: int = 2) -> None:
        self.cooldown = cooldown
        self.max_streak = max_streak
        self.streak = 0
        self.last = -1e9

    def should_ask(self, now: float) -> bool:
        if self.streak >= self.max_streak or now - self.last < self.cooldown:
            return False
        self.streak += 1
        self.last = now
        return True

    def understood(self) -> None:
        self.streak = 0


class StallWatch:
    """Kullanıcı gerçekten konuştu ama sunucudan hiçbir yanıt gelmediyse (dinliyor görünüp kitlenme) bunu yakalar.

    Tek tük tıkırtı ya da ortam gürültüsü konuşma sayılmaz: `min_frames` kare üst üste yüksek ses gerekir.
    Yanıtsız üst üste `max_trips` yenilemeden sonra vazgeçer, böylece sürekli yeniden bağlanma döngüsüne girilmez.
    """

    def __init__(self, limit: float = 15.0, min_frames: int = MIN_FRAMES, max_trips: int = 3) -> None:
        self.limit = limit
        self.min_frames = min_frames
        self.max_trips = max_trips
        self.frames = 0
        self.awaiting = False
        self.had_voice = False
        self.last_voice = 0.0
        self.trips = 0

    def voice(self, now: float, level: float) -> None:
        if level < VOICE_LEVEL:
            self.frames = 0
            return
        self.frames += 1
        self.last_voice = now
        if self.frames >= self.min_frames:
            self.awaiting = True
            self.had_voice = True

    def server_event(self) -> None:
        self.awaiting = False
        self.trips = 0

    def take_voice(self) -> bool:
        """Son turdan beri gerçek konuşma gönderildi mi? Okuyunca sıfırlanır."""
        value, self.had_voice = self.had_voice, False
        return value

    def stalled(self, now: float, *, idle: bool = False) -> bool:
        """`idle`: asistan konuşuyor, mikrofon kapalı ya da durakta. O sırada takılma sayılmaz."""
        if idle or not self.awaiting or self.trips >= self.max_trips:
            return False
        return now - self.last_voice >= self.limit

    def reset(self) -> None:
        """Yenileme yapıldı: bekleyişi sıfırla ama kaç kez denendiğini hatırla."""
        self.trips += 1
        self.awaiting = False
        self.had_voice = False
        self.frames = 0


class MicGate:
    """Müzik ya da uğultu varken mikrofonu temiz tutar.

    Sürekli çalan müzik, sunucunun "konuşma bitti" kararını bozar ve şarkı sözü konuşma sanılır.
    Kapı ortam seviyesini yavaşça öğrenir; yalnızca ortamın belirgin üstüne çıkan ses geçer.
    Kapalıyken sessizlik gönderilir, böylece sunucu cümlenin bittiğini görebilir.
    """

    MIN_OPEN = 0.03
    RATIO = 2.2
    HANGOVER = 9  # ~0,6 sn
    RISE = 0.004

    def __init__(self) -> None:
        self.floor = 0.0
        self.hold = 0

    def threshold(self) -> float:
        return max(self.MIN_OPEN, self.floor * self.RATIO + 0.008)

    def passes(self, level: float) -> bool:
        if level <= self.floor:
            self.floor = level * 0.4 + self.floor * 0.6
        else:
            # Yavaş yükselir: kısa konuşma ortamı oynatmaz, sürekli ses (müzik) birkaç saniyede ortam olur.
            self.floor += (level - self.floor) * self.RISE
        if level > self.threshold():
            self.hold = self.HANGOVER
            return True
        if self.hold > 0:
            self.hold -= 1
            return True
        return False


class GatedMic:
    """MicGate'in önüne ses başı payı koyar: kapı konuşmanın ilk kısık sesinde (ş, f, t gibi) geç açılırsa
    sözcüğün başı kesilmesin diye kapı açılırken son birkaç parça da (~0,2 sn) önce gönderilir.
    Kapalıyken sunucuya sessizlik gider (cümlenin bittiğini görsün)."""

    PREROLL = 3

    def __init__(self, gate: "MicGate | None" = None) -> None:
        self.gate = gate or MicGate()
        self.recent: list[bytes] = []
        self.open = False

    def process(self, data: bytes, level: float) -> list[bytes]:
        if self.gate.passes(level):
            out = ([*self.recent] if not self.open else []) + [data]
            self.recent, self.open = [], True
            return out
        self.open = False
        self.recent = (self.recent + [data])[-self.PREROLL:]
        return [bytes(len(data))]


class Leveler:
    """Kısık mikrofonu yumuşakça yükseltir (en çok 4 kat); sesli konuşmayı bozmaz. Tanıma kısık sesle daha çok yanılır."""

    TARGET = 0.25
    MAX_GAIN = 4.0
    QUIET = 0.02  # bunun altı sessizlik/ortam sayılır, yükseltilmez

    def __init__(self) -> None:
        self.gain = 1.0

    def apply(self, pcm: bytes) -> bytes:
        import array

        usable = pcm[: len(pcm) // 2 * 2]
        if not usable:
            return pcm
        samples = array.array("h")
        samples.frombytes(usable)
        level = max(abs(s) for s in samples) / 32768.0
        if level > self.QUIET:
            want = min(self.MAX_GAIN, max(1.0, self.TARGET / level))
            self.gain = want if want < self.gain else self.gain + (want - self.gain) * 0.2  # sesli ise hemen düş, kısıksa yavaş çık
        if self.gain <= 1.001:
            return pcm
        gain = self.gain
        out = array.array("h", (max(-32768, min(32767, int(s * gain))) for s in samples))
        return out.tobytes()


REPEAT_NOTE = (
    "Kullanıcının son sözünü anlayamadın (ses belirsizdi ya da kesikti). Tahmin yürütme, bir şey uydurma ve başka bir dile çevirme; "
    "kullanıcının dilinde tek kısa cümleyle tekrar etmesini rica et."
)
