"""
VLM Service
Handles async image analysis using any OpenAI-compatible VLM API
(Works with vLLM, SGLang, Ollama, OpenAI, etc.)
"""
import asyncio
import base64
import io
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
        prompt: str = "Describe what you see in this image in one sentence."
    ):
        """
        Initialize VLM service
        
        Args:
            model: Model name (e.g., "llama-3.2-11b-vision-instruct" for vLLM)
            api_base: Base URL for the API (e.g., "http://localhost:8000/v1" for vLLM)
            api_key: API key (use "EMPTY" for local servers)
            prompt: Default prompt to use for image analysis
        """
        self.model = model
        self.api_base = api_base
        self.prompt = prompt
        self.client = AsyncOpenAI(
            base_url=api_base,
            api_key=api_key
        )
        self.current_response = "Initializing..."
        self.is_processing = False
        self._processing_lock = asyncio.Lock()
        
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
            
        try:
            # Convert PIL Image to base64
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG')
            img_byte_arr = img_byte_arr.getvalue()
            img_base64 = base64.b64encode(img_byte_arr).decode('utf-8')
            
            # Create message with image
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_base64}"
                            }
                        }
                    ]
                }
            ]
            
            # Call API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=512,
                temperature=0.7
            )
            
            result = response.choices[0].message.content.strip()
            logger.info(f"VLM response: {result}")
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
    
    def update_prompt(self, new_prompt: str) -> None:
        """
        Update the default prompt
        
        Args:
            new_prompt: New prompt to use
        """
        self.prompt = new_prompt
        logger.info(f"Updated prompt to: {new_prompt}")
