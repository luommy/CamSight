#!/bin/bash
# Generate self-signed SSL certificate for local development

echo "Generating self-signed SSL certificate..."

openssl req -x509 -newkey rsa:4096 -nodes \
  -out cert.pem \
  -keyout key.pem \
  -days 365 \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1,IP:10.110.51.105"

echo "✓ Certificate generated!"
echo "  - cert.pem (certificate)"
echo "  - key.pem (private key)"
echo ""
echo "Note: Your browser will show a security warning because this is self-signed."
echo "You'll need to click 'Advanced' and 'Proceed to localhost' to access the site."

