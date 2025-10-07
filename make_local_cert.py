from datetime import datetime, timedelta
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

CN = "localhost"
SAN_DNS = ["localhost"]
SAN_IPS = ["127.0.0.1"]

# ключ
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

# subject/issuer одинаковые (self-signed)
name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, CN)])

# SAN: DNS и IP
alt_names = []
for d in SAN_DNS:
    alt_names.append(x509.DNSName(d))
for ip in SAN_IPS:
    alt_names.append(x509.IPAddress(__import__("ipaddress").ip_address(ip)))

cert = (
    x509.CertificateBuilder()
    .subject_name(name)
    .issuer_name(name)
    .public_key(key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(datetime.utcnow() - timedelta(minutes=1))
    .not_valid_after(datetime.utcnow() + timedelta(days=825))  # ~2.25 года
    .add_extension(x509.SubjectAlternativeName(alt_names), critical=False)
    .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
    .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
    .sign(private_key=key, algorithm=hashes.SHA256())
)

# пишем приватный ключ (PEM)
with open("localhost.key", "wb") as f:
    f.write(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

# пишем сертификат (PEM)
with open("localhost.crt", "wb") as f:
    f.write(cert.public_bytes(serialization.Encoding.PEM))

print("OK: wrote localhost.crt and localhost.key")
