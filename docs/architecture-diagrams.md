# Architecture Diagrams - Multi-User Analysis

## Current Architecture (Single User)

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser A                                │
│  ┌──────────────┐  ┌──────────────┐                            │
│  │   Video      │  │  WebSocket   │                            │
│  │   Stream     │  │  (Output)    │                            │
│  └──────┬───────┘  └──────▲───────┘                            │
└─────────┼──────────────────┼──────────────────────────────────┘
          │                  │
          │ WebRTC           │ WS (broadcast)
          ▼                  │
┌─────────────────────────────────────────────────────────────────┐
│                    server.py (Global State)                      │
│                                                                   │
│  ┌───────────────────────────────────────────────────┐          │
│  │  Global Variables (Shared Across All Users)       │          │
│  │                                                    │          │
│  │  • vlm_service (single instance)                  │          │
│  │    - current_response: "Latest VLM output"        │          │
│  │    - is_processing: True/False                    │          │
│  │    - _processing_lock: asyncio.Lock()             │          │
│  │                                                    │          │
│  │  • websockets = {ws_A, ws_B, ...}                 │          │
│  │  • pcs = {peer_A, peer_B, ...}                    │          │
│  │  • gpu_monitor (single instance)                  │          │
│  └───────────────────────────────────────────────────┘          │
│                                                                   │
│  ┌───────────────────────────────────────────────────┐          │
│  │  VideoProcessorTrack (Per Connection)             │          │
│  │                                                    │          │
│  │  Track A: uses shared vlm_service ─┐              │          │
│  │  Track B: uses shared vlm_service ─┼─► Single VLM│          │
│  │  Track C: uses shared vlm_service ─┘   Service   │          │
│  │                                                    │          │
│  │  • broadcast_text_update() → ALL websockets       │          │
│  └───────────────────────────────────────────────────┘          │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   VLM Backend    │
                    │  (vLLM/Ollama)   │
                    │                  │
                    │  • Single queue  │
                    │  • One inference │
                    │    at a time     │
                    └──────────────────┘

Problem: When Browser B connects:
  1. Browser B's video goes to Track B
  2. Track B calls vlm_service.process_frame()
  3. vlm_service.current_response = "Browser B's scene"
  4. broadcast_text_update() → sends to ALL (A, B, C)
  5. Browser A sees Browser B's output! ❌
```

---

## What Happens with Multiple Users (Current Code)

```
Time: T0
┌─────────┐     ┌─────────┐     ┌─────────┐
│ User A  │     │ User B  │     │ User C  │
│Browser  │     │Browser  │     │Browser  │
└────┬────┘     └────┬────┘     └────┬────┘
     │               │               │
     │ Connect       │               │
     ▼               │               │
┌─────────────────────────────────────────┐
│ Server (vlm_service.current_response =  │
│         "Initializing...")              │
└─────────────────────────────────────────┘
     │               │               │
     │ Start camera  │               │
     └──────────────►│ Frame 1       │
                     │ "Kitchen"     │
                     ▼               │
     ┌─────────────────────────────┐ │
     │ vlm_service.current_response │ │
     │ = "A kitchen with cabinets" │ │
     └─────────────────────────────┘ │
                     │               │
     │◄──────────────┤               │
     │ Broadcast     ├──────────────►│
     │ "Kitchen"     │  "Kitchen"    │
     │ CORRECT ✅    │  WRONG! ❌    │

Time: T1
     │               │               │
     │               │ Connect       │
     │               │ Start camera  │
     │               └──────────────►│ Frame 1
     │                               │ "Office"
     │                               ▼
                 ┌─────────────────────────────┐
                 │ vlm_service.current_response │
                 │ = "An office with desk"     │
                 └─────────────────────────────┘
     │               │               │
     │◄──────────────┼───────────────┤
     │ Broadcast     │  Broadcast    │ Broadcast
     │ "Office"      │  "Office"     │ "Office"
     │ WRONG! ❌     │  WRONG! ❌    │ CORRECT ✅

