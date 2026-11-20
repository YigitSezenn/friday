# Kapı: çok kullanıcılı hâle getirme (öneri, henüz yapılmadı)

## Bugünkü durum
Kapı sunucusu (`gate/server.py`, sunucuda `C:\Code\friday-kapi`) tek bir `GATE_KEY` bilir ve
tek bir komut kuyruğu tutar. Bilgisayar `/pc/poll` ile kuyruğu çeker, site/telefon `/komut`
ile kuyruğa yazar. Anahtar yalnızca sunucu sahibinin anahtarıdır; başka biri uygulamayı
kurunca kendi anahtarı sunucuda kayıtlı olmadığından 403 alır. Bu yüzden uzaktan komut
yalnızca sunucu sahibi için çalışır. Uygulama bunu Ayarlar › Telefon'da "Kapı: …" satırıyla
gösterir.

Ek bulgu: Uygulamadaki "Yenile" düğmesi yerel anahtarı değiştirip sunucuyu güncellemediği
için Kapı bağlantısını koparıyordu. Bu yüzden düğme şimdilik gizlendi.

## Öneri: anahtar = posta kutusu
Her anahtar kendi kuyruğunu açar; sunucuda hesap, kayıt ya da kullanıcı listesi gerekmez.

- `QUEUES: dict[str, CommandQueue]` (anahtar → kuyruk).
- `/pc/poll` başlığındaki anahtarın kuyruğunu boşaltır. `/komut` aynı anahtarın kuyruğuna yazar.
- Sunucu sahibinin `GATE_KEY`'i (ve Discord botu) kendi kuyruğunu kullanmaya devam eder.
- Anahtar yeterince uzun ve rastgele olduğundan (32 karakter) tahmin edilemez; HTTPS ile
  taşındığı için yolda okunamaz. Anahtar yenilemek artık güvenli: yeni anahtar yeni kuyruktur.

### Sunucuyu korumak için gerekenler
- Kuyruk sayısı üst sınırı (ör. 2000) ve boşta kalan kuyruğun 1 saat sonra silinmesi.
- Kuyruk başına en çok 50 komut, komut başına en çok 500 karakter (zaten var).
- IP başına dakikada istek sınırı; geçersiz uzunlukta anahtarlar (≠ 32) reddedilir.
- `Set-Cookie` için `Secure; SameSite=Strict` eklenmesi (şu an yok).
- Eski 8787 portu dışarıya kapatılır (yalnızca Caddy erişir).

### Uygulama tarafı
Değişiklik gerekmez: uygulama zaten kendi anahtarıyla `/pc/poll` yapar, telefon da QR'daki
anahtarla gönderir. "Yenile" düğmesi yeniden açılabilir.

## Seçenekler
1. **Bu öneri**: tek sunucu, herkes kendi kutusu. Sunucu sahibine yük (trafik, kötüye kullanım).
2. **Herkes kendi Kapı'sını kurar**: sunucu sahibine yük yok, ama kullanıcı için zahmetli.
3. **Uzaktan komutu yalnızca sahibe bırak**: şimdiki hâl; diğer kullanıcılara bu özellik gösterilmez.

Karar sizde. Sunucu kodu bu depoda yok (yerelde `gate/`, git'e girmiyor); değiştirmek için
sizin onayınız ve sunucuya yeniden dağıtım (`tools/deploy_gate.py`) gerekir.
