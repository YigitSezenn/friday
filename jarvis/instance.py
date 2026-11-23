"""Tek örnek denetimi: kısayola tıklayınca eski (takılı kalmış) süreç yüzünden hiçbir şey açılmamasın."""

from __future__ import annotations

import time


def take_over(acquire, signal, answered, kill, pause=time.sleep) -> bool:
    """True: bu süreç tek örnek oldu. `acquire()` kilidi almayı dener; kilit başkasındaysa çalışan örneğe
    'pencereni göster' denir (`signal`), `answered()` yanıtı bekler. Yanıt gelmezse o örnek takılmıştır:
    `kill()` ile sonlandırılır ve kilit yeniden alınır. Yanıt gelirse çalışan örnek öne gelmiştir, bu süreç çıkar."""
    if acquire():
        return True
    signal()
    if answered():
        return False
    kill()
    pause(1.0)
    return acquire()
