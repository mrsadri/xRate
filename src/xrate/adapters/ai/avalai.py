# src/xrate/adapters/ai/avalai.py
"""
Avalai API Service - Market Analysis Generation

This module provides integration with the Avalai API to generate market analysis
based on price data and recent news in Iran.

Files that USE this module:
- xrate.adapters.telegram.jobs (uses AvalaiService to generate analysis after price posts)

Files that this module USES:
- xrate.config (settings for API key configuration)
"""
import logging
import asyncio
from typing import Optional
from openai import OpenAI

from xrate.config import settings

log = logging.getLogger(__name__)


class AvalaiService:
    """
    Avalai API service for generating market analysis based on price data.
    
    This service sends market price data to the Avalai API and receives
    a one-line analysis in Farsi that considers recent news in Iran.
    """

    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.avalai.ir/v1"):
        """
        Initialize Avalai API service.
        
        Args:
            api_key: Optional Avalai API key (defaults to settings.avalai_key)
            base_url: API base URL (defaults to Avalai API endpoint)
        """
        self.api_key = api_key or settings.avalai_key
        self.base_url = base_url
        
        if not self.api_key:
            log.warning("Avalai API key not configured - analysis feature will be disabled")
            self.client = None
        else:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
            log.info("Avalai API service initialized with base_url=%s, api_key_length=%d", 
                    self.base_url, len(self.api_key))

    async def generate_analysis(self, price_message: str) -> Optional[str]:
        """
        Generate market analysis based on price message.
        
        This method sends the price message to Avalai API with a prompt
        to generate a one-line analysis in Farsi considering recent news in Iran.
        
        Args:
            price_message: The formatted price message to analyze
            
        Returns:
            Generated analysis text in Farsi, or None if API call fails or is disabled
        """
        if not self.client:
            log.debug("Avalai API not configured, skipping analysis generation")
            return None

        prompt = f"""بر اساس این دیتا و با توجه به آخرین اخبار پیش آمده در ایران یک نظریه یک خطی بنویس:

{price_message}"""

        try:
            log.info("Requesting market analysis from Avalai API (base_url=%s, model=gpt-5)", self.base_url)
            log.debug("Price message length: %d characters", len(price_message))
            log.debug("Prompt length: %d characters", len(prompt))
            
            # Run synchronous OpenAI client call in executor to make it async-friendly
            loop = asyncio.get_event_loop()
            log.debug("Running Avalai API call in executor")
            completion = await loop.run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model="gpt-5",
                    messages=[
                        {
                            "role": "system",
                            "content": "شما یک تحلیلگر اقتصادی هستید که بر اساس داده‌های قیمت و اخبار اخیر ایران تحلیل می‌نویسید.",
                        },
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],
                ),
            )
            
            log.debug("Avalai API call completed, processing response")
            analysis = completion.choices[0].message.content
            if analysis:
                log.info("Successfully received analysis from Avalai API (length=%d chars): %s", 
                        len(analysis), analysis[:100] + "..." if len(analysis) > 100 else analysis)
                return analysis.strip()
            else:
                log.warning("Avalai API returned empty analysis (completion.choices[0].message.content is None or empty)")
                log.debug("Full completion object: %s", completion)
                return None
                
        except Exception as e:
            log.error("Failed to generate analysis from Avalai API: %s", e, exc_info=True)
            log.error("Exception type: %s, Exception args: %s", type(e).__name__, e.args)
            return None

    def test_api(self) -> tuple[bool, str]:
        """
        Test Avalai API by sending a simple health check message.
        
        This is a synchronous method for health checks.
        
        Returns:
            Tuple of (success: bool, response: str)
        """
        if not self.client:
            log.debug("Avalai API not configured, skipping API test")
            return (False, "API key not configured")
        
        test_message = "در یک کلمه بگو آیا همه چیز اوکیه؟"
        
        try:
            log.info("Testing Avalai API with health check message: '%s'", test_message)
            completion = self.client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {
                        "role": "system",
                        "content": "شما یک دستیار مفید هستید.",
                    },
                    {
                        "role": "user",
                        "content": test_message,
                    },
                ],
            )
            
            response = completion.choices[0].message.content
            if response:
                log.info("Avalai API health check successful. Response: %s", response)
                return (True, response.strip())
            else:
                log.warning("Avalai API health check returned empty response")
                return (False, "Empty response from API")
                
        except Exception as e:
            log.error("Avalai API health check failed: %s", e, exc_info=True)
            log.error("Exception type: %s, Exception args: %s", type(e).__name__, e.args)
            return (False, f"API error: {str(e)}")

