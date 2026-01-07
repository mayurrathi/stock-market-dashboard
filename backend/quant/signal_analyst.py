import re
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_
from ..models import TelegramMessage, Stock, MarketNews
from .search_engine import search_duckduckgo

logger = logging.getLogger(__name__)

class SignalAnalyst:
    def __init__(self, db: Session):
        self.db = db
        self.valid_symbols = self._load_valid_symbols()

    def _load_valid_symbols(self):
        """Cache all valid stock symbols from DB for fast lookup"""
        stocks = self.db.query(Stock.symbol).filter(Stock.is_active == True).all()
        return {s[0] for s in stocks}

    async def process_new_signals(self, limit: int = 50):
        """
        Process raw Telegram messages: extract stocks, verify with news, assign signal.
        """
        # Fetch unprocessed messages
        messages = self.db.query(TelegramMessage).filter(
            or_(TelegramMessage.processed == False, TelegramMessage.processed == None),
            TelegramMessage.extracted_stocks == None
        ).order_by(TelegramMessage.message_date.desc()).limit(limit).all()

        if not messages:
            return 0

        logger.info(f"Processing {len(messages)} new signals...")
        processed_count = 0

        for msg in messages:
            try:
                # 1. Extract Stocks
                symbols = self._extract_symbols(msg.text)
                
                # 2. Analyze & Verify
                if symbols:
                    sentiment, action = self._analyze_sentiment(msg.text)
                    
                    # Verify with news for the primary stock (limit API calls)
                    # We only check news if we have a strong signal to validate
                    # For now, we mainly extract stocks. News verification adds latency.
                    # We will attach news context if available in DB or quick search.
                    
                    msg.extracted_stocks = symbols
                    msg.sentiment = sentiment
                    # logic to map sentiment to DB fields?
                    # The message table has 'sentiment' column.
                    
                    processed_count += 1
                
                # Mark as processed regardless of finding stocks to avoid infinite loops
                msg.processed = True
                
            except Exception as e:
                logger.error(f"Error processing message {msg.id}: {e}")
                continue

        try:
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to commit signals: {e}")
            self.db.rollback()

        return processed_count

    def _extract_symbols(self, text: str):
        """Find NSE symbols in text"""
        if not text:
            return []
            
        # Regex for potential symbols (all caps, 3-10 chars)
        potential = set(re.findall(r'\b[A-Z]{3,10}\b', text))
        
        # Filter against valid symbols
        found = [s for s in potential if s in self.valid_symbols]
        
        # Also check for "-EQ" suffix common in some feeds
        # Or "NIFTY", "BANKNIFTY"
        
        return list(set(found))

    def _analyze_sentiment(self, text: str):
        """
        Simple rule-based sentiment analysis.
        Returns (sentiment, action)
        """
        text = text.lower()
        
        bullish_terms = ['buy', 'long', 'bull', 'breakout', 'target', 'support', 'entry', 'accumulate']
        bearish_terms = ['sell', 'short', 'bear', 'breakdown', 'resistance', 'sl', 'stoploss', 'exit']
        
        bull_score = sum(1 for t in bullish_terms if t in text)
        bear_score = sum(1 for t in bearish_terms if t in text)
        
        if bull_score > bear_score:
            if bull_score >= 3:
                return 'very_bullish', 'STRONG BUY'
            return 'bullish', 'BUY'
        elif bear_score > bull_score:
            if bear_score >= 3:
                return 'very_bearish', 'STRONG SELL'
            return 'bearish', 'SELL'
            
        return 'neutral', 'HOLD'

    async def verify_signal_with_news(self, symbol: str) -> str:
        """
        Search for recent news to validate/invalidate the signal.
        Returns a summary string.
        """
        query = f"{symbol} share news latest"
        results = await search_duckduckgo(query, limit=3)
        
        if not results:
            return None
            
        return results[0]['title']  # Just return top headline for now
