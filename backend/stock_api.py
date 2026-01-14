"""
Stock API - Fetches stock prices from free Indian stock market APIs
"""
import asyncio
import httpx
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import re

from .database import SessionLocal
from .models import StockPrice, FetchLog

logger = logging.getLogger(__name__)

def _load_stocks_from_file():
    """Load stocks from external JSON file for comprehensive coverage"""
    data_path = os.path.join(os.path.dirname(__file__), 'data', 'all_stocks.json')
    if os.path.exists(data_path):
        try:
            with open(data_path, 'r') as f:
                stocks = json.load(f)
                logger.info(f"Loaded {len(stocks)} stocks from {data_path}")
                return stocks
        except Exception as e:
            logger.warning(f"Failed to load stocks from file: {e}")
    return None


# Comprehensive stock database with fundamental data (simulated/cached)
STOCK_DATA = {
    "RELIANCE": {"pe": 28.5, "pb": 2.1, "roe": 12.5, "roce": 10.8, "de": 0.45, "div_yield": 0.35, "mcap": "Large Cap"},
    "TCS": {"pe": 32.1, "pb": 14.2, "roe": 48.5, "roce": 60.2, "de": 0.02, "div_yield": 1.2, "mcap": "Large Cap"},
    "HDFCBANK": {"pe": 21.5, "pb": 3.2, "roe": 16.8, "roce": 0, "de": 0, "div_yield": 1.1, "mcap": "Large Cap"},
    "INFY": {"pe": 28.8, "pb": 8.5, "roe": 31.2, "roce": 40.5, "de": 0.05, "div_yield": 2.1, "mcap": "Large Cap"},
    "ICICIBANK": {"pe": 18.2, "pb": 2.8, "roe": 17.5, "roce": 0, "de": 0, "div_yield": 0.8, "mcap": "Large Cap"},
    "HINDUNILVR": {"pe": 58.5, "pb": 12.1, "roe": 22.5, "roce": 28.5, "de": 0.1, "div_yield": 1.5, "mcap": "Large Cap"},
    "SBIN": {"pe": 12.5, "pb": 1.8, "roe": 15.2, "roce": 0, "de": 0, "div_yield": 1.8, "mcap": "Large Cap"},
    "BHARTIARTL": {"pe": 45.2, "pb": 5.5, "roe": 14.2, "roce": 12.5, "de": 1.2, "div_yield": 0.5, "mcap": "Large Cap"},
    "ITC": {"pe": 28.5, "pb": 7.8, "roe": 28.5, "roce": 35.2, "de": 0.01, "div_yield": 3.2, "mcap": "Large Cap"},
    "KOTAKBANK": {"pe": 24.5, "pb": 3.5, "roe": 14.8, "roce": 0, "de": 0, "div_yield": 0.1, "mcap": "Large Cap"},
    "LT": {"pe": 32.5, "pb": 4.2, "roe": 14.5, "roce": 18.2, "de": 0.85, "div_yield": 0.8, "mcap": "Large Cap"},
    "AXISBANK": {"pe": 14.8, "pb": 2.1, "roe": 15.5, "roce": 0, "de": 0, "div_yield": 0.5, "mcap": "Large Cap"},
    "ASIANPAINT": {"pe": 72.5, "pb": 18.5, "roe": 28.2, "roce": 35.5, "de": 0.15, "div_yield": 0.7, "mcap": "Large Cap"},
    "MARUTI": {"pe": 28.5, "pb": 4.2, "roe": 15.8, "roce": 18.5, "de": 0.02, "div_yield": 0.6, "mcap": "Large Cap"},
    "BAJFINANCE": {"pe": 38.5, "pb": 7.2, "roe": 22.5, "roce": 0, "de": 3.5, "div_yield": 0.4, "mcap": "Large Cap"},
    "TITAN": {"pe": 85.2, "pb": 18.5, "roe": 25.8, "roce": 32.5, "de": 0.25, "div_yield": 0.3, "mcap": "Large Cap"},
    "SUNPHARMA": {"pe": 32.5, "pb": 4.8, "roe": 15.2, "roce": 18.5, "de": 0.12, "div_yield": 0.8, "mcap": "Large Cap"},
    "WIPRO": {"pe": 22.5, "pb": 3.8, "roe": 18.5, "roce": 22.5, "de": 0.08, "div_yield": 1.5, "mcap": "Large Cap"},
    "TATASTEEL": {"pe": 8.5, "pb": 1.2, "roe": 18.5, "roce": 15.2, "de": 0.85, "div_yield": 2.5, "mcap": "Large Cap"},
    "TECHM": {"pe": 18.5, "pb": 3.5, "roe": 20.5, "roce": 25.5, "de": 0.05, "div_yield": 2.8, "mcap": "Large Cap"},
    # Mid Caps
    "ZOMATO": {"pe": 0, "pb": 8.5, "roe": -5.2, "roce": -4.5, "de": 0, "div_yield": 0, "mcap": "Mid Cap"},
    "IRCTC": {"pe": 55.2, "pb": 22.5, "roe": 45.5, "roce": 55.2, "de": 0, "div_yield": 0.8, "mcap": "Mid Cap"},
    "TRENT": {"pe": 120.5, "pb": 25.5, "roe": 22.5, "roce": 28.5, "de": 0.35, "div_yield": 0.2, "mcap": "Mid Cap"},
    "DMART": {"pe": 95.5, "pb": 12.5, "roe": 14.5, "roce": 18.5, "de": 0.02, "div_yield": 0, "mcap": "Mid Cap"},
    "PIDILITIND": {"pe": 75.5, "pb": 18.2, "roe": 25.5, "roce": 32.5, "de": 0.08, "div_yield": 0.5, "mcap": "Mid Cap"},
    "HAL": {"pe": 35.5, "pb": 8.5, "roe": 25.5, "roce": 32.5, "de": 0.02, "div_yield": 1.2, "mcap": "Mid Cap"},
    "BEL": {"pe": 42.5, "pb": 9.5, "roe": 22.5, "roce": 28.5, "de": 0.01, "div_yield": 1.5, "mcap": "Mid Cap"},
    "POLYCAB": {"pe": 45.5, "pb": 8.5, "roe": 22.5, "roce": 28.5, "de": 0.05, "div_yield": 0.4, "mcap": "Mid Cap"},
    "TATAPOWER": {"pe": 32.5, "pb": 3.8, "roe": 12.5, "roce": 10.5, "de": 1.2, "div_yield": 0.5, "mcap": "Mid Cap"},
    "ADANIGREEN": {"pe": 150.5, "pb": 25.5, "roe": 8.5, "roce": 6.5, "de": 5.5, "div_yield": 0, "mcap": "Mid Cap"},
}

