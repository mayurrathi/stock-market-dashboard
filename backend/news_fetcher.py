"""
News Fetcher - Fetches market news from RSS feeds (Economic Times, Moneycontrol, NSE)
"""
import asyncio
import feedparser
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import re

from .database import SessionLocal
from .models import MarketNews, FetchLog, Config

logger = logging.getLogger(__name__)

# RSS Feed URLs for Indian Stock Market News
RSS_FEEDS = {
    "economic_times": {
        "name": "Economic Times Markets",
        "url": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    },
    "economic_times_stocks": {
        "name": "Economic Times Stocks",
        "url": "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",
    },
    "moneycontrol": {
        "name": "Moneycontrol",
        "url": "https://www.moneycontrol.com/rss/latestnews.xml",
    },
    "business_standard": {
        "name": "Business Standard Markets",
        "url": "https://www.business-standard.com/rss/markets.rss",
    },
    "livemint": {
        "name": "Livemint Markets",
        "url": "https://www.livemint.com/rss/markets",
    },
    "financial_express_markets": {
        "name": "Financial Express Markets",
        "url": "https://www.financialexpress.com/indian-markets/rss",
    },
    "financial_express_companies": {
        "name": "Financial Express Companies",
        "url": "https://www.financialexpress.com/companies/rss",
    },
}

# Common Indian stock symbols and keywords
STOCK_PATTERNS = [
    # Major indices
    r'\b(NIFTY|SENSEX|BANKNIFTY|NIFTY50)\b',
    # Common stock symbols (NSE format)
    r'\b([A-Z]{2,10})\b(?:\s+(?:shares?|stock|Ltd|Limited))',
    # Stock with price context
    r'\b([A-Z]{2,10})\s+(?:up|down|rises|falls|gains|drops)',
]


