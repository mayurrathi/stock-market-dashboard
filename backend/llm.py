"""
LLM Service - Integration with Google Generative AI (Gemini)
Updated to use new google-genai package
"""
import asyncio
from google import genai
from google.genai import types
import logging
import os
from typing import Optional

from .database import SessionLocal
from .models import Config

logger = logging.getLogger(__name__)

# Default model name - can be overridden via DB config
DEFAULT_MODEL = 'gemini-3.0-flash'

class LLMService:
    def __init__(self):
        self.api_key = None
        self.client = None
        self.model_name = DEFAULT_MODEL
        self.initialized = False
        
    async def _check_ai_enabled(self):
        """Check if AI features are globally enabled"""
        db = SessionLocal()
        try:
            config = db.query(Config).filter(Config.key == "ai_features_enabled").first()
            if config and config.value == "false":
                return False
            return True
        finally:
            db.close()

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
                
                # Initialize client with new google-genai package
                self.client = genai.Client(api_key=self.api_key)
                
                # Get configurable model name
                model_config = db.query(Config).filter(Config.key == "gemini_model").first()
                if model_config and model_config.value:
                    self.model_name = model_config.value
                
                self.initialized = True
                logger.info(f"LLM Service initialized with {self.model_name}")
            else:
                logger.debug("No Gemini API key found in configuration")
        except Exception as e:
            logger.error(f"Failed to initialize LLM service: {e}")
        finally:
            db.close()

    async def generate_reasoning(self, symbol: str, signal_type: str, context: str) -> Optional[str]:
        """Generate reasoning for a stock recommendation"""
        if not await self._check_ai_enabled():
            return None
            
        self._initialize()
        
        if not self.client:
            return None

        try:
            prompt = f"""
            As a financial analyst, provide a concise 1-sentence reasoning for a {signal_type} signal on {symbol}.
            Context: {context}
            
            CRITICAL: Tailor your reasoning strictly to the specified Timeframe in the context.
            - For 'next_day', focus on momentum, technical breakouts, or news catalysts.
            - For 'next_week', focus on weekly trends and key levels.
            - For 'next_month', focus on moving averages and sector performance.
            
            Keep it professional, specific to the data, and under 25 words. Do NOT use generic phrases like "Based on signals".
            """
            
            # Use new async generate_content API
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt
            )
            
            return response.text.strip() if response.text else None
        except Exception as e:
            logger.error(f"LLM generation failed for {symbol}: {e}")
            return None

    async def summarize_news(self, text: str) -> Optional[str]:
        """Summarize news text"""
        if not await self._check_ai_enabled():
            return None
            
        self._initialize()
        
        if not self.client:
            return None

        try:
            prompt = f"Summarize this financial news in 1 concise sentence: {text[:1000]}"
            
            # Use new async generate_content API
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt
            )
            
            return response.text.strip() if response.text else None
        except Exception as e:
            logger.error(f"LLM summarization failed: {e}")
            return None

    def is_available(self) -> bool:
        """Check if LLM service is configured and available"""
        # Note: synchronous check, mainly for static config availability
        self._initialize()
        return self.client is not None

    async def extract_stocks_from_message(self, text: str) -> list:
        """Use AI to extract stock symbols from a Telegram message"""
        if not await self._check_ai_enabled():
            return []
            
        self._initialize()
        
        if not self.client:
            return []

        try:
            prompt = f"""
            Analyze this Indian stock market message and extract any stock symbols mentioned.
            Return ONLY a JSON array of NSE/BSE stock symbols in uppercase (e.g., ["RELIANCE", "TCS", "INFY"]).
            If no stocks are mentioned, return empty array [].
            
            Message: {text[:2000]}
            
            JSON array only:
            """
            
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt
            )
            
            import json
            result = response.text.strip()
            # Clean up response - handle markdown code blocks
            if result.startswith("```"):
                result = result.split("```")[1].strip()
                if result.startswith("json"):
                    result = result[4:].strip()
            return json.loads(result) if result.startswith("[") else []
        except Exception as e:
            logger.error(f"Stock extraction failed: {e}")
            return []

    async def chat(self, message: str) -> str:
        """Handle general chat with the AI assistant"""
        if not await self._check_ai_enabled():
            return "AI features are currently disabled. Please enable them in Settings."
            
        self._initialize()
        
        if not self.client:
            return "Please configure the Gemini API key in Settings first."

        try:
            # Context-aware prompt but without restrictions
            prompt = f"""
            You are an intelligent AI assistant for the Indian Stock Market Dashboard.
            You have access to real-time market data, technical analysis, and news.
            
            User's Message: {message}
            
            Be helpful, detailed, and professional. 
            If the user asks for analysis, provide a comprehensive answer.
            """
            
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt
            )
            
            return response.text.strip() if response.text else "Sorry, I couldn't generate a response."
        except Exception as e:
            logger.error(f"Chat generation failed: {e}")
            return f"Error: {str(e)}"

    async def synthesize_recommendation(
        self, 
        symbol: str, 
        message_text: str,
        fundamentals: dict,
        recommendation_data: dict,
        technical_analysis: dict = None,
        news_context: str = ""
    ) -> dict:
        """
        AI synthesizes a final recommendation
        """
        if not await self._check_ai_enabled():
            return None
            
        self._initialize()
        
        if not self.client:
            return None

        try:
            # Build comprehensive context
            fundamentals_str = ", ".join([f"{k}: {v}" for k, v in fundamentals.items() if v]) if fundamentals else "N/A"
            existing_rec = recommendation_data.get("action", "HOLD") if recommendation_data else "N/A"
            confidence = recommendation_data.get("confidence", 50) if recommendation_data else 50
            
            # Format technical analysis
            tech_str = "N/A"
            if technical_analysis:
                patterns = ", ".join(technical_analysis.get("patterns", [])) or "None"
                tech_str = f"""
                RSI: {technical_analysis.get('rsi', 'N/A')}
                MACD: {technical_analysis.get('macd', 'N/A')}
                Trend: {technical_analysis.get('trend', 'N/A')}
                Support: {technical_analysis.get('support', 'N/A')}
                Resistance: {technical_analysis.get('resistance', 'N/A')}
                Patterns Detected: {patterns}
                """
            
            prompt = f"""
            As a senior Indian stock market analyst, provide a recommendation for {symbol}.
            
            SOURCE MESSAGE: {message_text[:500]}
            
            FUNDAMENTALS: {fundamentals_str}
            
            TECHNICAL ANALYSIS: {tech_str}
            
            EXISTING ENGINE RECOMMENDATION: {existing_rec} (Confidence: {confidence}%)
            
            RECENT NEWS: {news_context[:500] if news_context else 'No recent news'}
            
            Provide your analysis in this exact JSON format:
            {{
                "action": "BUY" or "SELL" or "HOLD",
                "confidence": 0-100,
                "summary": "One sentence recommendation",
                "bull_case": "Why buy",
                "bear_case": "Why sell",
                "key_levels": {{"support": price, "resistance": price}} or null
            }}
            
            JSON only:
            """
            
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt
            )
            
            import json
            result = response.text.strip()
            # Clean up markdown code blocks
            if result.startswith("```"):
                result = result.split("```")[1].strip()
                if result.startswith("json"):
                    result = result[4:].strip()
            
            parsed = json.loads(result)
            parsed["symbol"] = symbol
            parsed["is_ai_generated"] = True
            return parsed
        except Exception as e:
            logger.error(f"Recommendation synthesis failed for {symbol}: {e}")
            return None

# Global instance
llm_service = LLMService()
