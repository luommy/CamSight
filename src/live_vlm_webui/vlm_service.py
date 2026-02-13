# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
VLM Service
Handles async image analysis using any OpenAI-compatible VLM API
(Works with vLLM, SGLang, Ollama, OpenAI, etc.)
"""

import asyncio
import base64
import io
import time
from openai import AsyncOpenAI
from PIL import Image
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class VLMService:
    """Service for analyzing images using VLM via OpenAI-compatible API"""

    def __init__(
        self,
        model: str,
        api_base: str = "http://localhost:8000/v1",
        api_key: str = "EMPTY",
        prompt: str = "Describe what you see in this image in one sentence.",
        max_tokens: int = 512,
        enable_context: bool = True,
        max_history: int = 4,
    ):
        """
        Initialize VLM service

        Args:
            model: Model name (e.g., "llama-3.2-11b-vision-instruct" for vLLM)
            api_base: Base URL for the API (e.g., "http://localhost:8000/v1" for vLLM)
            api_key: API key (use "EMPTY" for local servers)
            prompt: Default prompt to use for image analysis
            max_tokens: Maximum tokens to generate
            enable_context: Enable contextual analysis with frame history (default: True)
            max_history: Maximum number of previous responses to keep (default: 4)
        """
        self.model = model
        self.api_base = api_base
        self.api_key = api_key if api_key else "EMPTY"
        self.prompt = prompt
        self.max_tokens = max_tokens
        self.client = AsyncOpenAI(base_url=api_base, api_key=api_key)
        self.current_response = "Initializing..."
        self.is_processing = False
        self._processing_lock = asyncio.Lock()

        # Context tracking for video understanding
        self.enable_context = enable_context
        self.max_history = max_history
        self.response_history = []  # Store previous frame analyses
        self._history_lock = asyncio.Lock()  # Protect history access

        # Metrics tracking
        self.last_inference_time = 0.0  # seconds
        self.total_inferences = 0
        self.total_inference_time = 0.0

        if self.enable_context:
            logger.info(
                f"Context-aware mode enabled: keeping {self.max_history} frame history"
            )

    async def _build_contextual_prompt(self, base_prompt: str) -> str:
        """
        Build a context-aware prompt by including previous frame analyses.

        This helps small VLMs understand temporal relationships in video streams.
        Thread-safe with async lock protection.

        Args:
            base_prompt: The base prompt template

        Returns:
            Enhanced prompt with historical context if available
        """
        # If context is disabled or no history yet, return base prompt
        if not self.enable_context or not self.response_history:
            return base_prompt

        # Build context section from history (thread-safe)
        async with self._history_lock:
            # Get recent history (reversed so most recent is first)
            recent_history = list(reversed(self.response_history[-self.max_history:]))

        if not recent_history:
            return base_prompt

        # Build context text
        context_lines = []
        for i, response in enumerate(recent_history, 1):
            # Truncate long responses to keep prompt manageable
            truncated = response[:150] + "..." if len(response) > 150 else response
            context_lines.append(f"  {i} frame(s) ago: {truncated}")

        context_text = "\n".join(context_lines)

        # Construct enhanced prompt
        contextual_prompt = f"""{base_prompt}

[Previous Frame Context]
{context_text}