Result: Everyone sees the most recent VLM output,
        regardless of whose camera triggered it!
```

---

## Solution 1: Multiple Instances (No Code Changes)

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  Browser A  │      │  Browser B  │      │  Browser C  │
└──────┬──────┘      └──────┬──────┘      └──────┬──────┘
       │                    │                    │
       │ :8090              │ :8091              │ :8092
       │                    │                    │
       ▼                    ▼                    ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  Instance 1 │      │  Instance 2 │      │  Instance 3 │
│  (server.py)│      │  (server.py)│      │  (server.py)│
│             │      │             │      │             │
│ vlm_service │      │ vlm_service │      │ vlm_service │
│   ISOLATED  │      │   ISOLATED  │      │   ISOLATED  │
└──────┬──────┘      └──────┬──────┘      └──────┬──────┘
       │                    │                    │
       └────────────────────┼────────────────────┘
                            ▼
                   ┌─────────────────┐
                   │   VLM Backend   │
                   │  (Shared OK)    │
                   │                 │
                   │  vLLM batches   │
                   │  all requests   │
                   └─────────────────┘

✅ Each user has isolated state
✅ No interference between users
✅ Easy to deploy (no code changes)
✅ VLM backend shared = efficient GPU use
```

**Deployment:**
```bash
# Terminal 1
python server.py --port 8090 --model llama-3.2-11b-vision --api-base http://localhost:8000/v1

# Terminal 2
python server.py --port 8091 --model llama-3.2-11b-vision --api-base http://localhost:8000/v1

# Terminal 3
python server.py --port 8092 --model llama-3.2-11b-vision --api-base http://localhost:8000/v1
```

---

## Solution 2: Session-Based Multi-User (Code Changes Required)

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  Browser A  │      │  Browser B  │      │  Browser C  │
└──────┬──────┘      └──────┬──────┘      └──────┬──────┘
       │                    │                    │
       │ :8090              │ :8090              │ :8090
       │                    │                    │
       └────────────────────┼────────────────────┘
                            ▼
              ┌──────────────────────────────┐
              │      server.py (Modified)    │
              │                              │
              │  user_sessions = {           │
              │    "sess_abc123": {          │ ← Browser A
              │      vlm_service: VLMService,│
              │      websocket: ws_A,        │
              │      video_track: track_A    │
              │    },                        │
              │    "sess_def456": {          │ ← Browser B
              │      vlm_service: VLMService,│
              │      websocket: ws_B,        │
              │      video_track: track_B    │
              │    },                        │
              │    "sess_ghi789": {          │ ← Browser C
              │      vlm_service: VLMService,│
              │      websocket: ws_C,        │
              │      video_track: track_C    │
              │    }                         │
              │  }                           │
              └───────────────┬──────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   VLM Backend    │
                    │  (vLLM/Ollama)   │
                    │                  │
                    │  Queue:          │
                    │  1. sess_abc123  │
                    │  2. sess_def456  │
                    │  3. sess_ghi789  │
                    └──────────────────┘

Key Changes:
1. WebSocket connection → Generate session_id
2. Create VLMService per session
3. Targeted sending (not broadcast):
   send_to_session(session_id, message)
4. Session cleanup on disconnect
```

**Code Changes Required:**

```python
# server.py modifications
user_sessions = {}  # session_id → session_data

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    # Generate unique session ID
    session_id = str(uuid.uuid4())

    # Create session-specific VLM service
    user_sessions[session_id] = {
        "vlm_service": VLMService(model=..., api_base=...),
        "websocket": ws,
        "video_track": None  # Set when WebRTC connects
    }

    await ws.send_json({
        "type": "session_created",
        "session_id": session_id
    })

    try:
        async for msg in ws:
            # Handle messages using session-specific service
            session = user_sessions[session_id]
            # ...
    finally:
        del user_sessions[session_id]  # Cleanup

