# FRIDAY telefon uygulaması

Jetpack Compose (Material 3) ile yazılmış yerel uygulama. Eskiden tek bir WebView'dı.

## Yapı (`app/src/main/java/com/friday/phone`)

| Klasör | İş |
|---|---|
| `domain/` | Saf Kotlin, Android'siz: eşleştirme kodu, QR bağlantısı, Wake-on-LAN paketi, kapı yanıtı, geçmiş. `app/src/test` altında JUnit testleri var. |
| `data/` | `FridayStore`: kalıcı bilgiler. `friday` dosyası ve `gate` anahtarı eski sürümle aynı, güncellemede eşleşme kaybolmaz. |
| `net/` | `GateClient` (komutu `/komut` üzerinden iletir) ve `WakeOnLan` (UDP). |
| `ui/` | `FridayViewModel`, tema, ekranlar (Eşleştirme, Komut, Uyandır, Ayarlar). |
| `MainActivity.kt` | Yalnızca kamera, ses tanıma ve açılış bağlantısı. |

## Davranış korunanlar

- Eşleştirme kodu `jarvis/gate_client.py` ve `site/src/main.js` ile aynı hesap.
- Wake-on-LAN: aynı denetim sırası (MAC, IP, port), port boşsa 9, paket hem IP'ye hem `255.255.255.255`'e gider.
- Açılış bağlantısı (`http://…/join`) ve QR (`SITE/#k=…`) aynı biçimde okunur.

## Derleme

Android Studio'da aç ya da `./gradlew assembleDebug`. Testler: `./gradlew test`.
