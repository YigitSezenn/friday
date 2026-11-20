"""Telefon köprüsü için kendinden imzalı sertifika.

Aynı Wi-Fi'de trafik şifrelensin diye: sertifika bilgisayarda bir kez üretilir, parmak izi
(SHA-256) QR kodunun içinde telefona verilir; telefon yalnızca bu parmak izini kabul eder
(sertifika sabitleme), bu yüzden alan adı/otorite gerekmez. Özel anahtar bilgisayardan çıkmaz.
"""

from __future__ import annotations

import datetime
import hashlib
import ssl
from pathlib import Path

from jarvis.paths import data_path

TLS_PORT = 8767


def _paths() -> tuple[Path, Path]:
    return data_path("config", "phone_cert.pem"), data_path("config", "phone_key.pem")


def _generate(cert_path: Path, key_path: Path) -> None:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "FRIDAY telefon köprüsü")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=3650))
        .sign(key, hashes.SHA256())
    )
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def ensure_cert() -> tuple[Path, Path]:
    cert_path, key_path = _paths()
    if not (cert_path.exists() and key_path.exists()):
        _generate(cert_path, key_path)
    return cert_path, key_path


def fingerprint() -> str:
    """Sertifikanın DER'inin SHA-256'sı, küçük harf hex (64 karakter)."""
    cert_path, _ = ensure_cert()
    der = ssl.PEM_cert_to_DER_cert(cert_path.read_text(encoding="ascii"))
    return hashlib.sha256(der).hexdigest()


def server_context() -> ssl.SSLContext:
    cert_path, key_path = ensure_cert()
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(str(cert_path), str(key_path))
    return context