def send_to_session(session_id, message):
    """Send message to specific user's WebSocket"""
    session = user_sessions.get(session_id)
    if session and session["websocket"]:
        asyncio.create_task(session["websocket"].send_str(message))

# video_processor.py modifications
class VideoProcessorTrack(VideoStreamTrack):
    def __init__(self, track, session_id, user_sessions):
        self.session_id = session_id
        self.user_sessions = user_sessions
        # Use session-specific VLM service
        self.vlm_service = user_sessions[session_id]["vlm_service"]
```

---

## Solution 3: Enterprise Architecture (Major Rewrite)

```
                         ┌─────────────────────┐
                         │   Load Balancer     │
                         │  (Nginx/HAProxy)    │
                         └──────────┬──────────┘
                                    │
                ┌───────────────────┼───────────────────┐
                │                   │                   │
                ▼                   ▼                   ▼
         ┌─────────────┐     ┌─────────────┐    ┌─────────────┐
         │  Frontend   │     │  Frontend   │    │  Frontend   │
         │  Server 1   │     │  Server 2   │    │  Server 3   │
         │  (Stateless)│     │  (Stateless)│    │  (Stateless)│
         └──────┬──────┘     └──────┬──────┘    └──────┬──────┘
                │                   │                   │
                └───────────────────┼───────────────────┘
                                    │
                            ┌───────▼────────┐
                            │  Redis/DB      │
                            │  (Session      │
                            │   Storage)     │
                            └───────┬────────┘
                                    │
                            ┌───────▼────────┐
                            │ Message Queue  │
                            │ (RabbitMQ)     │
                            └───────┬────────┘
                                    │
                ┌───────────────────┼───────────────────┐
                │                   │                   │
                ▼                   ▼                   ▼
         ┌─────────────┐     ┌─────────────┐    ┌─────────────┐
         │  VLM Worker │     │  VLM Worker │    │  VLM Worker │
         │   (GPU 1)   │     │   (GPU 2)   │    │   (GPU 3)   │
         └─────────────┘     └─────────────┘    └─────────────┘

Features:
• Horizontal scaling (add more frontend servers)
• Session persistence (Redis)
• Multiple VLM workers (parallel processing)
• Queue-based request distribution
• Health checks and auto-recovery
• Monitoring and logging (Prometheus/Grafana)
```

---

## Data Flow Comparison

### Current (Single User)

```
Frame arrives → VideoTrack → vlm_service.process_frame()
                               ↓
                        vlm_service.current_response = result
                               ↓
                        broadcast_text_update()
                               ↓
                        ALL websockets get message
```

### Multi-Instance (No Code Changes)

```
Instance 1:                    Instance 2:
Frame A → Track A              Frame B → Track B
    ↓                              ↓
vlm_service_1                  vlm_service_2
(isolated)                     (isolated)
    ↓                              ↓
broadcast → ws_A               broadcast → ws_B
(only User A)                  (only User B)
```

### Session-Based (Code Changes)

```
Frame arrives → VideoTrack (session_abc123)
                    ↓
            user_sessions["session_abc123"]["vlm_service"]
                    ↓
            response stored in session-specific state
                    ↓
            send_to_session("session_abc123", response)
                    ↓
            Only User A's websocket gets message
```

---

## VLM Backend Scaling

### Single Backend (Current)

```
┌────────────────────────────────────┐
│        GPU 0 (A100 40GB)           │
│                                    │
│  ┌──────────────────────────────┐ │
│  │  vLLM Server                 │ │
│  │  • Model: Llama-3.2-11B      │ │
│  │  • VRAM: 12GB                │ │
│  │  • Free: 28GB                │ │
│  └──────────────────────────────┘ │
└────────────────────────────────────┘
         ▲
         │ All requests
         │
    ┌────┴─────┬─────────┬─────────┐
    │          │         │         │
 Instance 1 Instance 2 Instance 3 ...

