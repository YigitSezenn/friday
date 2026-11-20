# /komut için HTTPS (Kapı sunucusu)

Bugün site `/komut` isteğini `http://SERVER-IP:8787/komut` adresine yönlendiriyor
(`site/vercel.json`). Bu bağlantı şifresiz olduğundan anahtar ve komut metni yolda okunabilir.
Çözüm: Kapı sunucusunun önüne HTTPS koymak. Kapı koduna dokunmadan, sunucuda şu adımlar yeterli:

1. **Alan adı**: bir alt alan adı seçin (ör. `kapi.sizin-alan.com`) ve DNS'te A kaydını
   `SERVER-IP` yapın.
2. **Caddy kur** (otomatik Let's Encrypt sertifikası):
   ```
   sudo apt install caddy
   ```
   `/etc/caddy/Caddyfile`:
   ```
   kapi.sizin-alan.com {
       reverse_proxy 127.0.0.1:8787
   }
   ```
   `sudo systemctl reload caddy`
3. **Güvenlik duvarı**: 80 ve 443'ü açın; 8787'yi dışarıya kapatın (yalnızca 127.0.0.1 dinlesin).
4. **Siteyi güncelle**: `site/vercel.json` içindeki hedefi
   `https://kapi.sizin-alan.com/komut` yapın ve `jarvis/gate_client.py` ile
   `phone-android/.../net/GateClient.kt` içindeki adresi aynı HTTPS adresine çevirin.
   Alan adını söylediğinizde bu üç dosyayı ben değiştiririm.
5. Doğrulama: `curl -i https://kapi.sizin-alan.com/komut` yanıt vermeli,
   `http://SERVER-IP:8787` dışarıdan ulaşılamaz olmalı.
