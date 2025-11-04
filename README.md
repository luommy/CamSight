# Live VLM WebUI

**A universal web interface for real-time Vision Language Model interaction and benchmarking.**

Stream your webcam to any VLM and get live AI-powered analysis - perfect for testing models, benchmarking performance, and exploring vision AI capabilities across different hardware platforms.

## Key Highlights

🌐 **Universal Compatibility** - Works with **any VLM served via OpenAI-compatible API** using base64-encoded images. Deploy on:
- 🟢 **NVIDIA Jetson** (Orin, AGX Xavier)
- 🔵 **NVIDIA DGX Spark** systems
- 🖥️ **Desktop/Workstation** (Linux, potentially Mac)
- ☁️ **Cloud APIs** (OpenAI, Anthropic, etc.)

## Features

### Core Functionality
- 🎥 **Real-time WebRTC streaming** - Low-latency bidirectional video
- 🔌 **OpenAI-compatible API** - Works with vLLM, SGLang, Ollama, TGI, or any vision API endpoint that uses base64-encoded images
- 📝 **Interactive prompt editor** - 10+ preset prompts (scene description, object detection, safety monitoring, OCR, etc.) + custom prompts
- ⚡ **Async processing** - Smooth video while VLM processes frames in background
- 🔧 **Flexible deployment** - Local inference or cloud APIs (OpenAI, Anthropic, etc.)

### UI & Visualization
- 🎨 **Modern NVIDIA-themed UI** - Professional design inspired by NVIDIA NGC Catalog with NVIDIA green accents
- 🌓 **Light/Dark theme toggle** - Automatic preference persistence with localStorage
- 📊 **Live system monitoring** - Real-time GPU, VRAM, CPU, and RAM stats with sparkline charts
- ⏱️ **Inference metrics** - Live latency tracking (last, average, total count) displayed with VLM output
- 🪞 **Video mirroring** - Toggle button overlay on camera view
- 📱 **Compact layout** - Single-screen design with all content visible (video, output, stats, controls)

### Configuration & Control
- 🎛️ **Dynamic settings** - Change model, prompt, and processing interval without restarting
- 📹 **Multi-camera support** - Detect and switch between multiple cameras (USB webcams, built-in cameras)
- 🔄 **Model auto-detection** - Refresh button to discover available models from API
- ⚙️ **Adjustable processing rate** - Control frame interval (1-3600 frames, default 30)
- 🎯 **Max tokens control** - Fine-tune output length (1-4096 tokens)
- 🔌 **WebSocket real-time updates** - Instant feedback on settings and analysis results

### Platform Support
- 💻 **Cross-platform monitoring** - Auto-detects NVIDIA GPUs (NVML), with framework for Apple Silicon and AMD
- 🖥️ **Dynamic system detection** - Automatically displays CPU model name and hostname
  - Linux: reads from `/proc/cpuinfo`
  - macOS: uses `sysctl machdep.cpu.brand_string`
  - Windows: uses WMIC
- 🔒 **HTTPS support** - Self-signed certificates for secure webcam access

## Future Enhancements (Roadmap)

- [ ] Benchmark mode for side-by-side model comparison
- [ ] Model download UI (➕ button placeholder ready)
- [ ] Cloud API templates (OpenAI, Anthropic quick configs)
- [ ] Recording functionality (save analysis sessions)
- [ ] Export results (JSON, CSV)
- [ ] Mobile app support

## Screenshot

