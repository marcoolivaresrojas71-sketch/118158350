from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import ipaddress
import os
import socket
import ssl
import subprocess


ROOT = Path(__file__).parent.resolve()
CERT_FILE = ROOT / "localhost+2.pem"
KEY_FILE = ROOT / "localhost+2-key.pem"
PORT = int(os.environ.get("PORT", "8443"))


def local_ip():
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("10.255.255.255", 1))
        address = probe.getsockname()[0]
        ipaddress.ip_address(address)
        return address
    finally:
        probe.close()


def ensure_certificate(address):
    if CERT_FILE.exists() and KEY_FILE.exists():
        return

    subject_alt_name = f"DNS:localhost,IP:127.0.0.1,IP:{address}"
    subprocess.run(
        [
            "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(KEY_FILE), "-out", str(CERT_FILE), "-days", "365",
            "-subj", "/CN=virAR local", "-addext", f"subjectAltName={subject_alt_name}",
        ],
        cwd=ROOT,
        check=True,
    )


address = local_ip()
ensure_certificate(address)

try:
    server = HTTPServer(("0.0.0.0", PORT), SimpleHTTPRequestHandler)
except OSError as error:
    if error.errno == 98:
        raise SystemExit(
            f"El puerto {PORT} ya está ocupado. Usa 'PORT=8444 python3 server.py' "
            "o detén el servidor anterior."
        ) from error
    raise
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)
server.socket = ssl_context.wrap_socket(server.socket, server_side=True)

print(f"Abre en este PC: https://localhost:{PORT}")
print(f"Abre en la red local: https://{address}:{PORT}")
print("El navegador puede mostrar una advertencia por ser un certificado local.")

try:
    server.serve_forever()
except KeyboardInterrupt:
    print("\nServidor detenido.")
finally:
    server.server_close()