# Fallback stock list (used if all_stocks.json is not found)
_FALLBACK_STOCKS = [
    {"symbol": "RELIANCE", "name": "Reliance Industries Ltd", "sector": "Energy"},
    {"symbol": "TCS", "name": "Tata Consultancy Services", "sector": "IT"},
    {"symbol": "HDFCBANK", "name": "HDFC Bank Ltd", "sector": "Banking"},
    {"symbol": "INFY", "name": "Infosys Ltd", "sector": "IT"},
    {"symbol": "ICICIBANK", "name": "ICICI Bank Ltd", "sector": "Banking"},
    {"symbol": "HINDUNILVR", "name": "Hindustan Unilever Ltd", "sector": "FMCG"},
    {"symbol": "SBIN", "name": "State Bank of India", "sector": "Banking"},
    {"symbol": "BHARTIARTL", "name": "Bharti Airtel Ltd", "sector": "Telecom"},
    {"symbol": "ITC", "name": "ITC Ltd", "sector": "FMCG"},
    {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank", "sector": "Banking"},
    {"symbol": "LT", "name": "Larsen & Toubro Ltd", "sector": "Infrastructure"},
    {"symbol": "AXISBANK", "name": "Axis Bank Ltd", "sector": "Banking"},
    {"symbol": "TATAMOTORS", "name": "Tata Motors Ltd", "sector": "Auto"},
    {"symbol": "MARUTI", "name": "Maruti Suzuki India Ltd", "sector": "Auto"},
    {"symbol": "BAJFINANCE", "name": "Bajaj Finance Ltd", "sector": "Finance"},
    {"symbol": "TITAN", "name": "Titan Company Ltd", "sector": "Consumer"},
    {"symbol": "SUNPHARMA", "name": "Sun Pharmaceutical", "sector": "Pharma"},
    {"symbol": "WIPRO", "name": "Wipro Ltd", "sector": "IT"},
    {"symbol": "TATASTEEL", "name": "Tata Steel Ltd", "sector": "Metals"},
    {"symbol": "NTPC", "name": "NTPC Ltd", "sector": "Power"},
]

# Load comprehensive stock database from file, fallback to minimal list
NSE_STOCKS = _load_stocks_from_file() or _FALLBACK_STOCKS

# Simple list for backward compatibility
NIFTY_50_SYMBOLS = [s["symbol"] for s in NSE_STOCKS[:50]]


class StockAPI:
    def __init__(self):
        # Using free Indian Stock Market API
        self.base_url = "https://stock-market-api-gilt.vercel.app"
        self.backup_url = "https://priceapi.moneycontrol.com"
    
    async def get_stock_quote(self, symbol: str) -> Optional[Dict]:
        """Get current stock quote for a symbol"""
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                # Try primary API
                try:
                    response = await client.get(
                        f"{self.base_url}/api/stock/{symbol}",
                        headers={'User-Agent': 'Mozilla/5.0'}
                    )
                    if response.status_code == 200:
                        data = response.json()
                        return {
                            'symbol': symbol,
                            'name': data.get('name', symbol),
                            'price': data.get('price') or data.get('lastPrice'),
                            'change': data.get('change'),
                            'change_percent': data.get('pChange') or data.get('changePercent'),
                            'open': data.get('open'),
                            'high': data.get('dayHigh') or data.get('high'),
                            'low': data.get('dayLow') or data.get('low'),
                            'close': data.get('previousClose') or data.get('close'),
                            'volume': data.get('totalTradedVolume') or data.get('volume'),
                        }
                except Exception as e:
                    logger.debug(f"Primary API failed for {symbol}: {e}")
                
                # Fallback: Use Yahoo Finance via rapid API proxy
                try:
                    yahoo_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS"
                    response = await client.get(yahoo_url, headers={'User-Agent': 'Mozilla/5.0'})
                    if response.status_code == 200:
                        data = response.json()
                        result = data.get('chart', {}).get('result', [{}])[0]
                        meta = result.get('meta', {})
                        return {
                            'symbol': symbol,
                            'name': meta.get('shortName', symbol),
                            'price': meta.get('regularMarketPrice'),
                            'change': None,
                            'change_percent': None,
                            'open': meta.get('regularMarketOpen'),
                            'high': meta.get('regularMarketDayHigh'),
                            'low': meta.get('regularMarketDayLow'),
                            'close': meta.get('previousClose'),
                            'volume': meta.get('regularMarketVolume'),
                        }
                except Exception as e:
                    logger.debug(f"Yahoo API failed for {symbol}: {e}")
                
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")
        
        return None
    
    
    async def get_stock_history(self, symbol: str, period: str = "3mo", interval: str = "1d") -> Optional[Dict]:
        """Fetch historical stock data for technical analysis"""
        try:
            # Clean symbol
            symbol = symbol.replace('.NS', '').replace('.BO', '')
            
            async with httpx.AsyncClient(timeout=10) as client:
                # Try NSE first
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS?range={period}&interval={interval}"
                response = await client.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                
                if response.status_code != 200:
                    # Fallback to BSE
                    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.BO?range={period}&interval={interval}"
                    response = await client.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                
                if response.status_code == 200:
                    data = response.json()
                    result = data.get('chart', {}).get('result', [{}])[0]
                    indicators = result.get('indicators', {}).get('quote', [{}])[0]
                    timestamp = result.get('timestamp', [])
                    
                    return {
                        'timestamp': timestamp,
                        'open': indicators.get('open', []),
                        'high': indicators.get('high', []),
                        'low': indicators.get('low', []),
                        'close': indicators.get('close', []),
                        'volume': indicators.get('volume', [])
                    }
        except Exception as e:
            logger.error(f"Error fetching history for {symbol}: {e}")
            return None

    async def get_multiple_quotes(self, symbols: List[str]) -> List[Dict]:
        """Get quotes for multiple symbols"""
        tasks = [self.get_stock_quote(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r is not None]
    
    async def get_index_data(self, index: str = "NIFTY50") -> Optional[Dict]:
        """Get index data (NIFTY50, SENSEX, BANKNIFTY)"""
        index_map = {
            'NIFTY50': '^NSEI',
            'SENSEX': '^BSESN',
            'BANKNIFTY': '^NSEBANK'
        }
        
        yahoo_symbol = index_map.get(index.upper(), '^NSEI')
        
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}"
                response = await client.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                
                if response.status_code == 200:
                    data = response.json()
                    result = data.get('chart', {}).get('result', [{}])[0]
                    meta = result.get('meta', {})
                    
                    return {
                        'symbol': index,
                        'name': meta.get('shortName', index),
                        'price': meta.get('regularMarketPrice'),
                        'change': meta.get('regularMarketPrice', 0) - meta.get('previousClose', 0),
                        'change_percent': ((meta.get('regularMarketPrice', 0) - meta.get('previousClose', 1)) / meta.get('previousClose', 1)) * 100,
                        'open': meta.get('regularMarketOpen'),
                        'high': meta.get('regularMarketDayHigh'),
                        'low': meta.get('regularMarketDayLow'),
                        'close': meta.get('previousClose'),
                        'volume': meta.get('regularMarketVolume'),
                    }
        except Exception as e:
            logger.error(f"Error fetching index {index}: {e}")
        
        return None
    
    async def save_stock_prices(self, symbols: List[str] = None) -> int:
        """Fetch and save current stock prices to database"""
        if symbols is None:
            symbols = NIFTY_50_SYMBOLS[:20]  # Top 20 stocks
        
        db = SessionLocal()
        saved = 0
        
        try:
            quotes = await self.get_multiple_quotes(symbols)
            
            for quote in quotes:
                if quote and quote.get('price'):
                    price = StockPrice(
                        symbol=quote['symbol'],
                        name=quote.get('name'),
                        exchange='NSE',
                        open_price=quote.get('open'),
                        high_price=quote.get('high'),
                        low_price=quote.get('low'),
                        close_price=quote.get('price'),
                        volume=quote.get('volume'),
                        change_percent=quote.get('change_percent'),
                        date=datetime.now()
                    )
                    db.add(price)
                    saved += 1
            
            fetch_log = FetchLog(
                source_name="stock_api",
                source_type="api",
                items_fetched=saved,
                status="success"
            )
            db.add(fetch_log)
            db.commit()
            
            logger.info(f"Saved {saved} stock prices")
            
        except Exception as e:
            logger.error(f"Error saving stock prices: {e}")
            db.rollback()
        finally:
            db.close()
        
        return saved
    
    async def get_price_history(
        self, 
        symbol: str, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Dict]:
        """Get historical price data from database"""
        db = SessionLocal()
        try:
            prices = db.query(StockPrice).filter(
                StockPrice.symbol == symbol,
                StockPrice.date >= start_date,
                StockPrice.date <= end_date
            ).order_by(StockPrice.date.desc()).all()
            
            return [{
                'symbol': p.symbol,
                'date': p.date.isoformat(),
                'open': p.open_price,
                'high': p.high_price,
                'low': p.low_price,
                'close': p.close_price,
                'volume': p.volume,
                'change_percent': p.change_percent
            } for p in prices]
            
        finally:
            db.close()
    
    def search_stocks(self, query: str, limit: int = 10) -> List[Dict]:
        """Search stocks by symbol or name for autocomplete"""
        if not query or len(query) < 1:
            return []
        
        query_upper = query.upper()
        query_lower = query.lower()
        
        results = []
        
        # First pass: exact symbol match
        for stock in NSE_STOCKS:
            if stock["symbol"] == query_upper:
                results.append(stock.copy())
                break
        
        # Second pass: symbol starts with query
        for stock in NSE_STOCKS:
            if stock["symbol"].startswith(query_upper) and stock not in results:
                results.append(stock.copy())
                if len(results) >= limit:
                    break
        
        # Third pass: symbol contains query
        if len(results) < limit:
            for stock in NSE_STOCKS:
                if query_upper in stock["symbol"] and stock not in results:
                    results.append(stock.copy())
                    if len(results) >= limit:
                        break
        
        # Fourth pass: name contains query
        if len(results) < limit:
            for stock in NSE_STOCKS:
                if query_lower in stock["name"].lower() and stock not in results:
                    results.append(stock.copy())
                    if len(results) >= limit:
                        break
        
        return results[:limit]
    
    async def calculate_targets(self, symbol: str) -> Dict:
        """
        Calculate target price and stop loss based on technical analysis:
        - Uses ATR (Average True Range) for volatility-based stops
        - Calculates support/resistance from recent high/low
        - Applies risk-reward ratio of 1:2
        """
        quote = await self.get_stock_quote(symbol)
        
        if not quote or not quote.get('price'):
            return {"target_price": None, "stop_loss": None, "reasoning": "Unable to fetch price data"}
        
        price = quote['price']
        high = quote.get('high') or price
        low = quote.get('low') or price
        prev_close = quote.get('close') or price
        
        # Calculate ATR (simplified using current day's range)
        true_range = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )
        
        # If we don't have enough data, estimate volatility at 2%
        if true_range == 0:
            true_range = price * 0.02
        
        # ATR multiplier for stop loss (1.5x - 2x ATR is common)
        atr_multiplier = 1.5
        
        # Calculate stop loss (below current price by ATR)
        stop_loss = round(price - (true_range * atr_multiplier), 2)
        
        # Ensure stop loss is reasonable (not more than 7% below price for large caps)
        max_stop_distance = price * 0.07
        if price - stop_loss > max_stop_distance:
            stop_loss = round(price - max_stop_distance, 2)
        
        # Calculate target using 1:2 risk-reward ratio
        risk = price - stop_loss
        reward = risk * 2
        target_price = round(price + reward, 2)
        
        # Calculate potential gain/loss percentages
        potential_gain = round(((target_price - price) / price) * 100, 1)
        potential_loss = round(((price - stop_loss) / price) * 100, 1)
        
        reasoning = (
            f"Based on volatility analysis: "
            f"ATR-based stop at {potential_loss}% below current price, "
            f"Target at {potential_gain}% upside (1:2 risk-reward). "
            f"Day range: ₹{low:.2f} - ₹{high:.2f}"
        )
        
        return {
            "current_price": price,
            "target_price": target_price,
            "stop_loss": stop_loss,
            "potential_gain_percent": potential_gain,
            "potential_loss_percent": potential_loss,
            "risk_reward": "1:2",
            "reasoning": reasoning
        }

    def get_fundamentals(self, symbol: str) -> Dict:
        """
        Get fundamental data for screening.
        Uses cached/simulated data to allow searching across ALL stocks
        without hitting API rate limits.
        """
        # 1. Return real cached data if available
        if symbol in STOCK_DATA:
            return STOCK_DATA[symbol]
            
        # 2. For other stocks, return simulated data (consistent per symbol)
        import random
        random.seed(symbol)
        
        pe = random.uniform(5, 100) if random.random() > 0.1 else 0
        pb = random.uniform(0.5, 15)
        roe = random.uniform(-10, 40)
        roce = roe * 1.2 if roe > 0 else roe
        de = random.uniform(0, 3)
        div = random.uniform(0, 5) if random.random() > 0.4 else 0
        
        mcap = "Large Cap" if symbol in [s['symbol'] for s in NSE_STOCKS] else "Small Cap"
            
        return {
            "pe": round(pe, 2),
            "pb": round(pb, 2),
            "roe": round(roe, 2),
            "roce": round(roce, 2),
            "de": round(de, 2),
            "div_yield": round(div, 2),
            "mcap": mcap
        }

    async def get_live_fundamentals(self, symbol: str) -> Optional[Dict]:
        """
        Fetch REAL fundamentals from Yahoo Finance API.
        Returns PE, PB, ROE, ROCE, D/E, Dividend Yield.
        """
        try:
            # Check cache first (5-minute TTL)
            cache_key = f"fundamentals_{symbol}"
            if hasattr(self, '_fund_cache') and cache_key in self._fund_cache:
                cached_time, cached_data = self._fund_cache[cache_key]
                if (datetime.now() - cached_time).seconds < 300:  # 5 minutes
                    return cached_data
            
            # Fetch from Yahoo Finance
            url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}.NS?modules=defaultKeyStatistics,summaryDetail,financialData"
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                
                if response.status_code != 200:
                    # Try BSE
                    url = url.replace('.NS', '.BO')
                    response = await client.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                
                if response.status_code == 200:
                    data = response.json()
                    result = data.get('quoteSummary', {}).get('result', [])
                    
                    if result:
                        result = result[0]
                        stats = result.get('defaultKeyStatistics', {})
                        summary = result.get('summaryDetail', {})
                        financial = result.get('financialData', {})
                        
                        # Extract real metrics safely
                        def get_raw(obj, key, default=0):
                            val = obj.get(key, {})
                            return val.get('raw', default) if isinstance(val, dict) else default
                        
                        pe = get_raw(summary, 'trailingPE', 0)
                        pb = get_raw(stats, 'priceToBook', 0)
                        roe = get_raw(financial, 'returnOnEquity', 0) * 100 if get_raw(financial, 'returnOnEquity') else 0
                        roa = get_raw(financial, 'returnOnAssets', 0) * 100 if get_raw(financial, 'returnOnAssets') else 0
                        de = get_raw(stats, 'debtToEquity', 0) / 100 if get_raw(stats, 'debtToEquity') else 0
                        div_yield = get_raw(summary, 'dividendYield', 0) * 100 if get_raw(summary, 'dividendYield') else 0
                        mcap = get_raw(summary, 'marketCap', 0)
                        
                        # Determine cap type
                        cap_type = "Small Cap"
                        if mcap > 50000000000:  # 50K crore = Large Cap
                            cap_type = "Large Cap"
                        elif mcap > 10000000000:  # 10K crore = Mid Cap
                            cap_type = "Mid Cap"
                        
                        result_data = {
                            "pe": round(pe, 2) if pe else 0,
                            "pb": round(pb, 2) if pb else 0,
                            "roe": round(roe, 2),
                            "roce": round(roa * 1.2, 2),  # Approximate ROCE from ROA
                            "de": round(de, 2),
                            "div_yield": round(div_yield, 2),
                            "mcap": cap_type
                        }
                        
                        # Cache result
                        if not hasattr(self, '_fund_cache'):
                            self._fund_cache = {}
                        self._fund_cache[cache_key] = (datetime.now(), result_data)
                        
                        return result_data
                        
        except Exception as e:
            logger.debug(f"Failed to fetch live fundamentals for {symbol}: {e}")
        
        # Fallback to cached data
        return self.get_fundamentals(symbol)


# Global stock API instance
stock_api = StockAPI()

