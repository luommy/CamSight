"""
RTSP Video Track for IP Camera Support

This module provides VideoStreamTrack implementation for RTSP streams,
allowing live-vlm-webui to process IP camera feeds instead of just webcams.

SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
SPDX-License-Identifier: Apache-2.0
"""

import av
import asyncio
import logging
import re
import threading
from typing import Optional
from aiortc import VideoStreamTrack
from av import VideoFrame

# Suppress verbose ffmpeg/libav logging (HEVC decoder errors are normal for IP cameras)
# These POC/slice errors happen due to network packet loss but stream recovers automatically
av.logging.set_level(av.logging.FATAL)  # Only show fatal errors that stop the stream

logger = logging.getLogger(__name__)


class RTSPVideoTrack(VideoStreamTrack):
    """
    Video track that reads from RTSP stream and converts to aiortc VideoFrame.

    This enables processing of IP camera feeds through the same pipeline as webcam input.
    Supports automatic reconnection on stream failure.

    Example:
        track = RTSPVideoTrack("rtsp://192.168.1.100:554/stream")
        frame = await track.recv()
    """

    def __init__(
        self,
        rtsp_url: str,
        reconnect_attempts: int = 5,
        reconnect_delay: float = 2.0,
        options: Optional[dict] = None,
    ):
        """
        Initialize RTSP video track.

        Args:
            rtsp_url: Full RTSP URL (e.g., rtsp://user:pass@192.168.1.100:554/stream)
            reconnect_attempts: Number of reconnection attempts on failure (default: 5)
            reconnect_delay: Base delay between reconnection attempts in seconds (default: 2.0)
            options: Additional PyAV container options (default: TCP transport)
        """
        super().__init__()
        self.rtsp_url = rtsp_url
        self.reconnect_attempts = reconnect_attempts
        self.reconnect_delay = reconnect_delay
        self.container: Optional[av.container.InputContainer] = None
        self.stream: Optional[av.video.VideoStream] = None
        self._stopped = False
        self._frame_count = 0

        # Thread lock to protect container access between executor thread and stop()
        self._container_lock = threading.Lock()

        # Default options for RTSP
        self.options = options or {
            "rtsp_transport": "tcp",  # TCP is more reliable than UDP for most networks
            "max_delay": "500000",  # 500ms max delay for low latency
            "rtsp_flags": "prefer_tcp",
        }

        # Connect to stream
        self._connect()

    def _sanitize_url(self, url: str) -> str:
        """
        Remove password from URL for safe logging.

        Args:
            url: RTSP URL potentially containing credentials

        Returns:
            URL with password replaced by ****
        """
        return re.sub(r"://([^:]+):([^@]+)@", r"://\1:****@", url)

    def _connect(self):
        """
        Connect to RTSP stream.

        Raises:
            Exception: If connection fails after all attempts
        """
        safe_url = self._sanitize_url(self.rtsp_url)

        try:
            logger.info(f"Connecting to RTSP stream: {safe_url}")

            # Open RTSP stream
            self.container = av.open(self.rtsp_url, options=self.options)

            # Get video stream
            if not self.container.streams.video:
                raise ValueError("No video stream found in RTSP source")

            self.stream = self.container.streams.video[0]

            # Log stream information
            codec = self.stream.codec_context.name
            width = self.stream.width or "unknown"
            height = self.stream.height or "unknown"
            fps = self.stream.average_rate or "unknown"

            logger.info(f"RTSP connected successfully: {codec} {width}x{height} @{fps}fps")

        except Exception as e:
            logger.error(f"Failed to connect to RTSP stream {safe_url}: {e}")
            raise

    async def recv(self) -> VideoFrame:
        """
        Receive next frame from RTSP stream.

        This is called by aiortc framework to get video frames.
        Runs demuxing/decoding in executor to avoid blocking event loop.

        Returns:
            VideoFrame: Next decoded video frame

        Raises:
            StopAsyncIteration: When stream ends or is stopped
        """
        if self._stopped:
            raise StopAsyncIteration

        try:
            # Read frame from container (blocking operation, run in executor)
            loop = asyncio.get_event_loop()
            frame = await loop.run_in_executor(None, self._read_frame)

            if frame is None:
                if not self._stopped:
                    logger.warning("RTSP stream ended unexpectedly, attempting reconnection")
                    await self._reconnect()
                    # Try again after reconnection
                    frame = await loop.run_in_executor(None, self._read_frame)
                    if frame is None:
                        raise StopAsyncIteration
                else:
                    raise StopAsyncIteration

            self._frame_count += 1

            # Log progress periodically
            if self._frame_count % 300 == 0:  # Every ~10 seconds at 30fps
                logger.debug(f"RTSP: Received {self._frame_count} frames")

            return frame

        except StopAsyncIteration:
            raise
        except Exception as e:
            logger.error(f"Error receiving RTSP frame: {e}", exc_info=True)
            # Try to reconnect on error
            if not self._stopped:
                await self._reconnect()
            raise

    def _read_frame(self) -> Optional[VideoFrame]:
        """
        Read and decode next frame from RTSP stream (blocking).

        This is a blocking operation and should be run in an executor.
        Uses container_lock to prevent race conditions with stop().

        Returns:
            VideoFrame or None if stream ended, stopped, or error occurred
        """
        # Fast path: check stopped before acquiring lock
        if self._stopped:
            return None

        # Acquire lock to safely read from container
        # This prevents stop() from closing the container while we're reading
        with self._container_lock:
            if self._stopped or not self.container or not self.stream:
                return None

            try:
                # Demux and decode packets until we get a video frame
                for packet in self.container.demux(self.stream):
                    # Check stopped inside loop for fast exit
                    if self._stopped:
                        return None
                    for frame in packet.decode():
                        if isinstance(frame, VideoFrame):
                            return frame

                # No more frames available (stream ended)
                logger.info("RTSP stream reached end of file")
                return None

            except av.error.EOFError:
                logger.warning("RTSP stream EOF")
                return None
            except Exception as e:
                if not self._stopped:  # Only log if not intentionally stopped
                    logger.error(f"Error decoding RTSP frame: {e}")
                return None

    async def _reconnect(self):
        """
        Attempt to reconnect to RTSP stream with exponential backoff.

        Tries multiple times with increasing delay between attempts.
        """
        safe_url = self._sanitize_url(self.rtsp_url)
        logger.info(f"Attempting RTSP reconnection to {safe_url}...")

        # Clean up existing connection
        if self.container:
            try:
                self.container.close()
            except Exception as e:
                logger.debug(f"Error closing container during reconnect: {e}")
            self.container = None
            self.stream = None

        # Try to reconnect with exponential backoff
        for attempt in range(self.reconnect_attempts):
            try:
                logger.info(f"Reconnection attempt {attempt + 1}/{self.reconnect_attempts}")

                # Wait with exponential backoff (2, 4, 8, 16, 32 seconds)
                if attempt > 0:
                    delay = self.reconnect_delay * (2 ** (attempt - 1))
                    logger.info(f"Waiting {delay}s before reconnection attempt...")
                    await asyncio.sleep(delay)

                # Attempt connection
                self._connect()
                logger.info(f"RTSP reconnected successfully on attempt {attempt + 1}")
                return

            except Exception as e:
                logger.warning(f"Reconnection attempt {attempt + 1} failed: {e}")
                if attempt == self.reconnect_attempts - 1:
                    logger.error(
                        f"RTSP reconnection failed after {self.reconnect_attempts} attempts"
                    )
                    raise

    def stop(self):
        """
        Stop the RTSP stream and clean up resources.

        Should be called when stream is no longer needed.
        """
        logger.debug(f"Stopping RTSP track, _stopped={self._stopped}")

        # Set stopped flag first to break recv() loop and _read_frame fast path
        self._stopped = True

        # Acquire lock to wait for any in-progress _read_frame to complete,
        # then safely close the container
        with self._container_lock:
            if self.container:
                try:
                    logger.debug("Closing RTSP container...")
                    self.container.close()
                    logger.info(f"RTSP stream closed: {self._frame_count} frames received")
                except Exception as e:
                    logger.warning(f"Error closing RTSP container: {e}", exc_info=True)
                finally:
                    # Always clear references even if close() failed
                    self.container = None
                    self.stream = None
                    logger.debug("RTSP container references cleared")

        # Call parent stop
        try:
            super().stop()
        except Exception as e:
            logger.warning(f"Error in parent VideoStreamTrack.stop(): {e}")

    @property
    def is_connected(self) -> bool:
        """Check if RTSP stream is currently connected."""
        return self.container is not None and not self._stopped

    def get_stats(self) -> dict:
        """
        Get statistics about the RTSP stream.

        Returns:
            Dictionary with stream statistics
        """
        stats = {
            "url": self._sanitize_url(self.rtsp_url),
            "connected": self.is_connected,
            "frames_received": self._frame_count,
            "stopped": self._stopped,
        }

        if self.stream:
            stats.update(
                {
                    "codec": self.stream.codec_context.name,
                    "width": self.stream.width,
                    "height": self.stream.height,
                    "fps": float(self.stream.average_rate) if self.stream.average_rate else None,
                }
            )

        return stats
