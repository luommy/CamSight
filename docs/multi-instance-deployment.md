# Quick Multi-Instance Deployment Guide

This guide shows you how to run multiple isolated instances of Live VLM WebUI for multiple users **without any code changes**.

## Overview

Each instance runs independently with:
- ✅ Separate VLM service (isolated state)
- ✅ Different port
- ✅ Independent settings and outputs
- ✅ No interference between users

## Deployment Options

### Option 1: Multiple Processes (Simple)

Run separate Python processes on different ports:

```bash
# Terminal 1 - Instance for User/Team A (port 8090)
python server.py \
  --port 8090 \
  --model llama-3.2-11b-vision-instruct \
  --api-base http://localhost:8000/v1 \
  --ssl-cert cert.pem --ssl-key key.pem

# Terminal 2 - Instance for User/Team B (port 8091)
python server.py \
  --port 8091 \
  --model llama-3.2-11b-vision-instruct \
  --api-base http://localhost:8000/v1 \
  --ssl-cert cert.pem --ssl-key key.pem

# Terminal 3 - Instance for User/Team C (port 8092)
python server.py \
  --port 8092 \
  --model llama-3.2-11b-vision-instruct \
  --api-base http://localhost:8000/v1 \
  --ssl-cert cert.pem --ssl-key key.pem
```

**Access URLs:**
- User A: `https://your-server:8090`
- User B: `https://your-server:8091`
- User C: `https://your-server:8092`

---

### Option 2: Systemd Services (Production)

Create systemd service files for automatic startup and management.

**Create `/etc/systemd/system/live-vlm-webui@.service`:**

```ini
[Unit]
Description=Live VLM WebUI Instance %i
After=network.target

[Service]
Type=simple
User=vlm
WorkingDirectory=/opt/live-vlm-webui
Environment="PATH=/opt/live-vlm-webui/.venv/bin"
ExecStart=/opt/live-vlm-webui/.venv/bin/python server.py \
    --port 809%i \
    --model llama-3.2-11b-vision-instruct \
    --api-base http://localhost:8000/v1 \
    --ssl-cert /opt/live-vlm-webui/cert.pem \
    --ssl-key /opt/live-vlm-webui/key.pem
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Start instances:**

```bash
# Enable and start 3 instances
sudo systemctl enable live-vlm-webui@0  # Port 8090
sudo systemctl enable live-vlm-webui@1  # Port 8091
sudo systemctl enable live-vlm-webui@2  # Port 8092

sudo systemctl start live-vlm-webui@0
sudo systemctl start live-vlm-webui@1
sudo systemctl start live-vlm-webui@2

# Check status
sudo systemctl status live-vlm-webui@*
```

---

### Option 3: Docker Compose (Recommended)

Create a `docker-compose.multi.yml` file:

```yaml
version: '3.8'

services:
  # Shared VLM backend (single instance, all frontends connect to it)
  vllm:
    image: vllm/vllm-openai:latest
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=0  # Use first GPU
    command: >
      --model meta-llama/Llama-3.2-11B-Vision-Instruct
      --host 0.0.0.0
      --port 8000
      --tensor-parallel-size 1
    ports:
      - "8000:8000"
    volumes:
      - $HOME/.cache/huggingface:/root/.cache/huggingface
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  # Frontend instance 1 (port 8090)
  webui-1:
    image: ghcr.io/nvidia-ai-iot/live-vlm-webui:latest-x86
    depends_on:
      - vllm
    environment:
      - VLM_API_BASE=http://vllm:8000/v1
      - VLM_MODEL=meta-llama/Llama-3.2-11B-Vision-Instruct
      - PORT=8090
    ports:
      - "8090:8090"
    volumes:
      - ./cert.pem:/app/cert.pem:ro
      - ./key.pem:/app/key.pem:ro
    restart: unless-stopped

  # Frontend instance 2 (port 8091)
  webui-2:
    image: ghcr.io/nvidia-ai-iot/live-vlm-webui:latest-x86
    depends_on:
      - vllm
    environment:
      - VLM_API_BASE=http://vllm:8000/v1
      - VLM_MODEL=meta-llama/Llama-3.2-11B-Vision-Instruct
      - PORT=8091
    ports:
      - "8091:8091"
    volumes:
      - ./cert.pem:/app/cert.pem:ro
      - ./key.pem:/app/key.pem:ro
    restart: unless-stopped

  # Frontend instance 3 (port 8092)
  webui-3:
    image: ghcr.io/nvidia-ai-iot/live-vlm-webui:latest-x86
    depends_on:
      - vllm
    environment:
      - VLM_API_BASE=http://vllm:8000/v1
      - VLM_MODEL=meta-llama/Llama-3.2-11B-Vision-Instruct
      - PORT=8092
    ports:
      - "8092:8092"
    volumes:
      - ./cert.pem:/app/cert.pem:ro
      - ./key.pem:/app/key.pem:ro
    restart: unless-stopped

  # Optional: Nginx reverse proxy for unified access
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./cert.pem:/etc/nginx/cert.pem:ro
      - ./key.pem:/etc/nginx/key.pem:ro
    depends_on:
      - webui-1
      - webui-2
      - webui-3
    restart: unless-stopped
