"""
WebRTC Live VLM WebUI Server
Main server that handles WebRTC connections and serves the web interface
"""
import asyncio
import json
import logging
import os
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
from aiortc.contrib.media import MediaRelay

from vlm_service import VLMService
from video_processor import VideoProcessorTrack

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global objects
relay = MediaRelay()
pcs = set()
vlm_service = None


async def index(request):
    """Serve the main HTML page"""
    content = open(os.path.join(os.path.dirname(__file__), "index.html"), "r").read()
    return web.Response(content_type="text/html", text=content)


async def offer(request):
    """Handle WebRTC offer from client"""
    params = await request.json()
    offer_sdp = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    # Create RTCPeerConnection
    pc = RTCPeerConnection()
    pcs.add(pc)

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logger.info(f"Connection state: {pc.connectionState}")
        if pc.connectionState in ["failed", "closed"]:
            await pc.close()
            pcs.discard(pc)

    @pc.on("track")
    def on_track(track):
        logger.info(f"Received track: {track.kind}")

        if track.kind == "video":
            # Create processor track with VLM service
            processor_track = VideoProcessorTrack(relay.subscribe(track), vlm_service)

            # Add processed track back to connection
            pc.addTrack(processor_track)
            logger.info(f"Added processed video track back to peer connection")

        @track.on("ended")
        async def on_ended():
            logger.info(f"Track {track.kind} ended")

    # Handle offer - this will trigger on_track
    await pc.setRemoteDescription(offer_sdp)

    # Create answer - this must happen after tracks are added
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    logger.info(f"Created answer with {len(pc.getTransceivers())} transceivers")

    return web.Response(
        content_type="application/json",
        text=json.dumps({
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type
        })
    )


async def on_shutdown(app):
    """Cleanup on server shutdown"""
    # Close all peer connections
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()


def main():
    """Main entry point"""
    import argparse
    import ssl

    parser = argparse.ArgumentParser(
        description="WebRTC Live VLM WebUI - Real-time vision model interaction",
        epilog="Examples:\n"
               "  vLLM:    python server.py --model llama-3.2-11b-vision-instruct --api-base http://localhost:8000/v1\n"
               "  SGLang:  python server.py --model llama-3.2-11b-vision-instruct --api-base http://localhost:30000/v1\n"
               "  Ollama:  python server.py --model llava:7b --api-base http://localhost:11434/v1\n"
               "  HTTPS:   python server.py --model llava:7b --api-base http://localhost:11434/v1 --ssl-cert cert.pem --ssl-key key.pem",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to (default: 8080)")
    parser.add_argument("--model", required=True, help="VLM model name (e.g., llama-3.2-11b-vision-instruct)")
    parser.add_argument("--api-base", default="http://localhost:8000/v1",
                        help="VLM API base URL - OpenAI-compatible (default: http://localhost:8000/v1)")
    parser.add_argument("--api-key", default="EMPTY",
                        help="API key - use 'EMPTY' for local servers (default: EMPTY)")
    parser.add_argument("--prompt", default="Describe what you see in this image in one sentence.",
                        help="Prompt to send to VLM (default: 'Describe what you see...')")
    parser.add_argument("--process-every", type=int, default=30, help="Process every Nth frame")
    parser.add_argument("--ssl-cert", help="Path to SSL certificate file (enables HTTPS)")
    parser.add_argument("--ssl-key", help="Path to SSL private key file (enables HTTPS)")

    args = parser.parse_args()

    # Initialize VLM service
    global vlm_service
    vlm_service = VLMService(
        model=args.model,
        api_base=args.api_base,
        api_key=args.api_key,
        prompt=args.prompt
    )
    logger.info(f"Initialized VLM service:")
    logger.info(f"  Model: {args.model}")
    logger.info(f"  API Base: {args.api_base}")
    logger.info(f"  Prompt: {args.prompt}")

    # Update frame processing rate in VideoProcessorTrack if needed
    # (This is a bit hacky but works for this demo)
    VideoProcessorTrack.process_every_n_frames = args.process_every

    # Create web application
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_post("/offer", offer)
    app.on_shutdown.append(on_shutdown)

    # Setup SSL if certificates provided
    ssl_context = None
    protocol = "http"
    if args.ssl_cert and args.ssl_key:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(args.ssl_cert, args.ssl_key)
        protocol = "https"
        logger.info("SSL enabled - using HTTPS")
    else:
        logger.warning("⚠️  SSL not enabled - webcam access requires HTTPS!")
        logger.warning("⚠️  Generate certificates with: ./generate_cert.sh")
        logger.warning("⚠️  Then restart with: --ssl-cert cert.pem --ssl-key key.pem")

    # Run server
    logger.info(f"Starting server on {args.host}:{args.port}")
    logger.info(f"Open {protocol}://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port} in your browser")

    web.run_app(app, host=args.host, port=args.port, ssl_context=ssl_context)


if __name__ == "__main__":
    main()