Bottleneck: Single inference engine
Throughput: ~15-30 req/sec
```

### Multiple Backends (Scaled)

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   GPU 0      │  │   GPU 1      │  │   GPU 2      │
│              │  │              │  │              │
│  vLLM Server │  │  vLLM Server │  │  vLLM Server │
│  (12GB)      │  │  (12GB)      │  │  (12GB)      │
└──────────────┘  └──────────────┘  └──────────────┘
       ▲                 ▲                 ▲
       │                 │                 │
       └─────────────────┼─────────────────┘
                         │
                 Load Balancer
                         │
       ┌─────────────────┼─────────────────┐
       │                 │                 │
   Instance 1       Instance 2       Instance 3

Throughput: ~45-90 req/sec (3x improvement)
Redundancy: If one GPU fails, others continue
```

---

## Memory & Performance Scaling

### 1 User (Current)
```
Memory: 13GB (500MB WebUI + 12GB VLM)
GPU: 30% utilization (inference only)
Latency: 500-1000ms
```

### 3 Users (Multi-Instance, Shared VLM)
```
Memory: 14.5GB (3x500MB WebUI + 12GB VLM)
GPU: 60-70% utilization
Latency: 600-1200ms (slight increase)
```

### 10 Users (Multi-Instance, Shared VLM)
```
Memory: 17GB (10x500MB WebUI + 12GB VLM)
GPU: 90-100% utilization
Latency: 1000-2000ms (queuing delay)
Recommendation: Add more VLM backends
```

### 10 Users (Session-Based, Shared VLM)
```
Memory: 15GB (1 process + 10 sessions + 12GB VLM)
GPU: 90-100% utilization
Latency: 1000-2000ms (same as multi-instance)
Advantage: Single process easier to manage
```

---

## Quick Decision Matrix

| Scenario | Users | Solution | Effort | Time |
|----------|-------|----------|--------|------|
| **Personal use** | 1 | Current code | None | 0 hours |
| **Small team demo** | 2-5 | Multiple instances | Low | 30 min |
| **Department demo** | 5-20 | Multiple instances + LB | Medium | 2-4 hours |
| **Cross-team sharing** | 10-50 | Session-based | High | 1-2 weeks |
| **Public/Enterprise** | 50+ | Enterprise arch | Very High | 4-8 weeks |

---

## Recommended Architecture for NVIDIA Internal Use

```
                    ┌─────────────────────┐
                    │  NVIDIA Internal    │
                    │    Network/VPN      │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Nginx (443)        │
                    │  • SSL termination  │
                    │  • Path routing     │
                    │  • /user1, /user2   │
                    └──────────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
  ┌──────────┐          ┌──────────┐          ┌──────────┐
  │ Instance │          │ Instance │          │ Instance │
  │ 1 :8090  │          │ 2 :8091  │          │ 3 :8092  │
  └─────┬────┘          └─────┬────┘          └─────┬────┘
        │                     │                      │
        └─────────────────────┼──────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   DGX Station     │
                    │   A100 (40GB)     │
                    │                   │
                    │   vLLM Server     │
                    │   :8000           │
                    └───────────────────┘

Access:
• https://internal-server.nvidia.com/user1 → Instance 1
• https://internal-server.nvidia.com/user2 → Instance 2
• https://internal-server.nvidia.com/user3 → Instance 3

Benefits:
✅ Easy to deploy (no code changes)
✅ Isolated user experiences
✅ Single VLM backend (efficient)
✅ Behind corporate firewall (secure)
✅ Simple to add more instances
```

---

## Summary: State Sharing Problem

**Root Cause:** Single `vlm_service` instance with shared `current_response`

**Symptoms:**
- User A sees User B's camera outputs
- Settings changes affect everyone
- Connection status shared

**Fix Options:**
1. **Easy:** Run separate server instances (5 min setup)
2. **Moderate:** Implement session management (1-2 weeks dev)
3. **Complex:** Full enterprise rewrite (4-8 weeks dev)

**Recommendation:** Start with Option 1 (multiple instances) for immediate use!





