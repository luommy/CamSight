# Quick Reference: Multi-User Considerations

## TL;DR - Current Status

**✅ Works great for:** Single user or scheduled access
**❌ Not ready for:** Multiple concurrent users accessing the same URL

---

## What Happens Now with Multiple Users?

If User A and User B both access `https://server:8090` at the same time:

| What You'll See | Why |
|-----------------|-----|
| 🔴 **Both see same VLM output** | Single shared `current_response` variable |
| 🔴 **User B sees User A's camera analysis** | VLM responses broadcast to all WebSocket clients |
| 🔴 **Settings changes affect everyone** | Single global `vlm_service` instance |
| 🔴 **Connection status shared** | WebSocket "Connected" shown to all |
| 🟢 **Video streams work independently** | Each WebRTC connection has its own track (video isolation works) |

---

## Easiest Solution: Run Multiple Instances

### 5-Minute Setup (No Code Changes)

**Terminal 1:**
```bash
python server.py --port 8090 --model llama-3.2-11b-vision-instruct --api-base http://localhost:8000/v1 --ssl-cert cert.pem --ssl-key key.pem
```

**Terminal 2:**
```bash
python server.py --port 8091 --model llama-3.2-11b-vision-instruct --api-base http://localhost:8000/v1 --ssl-cert cert.pem --ssl-key key.pem
```

**Terminal 3:**
```bash
python server.py --port 8092 --model llama-3.2-11b-vision-instruct --api-base http://localhost:8000/v1 --ssl-cert cert.pem --ssl-key key.pem
```

**Share different URLs:**
- User 1: `https://server:8090`
- User 2: `https://server:8091`
- User 3: `https://server:8092`

**Result:** ✅ Complete isolation, no interference!

---

## Docker Compose (Production Ready)

Create `docker-compose.multi.yml`:

```yaml
version: '3.8'

services:
  # Shared VLM backend
  vllm:
    image: vllm/vllm-openai:latest
    runtime: nvidia
    command: --model meta-llama/Llama-3.2-11B-Vision-Instruct --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  # WebUI instances (add more as needed)
  webui-1:
    image: ghcr.io/nvidia-ai-iot/live-vlm-webui:latest-x86
    depends_on: [vllm]
    environment:
      - VLM_API_BASE=http://vllm:8000/v1
      - VLM_MODEL=meta-llama/Llama-3.2-11B-Vision-Instruct
      - PORT=8090
    ports: ["8090:8090"]
    volumes:
      - ./cert.pem:/app/cert.pem:ro
      - ./key.pem:/app/key.pem:ro

  webui-2:
    image: ghcr.io/nvidia-ai-iot/live-vlm-webui:latest-x86
    depends_on: [vllm]
    environment:
      - VLM_API_BASE=http://vllm:8000/v1
      - VLM_MODEL=meta-llama/Llama-3.2-11B-Vision-Instruct
      - PORT=8091
    ports: ["8091:8091"]
    volumes:
      - ./cert.pem:/app/cert.pem:ro
      - ./key.pem:/app/key.pem:ro

  webui-3:
    image: ghcr.io/nvidia-ai-iot/live-vlm-webui:latest-x86
    depends_on: [vllm]
    environment:
      - VLM_API_BASE=http://vllm:8000/v1
      - VLM_MODEL=meta-llama/Llama-3.2-11B-Vision-Instruct
      - PORT=8092
    ports: ["8092:8092"]
    volumes:
      - ./cert.pem:/app/cert.pem:ro
      - ./key.pem:/app/key.pem:ro
```

**Start:**
```bash
docker-compose -f docker-compose.multi.yml up -d
```

---

## Resource Requirements

| Users | Solution | RAM | GPU VRAM | Notes |
|-------|----------|-----|----------|-------|
| **1** | Current code | 13GB | 12GB | Perfect as-is |
| **2-5** | Multiple instances | 15GB | 12GB (shared) | Recommended |
| **5-10** | Multiple instances | 17GB | 12GB | A100 40GB ideal |
| **10-20** | Session-based (needs dev) | 18GB | 12GB | Consider 80GB GPU |
| **20+** | Enterprise (major rewrite) | Varies | Multi-GPU | Kubernetes + Load Balancer |

*Assumes Llama-3.2-11B-Vision model*

---

## Key Files to Understand

### server.py (lines 28-34)
```python
# These are GLOBAL (shared across all users)
vlm_service = None      # Single instance for everyone
websockets = set()      # All WebSocket connections
pcs = set()            # All WebRTC peer connections
```

### vlm_service.py (lines 48-49)
```python
# This response is shared
self.current_response = "Initializing..."  # All users see this
self.is_processing = False                  # Single flag
```

### server.py (lines 376-398)
```python
def broadcast_text_update(text: str, metrics: dict):
    """Broadcast to ALL connected WebSocket clients"""
    for ws in websockets:  # Sends to everyone!
        asyncio.create_task(ws.send_str(message))
```

---

## When to Use What Solution?

### ✅ Use Current Code (Single User)
- Personal projects
- Development/testing
- One person at a time

### ✅ Use Multiple Instances (Recommended for Teams)
- 2-20 concurrent users
- NVIDIA team demos
- Internal testing/showcase
- **Effort:** 5-30 minutes setup
- **No code changes needed!**

### ⚠️ Use Session-Based (Needs Development)
- 10-50 concurrent users
- Need single URL for all users
- Want centralized management
- **Effort:** 1-2 weeks development

