import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()

TLS_CERT = os.environ.get("TLS_CERT", str(BASE_DIR / "certs/cert.pem"))
TLS_KEY  = os.environ.get("TLS_KEY",  str(BASE_DIR / "certs/key.pem"))

HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 8443))

API_KEY = os.environ.get("CLIENT_INFO_API_KEY", "")

CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")