```

**Start the stack:**

```bash
docker-compose -f docker-compose.multi.yml up -d
```

**Access:**
- Direct: `https://server:8090`, `https://server:8091`, `https://server:8092`
- Via Nginx: `https://server/user1`, `https://server/user2`, `https://server/user3`

---

### Option 4: Kubernetes Deployment (Advanced)

For larger deployments (10+ users), use Kubernetes with multiple pods:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: live-vlm-webui
spec:
  replicas: 5  # 5 independent instances
  selector:
    matchLabels:
      app: live-vlm-webui
  template:
    metadata:
      labels:
        app: live-vlm-webui
    spec:
      containers:
      - name: webui
        image: ghcr.io/nvidia-ai-iot/live-vlm-webui:latest-x86
        env:
        - name: VLM_API_BASE
          value: "http://vllm-service:8000/v1"
        - name: VLM_MODEL
          value: "llama-3.2-11b-vision-instruct"
        ports:
        - containerPort: 8090
        resources:
          limits:
            memory: "1Gi"
            cpu: "1000m"
---
apiVersion: v1
kind: Service
metadata:
  name: live-vlm-webui
spec:
  selector:
    app: live-vlm-webui
  type: LoadBalancer
  ports:
  - port: 443
    targetPort: 8090
    protocol: TCP
```

**Deploy:**

```bash
kubectl apply -f k8s-deployment.yaml
```

This creates 5 pods behind a load balancer, each serving independent users.

---

## VLM Backend Considerations

### Single VLM Backend (Shared)

**Pros:**
- ✅ Efficient GPU utilization
- ✅ Easy to manage
- ✅ vLLM batches requests automatically

**Cons:**
- ❌ All users share VLM capacity
- ❌ Higher latency with more users
- ❌ Single point of failure

**Recommended for:** 5-20 concurrent users with A100/H100 GPU

---

### Multiple VLM Backends (Isolated)

Run separate VLM instances for complete isolation:

```bash
# VLM instance 1 (GPU 0, port 8000)
CUDA_VISIBLE_DEVICES=0 python -m vllm.entrypoints.openai.api_server \
  --model llama-3.2-11b-vision-instruct \
  --port 8000 &

# VLM instance 2 (GPU 1, port 8001)
CUDA_VISIBLE_DEVICES=1 python -m vllm.entrypoints.openai.api_server \
  --model llama-3.2-11b-vision-instruct \
  --port 8001 &

# VLM instance 3 (GPU 2, port 8002)
CUDA_VISIBLE_DEVICES=2 python -m vllm.entrypoints.openai.api_server \
  --model llama-3.2-11b-vision-instruct \
  --port 8002 &
```

Then point each WebUI instance to its dedicated VLM:

```bash
# WebUI 1 → VLM 1
python server.py --port 8090 --api-base http://localhost:8000/v1

# WebUI 2 → VLM 2
python server.py --port 8091 --api-base http://localhost:8001/v1

