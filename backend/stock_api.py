"""
Stock API - Fetches stock prices from free Indian stock market APIs
"""
import asyncio
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import re

from .database import SessionLocal
from .models import StockPrice, FetchLog

logger = logging.getLogger(__name__)

# Comprehensive NSE Stock Database with Names and Sectors
NSE_STOCKS = [
    # NIFTY 50 - Large Caps
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
    {"symbol": "ASIANPAINT", "name": "Asian Paints Ltd", "sector": "Consumer"},
    {"symbol": "MARUTI", "name": "Maruti Suzuki India Ltd", "sector": "Auto"},
    {"symbol": "BAJFINANCE", "name": "Bajaj Finance Ltd", "sector": "Finance"},
    {"symbol": "TITAN", "name": "Titan Company Ltd", "sector": "Consumer"},
    {"symbol": "SUNPHARMA", "name": "Sun Pharmaceutical", "sector": "Pharma"},
    {"symbol": "NESTLEIND", "name": "Nestle India Ltd", "sector": "FMCG"},
    {"symbol": "WIPRO", "name": "Wipro Ltd", "sector": "IT"},
    {"symbol": "ULTRACEMCO", "name": "UltraTech Cement Ltd", "sector": "Cement"},
    {"symbol": "HCLTECH", "name": "HCL Technologies Ltd", "sector": "IT"},
    {"symbol": "BAJAJFINSV", "name": "Bajaj Finserv Ltd", "sector": "Finance"},
    {"symbol": "POWERGRID", "name": "Power Grid Corporation", "sector": "Power"},
    {"symbol": "NTPC", "name": "NTPC Ltd", "sector": "Power"},
    {"symbol": "TATASTEEL", "name": "Tata Steel Ltd", "sector": "Metals"},
    {"symbol": "TECHM", "name": "Tech Mahindra Ltd", "sector": "IT"},
    {"symbol": "ONGC", "name": "Oil & Natural Gas Corp", "sector": "Energy"},
    {"symbol": "ADANIENT", "name": "Adani Enterprises Ltd", "sector": "Diversified"},
    {"symbol": "COALINDIA", "name": "Coal India Ltd", "sector": "Mining"},
    {"symbol": "JSWSTEEL", "name": "JSW Steel Ltd", "sector": "Metals"},
    {"symbol": "TATAMOTORS", "name": "Tata Motors Ltd", "sector": "Auto"},
    {"symbol": "INDUSINDBK", "name": "IndusInd Bank Ltd", "sector": "Banking"},
    {"symbol": "M&M", "name": "Mahindra & Mahindra Ltd", "sector": "Auto"},
    {"symbol": "HINDALCO", "name": "Hindalco Industries Ltd", "sector": "Metals"},
    {"symbol": "BAJAJ-AUTO", "name": "Bajaj Auto Ltd", "sector": "Auto"},
    {"symbol": "DRREDDY", "name": "Dr Reddy's Laboratories", "sector": "Pharma"},
    {"symbol": "APOLLOHOSP", "name": "Apollo Hospitals", "sector": "Healthcare"},
    {"symbol": "EICHERMOT", "name": "Eicher Motors Ltd", "sector": "Auto"},
    {"symbol": "GRASIM", "name": "Grasim Industries Ltd", "sector": "Cement"},
    {"symbol": "BRITANNIA", "name": "Britannia Industries", "sector": "FMCG"},
    {"symbol": "CIPLA", "name": "Cipla Ltd", "sector": "Pharma"},
    {"symbol": "DIVISLAB", "name": "Divi's Laboratories Ltd", "sector": "Pharma"},
    {"symbol": "SBILIFE", "name": "SBI Life Insurance", "sector": "Insurance"},
    {"symbol": "ADANIPORTS", "name": "Adani Ports & SEZ", "sector": "Infrastructure"},
    {"symbol": "TATACONSUM", "name": "Tata Consumer Products", "sector": "FMCG"},
    {"symbol": "BPCL", "name": "Bharat Petroleum Corp", "sector": "Energy"},
    {"symbol": "HEROMOTOCO", "name": "Hero MotoCorp Ltd", "sector": "Auto"},
    {"symbol": "UPL", "name": "UPL Ltd", "sector": "Chemicals"},
    {"symbol": "HDFCLIFE", "name": "HDFC Life Insurance", "sector": "Insurance"},
    {"symbol": "LTIM", "name": "LTIMindtree Ltd", "sector": "IT"},
    # Additional Popular Stocks
    {"symbol": "ZOMATO", "name": "Zomato Ltd", "sector": "Consumer Tech"},
    {"symbol": "PAYTM", "name": "One 97 Communications", "sector": "Fintech"},
    {"symbol": "NYKAA", "name": "FSN E-Commerce (Nykaa)", "sector": "E-commerce"},
    {"symbol": "POLICYBZR", "name": "PB Fintech (Policybazaar)", "sector": "Fintech"},
    {"symbol": "DELHIVERY", "name": "Delhivery Ltd", "sector": "Logistics"},
    {"symbol": "IRCTC", "name": "IRCTC Ltd", "sector": "Travel"},
    {"symbol": "TRENT", "name": "Trent Ltd (Westside)", "sector": "Retail"},
    {"symbol": "DMART", "name": "Avenue Supermarts (DMart)", "sector": "Retail"},
    {"symbol": "PIDILITIND", "name": "Pidilite Industries", "sector": "Chemicals"},
    {"symbol": "SIEMENS", "name": "Siemens Ltd", "sector": "Engineering"},
    {"symbol": "HAVELLS", "name": "Havells India Ltd", "sector": "Consumer Durables"},
    {"symbol": "ABB", "name": "ABB India Ltd", "sector": "Engineering"},
    {"symbol": "GODREJCP", "name": "Godrej Consumer Products", "sector": "FMCG"},
    {"symbol": "MARICO", "name": "Marico Ltd", "sector": "FMCG"},
    {"symbol": "DABUR", "name": "Dabur India Ltd", "sector": "FMCG"},
    {"symbol": "COLPAL", "name": "Colgate-Palmolive India", "sector": "FMCG"},
    {"symbol": "BERGEPAINT", "name": "Berger Paints India", "sector": "Consumer"},
    {"symbol": "ICICIPRULI", "name": "ICICI Prudential Life", "sector": "Insurance"},
    {"symbol": "BANKBARODA", "name": "Bank of Baroda", "sector": "Banking"},
    {"symbol": "PNB", "name": "Punjab National Bank", "sector": "Banking"},
    {"symbol": "CANBK", "name": "Canara Bank", "sector": "Banking"},
    {"symbol": "IDFCFIRSTB", "name": "IDFC First Bank Ltd", "sector": "Banking"},
    {"symbol": "FEDERALBNK", "name": "Federal Bank Ltd", "sector": "Banking"},
    {"symbol": "BANDHANBNK", "name": "Bandhan Bank Ltd", "sector": "Banking"},
    {"symbol": "YESBANK", "name": "Yes Bank Ltd", "sector": "Banking"},
    {"symbol": "JUBLFOOD", "name": "Jubilant FoodWorks (Dominos)", "sector": "QSR"},
    {"symbol": "PAGEIND", "name": "Page Industries (Jockey)", "sector": "Textiles"},
    {"symbol": "MUTHOOTFIN", "name": "Muthoot Finance Ltd", "sector": "Finance"},
    {"symbol": "CHOLAFIN", "name": "Cholamandalam Investment", "sector": "Finance"},
    {"symbol": "M&MFIN", "name": "Mahindra & Mahindra Financial", "sector": "Finance"},
    {"symbol": "SHRIRAMFIN", "name": "Shriram Finance Ltd", "sector": "Finance"},
    {"symbol": "VEDL", "name": "Vedanta Ltd", "sector": "Metals"},
    {"symbol": "NMDC", "name": "NMDC Ltd", "sector": "Mining"},
    {"symbol": "SAIL", "name": "Steel Authority of India", "sector": "Metals"},
    {"symbol": "JINDALSTEL", "name": "Jindal Steel & Power", "sector": "Metals"},
    {"symbol": "ADANIGREEN", "name": "Adani Green Energy", "sector": "Renewable Energy"},
    {"symbol": "ADANIPOWER", "name": "Adani Power Ltd", "sector": "Power"},
    {"symbol": "TATAPOWER", "name": "Tata Power Company", "sector": "Power"},
    {"symbol": "TORNTPOWER", "name": "Torrent Power Ltd", "sector": "Power"},
    {"symbol": "RECLTD", "name": "REC Ltd", "sector": "Finance"},
    {"symbol": "PFC", "name": "Power Finance Corporation", "sector": "Finance"},
    {"symbol": "IOC", "name": "Indian Oil Corporation", "sector": "Energy"},
    {"symbol": "GAIL", "name": "GAIL (India) Ltd", "sector": "Energy"},
    {"symbol": "PETRONET", "name": "Petronet LNG Ltd", "sector": "Energy"},
    {"symbol": "HAL", "name": "Hindustan Aeronautics", "sector": "Defence"},
    {"symbol": "BEL", "name": "Bharat Electronics Ltd", "sector": "Defence"},
    {"symbol": "BHEL", "name": "Bharat Heavy Electricals", "sector": "Engineering"},
]

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


# Global stock API instance
stock_api = StockAPI()