### ⚠️ Use Enterprise Architecture (Major Project)
- 50+ concurrent users
- Public deployment
- Need autoscaling
- **Effort:** 4-8 weeks development

---

## Testing Multi-User Behavior

### Test 1: Verify Current Limitation

1. Open Chrome tab A: `https://localhost:8090`
2. Start camera and VLM analysis
3. Wait for VLM output (e.g., "A person in a room")
4. Open Chrome tab B (Incognito): `https://localhost:8090`
5. **Observe:** Tab B shows "Connected" and sees tab A's output ❌

### Test 2: Verify Multi-Instance Works

1. Start instance 1: `python server.py --port 8090 ...`
2. Start instance 2: `python server.py --port 8091 ...`
3. Open tab A: `https://localhost:8090` (show your face)
4. Open tab B: `https://localhost:8091` (show a book)
5. **Observe:** Each tab shows its own VLM output ✅

---

## Common Questions

### Q: Can multiple instances share the same VLM backend?
**A:** Yes! Multiple WebUI instances can point to the same vLLM server. vLLM will batch requests efficiently.

```bash
# One VLM backend
python -m vllm.entrypoints.openai.api_server --model llama-3.2-11b-vision-instruct --port 8000

# Multiple WebUI instances connecting to it
python server.py --port 8090 --api-base http://localhost:8000/v1
python server.py --port 8091 --api-base http://localhost:8000/v1
python server.py --port 8092 --api-base http://localhost:8000/v1
```

---

### Q: How many users can share one GPU?
**A:** Depends on GPU and model:

| GPU | Model | Concurrent Users | Latency |
|-----|-------|------------------|---------|
| RTX 4090 | Llama-3.2-11B | 2-4 | 1-2s |
| A100 40GB | Llama-3.2-11B | 5-10 | 1-2s |
| A100 80GB | Llama-3.2-11B | 10-20 | 1-3s |
| 8x A100 | Llama-3.2-90B | 10-20 | 2-4s |

---

### Q: What about security for cloud deployment?
**A:** Current version has no authentication! For cloud:
- Add authentication (JWT, API keys)
- Use proper SSL certificates (Let's Encrypt)
- Add rate limiting
- Input validation
- Firewall rules

See `MULTI_USER_ANALYSIS.md` for details.

---

### Q: Will this work with Ollama/SGLang/other backends?
**A:** Yes! Multiple instances work with any OpenAI-compatible backend:

```bash
# Ollama backend (shared)
ollama serve  # Port 11434

# Multiple WebUI instances
python server.py --port 8090 --model llava:7b --api-base http://localhost:11434/v1
python server.py --port 8091 --model llava:7b --api-base http://localhost:11434/v1
```

---

### Q: Can I assign different models to different users?
**A:** Yes with multiple instances:

```bash
# User 1 gets Llama-3.2-11B
python server.py --port 8090 --model llama-3.2-11b-vision-instruct --api-base http://localhost:8000/v1

# User 2 gets Phi-3.5-Vision (faster)
python server.py --port 8091 --model phi-3.5-vision-instruct --api-base http://localhost:8001/v1
```

---

## Monitoring Multiple Instances

### Quick Status Check
```bash
# See running instances
ps aux | grep "server.py" | grep -v grep

# Check ports
ss -tlnp | grep '809[0-9]'

# Watch GPU usage
watch -n 1 nvidia-smi
```

### Docker Status
```bash
# Check containers
docker-compose -f docker-compose.multi.yml ps

# View logs
docker-compose -f docker-compose.multi.yml logs -f webui-1

# Resource usage
docker stats
```

---

## Troubleshooting

### Port Already in Use
```bash
# Find what's using the port
lsof -i :8090

# Kill it
kill $(lsof -ti :8090)
```

### Instance Not Responding
```bash
# Check logs
journalctl -u live-vlm-webui@0 -f  # If using systemd
tail -f /var/log/live-vlm-webui-8090.log  # If logging to file
```

### VLM Backend Down
```bash
# Test VLM backend
curl http://localhost:8000/v1/models

# Restart vLLM
docker restart vllm  # If using Docker
# or
pkill -f vllm && python -m vllm.entrypoints.openai.api_server ...
```

---

## Next Steps

1. **Try it now:** Run 2-3 instances and test with multiple browsers
2. **Read detailed analysis:** See `MULTI_USER_ANALYSIS.md`
3. **Deployment guide:** See `docs/multi-instance-deployment.md`
4. **Architecture diagrams:** See `docs/architecture-diagrams.md`

---

## Summary

| Aspect | Current Code | Multiple Instances | Session-Based |
|--------|-------------|-------------------|---------------|
| **Users** | 1 | 2-20 | 10-50+ |
| **Isolation** | N/A | ✅ Complete | ✅ Complete |
| **Code Changes** | None | ❌ None needed | ✅ Required (1-2 weeks) |
| **Setup Time** | 0 | 5-30 min | N/A |
| **Management** | Easy | Easy (systemd/Docker) | Medium |
| **Resource Efficient** | ✅ | ✅ (shared VLM) | ✅✅ (single process) |

**Recommendation:** Use **Multiple Instances** for NVIDIA team demos. It's the fastest path to multi-user support! 🚀

---

*For more details, see:*
- `MULTI_USER_ANALYSIS.md` - Complete technical analysis
- `docs/multi-instance-deployment.md` - Deployment examples
- `docs/architecture-diagrams.md` - Visual architecture guides