[Current Frame Analysis]
Based on the above context, analyze the current frame and describe any changes or continuation of actions."""

        return contextual_prompt

    async def analyze_image(self, image: Image.Image, prompt: Optional[str] = None) -> str:
        """
        Analyze an image using the VLM model

        Args:
            image: PIL Image to analyze
            prompt: Prompt for the VLM (uses default if None)

        Returns:
            Generated response string
        """
        if prompt is None:
            prompt = self.prompt

        # Build context-aware prompt if enabled
        contextual_prompt = await self._build_contextual_prompt(prompt)

        try:
            start_time = time.perf_counter()

            # Convert PIL Image to base64
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format="JPEG")
            img_byte_arr = img_byte_arr.getvalue()
            img_base64 = base64.b64encode(img_byte_arr).decode("utf-8")

            # Create message with image
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": contextual_prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"},
                        },
                    ],
                }
            ]

            # Call API
            response = await self.client.chat.completions.create(
                model=self.model, messages=messages, max_tokens=self.max_tokens, temperature=0.7
            )

            # Calculate latency
            end_time = time.perf_counter()
            inference_time = end_time - start_time

            # Update metrics
            self.last_inference_time = inference_time
            self.total_inferences += 1
            self.total_inference_time += inference_time

            result = response.choices[0].message.content.strip()

            # Save to history if context is enabled (thread-safe)
            if self.enable_context and result and not result.startswith("Error"):
                async with self._history_lock:
                    self.response_history.append(result)
                    # Keep only the most recent N responses to avoid memory growth
                    if len(self.response_history) > self.max_history * 2:
                        self.response_history = self.response_history[-self.max_history:]

            logger.info(f"VLM response: {result} (latency: {inference_time*1000:.0f}ms)")
            return result

        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            return f"Error: {str(e)}"

    async def process_frame(self, image: Image.Image, prompt: Optional[str] = None) -> None:
        """
        Process a frame asynchronously. Updates self.current_response when done.
        If already processing, this call is skipped.

        Args:
            image: PIL Image to process
            prompt: Optional custom prompt (uses default if None)
        """
        # Non-blocking check if we're already processing
        if self._processing_lock.locked():
            logger.debug("VLM busy, skipping frame")
            return

        async with self._processing_lock:
            self.is_processing = True
            try:
                response = await self.analyze_image(image, prompt)
                self.current_response = response
            finally:
                self.is_processing = False

    def get_current_response(self) -> tuple[str, bool]:
        """
        Get the current response and processing status

        Returns:
            Tuple of (response, is_processing)
        """
        return self.current_response, self.is_processing

    def get_metrics(self) -> dict:
        """
        Get current performance metrics

        Returns:
            Dict with latency and throughput metrics
        """
        avg_latency = (
            self.total_inference_time / self.total_inferences if self.total_inferences > 0 else 0.0
        )

        return {
            "last_latency_ms": self.last_inference_time * 1000,
            "avg_latency_ms": avg_latency * 1000,
            "total_inferences": self.total_inferences,
            "is_processing": self.is_processing,
        }

    def update_prompt(self, new_prompt: str, max_tokens: Optional[int] = None) -> None:
        """
        Update the default prompt and optionally max_tokens

        Args:
            new_prompt: New prompt to use
            max_tokens: Maximum tokens to generate (optional)
        """
        self.prompt = new_prompt
        if max_tokens is not None:
            self.max_tokens = max_tokens
            logger.info(f"Updated prompt to: {new_prompt}, max_tokens: {max_tokens}")
        else:
            logger.info(f"Updated prompt to: {new_prompt}")

    async def clear_history(self) -> None:
        """
        Clear the response history (useful when switching scenes or restarting analysis).
        Thread-safe operation.
        """
        async with self._history_lock:
            count = len(self.response_history)
            self.response_history.clear()
            if count > 0:
                logger.info(f"Cleared {count} frames from history")

    async def get_history_summary(self) -> dict:
        """
        Get a summary of the current history state.
        Thread-safe operation.

        Returns:
            Dictionary with history statistics
        """
        async with self._history_lock:
            return {
                "enabled": self.enable_context,
                "max_history": self.max_history,
                "current_count": len(self.response_history),
                "history": list(self.response_history[-self.max_history:]) if self.response_history else []
            }

    def set_context_mode(self, enable: bool) -> None:
        """
        Enable or disable context-aware analysis.

        Args:
            enable: True to enable context tracking, False to disable
        """
        old_state = self.enable_context
        self.enable_context = enable
        logger.info(f"Context mode: {old_state} -> {enable}")

        if not enable and self.response_history:
            logger.info("Context disabled, but history is preserved (use clear_history() to remove)")

    def update_api_settings(
        self, api_base: Optional[str] = None, api_key: Optional[str] = None
    ) -> None:
        """
        Update API base URL and/or API key, recreating the client

        Args:
            api_base: New API base URL (optional)
            api_key: New API key (optional, use empty string for local services)
        """
        if api_base:
            self.api_base = api_base
        if api_key is not None:  # Allow empty string
            self.api_key = api_key if api_key else "EMPTY"

        # Recreate the client with new settings
        self.client = AsyncOpenAI(base_url=self.api_base, api_key=self.api_key)

        masked_key = (
            "***" + self.api_key[-4:]
            if self.api_key and len(self.api_key) > 4 and self.api_key != "EMPTY"
            else "EMPTY"
        )
        logger.info(f"Updated API settings - base: {self.api_base}, key: {masked_key}")
