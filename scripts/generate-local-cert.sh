#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CERT_DIR="$ROOT_DIR/certs"
CRT="$CERT_DIR/local.crt"
KEY="$CERT_DIR/local.key"

mkdir -p "$CERT_DIR"

if [[ -f "$CRT" && -f "$KEY" ]]; then
  echo "Existing certificate found:"
  echo "  $CRT"
  echo "  $KEY"
  echo "Remove them first if you want to regenerate."
  exit 0
fi

openssl req -x509 -nodes -newkey rsa:2048 -sha256 -days 825 \
  -keyout "$KEY" \
  -out "$CRT" \
  -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,DNS:study-dashboard.local,IP:127.0.0.1,IP:::1"

chmod 600 "$KEY"
chmod 644 "$CRT"

cat <<MSG
Generated local HTTPS certificate:
  $CRT
  $KEY

Use:
  docker compose up -d --build
  open https://localhost:3443

Browsers will warn because this is self-signed. For local testing, accept the warning
or import certs/local.crt into your system/browser trust store.
MSG
