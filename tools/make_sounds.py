"""FRIDAY ses varlıklarını sentezler (özgün, telifsiz). Çalıştır: python tools/make_sounds.py

Üretilenler (assets/sounds, 44.1 kHz 16-bit stereo WAV):
  startup.wav   ~5.5 sn  derin sub-vuruş, yükselen filtre süpürmesi, açılan akor, parlak "çan" ve ışıltı
  shutdown.wav  ~4.5 sn  alçalan akor, düşen süpürme, enerjinin söndüğü sub-düşüş
  success.wav   ~0.5 sn  kısa çift ton onay
  ambient.wav   ~24 sn   döngüye uygun, sakin sentezleyici ortam pedi
"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SR = 44100
OUT = Path(__file__).resolve().parent.parent / "assets" / "sounds"
RNG = np.random.default_rng(48)


def t(sec):
    return np.arange(int(sec * SR)) / SR


def env(n, a, d, s, r):
    """ADSR (saniye) -> n örneklik zarf."""
    e = np.ones(n)
    na, nd, nr = int(a * SR), int(d * SR), int(r * SR)
    e[:na] = np.linspace(0, 1, na, endpoint=False) if na else 1
    if nd:
        e[na:na + nd] = np.linspace(1, s, nd)
    e[na + nd:] = s
    if nr:
        nr = min(nr, n)
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def lowpass(x, cutoff):
    """Tek kutuplu alçak geçiren; cutoff skaler ya da dizi (Hz)."""
    cutoff = np.broadcast_to(np.asarray(cutoff, dtype=float), x.shape)
    a = 1 - np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def saw(freq, n, voices=3, detune=0.004):
    tt = np.arange(n) / SR
    out = np.zeros(n)
    for v in range(voices):
        f = freq * (1 + detune * (v - (voices - 1) / 2))
        ph = (tt * f + RNG.random()) % 1.0
        out += 2 * ph - 1
    return out / voices


def bell(freq, sec, decay=3.0):
    tt = t(sec)
    parts = [(1.0, 1.0), (2.76, 0.45), (5.4, 0.22), (8.93, 0.1)]
    out = sum(a * np.sin(2 * np.pi * freq * r * tt) * np.exp(-decay * (0.6 + r * 0.25) * tt) for r, a in parts)
    return out * (1 - np.exp(-tt * 400))


def reverb(x, wet=0.28, size=1.6):
    """Basit Schroeder yankısı (stereo karşıtı gecikmeler)."""
    n = len(x)
    l = x.copy()
    r = x.copy()
    for i, (d, g) in enumerate([(0.029, .55), (0.037, .5), (0.043, .45), (0.061, .4), (0.083, .35), (0.121, .3), (0.173, .22)]):
        k = int(d * SR * size)
        l[k:] += g * x[: n - k] * (1 if i % 2 else .8)
        r[k + 37:] += g * x[: n - k - 37] * (.8 if i % 2 else 1)
    return (x * (1 - wet) + l * wet), (x * (1 - wet) + r * wet)


def norm(l, r, peak=0.89):  # noqa
    m = max(np.abs(l).max(), np.abs(r).max(), 1e-9)
    return l / m * peak, r / m * peak


def save(name, l, r, peak=0.89):
    l, r = norm(l, r, peak)
    fade = int(0.02 * SR)
    l[:fade] *= np.linspace(0, 1, fade)
    r[:fade] *= np.linspace(0, 1, fade)
    l[-fade:] *= np.linspace(1, 0, fade)
    r[-fade:] *= np.linspace(1, 0, fade)
    data = (np.stack([l, r], 1) * 32767).astype("<i2")
    OUT.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUT / name), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    print(name, f"{len(l) / SR:.1f}s")


def pad(freqs, sec, cutoff, gain=1.0):
    n = int(sec * SR)
    x = sum(saw(f, n) for f in freqs) / len(freqs)
    return lowpass(x, cutoff) * gain


def startup():
    sec = 5.8
    n = int(sec * SR)
    tt = t(sec)
    # 1) Sub-vuruş: 0 sn'de alçalan sinüs
    f = 90 * np.exp(-tt * 3.2) + 38
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 1.3)
    # 2) Yükselen süpürme (0–1.6 sn) – filtreli testere
    sweep_f = 110 * 2 ** (tt / 1.6 * 4)
    sweep = np.sin(2 * np.pi * np.cumsum(np.minimum(sweep_f, 1800)) / SR)
    sweep *= np.where(tt < 1.6, (tt / 1.6) ** 2, 0) * np.exp(-np.maximum(tt - 1.6, 0) * 9)
    # 3) Akor (1.5 sn'den itibaren, Dm9 -> parlak): D2 A2 D3 F3 A3 E4
    notes = [73.42, 110.0, 146.83, 174.61, 220.0, 329.63]
    cut = 300 + 3200 * np.clip((tt - 1.4) / 2.2, 0, 1) ** 1.5
    chord = pad(notes, sec, cut)
    chord *= env(n, 1.6, 1.0, 0.75, 2.4) * np.where(tt >= 1.4, 1, 0) * 0.9
    chord *= np.clip((tt - 1.4) / 1.4, 0, 1)
    # 4) Parlak çan (1.6 sn'de vuruş, ikinci 2.3 sn)
    b = np.zeros(n)
    for start, fr, g in [(1.6, 587.33, 0.7), (2.25, 880.0, 0.45), (2.9, 1174.66, 0.3)]:
        sig = bell(fr, 3.2) * g
        i0 = int(start * SR)
        m = min(len(sig), n - i0)
        b[i0:i0 + m] += sig[:m]
    # 5) Işıltı: yüksek frekanslı kısa arpej
    sp = np.zeros(n)
    for k, fr in enumerate([1760, 2349, 2637, 3520, 3951, 4699]):
        i0 = int((2.0 + k * 0.11) * SR)
        sig = np.sin(2 * np.pi * fr * t(0.9)) * np.exp(-t(0.9) * 5) * 0.08
        m = min(len(sig), n - i0)
        sp[i0:i0 + m] += sig[:m]
    # 6) Hava / nefes (ilk 1.6 sn filtreli gürültü, yükselir)
    noise = lowpass(RNG.standard_normal(n), 400 + 5000 * np.clip(tt / 1.6, 0, 1) ** 2)
    noise *= np.where(tt < 1.7, (tt / 1.7) ** 2, np.exp(-(tt - 1.7) * 4)) * 0.25
    mono = sub * 0.38 + sweep * 0.3 + chord * 1.1 + b * 0.85 + sp * 1.3 + noise * 0.7
    l, r = reverb(mono, 0.3, 1.8)
    # Hafif stereo genişletme
    sh = int(0.0007 * SR)
    r = np.roll(r, sh)
    save("startup.wav", l, r)


def shutdown():
    sec = 4.7
    n = int(sec * SR)
    tt = t(sec)
    # Alçalan akor: parlak -> kararan, yüksek notalar önce söner
    notes = [329.63, 220.0, 174.61, 146.83, 110.0, 73.42]
    cut = 3400 * np.exp(-tt * 1.15) + 160
    # perde hafifçe düşer (güç kesilmesi hissi)
    droop = 1 - 0.18 * np.clip(tt / sec, 0, 1) ** 2
    chord = np.zeros(n)
    for f in notes:
        ph = np.cumsum(f * droop) / SR
        chord += (2 * ((ph + RNG.random()) % 1) - 1) + (2 * ((ph * 1.004) % 1) - 1)
    chord = lowpass(chord / (2 * len(notes)), cut) * env(n, 0.04, 0.4, 0.8, 1.9)
    # Düşen süpürme
    sf = 1500 * np.exp(-tt * 2.2) + 60
    swp = np.sin(2 * np.pi * np.cumsum(sf) / SR) * np.exp(-tt * 1.7) * 0.5
    # Çan: iki alçalan vuruş
    b = np.zeros(n)
    for start, fr, g in [(0.0, 880.0, 0.5), (0.5, 587.33, 0.45), (1.05, 392.0, 0.35)]:
        sig = bell(fr, 3.0, 3.6) * g
        i0 = int(start * SR)
        m = min(len(sig), n - i0)
        b[i0:i0 + m] += sig[:m]
    # Sub-düşüş (enerjinin boşalması) ~1.1 sn'de
    sf2 = 70 * np.exp(-np.maximum(tt - 1.1, 0) * 1.6) + 25
    sub = np.sin(2 * np.pi * np.cumsum(sf2) / SR) * np.where(tt >= 1.1, np.exp(-(tt - 1.1) * 1.4), 0) * 0.9
    sub *= np.clip((tt - 1.1) / 0.06, 0, 1)
    # Güç kesilme "tşş": filtreli gürültü
    noise = lowpass(RNG.standard_normal(n), 6000 * np.exp(-tt * 2.5) + 200) * np.exp(-tt * 2.2) * 0.18
    mono = chord * 0.75 + swp * 0.4 + b * 0.6 + sub + noise
    mono *= np.clip((sec - tt) / 1.2, 0, 1) ** 1.2  # uzun söndürme
    l, r = reverb(mono, 0.34, 2.0)
    save("shutdown.wav", l, r)


def success():
    sec = 0.55
    tt = t(sec)
    a = np.sin(2 * np.pi * 880 * tt) * env(len(tt), 0.004, 0.08, 0.2, 0.15)
    bb = np.zeros_like(tt)
    i0 = int(0.09 * SR)
    seg = np.sin(2 * np.pi * 1318.5 * tt[: len(tt) - i0]) * env(len(tt) - i0, 0.004, 0.1, 0.15, 0.2)
    bb[i0:] = seg
    mono = a * 0.6 + bb * 0.5
    l, r = reverb(mono, 0.25, 1.0)
    save("success.wav", l, r)


def ambient():
    sec = 24.0
    n = int(sec * SR)
    tt = t(sec)
    mono = np.zeros(n)
    # Sakin Dm9 pedi; periyodik filtre nefesi (24 sn'de tam 2 döngü -> dikişsiz döngü)
    breathe = 0.5 + 0.5 * np.sin(2 * np.pi * tt / 12.0)
    for f, g in [(73.42, .6), (110.0, .5), (146.83, .4), (220.0, .3), (329.63, .18), (440.0, .1)]:
        # tam sayıda döngüye oturan LFO
        vib = 1 + 0.002 * np.sin(2 * np.pi * tt * (1 / 8.0))
        ph = np.cumsum(f * vib) / SR
        mono += g * (np.sin(2 * np.pi * ph) + 0.35 * np.sin(4 * np.pi * ph + 0.3))
    mono *= 0.5 + 0.5 * breathe
    mono = lowpass(mono, 500 + 900 * breathe)
    # Çok seyrek, yumuşak çan vuruşları
    for start, fr in [(3.0, 587.33), (9.0, 440.0), (15.0, 659.25), (20.0, 523.25)]:
        sig = bell(fr, 3.5, 2.2) * 0.08
        i0 = int(start * SR)
        m = min(len(sig), n - i0)
        mono[i0:i0 + m] += sig[:m]
    l, r = reverb(mono, 0.4, 2.2)
    # Dikişsiz döngü için başı ve sonu çapraz karıştır
    fade = int(1.5 * SR)
    for ch in (l, r):
        tail = ch[-fade:].copy()
        ch[:fade] = ch[:fade] * np.linspace(0, 1, fade) + tail * np.linspace(1, 0, fade)
    l, r = l[:-fade], r[:-fade]
    save("ambient.wav", l, r, 0.5)


if __name__ == "__main__":
    startup()
    shutdown()
    success()
    ambient()
