#!/bin/bash
# Start Live VLM WebUI Server with HTTPS

cd "$(dirname "$0")"

# Check if certificates exist
if [ ! -f "cert.pem" ] || [ ! -f "key.pem" ]; then
    echo "Certificates not found. Generating..."
    ./generate_cert.sh
    echo ""
fi

# Start server with HTTPS
echo "Starting Live VLM WebUI server..."
echo "Model: llama3.2-vision:11b"
echo "API: http://localhost:11434/v1 (Ollama)"
echo ""
echo "⚠️  Your browser will show a security warning (self-signed certificate)"
echo "    Click 'Advanced' → 'Proceed to localhost' (or 'Accept Risk')"
echo ""

python server.py \
  --model llama3.2-vision:11b \
  --api-base http://localhost:11434/v1 \
  --ssl-cert cert.pem \
  --ssl-key key.pem \
  --host 0.0.0.0 \
  --port 8080

