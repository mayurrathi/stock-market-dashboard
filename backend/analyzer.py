"""
Analyzer - Correlates Telegram signals with market data and generates recommendations
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging
import re
import random
from collections import Counter

from .database import SessionLocal
from .models import TelegramMessage, MarketNews, StockPrice, Analysis, Recommendation
from .llm import llm_service

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

logger = logging.getLogger(__name__)

# Comprehensive stock list - Large Caps, Mid Caps, Small Caps, Penny Stocks
LARGE_CAP_STOCKS = [
    'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK', 'HINDUNILVR', 'SBIN',
    'BHARTIARTL', 'ITC', 'KOTAKBANK', 'LT', 'AXISBANK', 'ASIANPAINT', 'MARUTI',
    'BAJFINANCE', 'TITAN', 'SUNPHARMA', 'NESTLEIND', 'WIPRO', 'ULTRACEMCO',
    'HCLTECH', 'BAJAJFINSV', 'POWERGRID', 'NTPC', 'TATASTEEL', 'TECHM',
    'ONGC', 'ADANIENT', 'COALINDIA', 'JSWSTEEL', 'TATAMOTORS', 'INDUSINDBK',
    'HINDALCO', 'DRREDDY', 'APOLLOHOSP', 'EICHERMOT', 'GRASIM', 'BRITANNIA',
    'CIPLA', 'DIVISLAB', 'SBILIFE', 'ADANIPORTS', 'TATACONSUM', 'BPCL'
]

MID_CAP_STOCKS = [
    'ZOMATO', 'PAYTM', 'NYKAA', 'POLICYBZR', 'DELHIVERY', 'IRCTC', 'TRENT',
    'DMART', 'PIDILITIND', 'SIEMENS', 'HAVELLS', 'ABB', 'GODREJCP', 'MARICO',
    'DABUR', 'COLPAL', 'BERGEPAINT', 'ICICIPRULI', 'BANKBARODA', 'PNB',
    'CANBK', 'IDFCFIRSTB', 'FEDERALBNK', 'BANDHANBNK', 'JUBLFOOD', 'PAGEIND',
    'MUTHOOTFIN', 'CHOLAFIN', 'SHRIRAMFIN', 'VEDL', 'NMDC', 'SAIL',
    'JINDALSTEL', 'ADANIGREEN', 'ADANIPOWER', 'TATAPOWER', 'TORNTPOWER',
    'RECLTD', 'PFC', 'IOC', 'GAIL', 'PETRONET', 'HAL', 'BEL', 'BHEL',
    'ESCORTS', 'BALKRISIND', 'MRF', 'ASHOKLEY', 'TATAELXSI', 'PERSISTENT',
    'COFORGE', 'MPHASIS', 'LICI', 'PATANJALI', 'POLYCAB', 'VOLTAS'
]

SMALL_CAP_STOCKS = [
    'RPOWER', 'SUZLON', 'IDEA', 'YESBANK', 'PNB', 'IDFCFIRSTB', 'BANDHANBNK',
    'GMRINFRA', 'NHPC', 'SJVN', 'HUDCO', 'IRFC', 'RVNL', 'IRCON', 'NBCC',
    'RAILTEL', 'RITES', 'COCHINSHIP', 'GRSE', 'MAZAGON', 'GARDEN',
    'AUROPHARMA', 'ALKEM', 'LUPIN', 'CADILAHC', 'BIOCON', 'GLENMARK',
    'GRANULES', 'LAURUS', 'NATCOPHARM', 'SYNGENE', 'IPCALAB', 'TORNTPHARM',
    'ZYDUSLIFE', 'AMARAJABAT', 'EXIDEIND', 'SCHAEFFLER', 'CUMMINSIND',
    'GRINDWELL', 'AARTIIND', 'DEEPAKNTR', 'NAVINFLUOR', 'PVRINOX', 'INDIGOPNTS'
]

PENNY_STOCKS = [
    'RPOWER', 'SUZLON', 'IDEA', 'DELTACORP', 'JAIPRAKASH', 'JPASSOCIAT',
    'GTLINFRA', 'RELINFRA', 'PEL', 'RCF', 'NFL', 'FACT', 'GSFC', 'GNFC',
    'MRPL', 'CESC', 'NHPC', 'SJVN', 'NCC', 'WABAG', 'HFCL', 'TANLA',
    'ROUTE', 'INDIACEM', 'JKCEMENT', 'RAMCOCEM', 'PRISMJOHN', 'SOBHA',
    'PRESTIGE', 'BRIGADE', 'OBEROIRLTY', 'GODREJPROP', 'DLF', 'PHOENIXLTD',
    'SUNTV', 'ZEEL', 'NETWORK18', 'TV18BRDCST', 'DISHTV', 'INDIGO', 'SPICEJET'
]

ALL_STOCKS = list(set(LARGE_CAP_STOCKS + MID_CAP_STOCKS + SMALL_CAP_STOCKS + PENNY_STOCKS))

# Build regex pattern dynamically
STOCK_PATTERNS = [
    r'\b(' + '|'.join(ALL_STOCKS[:50]) + r')\b',
    r'\b(' + '|'.join(ALL_STOCKS[50:100]) + r')\b',
    r'\b(' + '|'.join(ALL_STOCKS[100:]) + r')\b',
    r'\b(NIFTY|SENSEX|BANKNIFTY|NIFTY50)\b',
]

# Action keywords
BUY_KEYWORDS = [
    'buy', 'long', 'bullish', 'accumulate', 'add', 'target', 'upside',
    'breakout', 'support', 'bounce', 'reversal up', 'bottom', 'entry',
    'multibagger', 'rocket', 'gem', 'undervalued', 'strong', 'outperform'
]
SELL_KEYWORDS = [
    'sell', 'short', 'bearish', 'book profit', 'exit', 'downside',
    'breakdown', 'resistance', 'crash', 'fall', 'correction', 'stop loss',
    'avoid', 'overvalued', 'weak', 'underperform', 'dump'
]
HOLD_KEYWORDS = [
    'hold', 'wait', 'consolidation', 'sideways', 'range bound', 'neutral'
]


class StockAnalyzer:
    def __init__(self):
        self.vader = SentimentIntensityAnalyzer()
    
    def extract_stocks(self, text: str) -> List[str]:
        """Extract stock symbols from text"""
        stocks = set()
        text_upper = text.upper()
        
        for pattern in STOCK_PATTERNS:
            matches = re.findall(pattern, text_upper)
            stocks.update(matches)
        
        # Common company name mapping
        company_map = {
            'reliance': 'RELIANCE', 'tata steel': 'TATASTEEL', 'infosys': 'INFY',
            'tcs': 'TCS', 'wipro': 'WIPRO', 'hdfc bank': 'HDFCBANK',
            'icici bank': 'ICICIBANK', 'axis bank': 'AXISBANK', 'sbi': 'SBIN',
            'kotak': 'KOTAKBANK', 'bharti airtel': 'BHARTIARTL', 'airtel': 'BHARTIARTL',
            'adani': 'ADANIENT', 'maruti': 'MARUTI', 'bajaj': 'BAJFINANCE',
            'asian paints': 'ASIANPAINT', 'hul': 'HINDUNILVR', 'l&t': 'LT',
            'sun pharma': 'SUNPHARMA', 'tech mahindra': 'TECHM',
        }
        
        text_lower = text.lower()
        for company, symbol in company_map.items():
            if company in text_lower:
                stocks.add(symbol)
        
        return list(stocks)
    
    async def deep_analyze_messages(self, messages: List[TelegramMessage]) -> Dict:
        """Perform deep analysis on a collection of messages to identify trends and recommendations"""
        if not messages:
            return {}
            
        stock_counts = Counter()
        stock_sentiments = {}
        stock_context = {}  # Store snippets for reasoning
        
        for msg in messages:
            if not msg.text:
                continue
                
            stocks = self.extract_stocks(msg.text)
            sentiment, confidence = self.analyze_sentiment(msg.text)
            
            for stock in stocks:
                stock_counts[stock] += 1
                if stock not in stock_sentiments:
                    stock_sentiments[stock] = {'bullish': 0, 'bearish': 0, 'neutral': 0, 'total': 0}
                    stock_context[stock] = []
                
                stock_sentiments[stock][sentiment] += 1
                stock_sentiments[stock]['total'] += 1
                
                # Keep relevant snippet for reasoning (first 100 chars mention)
                if len(stock_context[stock]) < 3:
                    snippet = msg.text[:150] + "..." if len(msg.text) > 150 else msg.text
                    stock_context[stock].append(snippet)
        
        # Rank stocks by mention frequency and sentiment weighted score
        scored_stocks = []
        for stock, counts in stock_sentiments.items():
            # Basic score: Bullish - Bearish, weighted by total mentions
            score = (counts['bullish'] - counts['bearish']) * (1 + (counts['total'] / 10))
            scored_stocks.append({
                'symbol': stock,
                'score': score,
                'total_mentions': counts['total'],
                'sentiment': 'bullish' if counts['bullish'] > counts['bearish'] else 'bearish' if counts['bearish'] > counts['bullish'] else 'neutral',
                'context': stock_context[stock]
            })
            
        scored_stocks.sort(key=lambda x: abs(x['score']), reverse=True)
        
        return {
            'analyzed_count': len(messages),
            'top_stocks': scored_stocks[:20],
            'sentiments': stock_sentiments
        }

    def analyze_sentiment(self, text: str) -> Tuple[str, float]:
        """Analyze sentiment using VADER (Valence Aware Dictionary and sEntiment Reasoner)"""
        if not text:
            return 'neutral', 50.0
            
        try:
            # VADER analysis
            scores = self.vader.polarity_scores(text)
            compound = scores['compound']
            
            # Confidence based on intensity
            confidence = (abs(compound) * 50) + 50
            
            # Standard VADER thresholds
            if compound >= 0.05:
                return 'bullish', confidence
            elif compound <= -0.05:
                return 'bearish', confidence
            else:
                return 'neutral', 50.0
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return 'neutral', 50.0
    
    def extract_price_targets(self, text: str) -> Dict:
        """Extract price targets and stop losses from text"""
        targets = {}
        
        # Target patterns
        target_patterns = [
            r'target[:\s]+(?:rs\.?|₹)?\s*(\d+(?:,\d+)*(?:\.\d+)?)',
            r'tgt[:\s]+(?:rs\.?|₹)?\s*(\d+(?:,\d+)*(?:\.\d+)?)',
            r'tp[:\s]+(?:rs\.?|₹)?\s*(\d+(?:,\d+)*(?:\.\d+)?)',
        ]
        
        for pattern in target_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                targets['target'] = float(match.group(1).replace(',', ''))
                break
        
        # Stop loss patterns
        sl_patterns = [
            r'stop\s*loss[:\s]+(?:rs\.?|₹)?\s*(\d+(?:,\d+)*(?:\.\d+)?)',
            r'sl[:\s]+(?:rs\.?|₹)?\s*(\d+(?:,\d+)*(?:\.\d+)?)',
        ]
        
        for pattern in sl_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                targets['stop_loss'] = float(match.group(1).replace(',', ''))
                break
        
        return targets
    
    async def analyze_timeframe(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """Analyze messages and news within a time period"""
        db = SessionLocal()
        
        try:
            # Get Telegram messages in range
            messages = db.query(TelegramMessage).filter(
                TelegramMessage.created_at >= start_date,
                TelegramMessage.created_at <= end_date
            ).all()
            
            # Get news in range
            news = db.query(MarketNews).filter(
                MarketNews.published_at >= start_date,
                MarketNews.published_at <= end_date
            ).all()
            
            # Aggregate stock mentions
            stock_mentions = Counter()
            stock_sentiments = {}
            
            # Perform deep message analysis
            msg_analysis = await self.deep_analyze_messages(messages)
            
            # Combine news analysis for mentions
            for article in news:
                if article.extracted_stocks:
                    for stock in article.extracted_stocks:
                        sentiment = 'bullish' if article.sentiment == 'positive' else 'bearish' if article.sentiment == 'negative' else 'neutral'
                        
                        if stock not in stock_sentiments:
                            stock_sentiments[stock] = {'bullish': 0, 'bearish': 0, 'neutral': 0, 'total': 0}
                        
                        stock_sentiments[stock][sentiment] += 1
                        stock_sentiments[stock]['total'] += 1
            
            # Merge message analysis into final stock_sentiments
            if msg_analysis and 'sentiments' in msg_analysis:
                for stock, counts in msg_analysis['sentiments'].items():
                    if stock not in stock_sentiments:
                        stock_sentiments[stock] = {'bullish': 0, 'bearish': 0, 'neutral': 0, 'total': 0}
                    
                    for k in ['bullish', 'bearish', 'neutral', 'total']:
                        if k in counts:
                            stock_sentiments[stock][k] += counts[k]
            
            # Rank stocks by mention frequency and sentiment weighted score
            stock_mentions = Counter({s: counts['total'] for s, counts in stock_sentiments.items()})
            
            # Overall sentiment
            total_bullish = sum(s['bullish'] for s in stock_sentiments.values())
            total_bearish = sum(s['bearish'] for s in stock_sentiments.values())
            overall = 'bullish' if total_bullish > total_bearish else 'bearish' if total_bearish > total_bullish else 'neutral'
            
            # Create analysis record
            analysis = Analysis(
                start_date=start_date,
                end_date=end_date,
                messages_analyzed=len(messages),
                news_analyzed=len(news),
                stocks_mentioned=list(stock_mentions.keys()),
                overall_sentiment=overall,
                summary=f"Deep analysis of {len(messages)} messages and {len(news)} news articles. Top stocks: {', '.join(s for s, _ in stock_mentions.most_common(5))}"
            )
            db.add(analysis)
            db.commit()
            db.refresh(analysis)
            
            return {
                'analysis_id': analysis.id,
                'messages_analyzed': len(messages),
                'news_analyzed': len(news),
                'top_stocks': stock_mentions.most_common(20),
                'stock_sentiments': stock_sentiments,
                'overall_sentiment': overall,
                'is_deep': True
            }
            
        finally:
            db.close()
    
    def generate_recommendation(
        self,
        symbol: str,
        sentiment_data: Dict,
        timeframe: str
    ) -> Dict:
        """Generate a recommendation for a stock and timeframe"""
        bullish = sentiment_data.get('bullish', 0)
        bearish = sentiment_data.get('bearish', 0)
        neutral = sentiment_data.get('neutral', 0)
        total = bullish + bearish + neutral
        
        if total == 0:
            return None
        
        # Calculate confidence
        if bullish > bearish:
            action = 'BUY'
            confidence = (bullish / total) * 100
        elif bearish > bullish:
            action = 'SELL'
            confidence = (bearish / total) * 100
        else:
            action = 'HOLD'
            confidence = 50.0
        
        # Adjust confidence based on timeframe
        timeframe_adjustments = {
            'next_day': 0.9,  # Higher volatility, lower confidence
            'next_week': 0.95,
            'next_month': 1.0,
            '1yr': 0.85,
            '2yr': 0.75,
            '5yr': 0.65,
            '10yr': 0.55,
        }
        
        confidence *= timeframe_adjustments.get(timeframe, 1.0)
        
        # Generate timeframe-specific reasoning
        timeframe_insight = {
            'next_day': "Short-term momentum suggests",
            'next_week': "Weekly trend analysis indicates",
            'next_month': "Monthly outlook shows",
            '1yr': "Annual projections based on fundamentals suggest",
            '2yr': "Medium-term growth trajectory indicates",
            '5yr': "Long-term value creation potential shows",
            '10yr': "Ultra long-term compounding perspective suggests"
        }
        
        insight_prefix = timeframe_insight.get(timeframe, "Analysis indicates")
        
        reasoning_templates = {
            'BUY': f"{insight_prefix} potential upside. Detected {bullish} bullish signals out of {total} mentions in recent discussions.",
            'SELL': f"{insight_prefix} possible downside. Detected {bearish} bearish signals out of {total} mentions in recent discussions.",
            'HOLD': f"{insight_prefix} mixed sentiment. {bullish} bullish / {bearish} bearish signals. Market consensus is unclear."
        }
        
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'action': action,
            'confidence': round(confidence, 2),
            'reasoning': reasoning_templates[action]
        }
    
    async def generate_all_recommendations(
        self,
        analysis_result: Dict
    ) -> List[Dict]:
        """Generate diverse recommendations for all timeframes with randomization"""
        db = SessionLocal()
        recommendations = []
        
        timeframes = ['next_day', 'next_week', 'next_month']
        
        try:
            # Get stocks from analysis
            top_stocks = [s for s, _ in analysis_result.get('top_stocks', [])]
            stock_sentiments = analysis_result.get('stock_sentiments', {})
            analysis_id = analysis_result.get('analysis_id')
            
            # Only process stocks that actually have data
            all_stocks = top_stocks
            
            for symbol in all_stocks[:20]:  # Limit to top 20 real stocks
                if symbol not in stock_sentiments:
                    continue
                    
                sentiment_data = stock_sentiments[symbol]
                
                for timeframe in timeframes:
                    rec = self.generate_recommendation(symbol, sentiment_data, timeframe)
                    
                    if rec:
                        # ALWAYS use LLM for reasoning to avoid repetitive templates
                        # Fallback to template only on error
                        try:
                            context = f"Symbol: {symbol}. Timeframe: {timeframe}. Signals: {sentiment_data}. Market Cap: {self._get_stock_category(symbol)}."
                            llm_reasoning = await llm_service.generate_reasoning(
                                symbol=symbol,
                                signal_type=rec['action'],
                                context=context
                            )
                            if llm_reasoning:
                                rec['reasoning'] = llm_reasoning
                        except Exception as e:
                            logger.warning(f"LLM Reasoning failed for {symbol}: {e}")

                        # Add stock category label
                        rec['category'] = self._get_stock_category(symbol)
                        
                        # Save to database
                        db_rec = Recommendation(
                            analysis_id=analysis_id,
                            symbol=rec['symbol'],
                            timeframe=rec['timeframe'],
                            action=rec['action'],
                            confidence=rec['confidence'],
                            reasoning=rec['reasoning']
                        )
                        db.add(db_rec)
                        recommendations.append(rec)
            
            db.commit()
            logger.info(f"Generated {len(recommendations)} diverse recommendations")
            
        finally:
            db.close()
        
        return recommendations
    

    
    def _get_stock_category(self, symbol: str) -> str:
        """Get market cap category for a stock"""
        if symbol in LARGE_CAP_STOCKS:
            return 'Large Cap'
        elif symbol in MID_CAP_STOCKS:
            return 'Mid Cap'
        elif symbol in PENNY_STOCKS:
            return 'Penny Stock'
        elif symbol in SMALL_CAP_STOCKS:
            return 'Small Cap'
        else:
            return 'Unknown'
    

    async def get_recommendations_by_timeframe(
        self,
        timeframe: str
    ) -> List[Dict]:
        """Get latest recommendations for a specific timeframe"""
        db = SessionLocal()
        
        try:
            recs = db.query(Recommendation).filter(
                Recommendation.timeframe == timeframe
            ).order_by(Recommendation.created_at.desc()).limit(10).all()
            
            return [{
                'id': r.id,
                'symbol': r.symbol,
                'action': r.action,
                'confidence': r.confidence,
                'reasoning': r.reasoning,
                'created_at': r.created_at.isoformat()
            } for r in recs]
            
        finally:
            db.close()


# Global analyzer instance
analyzer = StockAnalyzer()
