# /komut HTTPS (Kapı sunucusu)

Kapı sunucusunun önünde Caddy çalışır ve `https://friday-kapi.duckdns.org` adresine
Let's Encrypt sertifikası verir; istekler sunucu içinde `127.0.0.1:8787`'ye iletilir.
Site (`site/vercel.json`), Windows uygulaması (`jarvis/gate_client.py`) ve Android (site
üzerinden) bu adresi kullanır; anahtar ve komut metni artık şifreli gider.

## Sunucuda kurulum (Windows VDS)
1. `C:\caddy\caddy.exe` indirilir (https://caddyserver.com/download, Windows amd64).
2. `C:\caddy\Caddyfile`:
   ```
   friday-kapi.duckdns.org {
       reverse_proxy 127.0.0.1:8787
   }
   ```
3. Güvenlik duvarında 80 ve 443 açılır (Windows güvenlik duvarı ve VDS panelindeki kurallar).
4. `C:\caddy\caddy.exe run --config C:\caddy\Caddyfile`
5. Alan adı DuckDNS'te sunucu IP'sine işaret etmelidir.

## Sonraki adımlar
- Caddy'yi Windows servisi yapın (pencere kapanınca durmasın).
- 8787 portunu dışarıya kapatın (yalnızca 127.0.0.1 dinlesin veya güvenlik duvarıyla engelleyin).
- Windows uygulaması adresi `config/gate_url.txt` ya da `FRIDAY_GATE_URL` ile değiştirilebilir.