![](https://github.com/user-attachments/assets/0fa02fc5-c130-43e8-b42d-acd01853270c)

## Architecture

1. **Uplink**: Webcam video → WebRTC → Server
2. **Processing**: Server extracts frames → VLM analyzes based on your prompt (async)
3. **Downlink**: Clean video stream → WebRTC → Browser
4. **UI Updates**: VLM results → WebSocket → Real-time text display

The VLM processes frames asynchronously in the background. The video stream continues smoothly while results are displayed in a separate text panel via WebSocket, ensuring no visual interference and instant updates when new analysis completes.

## Prerequisites

- Python 3.8+
- A VLM serving backend (choose one):
  - [vLLM](https://github.com/vllm-project/vllm) (recommended for performance)
  - [SGLang](https://github.com/sgl-project/sglang) (good for complex reasoning)
  - [Ollama](https://ollama.ai/) (easiest to get started)
  - Any OpenAI-compatible API
- Webcam (V4L2 compliant video source)

## Installation

1. **Clone the repository**:
```bash
git clone https://github.com/nvidia-ai-iot/live-vlm-webui.git
cd live-vlm-webui
```

2. **Create a conda environment** (recommended):
```bash
conda create -n live-vlm-webui python=3.10 -y
conda activate live-vlm-webui
```

3. **Install Python dependencies**:
```bash
pip install -r requirements.txt
```

4. **Generate SSL certificates** (required for webcam access):
```bash
./generate_cert.sh
```

This will create `cert.pem` and `key.pem` in the project directory. These are self-signed certificates for local development.

**Note:** Modern browsers require HTTPS to access webcam/microphone. The self-signed certificate will trigger a security warning - you'll need to click "Advanced" → "Proceed" to accept it.

5. **Set up your VLM backend** (choose one):

### Option A: Ollama (Easiest)
```bash
# Install ollama from https://ollama.ai/download
# Pull a vision model
ollama pull llava:7b

# Start ollama server
ollama serve
```

### Option B: vLLM (Recommended)
```bash
# Install vLLM
pip install vllm

# Start vLLM server with a vision model
python -m vllm.entrypoints.openai.api_server \
  --model llama-3.2-11b-vision-instruct \
  --port 8000
```

### Option C: SGLang
```bash
# Install SGLang
pip install "sglang[all]"

# Start SGLang server
python -m sglang.launch_server \
  --model-path llama-3.2-11b-vision-instruct \
  --port 30000
```

## Usage

### Quick Start

1. **Start your VLM backend** (see installation above)

2. **Start the server** (easiest way):
```bash
./start_server.sh
```

This will automatically start the server with SSL enabled using Ollama's `llama3.2-vision:11b` model.

3. **Open your browser** and navigate to:
```
https://<IP_ADDRESS>:8080
```

4. **Accept the security warning** (click "Advanced" → "Proceed")

Click "**Advanced**" button.

![](https://github.com/user-attachments/assets/2d93e90b-708b-4834-baee-f916037b2ea1")

Then click on "**Proceeed to <IP_ADDRESS> (unsafe)**".

![](https://github.com/user-attachments/assets/455bd71f-2d87-4aa2-9da7-b75c84e8c262")

5. **Click "Start Analysis"** and allow camera access

![](https://github.com/user-attachments/assets/c2a8c58b-9271-479e-88a1-8369dbcc3178)

### Using the Web Interface

Once the server is running, the web interface provides full control:

**Left Sidebar Controls:**
- **VLM API Configuration** - Change API URL, key, and model on-the-fly
  - **Model Selection** with compact icon buttons: 🔄 Refresh models | ➕ Download (coming soon)
  - Auto-detects available models from your VLM API
- **Camera and App Control** - Select camera and control application
  - Dropdown menu lists all detected video input devices
  - Switch cameras on-the-fly without restarting analysis
  - **Start/Stop buttons** - Open camera and start VLM analysis | Stop
- **Prompt Editor** - Choose from 10+ presets or write custom prompts
  - Adjust **Max Tokens** for response length (1-4096)
  - Presets include: scene description, object detection, safety monitoring, OCR, emotion detection, etc.
- **Processing Settings** - Set frame interval (1-3600 frames)
  - Lower (5-30) = more frequent analysis, higher GPU usage
  - Higher (60-300) = less frequent, good for benchmarking and power saving

**Main Content Area:**
- **Video Feed** - Live webcam with mirror toggle button (🔄) overlay in corner
- **VLM Output Card** - Real-time analysis results with:
  - Model name and inference latency metrics (last, average, count)
  - Current prompt display (shown in gray box with green accent)
  - Generated text output with fade effect to indicate freshness
- **System Stats Card** - Live monitoring with:
  - System info header: `hostname (CPU model) with GPU name`
  - GPU utilization and VRAM usage with progress bars
  - CPU and RAM stats with progress bars
  - Sparkline graphs showing historical trends (60-second window)

**Header:**
- **Logo and Title** - 🎥 "Live VLM WebUI" with subtitle
- **Connection Status** - Shows WebSocket connectivity (Connected/Disconnected)
- **Theme Toggle** - Switch between Light/Dark modes (🌙/☀️)

### Manual Usage

**With vLLM**:
```bash
python server.py --model llama-3.2-11b-vision-instruct \
  --api-base http://localhost:8000/v1 \
  --ssl-cert cert.pem --ssl-key key.pem
```

**With SGLang**:
```bash
python server.py --model llama-3.2-11b-vision-instruct \
  --api-base http://localhost:30000/v1 \
  --ssl-cert cert.pem --ssl-key key.pem
```

**With Ollama**:
```bash
python server.py --model llava:7b \
  --api-base http://localhost:11434/v1 \
  --ssl-cert cert.pem --ssl-key key.pem
```

### Custom Prompts - Beyond Captioning

The real power is in custom prompts! Here are some examples:

**Scene Description (default)**:
```bash
python server.py --model llama-3.2-11b-vision-instruct \
  --api-base http://localhost:8000/v1 \
  --ssl-cert cert.pem --ssl-key key.pem \
  --prompt "Describe what you see in this image in one sentence."
```

**Object Detection**:
```bash
python server.py --model llama-3.2-11b-vision-instruct \
  --api-base http://localhost:8000/v1 \
  --ssl-cert cert.pem --ssl-key key.pem \
  --prompt "List all objects you can see in this image."
```

**Safety Monitoring**:
```bash
python server.py --model llama-3.2-11b-vision-instruct \
  --api-base http://localhost:8000/v1 \
  --ssl-cert cert.pem --ssl-key key.pem \
  --prompt "Alert me if you see any safety hazards or dangerous situations."
```

**Activity Recognition**:
```bash
python server.py --model llama-3.2-11b-vision-instruct \
  --api-base http://localhost:8000/v1 \
  --ssl-cert cert.pem --ssl-key key.pem \
  --prompt "What activity is the person performing?"
```

**Accessibility**:
```bash
python server.py --model llama-3.2-11b-vision-instruct \
  --api-base http://localhost:8000/v1 \
  --ssl-cert cert.pem --ssl-key key.pem \
  --prompt "Describe the scene in detail for a visually impaired person."
```

**Emotion/Expression Detection**:
```bash
python server.py --model llama-3.2-11b-vision-instruct \
  --api-base http://localhost:8000/v1 \
  --ssl-cert cert.pem --ssl-key key.pem \
  --prompt "Describe the facial expressions and emotions you observe."
```

## Configuration

### Command-line Options

```bash
python server.py --help
```

**Required**:
- `--model MODEL` - VLM model name (e.g., `llama-3.2-11b-vision-instruct`)

**Optional**:
- `--host HOST` - Host to bind to (default: `0.0.0.0`)
- `--port PORT` - Port to bind to (default: `8080`)
- `--api-base URL` - VLM API base URL (default: `http://localhost:8000/v1`)
- `--api-key KEY` - API key, use `EMPTY` for local servers (default: `EMPTY`)
- `--prompt TEXT` - Custom prompt for VLM (default: scene description)
- `--process-every N` - Process every Nth frame (default: `30`)

### Example Configurations

**High-frequency updates** (more responsive, higher CPU usage):
```bash
python server.py --model llama-3.2-11b-vision-instruct \
  --api-base http://localhost:8000/v1 \
  --process-every 15
```

**Custom port and host**:
```bash
python server.py --model llava:7b \
  --api-base http://localhost:11434/v1 \
  --host 0.0.0.0 \
  --port 3000
```

**Using OpenAI API** (or any remote service):
```bash
python server.py --model gpt-4-vision-preview \
  --api-base https://api.openai.com/v1 \
  --api-key your-api-key-here
```

## Performance Tuning

### Frame Processing Rate
You can adjust frame processing in two ways:

**Via Command Line** (at startup):
```bash
python server.py --model llama-3.2-11b-vision-instruct \
  --api-base http://localhost:8000/v1 \
  --ssl-cert cert.pem --ssl-key key.pem \
  --process-every 60  # Process every 60 frames
```

**Via Web UI** (while running):
- Go to "Processing Settings" in the left sidebar
- Change "Frame Processing Interval" (1-3600 frames)
- Click "Apply Settings" - takes effect immediately!

**Guidelines:**
- **Lower values** (5-15 frames) = more frequent analysis, higher GPU usage (~2-6 FPS @ 30fps)
- **Default** (30 frames) = balanced, ~1 FPS analysis @ 30fps video
- **Higher values** (60-120 frames) = less frequent, good for monitoring (~0.25-0.5 FPS)
- **Very high** (300-3600 frames) = infrequent updates for benchmarking or power saving
  - 300 frames = ~10 second intervals @ 30fps
  - 900 frames = ~30 second intervals @ 30fps
  - 3600 frames = ~2 minute intervals @ 30fps

### Model Selection
Choose based on your hardware and needs:

**Fast models (good for prototyping)**:
- `llava:7b` (Ollama)
- `llava-1.5-7b-hf` (vLLM/SGLang)

**Balanced**:
- `llama-3.2-11b-vision-instruct` (recommended)
- `llava:13b`

**High quality** (requires significant GPU memory):
- `llava:34b`
- `gpt-4-vision-preview` (via OpenAI API)

### Video Resolution
Edit `index.html` to change the requested video resolution:
```javascript
video: {
    width: { ideal: 640 },   // Lower for better performance
    height: { ideal: 480 }
}
```

## API Compatibility

This tool uses the OpenAI chat completions API format with vision support. Any backend that implements this standard will work:

### Tested Backends
- ✅ **vLLM** - Best performance, production-ready
- ✅ **SGLang** - Great for complex prompts
- ✅ **Ollama** - Easiest setup
- ✅ **OpenAI API** - Cloud-based (requires API key)

### Message Format
```python
{
  "model": "model-name",
  "messages": [{
    "role": "user",
    "content": [
      {"type": "text", "text": "your prompt"},
      {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
    ]
  }]
}
```

## Use Cases

- 🎬 **Content Creation** - Live scene analysis for video production
- 🔒 **Security** - Real-time monitoring and alert generation
- ♿ **Accessibility** - Visual assistance for visually impaired users
- 🎮 **Gaming** - AI game master or interactive experiences
- 🏥 **Healthcare** - Activity monitoring, fall detection
- 🏭 **Industrial** - Quality control, safety monitoring
- 📚 **Education** - Interactive learning experiences
- 🤖 **Robotics** - Visual feedback for robot control

## Project Structure

```
live-vlm-webui/
├── server.py            # Main WebRTC server with WebSocket support
├── video_processor.py   # Video frame processing and VLM integration
├── vlm_service.py       # VLM service (OpenAI-compatible API client)
├── gpu_monitor.py       # Cross-platform GPU/system monitoring (NVML, etc.)
├── index.html           # Frontend web UI (NVIDIA-themed, dark/light mode)
├── requirements.txt     # Python dependencies
├── start_server.sh      # Quick start script with SSL
├── generate_cert.sh     # SSL certificate generation script
├── examples.sh          # Example commands for different setups
├── ROADMAP.md          # Detailed future plans and milestones
├── .gitignore           # Git ignore patterns
└── README.md           # This file
```

## Troubleshooting

### Camera not accessible

**Issue:** Browser won't allow camera access
**Solution:**
- ✅ Make sure you're using **HTTPS** (not HTTP)
- ✅ Generate SSL certificates: `./generate_cert.sh`
- ✅ Start server with SSL: `./start_server.sh` or add `--ssl-cert cert.pem --ssl-key key.pem`
- ✅ Accept the security warning in your browser (Advanced → Proceed)
- ✅ Check browser permissions for camera access
- ✅ Try Chrome/Edge (best WebRTC support)

**Important:** Modern browsers require HTTPS to access webcam/microphone for security reasons.

### SSL Certificate Warning

**Issue:** Browser shows "Your connection is not private" warning
**Solution:** This is normal for self-signed certificates!
1. Click **"Advanced"** or **"Show Details"**
2. Click **"Proceed to localhost (unsafe)"** or **"Accept the Risk and Continue"**
3. The warning appears because we're using a self-signed certificate for local development

For production use, get a proper SSL certificate from Let's Encrypt or a certificate authority.

### VLM connection errors
- Verify your VLM backend is running
- Check the API base URL matches your backend's port
- For vLLM: `http://localhost:8000/v1`
- For SGLang: `http://localhost:30000/v1`
- For Ollama: `http://localhost:11434/v1`

### "Model not found" errors
- Ensure the model is loaded in your backend
- Model names must match exactly
- For Ollama, use `ollama list` to see available models

### Slow performance
- Use a smaller/faster model (e.g., `llava:7b`)
- Increase `--process-every` to process fewer frames
- Reduce video resolution in `index.html`
- Ensure your VLM backend is using GPU acceleration

### Connection issues
- Check that the server is running and accessible
- Verify firewall settings if accessing from another device
- Try using `--host 0.0.0.0` to bind to all interfaces

## Development

### Customizing the VLM Service

Edit `vlm_service.py` to customize API calls:

```python
# Add custom parameters
response = await self.client.chat.completions.create(
    model=self.model,
    messages=messages,
    max_tokens=self.max_tokens,
    temperature=0.7,  # Adjust for creativity
    top_p=0.9,        # Adjust for diversity
)
```

### WebSocket Communication

The server uses WebSocket for real-time bidirectional communication:

**Server → Client:**
- `vlm_response` - VLM analysis results and metrics
- `gpu_stats` - System monitoring data (GPU, CPU, RAM)
- `status` - Connection and processing status updates

**Client → Server:**
- `update_prompt` - Change prompt and max_tokens on-the-fly
- `update_model` - Switch VLM model without restart
- `update_processing` - Adjust frame processing interval

Example: Sending a prompt update from JavaScript:
```javascript
websocket.send(JSON.stringify({
    type: 'update_prompt',
    prompt: 'Describe the scene',
    max_tokens: 100
}));
```

### Adding New GPU Monitors

Extend `gpu_monitor.py` for new platforms:

```python
class AppleSiliconMonitor(GPUMonitor):
    """Monitoring for Apple M1/M2/M3 chips"""

    def get_stats(self) -> Dict:
        # Use powermetrics or ioreg to get GPU stats
        # Return standardized dict format
        pass
```

### Customizing the UI Theme

Edit CSS variables in `index.html` to customize colors:

```css
:root {
    --nvidia-green: #76B900;  /* NVIDIA brand color */
    --bg-primary: #000000;    /* Dark theme background */
    --text-primary: #FFFFFF;  /* Text color */
    /* ... more variables */
}
```

## License

MIT License - Feel free to use and modify for your projects!

## Contributing

Contributions welcome! Areas for improvement:
- ✅ ~~WebSocket support for dynamic prompt updates~~ (Implemented!)
- ✅ ~~Live GPU/system monitoring~~ (Implemented!)
- ✅ ~~Interactive prompt editor~~ (Implemented!)
- ✅ ~~Inference latency metrics~~ (Implemented!)
- 🔄 Apple Silicon GPU monitoring
- 🔄 AMD GPU monitoring
- 📹 Recording functionality
- 🎥 Multiple simultaneous camera support
- 🔊 Audio description output (TTS)
- 📱 Mobile app support
- 🏆 Benchmark mode with side-by-side comparison
- 📊 Export analysis results (JSON, CSV)

## Acknowledgments

- Built with [aiortc](https://github.com/aiortc/aiortc) - Python WebRTC implementation
- Compatible with [vLLM](https://github.com/vllm-project/vllm), [SGLang](https://github.com/sgl-project/sglang), and [Ollama](https://ollama.ai/)
- Inspired by the growing ecosystem of open-source vision language models, including [NanoVLM](https://dusty-nv.github.io/NanoLLM/).

## Citation

If you use this in your research or project, please cite:

```bibtex
@software{live_vlm_webui,
  title = {Live VLM WebUI: Real-time Vision AI Interaction},
  year = {2025},
  url = {https://github.com/nvidia-ai-iot/live-vlm-webui}
}
```