# WebUI 3 → VLM 3
python server.py --port 8092 --api-base http://localhost:8002/v1
```

**Recommended for:** VIP users or critical applications needing guaranteed latency

---

## Reverse Proxy Setup (Optional)

Use Nginx to provide a single entry point with path-based routing:

**`nginx.conf`:**

```nginx
events {
    worker_connections 1024;
}

http {
    upstream webui_instance_1 {
        server localhost:8090;
    }

    upstream webui_instance_2 {
        server localhost:8091;
    }

    upstream webui_instance_3 {
        server localhost:8092;
    }

    server {
        listen 443 ssl;
        server_name your-server.com;

        ssl_certificate /path/to/cert.pem;
        ssl_certificate_key /path/to/key.pem;

        # Instance 1
        location /user1/ {
            proxy_pass https://webui_instance_1/;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
        }

        # Instance 2
        location /user2/ {
            proxy_pass https://webui_instance_2/;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
        }

        # Instance 3
        location /user3/ {
            proxy_pass https://webui_instance_3/;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
        }

        # Landing page
        location = / {
            return 200 '
            <html>
            <head><title>Live VLM WebUI - Multi-User</title></head>
            <body style="font-family: sans-serif; max-width: 600px; margin: 50px auto;">
                <h1>Live VLM WebUI</h1>
                <p>Choose your instance:</p>
                <ul>
                    <li><a href="/user1/">Instance 1</a></li>
                    <li><a href="/user2/">Instance 2</a></li>
                    <li><a href="/user3/">Instance 3</a></li>
                </ul>
            </body>
            </html>';
            add_header Content-Type text/html;
        }
    }
}
```

**Start Nginx:**

```bash
nginx -c /path/to/nginx.conf
```

**Access:**
- Landing page: `https://your-server.com/`
- User 1: `https://your-server.com/user1/`
- User 2: `https://your-server.com/user2/`
- User 3: `https://your-server.com/user3/`

---

## Resource Planning

### Memory Usage

| Component | Per Instance | 3 Instances | 10 Instances |
|-----------|--------------|-------------|--------------|
| **WebUI Server** | ~500MB | ~1.5GB | ~5GB |
| **VLM Backend** | ~12GB (11B model) | 12GB (shared) | 12GB (shared) |
| **System overhead** | ~1GB | ~2GB | ~4GB |
| **Total** | ~13.5GB | ~15.5GB | ~21GB |

*Assumes shared VLM backend. For isolated VLM backends, multiply VLM memory by number of instances.*

### GPU Allocation

**Scenario 1: Single GPU (Shared VLM)**
```
┌──────────────────────────────┐
│  GPU 0 (A100 40GB)           │
│  ┌────────────────────────┐  │
│  │  vLLM (12GB)           │  │
│  └────────────────────────┘  │
│                              │
│  Serves all WebUI instances  │
└──────────────────────────────┘
```

**Scenario 2: Multiple GPUs (Isolated VLM)**
```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ GPU 0        │  │ GPU 1        │  │ GPU 2        │
│ vLLM 1       │  │ vLLM 2       │  │ vLLM 3       │
│ (12GB)       │  │ (12GB)       │  │ (12GB)       │
└──────────────┘  └──────────────┘  └──────────────┘
       ↑                 ↑                 ↑
    WebUI 1          WebUI 2          WebUI 3
```

---

## Monitoring Multiple Instances

### Process Monitoring

```bash
# Check running instances
ps aux | grep "server.py"

# Check ports in use
ss -tlnp | grep '809[0-9]'

# Monitor resource usage
htop -p $(pgrep -d',' -f server.py)
```

### Docker Monitoring

```bash
# Check container status
docker-compose -f docker-compose.multi.yml ps

# View logs
docker-compose -f docker-compose.multi.yml logs -f webui-1
docker-compose -f docker-compose.multi.yml logs -f webui-2

# Resource usage
docker stats
```

### Simple Dashboard Script

Create `monitor.sh`:

```bash
#!/bin/bash

watch -n 1 '
echo "=== Live VLM WebUI Multi-Instance Monitor ==="
echo ""
echo "WebUI Instances:"
ps aux | grep "[s]erver.py" | awk "{print \$2, \$11, \$12, \$13}"
echo ""
echo "Port Status:"
ss -tlnp | grep "809[0-9]"
echo ""
echo "VLM Backend:"
curl -s http://localhost:8000/v1/models | jq -r ".data[0].id"
echo ""
echo "Memory Usage:"
free -h | grep Mem
echo ""
echo "GPU Usage:"
nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits
'
```

