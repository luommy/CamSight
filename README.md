# Live VLM WebUI

**A universal web interface for real-time Vision Language Model interaction and benchmarking.**

Stream your webcam to any VLM and get live AI-powered analysis - perfect for testing models, benchmarking performance, and exploring vision AI capabilities across different hardware platforms.

## Key Highlights

🌐 **Universal Compatibility** - Works with **any VLM served via OpenAI-compatible API** using base64-encoded images. Deploy on:
- 🟢 **NVIDIA Jetson** (Orin, AGX Xavier)
- 🔵 **NVIDIA DGX** systems
- 🖥️ **Desktop/Workstation** (Linux, potentially Mac)
- ☁️ **Cloud APIs** (OpenAI, Anthropic, etc.)

## Features

- 🎥 **Real-time WebRTC streaming** - Low-latency bidirectional video
- 🔌 **OpenAI-compatible API** - Works with vLLM, SGLang, Ollama, TGI, or any vision API endpoint that uses base64-encoded images
- 📝 **Custom prompts** - Scene description, object detection, monitoring, alert and more
- ⚡ **Async processing** - Smooth video while VLM processes frames
- 🎨 **Modern web UI** - Clean, responsive interface with HTTPS support
- 🔧 **Flexible deployment** - Local inference or cloud APIs

## Future Enhancements (Roadmap)

- [ ] Interactive prompt editor with dropdown presets
- [ ] Model selection dropdown (auto-detect available models from API)
- [ ] Separate video and text overlay (independent HTML elements)
- [ ] Live GPU utilization stats (memory, load)
- [ ] Inference latency metrics (ms per frame)
- [ ] Multi-platform GPU monitoring (NVIDIA, Apple Silicon, AMD)
- [ ] Benchmark mode for performance comparison across hardware

## Screenshot

![](https://github.com/user-attachments/assets/0655f5d1-3912-49fb-b1b3-c1107c1ced5b)

## Architecture

1. **Uplink**: Webcam video → WebRTC → Server
2. **Processing**: Server extracts frames → VLM analyzes based on your prompt (async)
3. **Downlink**: Server adds text overlay → WebRTC → Browser

The VLM processes frames asynchronously. While processing, the video stream continues with the most recent response overlaid. This ensures smooth video without blocking.

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
https://localhost:8080
```

4. **Accept the security warning** (click "Advanced" → "Proceed")

Click "**Advanced**" button.

![](https://github.com/user-attachments/assets/2d93e90b-708b-4834-baee-f916037b2ea1")

Then click on "**Proceeed to <IP_ADDRESS> (unsafe)**".

![](https://github.com/user-attachments/assets/455bd71f-2d87-4aa2-9da7-b75c84e8c262")

5. **Click "Start VLM Analysis"** and allow camera access

![](https://github.com/user-attachments/assets/c2a8c58b-9271-479e-88a1-8369dbcc3178)

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
Adjust `--process-every` to control how often frames are sent to the VLM:
- Higher values (e.g., 60) = less frequent updates, lower CPU/GPU usage
- Lower values (e.g., 15) = more frequent updates, higher resource usage
- Default (30) = ~1 update per second at 30fps

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
├── server.py           # Main WebRTC server
├── video_processor.py  # Video processing and text overlay
├── vlm_service.py      # VLM service (OpenAI-compatible API client)
├── index.html          # Frontend web interface
├── requirements.txt    # Python dependencies
├── .gitignore          # Git ignore file
└── README.md          # This file
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
    max_tokens=512,
    temperature=0.7,  # Adjust for creativity
    top_p=0.9,        # Adjust for diversity
)
```

### Customizing the Overlay

Edit `video_processor.py` to change how text is displayed:

```python
def _add_text_overlay(self, img, text, status):
    # Customize colors, fonts, positions, etc.
    text_color = (255, 255, 255)  # White
    bg_color = (0, 0, 0)           # Black
    font_scale = 0.7
    # ... more customization
```

### Adding Dynamic Prompt Updates

You could extend the UI to allow prompt changes without restarting:

```javascript
// In index.html, add a prompt input and send via WebSocket
// Then update vlm_service.update_prompt(new_prompt)
```

## License

MIT License - Feel free to use and modify for your projects!

## Contributing

Contributions welcome! Areas for improvement:
- WebSocket support for dynamic prompt updates
- Recording functionality
- Multiple simultaneous camera support
- Audio description output
- Mobile app support

## Acknowledgments

- Built with [aiortc](https://github.com/aiortc/aiortc) - Python WebRTC implementation
- Compatible with [vLLM](https://github.com/vllm-project/vllm), [SGLang](https://github.com/sgl-project/sglang), and [Ollama](https://ollama.ai/)
- Inspired by the growing ecosystem of open-source vision language models

## Citation

If you use this in your research or project, please cite:

```bibtex
@software{live_vlm_webui,
  title = {Live VLM WebUI: Real-time Vision AI Interaction},
  year = {2025},
  url = {https://github.com/yourusername/live-vlm-webui}
}
```
