"""
LLM Service - Integration with Generative AI (Google Gemini)
"""
import asyncio
import google.generativeai as genai
import logging
import os
from typing import Optional

from .database import SessionLocal
from .models import Config

logger = logging.getLogger(__name__)

# Default model name - can be overridden via DB config
DEFAULT_MODEL = 'gemini-pro'

class LLMService:
    def __init__(self):
        self.api_key = None
        self.model = None
        self.model_name = DEFAULT_MODEL
        self.initialized = False
        self._has_async = None  # Cache async capability check
        
    def _initialize(self):
        """Lazy initialization of LLM service"""
        if self.initialized:
            return

        db = SessionLocal()
        try:
            # Get API key
            config = db.query(Config).filter(Config.key == "gemini_api_key").first()
            if config and config.value:
                self.api_key = config.value
                genai.configure(api_key=self.api_key)
                
                # Get configurable model name
                model_config = db.query(Config).filter(Config.key == "gemini_model").first()
                if model_config and model_config.value:
                    self.model_name = model_config.value
                
                self.model = genai.GenerativeModel(self.model_name)
                self.initialized = True
                logger.info(f"LLM Service initialized with {self.model_name}")
            else:
                logger.debug("No Gemini API key found in configuration")
        except Exception as e:
            logger.error(f"Failed to initialize LLM service: {e}")
        finally:
            db.close()
    
    def _check_async_support(self) -> bool:
        """Check if the model supports async generation"""
        if self._has_async is None:
            self._has_async = hasattr(self.model, 'generate_content_async')
        return self._has_async

    async def generate_reasoning(self, symbol: str, signal_type: str, context: str) -> Optional[str]:
        """Generate reasoning for a stock recommendation"""
        self._initialize()
        
        if not self.model:
            return None

        try:
            prompt = f"""
            As a financial analyst, provide a concise 1-sentence reasoning for a {signal_type} signal on {symbol}.
            Context: {context}
            Keep it professional, data-backed if possible, and under 20 words.
            """
            
            # Try async first, fall back to sync if not available
            if self._check_async_support():
                response = await self.model.generate_content_async(prompt)
            else:
                # Run sync version in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, 
                    lambda: self.model.generate_content(prompt)
                )
            
            return response.text.strip()
        except Exception as e:
            logger.error(f"LLM generation failed for {symbol}: {e}")
            return None

    async def summarize_news(self, text: str) -> Optional[str]:
        """Summarize news text"""
        self._initialize()
        
        if not self.model:
            return None

        try:
            prompt = f"Summarize this financial news in 1 concise sentence: {text[:1000]}"
            
            # Try async first, fall back to sync if not available
            if self._check_async_support():
                response = await self.model.generate_content_async(prompt)
            else:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.model.generate_content(prompt)
                )
            
            return response.text.strip()
        except Exception as e:
            logger.error(f"LLM summarization failed: {e}")
            return None

# Global instance
llm_service = LLMService()