---

## Troubleshooting

### Port Already in Use

```bash
# Find what's using port 8090
lsof -i :8090

# Kill process
kill $(lsof -ti :8090)
```

### VLM Backend Overwhelmed

**Symptoms:**
- Increasing latency
- Timeout errors
- Slow responses

**Solutions:**
1. Use faster model (Phi-3.5-Vision 4B)
2. Reduce processing frequency (`--process-every 60`)
3. Add more VLM backends
4. Upgrade to larger GPU (A100 80GB, H100)

### SSL Certificate Issues

Each instance needs to use the same cert, or generate unique certs:

```bash
# Shared cert (recommended)
./generate_cert.sh
# Use same cert.pem/key.pem for all instances

# Unique certs per instance
./generate_cert.sh && mv cert.pem cert-1.pem && mv key.pem key-1.pem
./generate_cert.sh && mv cert.pem cert-2.pem && mv key.pem key-2.pem
./generate_cert.sh && mv cert.pem cert-3.pem && mv key.pem key-3.pem

# Start with unique certs
python server.py --port 8090 --ssl-cert cert-1.pem --ssl-key key-1.pem
python server.py --port 8091 --ssl-cert cert-2.pem --ssl-key key-2.pem
```

---

## Cost Estimation (Cloud Hosting)

### AWS

| Instance Type | GPU | vCPU | RAM | Price/hr | 3 Instances + VLM |
|---------------|-----|------|-----|----------|-------------------|
| **g5.xlarge** | A10G (24GB) | 4 | 16GB | $1.01 | ~$3/hr (~$2,160/mo) |
| **g5.2xlarge** | A10G (24GB) | 8 | 32GB | $1.21 | ~$3.63/hr (~$2,614/mo) |
| **p4d.24xlarge** | 8x A100 (40GB) | 96 | 1152GB | $32.77 | ~$32.77/hr (~$23,595/mo) |

*Prices are estimates (2024). Use spot instances for 70% savings.*

### Azure

| Instance Type | GPU | vCPU | RAM | Price/hr | 3 Instances + VLM |
|---------------|-----|------|-----|----------|-------------------|
| **NC6s_v3** | V100 (16GB) | 6 | 112GB | $3.06 | ~$3.06/hr (~$2,203/mo) |
| **ND96asr_v4** | 8x A100 (40GB) | 96 | 900GB | $27.20 | ~$27.20/hr (~$19,584/mo) |

---

## Best Practices

1. **Firewall Configuration**
   - Only expose ports you need (8090-8092, 443)
   - Use VPN for internal demos
   - Restrict SSH access

2. **SSL Certificates**
   - Use Let's Encrypt for public domains
   - Use corporate CA for internal
   - Auto-renew certificates

3. **Logging**
   - Centralize logs (syslog, CloudWatch)
   - Rotate logs to save disk space
   - Monitor for errors

4. **Backup**
   - Version control configuration files
   - Document deployment steps
   - Keep SSL certificates backed up

5. **Update Strategy**
   - Test updates on one instance first
   - Rolling updates (update instance 1, test, then 2, then 3)
   - Keep one instance on previous version during updates

---

## Summary

**Quick Start (5 minutes):**
```bash
# Run 3 instances
python server.py --port 8090 --model llama-3.2-11b-vision-instruct &
python server.py --port 8091 --model llama-3.2-11b-vision-instruct &
python server.py --port 8092 --model llama-3.2-11b-vision-instruct &

# Share these URLs with your team
echo "User 1: https://$(hostname -I | awk '{print $1}'):8090"
echo "User 2: https://$(hostname -I | awk '{print $1}'):8091"
echo "User 3: https://$(hostname -I | awk '{print $1}'):8092"
```

**Production (Docker Compose):**
```bash
docker-compose -f docker-compose.multi.yml up -d
```

That's it! Each user gets an isolated instance. 🚀





