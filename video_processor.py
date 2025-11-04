"""
Video Track Processor
Handles video frames, adds text overlays, and manages VLM processing
"""
import asyncio
import cv2
import numpy as np
from PIL import Image
from av import VideoFrame
from aiortc import VideoStreamTrack
from typing import Optional
import logging

from vlm_service import VLMService

logger = logging.getLogger(__name__)


class VideoProcessorTrack(VideoStreamTrack):
    """
    Video track that receives frames, sends them to VLM for analysis,
    and overlays responses on the video before sending back
    """

    def __init__(self, track: VideoStreamTrack, vlm_service: VLMService, text_callback=None):
        super().__init__()
        self.track = track
        self.vlm_service = vlm_service
        self.text_callback = text_callback  # Callback to send text updates
        self.last_frame: Optional[np.ndarray] = None
        self.frame_count = 0
        self.process_every_n_frames = 30  # Process every N frames to avoid overloading VLM

    async def recv(self):
        """
        Receive frame from input track, process it, and return with text overlay
        """
        try:
            # Get frame from incoming track
            frame = await self.track.recv()

            # Convert to numpy array
            img = frame.to_ndarray(format="bgr24")
            self.last_frame = img.copy()

            # Increment frame counter
            self.frame_count += 1

            # Log first frame
            if self.frame_count == 1:
                logger.info(f"First frame received: {img.shape}")

            # Send frame to VLM for analysis (async, non-blocking)
            # Only process every Nth frame to avoid overwhelming the VLM
            if self.frame_count % self.process_every_n_frames == 0:
                # Convert to PIL Image for VLM
                pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
                # Fire and forget - don't wait for result
                asyncio.create_task(self.vlm_service.process_frame(pil_img))
                logger.debug(f"Sent frame {self.frame_count} to VLM")

            # Get current response (may be old if VLM is still processing)
            response, is_processing = self.vlm_service.get_current_response()

            # Get metrics
            metrics = self.vlm_service.get_metrics()

            # Send text update via callback (for WebSocket)
            if self.text_callback:
                self.text_callback(response, metrics)

            # Return clean video frame (no overlay)
            new_frame = VideoFrame.from_ndarray(img, format="bgr24")
            new_frame.pts = frame.pts
            new_frame.time_base = frame.time_base

            return new_frame

        except Exception as e:
            logger.error(f"Error processing frame: {e}", exc_info=True)
            raise

    def _add_text_overlay(self, img: np.ndarray, text: str, status: str = "") -> np.ndarray:
        """
        Add text overlay to image

        Args:
            img: Input image (BGR format)
            text: Text to overlay (VLM response)
            status: Optional status text

        Returns:
            Image with text overlay
        """
        img_copy = img.copy()
        height, width = img_copy.shape[:2]

        # Prepare text
        full_text = f"{text} {status}" if status else text

        # Text wrapping - split long captions
        max_chars_per_line = 60
        words = full_text.split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            if current_length + len(word) + 1 <= max_chars_per_line:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_length = len(word)

        if current_line:
            lines.append(' '.join(current_line))

        # Text properties
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        font_thickness = 2
        text_color = (255, 255, 255)  # White
        bg_color = (0, 0, 0)  # Black background
        padding = 10
        line_height = 30

        # Calculate total height needed
        total_text_height = len(lines) * line_height + 2 * padding

        # Create semi-transparent overlay at bottom
        overlay = img_copy.copy()
        cv2.rectangle(
            overlay,
            (0, height - total_text_height),
            (width, height),
            bg_color,
            -1
        )

        # Blend overlay with original image
        alpha = 0.7
        cv2.addWeighted(overlay, alpha, img_copy, 1 - alpha, 0, img_copy)

        # Add text lines
        y_position = height - total_text_height + padding + line_height
        for line in lines:
            cv2.putText(
                img_copy,
                line,
                (padding, y_position),
                font,
                font_scale,
                text_color,
                font_thickness,
                cv2.LINE_AA
            )
            y_position += line_height

        return img_copy