class NewsFetcher:
    def __init__(self):
        self.feeds = RSS_FEEDS.copy()
    
    def extract_stocks(self, text: str) -> List[str]:
        """Extract stock symbols mentioned in text"""
        stocks = set()
        
        # Common company name to symbol mapping
        company_mapping = {
            'reliance': 'RELIANCE', 'tata': 'TATASTEEL', 'infosys': 'INFY',
            'tcs': 'TCS', 'wipro': 'WIPRO', 'hdfc': 'HDFCBANK', 'icici': 'ICICIBANK',
            'axis': 'AXISBANK', 'sbi': 'SBIN', 'kotak': 'KOTAKBANK',
            'bharti': 'BHARTIARTL', 'airtel': 'BHARTIARTL', 'adani': 'ADANIENT',
            'maruti': 'MARUTI', 'bajaj': 'BAJFINANCE', 'itc': 'ITC',
            'asian paints': 'ASIANPAINT', 'hindustan unilever': 'HINDUNILVR',
            'hul': 'HINDUNILVR', 'l&t': 'LT', 'larsen': 'LT',
            'sun pharma': 'SUNPHARMA', 'tech mahindra': 'TECHM',
            'nifty': 'NIFTY50', 'sensex': 'SENSEX', 'banknifty': 'BANKNIFTY',
        }
        
        text_lower = text.lower()
        for company, symbol in company_mapping.items():
            if company in text_lower:
                stocks.add(symbol)
        
        # Pattern-based extraction
        for pattern in STOCK_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match) >= 2 and match.upper() not in ['THE', 'AND', 'FOR', 'WITH']:
                    stocks.add(match.upper())
        
        return list(stocks)
    
    def analyze_sentiment(self, text: str) -> str:
        """Analyze sentiment using VADER via StockAnalyzer for consistency across the app"""
        from .analyzer import analyzer
        
        sentiment, confidence = analyzer.analyze_sentiment(text)
        
        # Map analyzer output to news sentiment format
        sentiment_map = {
            'bullish': 'positive',
            'bearish': 'negative',
            'neutral': 'neutral'
        }
        return sentiment_map.get(sentiment, 'neutral')
    
    async def fetch_feed(self, feed_key: str) -> List[Dict]:
        """Fetch articles from a single RSS feed"""
        feed_info = self.feeds.get(feed_key)
        if not feed_info:
            return []
        
        articles = []
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(feed_info['url'], headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                
                if response.status_code == 200:
                    feed = feedparser.parse(response.text)
                    
                    for entry in feed.entries[:20]:  # Limit to 20 articles per feed
                        published = None
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            published = datetime(*entry.published_parsed[:6])
                        
                        title = entry.get('title', '')
                        summary = entry.get('summary', entry.get('description', ''))
                        
                        # Clean HTML from summary
                        summary = re.sub(r'<[^>]+>', '', summary)[:500]
                        
                        articles.append({
                            'source': feed_key,
                            'title': title,
                            'link': entry.get('link', ''),
                            'summary': summary,
                            'published_at': published,
                            'extracted_stocks': self.extract_stocks(f"{title} {summary}"),
                            'sentiment': self.analyze_sentiment(f"{title} {summary}")
                        })
                    
                    logger.info(f"Fetched {len(articles)} articles from {feed_info['name']}")
                else:
                    logger.warning(f"Failed to fetch {feed_key}: HTTP {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Error fetching feed {feed_key}: {e}")
        
        return articles
    
    async def fetch_all_feeds(self) -> int:
        """Fetch news from all configured RSS feeds"""
        db = SessionLocal()
        total_added = 0
        total_skipped = 0
        
        try:
            tasks = [self.fetch_feed(key) for key in self.feeds.keys()]
            results = await asyncio.gather(*tasks)
            
            for articles in results:
                for article in articles:
                    try:
                        # Check for duplicate first
                        existing = db.query(MarketNews).filter(
                            MarketNews.link == article['link']
                        ).first()
                        
                        if existing:
                            total_skipped += 1
                            continue
                        
                        news = MarketNews(
                            source=article['source'],
                            title=article['title'],
                            link=article['link'],
                            summary=article['summary'],
                            published_at=article['published_at'],
                            extracted_stocks=article['extracted_stocks'],
                            sentiment=article['sentiment']
                        )
                        db.add(news)
                        db.flush()  # Flush to catch any errors immediately
                        total_added += 1
                        
                    except Exception as article_error:
                        # Log but continue on individual article errors
                        logger.debug(f"Skipping duplicate article: {article.get('title', '')[:50]}")
                        db.rollback()
                        total_skipped += 1
            
            # Final commit for all successful additions
            db.commit()
            
            # Log the fetch
            fetch_log = FetchLog(
                source_name="rss_feeds",
                source_type="rss",
                items_fetched=total_added,
                status="success"
            )
            db.add(fetch_log)
            db.commit()
            
            logger.info(f"News fetch complete: {total_added} added, {total_skipped} skipped")
            
        except Exception as e:
            logger.error(f"Error in fetch_all_feeds: {e}")
            db.rollback()
            
            fetch_log = FetchLog(
                source_name="rss_feeds",
                source_type="rss",
                items_fetched=total_added,
                status="error",
                error_message=str(e)
            )
            db.add(fetch_log)
            db.commit()
        finally:
            db.close()
        
        return total_added

    
    async def get_news_by_daterange(
        self, 
        start_date: datetime, 
        end_date: datetime,
        stocks: Optional[List[str]] = None
    ) -> List[Dict]:
        """Get news articles within a date range, optionally filtered by stocks"""
        db = SessionLocal()
        try:
            query = db.query(MarketNews).filter(
                MarketNews.published_at >= start_date,
                MarketNews.published_at <= end_date
            )
            
            news_list = query.order_by(MarketNews.published_at.desc()).all()
            
            # Filter by stocks if specified
            if stocks:
                filtered = []
                for news in news_list:
                    if news.extracted_stocks:
                        if any(s in news.extracted_stocks for s in stocks):
                            filtered.append(news)
                news_list = filtered
            
            return [{
                'id': n.id,
                'source': n.source,
                'title': n.title,
                'link': n.link,
                'summary': n.summary,
                'published_at': n.published_at.isoformat() if n.published_at else None,
                'stocks': n.extracted_stocks,
                'sentiment': n.sentiment
            } for n in news_list]
            
        finally:
            db.close()


# Global fetcher instance
news_fetcher = NewsFetcher()
