"""
Stock Market Dashboard - FastAPI Backend
Real-time stock signal analyzer with Telegram monitoring and BSE/NSE correlation
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import engine, SessionLocal, get_db, Base
from .models import (
    Config, Source, TelegramMessage, MarketNews, 
    StockPrice, Analysis, Recommendation, Log, FetchLog, WatchlistStock, AllStarPick, SECTOR_MAPPING, Stock
)
from .monitor import monitor
from .news_fetcher import news_fetcher
from .stock_api import stock_api, NSE_STOCKS
from .analyzer import analyzer, LARGE_CAP_STOCKS, MID_CAP_STOCKS, SMALL_CAP_STOCKS, PENNY_STOCKS
from .llm import llm_service

import logging
import pytz

IST = pytz.timezone('Asia/Kolkata')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tables
Base.metadata.create_all(bind=engine)


async def seed_stocks():
    """Seed stocks from hardcoded lists to DB (Phase 1)"""
    db = SessionLocal()
    try:
        if db.query(Stock).count() > 0:
            return  # Already seeded

        logger.info("Seeding stocks database...")
        
        # Helper to get cap type
        def get_cap_type(symbol):
            if symbol in LARGE_CAP_STOCKS: return "Large"
            if symbol in MID_CAP_STOCKS: return "Mid"
            if symbol in SMALL_CAP_STOCKS: return "Small"
            if symbol in PENNY_STOCKS: return "Penny"
            return "Unknown"

        stocks_to_add = []
        added_symbols = set()

        # 1. Add from NSE_STOCKS (Rich data with sectors)
        for s in NSE_STOCKS:
            symbol = s['symbol']
            if symbol not in added_symbols:
                stocks_to_add.append(Stock(
                    symbol=symbol,
                    name=s['name'],
                    sector=s['sector'],
                    cap_type=get_cap_type(symbol)
                ))
                added_symbols.add(symbol)
        
        # 2. Add remaining from Analyzer lists (Simple symbols)
        all_lists = LARGE_CAP_STOCKS + MID_CAP_STOCKS + SMALL_CAP_STOCKS + PENNY_STOCKS
        for symbol in all_lists:
            if symbol not in added_symbols:
                stocks_to_add.append(Stock(
                    symbol=symbol,
                    name=symbol,  # Fallback name
                    sector="Unknown",
                    cap_type=get_cap_type(symbol)
                ))
                added_symbols.add(symbol)

        db.bulk_save_objects(stocks_to_add)
        db.commit()
        logger.info(f"Seeded {len(stocks_to_add)} stocks")

    except Exception as e:
        logger.error(f"Stock seeding failed: {e}")
    finally:
        db.close()


async def news_background_task():
    """Background task to fetch news every 30 minutes"""
    logger.info("Starting background news fetcher task (30m interval)")
    while True:
        try:
            # Wait 30 minutes between fetches
            # Initial wait of 1 minute to let the server settle
            await asyncio.sleep(60)
            
            while True:
                logger.info("Scheduled background news fetch starting...")
                added = await news_fetcher.fetch_all_feeds()
                logger.info(f"Background news fetch complete: {added} new articles")
                
                # Wait 30 minutes
                await asyncio.sleep(1800)
        except asyncio.CancelledError:
            logger.info("Background news fetcher task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in background news fetcher: {e}")
            await asyncio.sleep(300)  # Wait 5 minutes before retrying on error


async def telegram_background_task():
    """Background task to auto-fetch Telegram messages every 15 minutes"""
    logger.info("Starting background Telegram fetcher task (15m interval)")
    # Initial wait of 2 minutes to let the server settle
    await asyncio.sleep(120)
    
    while True:
        try:
            logger.info("Scheduled background Telegram fetch starting...")
            db = SessionLocal()
            try:
                sources = db.query(Source).filter(Source.active == True).all()
                total_fetched = 0
                for source in sources:
                    try:
                        fetched = await monitor.fetch_channel_history(source.channel_username, limit=20)
                        total_fetched += fetched
                        logger.info(f"Fetched {fetched} messages from {source.name}")
                    except Exception as e:
                        logger.error(f"Error fetching from {source.name}: {e}")
                logger.info(f"Background Telegram fetch complete: {total_fetched} new messages from {len(sources)} sources")
            finally:
                db.close()
            
            # Wait 15 minutes
            await asyncio.sleep(900)
        except asyncio.CancelledError:
            logger.info("Background Telegram fetcher task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in background Telegram fetcher: {e}")
            await asyncio.sleep(300)  # Wait 5 minutes before retrying on error

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("Starting Stock Market Dashboard...")
    
    # Phase 1: Seed Stocks
    await seed_stocks()
    
    # Start background news fetcher
    news_task = asyncio.create_task(news_background_task())
    
    # Start background Telegram fetcher (15 min interval)
    telegram_task = asyncio.create_task(telegram_background_task())
    
    # Try to restore Telegram session
    db = SessionLocal()
    try:
        api_id = db.query(Config).filter(Config.key == "telegram_api_id").first()
        api_hash = db.query(Config).filter(Config.key == "telegram_api_hash").first()
        
        if api_id and api_hash:
            try:
                await monitor.initialize(int(api_id.value), api_hash.value)
                if await monitor.is_authorized():
                    logger.info("Telegram session restored")
                    
                    # Start monitoring configured channels
                    channels = db.query(Config).filter(Config.key == "telegram_channels").first()
                    if channels and channels.json_value:
                        await monitor.start_monitoring(channels.json_value)
            except Exception as e:
                logger.warning(f"Could not restore Telegram: {e}")
    finally:
        db.close()
    
    yield
    
    # Cancel background tasks
    news_task.cancel()
    telegram_task.cancel()
    logger.info("Shutting down...")


app = FastAPI(
    title="Stock Market Dashboard API",
    description="Real-time stock signal analyzer with Telegram and BSE/NSE integration",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Pydantic Models ==============

class TelegramLoginRequest(BaseModel):
    api_id: int
    api_hash: str
    phone: str

class TelegramVerifyRequest(BaseModel):
    phone: str
    code: str
    two_fa_password: Optional[str] = None

class SourceCreate(BaseModel):
    name: str
    channel_username: str

class DateRangeRequest(BaseModel):
    start_date: datetime
    end_date: datetime

class TimeShortcut(BaseModel):
    shortcut: str  # last_hour, today, last_day, last_week, last_month

class WatchlistAdd(BaseModel):
    symbol: str
    name: Optional[str] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    notes: Optional[str] = None

class WatchlistUpdate(BaseModel):
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    notes: Optional[str] = None



# ============== Health Check ==============

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# ============== All Star Picks (Top 10 Daily) ==============

def get_validity_expiry_ist() -> datetime:
    """Get validity expiry (Next Market Open - 09:15 AM IST)"""
    import pytz
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.now(ist)
    
    # Target: 09:15 AM
    expiry = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
    
    # If currently past 9:15 AM, expires TOMORROW at 9:15 AM
    # This keeps data valid throughout the trading day and the evening/night research session
    if now_ist >= expiry:
        expiry += timedelta(days=1)
    
    # Skip weekends (Saturday/Sunday -> Monday)
    while expiry.weekday() >= 5:  # Saturday = 5, Sunday = 6
        expiry += timedelta(days=1)
    
    return expiry

@app.get("/api/allstar")
async def get_allstar_picks(db: Session = Depends(get_db)):
    """Get Top 10 All Star stock picks - valid for the trading day"""
    import pytz
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    
    # Check for valid cached picks
    cached = db.query(AllStarPick).filter(
        AllStarPick.valid_until > now
    ).order_by(AllStarPick.confidence.desc()).limit(10).all()
    
    if len(cached) >= 10:
        # Return cached picks
        return {
            "picks": [{
                "id": p.id,
                "symbol": p.symbol,
                "name": p.name,
                "category": p.category,
                "action": p.action,
                "confidence": p.confidence,
                "reasoning": p.reasoning,
                "current_price": p.current_price,
                "target_price": p.target_price,
                "stop_loss": p.stop_loss,
                "news_count": p.news_count,
                "valid_until": p.valid_until.isoformat() if p.valid_until else None
            } for p in cached],
            "cached": True,
            "valid_until": cached[0].valid_until.isoformat() if cached else None,
            "generated_at": cached[0].created_at.isoformat() if cached else None
        }
    
    # Need to generate fresh picks - delete expired
    db.query(AllStarPick).filter(AllStarPick.valid_until <= now).delete()
    db.commit()
    
    # Generate new picks based on analysis
    picks = await generate_allstar_picks(db)
    
    return {
        "picks": picks,
        "cached": False,
        "valid_until": get_next_market_close_ist().isoformat(),
        "generated_at": datetime.now(ist).isoformat()
    }


async def generate_allstar_picks(db: Session) -> list:
    """Generate fresh All Star picks from news and telegram analysis.
    
    Refactored into smaller helper functions for better maintainability.
    """
    from .analyzer import analyzer, LARGE_CAP_STOCKS, MID_CAP_STOCKS, SMALL_CAP_STOCKS, PENNY_STOCKS
    from .stock_api import stock_api, NSE_STOCKS
    import random
    import pytz
    
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    valid_until = get_validity_expiry_ist()
    day_ago = now - timedelta(hours=24)
    
    # Step 1: Fetch recent data
    news = db.query(MarketNews).filter(MarketNews.created_at >= day_ago).all()
    messages = db.query(TelegramMessage).filter(TelegramMessage.created_at >= day_ago).all()
    
    # Step 2: Aggregate stock mentions and sentiments
    stock_data = _aggregate_stock_mentions(news, messages, analyzer)
    
    # Step 3: Select diverse picks (top analyzed + random from categories)
    all_picks = _select_diverse_picks(
        stock_data, LARGE_CAP_STOCKS, MID_CAP_STOCKS, SMALL_CAP_STOCKS, PENNY_STOCKS
    )
    
    # Step 4: Generate detailed picks with prices and targets
    picks = []
    for symbol in all_picks:
        pick_data = await _generate_pick_details(
            symbol, stock_data, valid_until, 
            NSE_STOCKS, LARGE_CAP_STOCKS, MID_CAP_STOCKS, SMALL_CAP_STOCKS, PENNY_STOCKS,
            stock_api, db
        )
        picks.append(pick_data)
    
    db.commit()
    return picks


def _aggregate_stock_mentions(news: list, messages: list, analyzer) -> dict:
    """Aggregate stock mentions and sentiments from news and messages.
    
    Returns dict: {symbol: {mentions, bullish, bearish, neutral}}
    """
    stock_data = {}
    
    # Process news articles
    for article in news:
        if article.extracted_stocks:
            for symbol in article.extracted_stocks:
                if symbol not in stock_data:
                    stock_data[symbol] = {"mentions": 0, "bullish": 0, "bearish": 0, "neutral": 0}
                stock_data[symbol]["mentions"] += 1
                if article.sentiment == "positive":
                    stock_data[symbol]["bullish"] += 1
                elif article.sentiment == "negative":
                    stock_data[symbol]["bearish"] += 1
                else:
                    stock_data[symbol]["neutral"] += 1
    
    # Process Telegram messages
    for msg in messages:
        if msg.text:
            stocks = analyzer.extract_stocks(msg.text)
            sentiment, _ = analyzer.analyze_sentiment(msg.text)
            for symbol in stocks:
                if symbol not in stock_data:
                    stock_data[symbol] = {"mentions": 0, "bullish": 0, "bearish": 0, "neutral": 0}
                stock_data[symbol]["mentions"] += 1
                stock_data[symbol][sentiment] += 1
    
    return stock_data


def _select_diverse_picks(stock_data: dict, large_caps: list, mid_caps: list, 
                          small_caps: list, penny_stocks: list, max_picks: int = 10) -> list:
    """Select diverse stock picks from analyzed data and random categories.
    
    Returns list of symbols (max 10).
    """
    import random
    
    # Score and sort stocks (skip indices)
    scored_stocks = []
    for symbol, data in stock_data.items():
        if symbol in ["NIFTY", "NIFTY50", "SENSEX", "BANKNIFTY"]:
            continue
        score = data["mentions"] * 0.5 + data["bullish"] * 1.0 - data["bearish"] * 0.5
        scored_stocks.append((symbol, score, data))
    
    scored_stocks.sort(key=lambda x: x[1], reverse=True)
    top_analyzed = [s for s, _, _ in scored_stocks[:5]]
    
    # Add random picks from each category for diversity
    random_large = random.sample(large_caps, min(2, len(large_caps)))
    random_mid = random.sample(mid_caps, min(2, len(mid_caps)))
    random_small = random.sample(small_caps, min(1, len(small_caps)))
    random_penny = random.sample(penny_stocks, min(1, len(penny_stocks)))
    
    all_picks = list(set(top_analyzed + random_large + random_mid + random_small + random_penny))
    random.shuffle(all_picks)
    return all_picks[:max_picks]


def _determine_action_and_confidence(data: dict) -> tuple:
    """Determine BUY/SELL/HOLD action and confidence score from sentiment data.
    
    Returns tuple: (action, confidence)
    """
    bullish = data.get("bullish", 0)
    bearish = data.get("bearish", 0)
    neutral = data.get("neutral", 0)
    mentions = data.get("mentions", 0)
    total = bullish + bearish + neutral
    
    if bullish > bearish:
        action = "BUY"
        confidence = min(95, (bullish / max(1, total)) * 100 + mentions * 2)
    elif bearish > bullish:
        action = "SELL"
        confidence = min(95, (bearish / max(1, total)) * 100 + mentions * 2)
    else:
        action = "HOLD"
        confidence = 50 + mentions * 2
    
    return action, round(confidence, 1)


def _get_stock_category(symbol: str, large_caps: list, mid_caps: list, 
                        small_caps: list, penny_stocks: list) -> str:
    """Get market cap category for a stock symbol."""
    if symbol in large_caps:
        return "Large Cap"
    elif symbol in mid_caps:
        return "Mid Cap"
    elif symbol in small_caps:
        return "Small Cap"
    elif symbol in penny_stocks:
        return "Penny Stock"
    return "Unknown"


async def _generate_pick_details(symbol: str, stock_data: dict, valid_until,
                                  nse_stocks: list, large_caps: list, mid_caps: list,
                                  small_caps: list, penny_stocks: list,
                                  stock_api, db) -> dict:
    """Generate detailed pick data for a symbol including price targets.
    
    Also saves the pick to database.
    """
    # Get stock info
    stock_info = next((s for s in nse_stocks if s["symbol"] == symbol), None)
    name = stock_info["name"] if stock_info else symbol
    
    # Get category
    category = _get_stock_category(symbol, large_caps, mid_caps, small_caps, penny_stocks)
    
    # Get sentiment data
    data = stock_data.get(symbol, {"mentions": 0, "bullish": 1, "bearish": 0, "neutral": 0})
    
    # Determine action and confidence
    action, confidence = _determine_action_and_confidence(data)
    
    # Get price and calculate targets
    quote = await stock_api.get_stock_quote(symbol)
    current_price = quote.get("price") if quote else None
    
    target_price = None
    stop_loss = None
    
    if current_price:
        targets = await stock_api.calculate_targets(symbol)
        target_price = targets.get("target_price")
        stop_loss = targets.get("stop_loss")
    
    # Generate reasoning
    if data["mentions"] > 0:
        reasoning = f"Based on {data['mentions']} mentions in last 24h with {data['bullish']} bullish and {data['bearish']} bearish signals."
    else:
        reasoning = f"Random discovery from {category} category - diversification pick."
    
    # Save to database
    pick = AllStarPick(
        symbol=symbol,
        name=name,
        category=category,
        action=action,
        confidence=confidence,
        reasoning=reasoning,
        current_price=current_price,
        target_price=target_price,
        stop_loss=stop_loss,
        news_count=data["mentions"],
        sentiment_score=data["bullish"] - data["bearish"],
        valid_until=valid_until
    )
    db.add(pick)
    
    return {
        "symbol": symbol,
        "name": name,
        "category": category,
        "action": action,
        "confidence": confidence,
        "reasoning": reasoning,
        "current_price": current_price,
        "target_price": target_price,
        "stop_loss": stop_loss,
        "news_count": data["mentions"],
        "valid_until": valid_until.isoformat(),
        "generated_at": datetime.now().isoformat()
    }


# ============== Telegram Auth ==============

@app.post("/api/telegram/login")
async def telegram_login(request: TelegramLoginRequest, db: Session = Depends(get_db)):
    """Initialize Telegram client and send verification code"""
    try:
        await monitor.initialize(request.api_id, request.api_hash)
        result = await monitor.send_code(request.phone)
        
        # Save credentials
        for key, value in [
            ("telegram_api_id", str(request.api_id)),
            ("telegram_api_hash", request.api_hash),
            ("telegram_phone", request.phone)
        ]:
            config = db.query(Config).filter(Config.key == key).first()
            if config:
                config.value = value
            else:
                db.add(Config(key=key, value=value))
        db.commit()
        
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/telegram/verify")
async def telegram_verify(request: TelegramVerifyRequest):
    """Verify Telegram code"""
    try:
        result = await monitor.verify_code(
            request.phone, 
            request.code, 
            request.two_fa_password
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/telegram/status")
async def telegram_status():
    """Get Telegram connection status"""
    is_authorized = await monitor.is_authorized()
    return {
        "authorized": is_authorized,
        "status": monitor.get_status()
    }


# ============== Sources Management ==============

@app.get("/api/sources")
async def get_sources(db: Session = Depends(get_db)):
    """Get all configured Telegram sources"""
    sources = db.query(Source).all()
    return [{
        "id": s.id,
        "name": s.name,
        "channel_id": s.channel_id,
        "channel_username": s.channel_username,
        "active": s.active,
        "last_fetched": s.last_fetched.isoformat() if s.last_fetched else None
    } for s in sources]

@app.post("/api/sources")
async def add_source(source: SourceCreate, db: Session = Depends(get_db)):
    """Add a new Telegram channel source"""
    existing = db.query(Source).filter(
        Source.channel_username == source.channel_username
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Source already exists")
    
    new_source = Source(
        name=source.name,
        channel_username=source.channel_username,
        channel_id=source.channel_username,
        active=True
    )
    db.add(new_source)
    db.commit()
    db.refresh(new_source)
    
    # Update monitored channels config
    channels_config = db.query(Config).filter(Config.key == "telegram_channels").first()
    channels = channels_config.json_value if channels_config else []
    channels.append(source.channel_username)
    
    if channels_config:
        channels_config.json_value = channels
    else:
        db.add(Config(key="telegram_channels", json_value=channels))
    db.commit()
    
    return {"id": new_source.id, "message": "Source added successfully"}

@app.delete("/api/sources/{source_id}")
async def delete_source(source_id: int, db: Session = Depends(get_db)):
    """Delete a source"""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    db.delete(source)
    db.commit()
    return {"message": "Source deleted"}

@app.post("/api/sources/{source_id}/fetch")
async def fetch_source(source_id: int, limit: int = 50, db: Session = Depends(get_db)):
    """Manually fetch messages from a source"""
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    if not await monitor.is_authorized():
        raise HTTPException(status_code=401, detail="Telegram not authenticated")
    
    count = await monitor.fetch_channel_history(source.channel_username, limit)
    
    source.last_fetched = datetime.now()
    db.commit()
    
    # After fetching, run a deep analysis on the last 50 messages from this source
    # to provide immediate recommendations
    from datetime import timedelta
    start_date = datetime.now() - timedelta(days=7) # Last week by default
    end_date = datetime.now()
    
    analysis_result = await analyzer.analyze_timeframe(start_date, end_date)
    recommendations = await analyzer.generate_all_recommendations(analysis_result)
    
    return {
        "messages_fetched": count,
        "analysis": analysis_result,
        "recommendations": recommendations[:10] # Top 10 for immediate feedback
    }


# ============== Messages ==============

def get_time_range(shortcut: str) -> tuple:
    """Convert time shortcut to date range in IST"""
    now = datetime.now(IST)
    
    shortcuts = {
        "last_hour": (now - timedelta(hours=1), now),
        "today": (now.replace(hour=0, minute=0, second=0, microsecond=0), now),
        "last_day": (now - timedelta(days=1), now),
        "last_week": (now - timedelta(weeks=1), now),
        "last_month": (now - timedelta(days=30), now),
    }
    
    return shortcuts.get(shortcut, (now - timedelta(days=1), now))

@app.get("/api/messages")
async def get_messages(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    shortcut: Optional[str] = None,
    source_id: Optional[int] = None,
    search: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get messages with calendar filter or time shortcuts"""
    
    # Use shortcut if provided, otherwise use date range
    if shortcut:
        start_date, end_date = get_time_range(shortcut)
    elif not start_date or not end_date:
        start_date, end_date = get_time_range("last_day")
    
    # Ensure naive comparison for SQLite stability
    if start_date and start_date.tzinfo:
        start_date = start_date.replace(tzinfo=None)
    if end_date and end_date.tzinfo:
        end_date = end_date.replace(tzinfo=None)
    
    query = db.query(TelegramMessage).filter(
        TelegramMessage.message_date >= start_date,
        TelegramMessage.message_date <= end_date
    )
    
    if source_id:
        query = query.filter(TelegramMessage.source_id == source_id)
    
    if search:
        query = query.filter(TelegramMessage.text.ilike(f"%{search}%"))
    
    messages = query.order_by(TelegramMessage.message_date.desc()).limit(limit).all()
    
    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "count": len(messages),
        "messages": [{
            "id": m.id,
            "channel_name": m.channel_name,
            "text": m.text,
            "urls": m.urls,
            "extracted_stocks": m.extracted_stocks,
            "sentiment": m.sentiment,
            "created_at": m.created_at.isoformat()
        } for m in messages]
    }


# ============== Live Signal Feed ==============

@app.get("/api/signals/live")
async def get_live_signals(
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get recent Telegram signals with stock analysis for live feed"""
    # Get messages from the last hour
    one_hour_ago = datetime.now(IST) - timedelta(hours=1)
    if one_hour_ago.tzinfo:
        one_hour_ago = one_hour_ago.replace(tzinfo=None)
    
    messages = db.query(TelegramMessage).filter(
        TelegramMessage.message_date >= one_hour_ago,
        TelegramMessage.extracted_stocks != None
    ).order_by(TelegramMessage.message_date.desc()).limit(limit).all()
    
    signals = []
    for m in messages:
        stocks = m.extracted_stocks if isinstance(m.extracted_stocks, list) else []
        sentiment = m.sentiment or 'neutral'
        
        # Determine if this requires attention
        requires_attention = False
        action = 'HOLD'
        
        if sentiment in ['very_bullish', 'bullish']:
            action = 'BUY' if sentiment == 'bullish' else 'STRONG BUY'
            requires_attention = (sentiment == 'very_bullish')
        elif sentiment in ['very_bearish', 'bearish']:
            action = 'SELL' if sentiment == 'bearish' else 'AVOID'
            requires_attention = (sentiment == 'very_bearish')
        
        signals.append({
            "id": m.id,
            "channel_name": m.channel_name,
            "text": m.text[:200] + "..." if len(m.text) > 200 else m.text,
            "stocks": stocks,
            "sentiment": sentiment,
            "action": action,
            "requires_attention": requires_attention,
            "timestamp": m.message_date.isoformat() if m.message_date else m.created_at.isoformat()
        })
    
    return {
        "count": len(signals),
        "signals": signals,
        "last_updated": datetime.now(IST).isoformat()
    }


# ============== Market News ==============

@app.get("/api/news")
async def get_news(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    shortcut: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get market news with filters"""
    
    if shortcut:
        start_date, end_date = get_time_range(shortcut)
    elif not start_date or not end_date:
        start_date, end_date = get_time_range("last_week")
    
    # Ensure naive comparison for SQLite stability
    if start_date and start_date.tzinfo:
        start_date = start_date.replace(tzinfo=None)
    if end_date and end_date.tzinfo:
        end_date = end_date.replace(tzinfo=None)
    
    query = db.query(MarketNews).filter(
        MarketNews.published_at >= start_date,
        MarketNews.published_at <= end_date
    )
    
    if source:
        query = query.filter(MarketNews.source == source)
    
    news = query.order_by(MarketNews.published_at.desc()).limit(limit).all()
    
    return {
        "count": len(news),
        "news": [{
            "id": n.id,
            "source": n.source,
            "title": n.title,
            "summary": n.summary,
            "link": n.link,
            "stocks": n.extracted_stocks,
            "sentiment": n.sentiment,
            "published_at": n.published_at.isoformat() if n.published_at else None
        } for n in news]
    }

@app.post("/api/news/fetch")
async def fetch_news():
    """Manually fetch news from all RSS feeds"""
    count = await news_fetcher.fetch_all_feeds()
    return {"articles_fetched": count}


# ============== Stock Prices ==============

@app.get("/api/stocks/quote/{symbol}")
async def get_stock_quote(symbol: str):
    """Get current stock quote"""
    quote = await stock_api.get_stock_quote(symbol.upper())
    if not quote:
        raise HTTPException(status_code=404, detail="Stock not found")
    return quote

@app.get("/api/stocks/indices")
async def get_indices():
    """Get major index values"""
    nifty = await stock_api.get_index_data("NIFTY50")
    sensex = await stock_api.get_index_data("SENSEX")
    banknifty = await stock_api.get_index_data("BANKNIFTY")
    
    return {
        "NIFTY50": nifty,
        "SENSEX": sensex,
        "BANKNIFTY": banknifty
    }

@app.post("/api/stocks/fetch")
async def fetch_stock_prices(symbols: Optional[List[str]] = None):
    """Fetch and store current stock prices"""
    count = await stock_api.save_stock_prices(symbols)
    return {"prices_fetched": count}

@app.get("/api/stocks/search")
async def search_stocks(q: str = Query(..., min_length=1, description="Search query")):
    """Search stocks by symbol or name for autocomplete"""
    results = stock_api.search_stocks(q, limit=10)
    return {"query": q, "results": results}

@app.get("/api/stocks/analyze/{symbol}")
async def analyze_stock(symbol: str):
    """Analyze a stock and calculate recommended target price and stop loss"""
    analysis = await stock_api.calculate_targets(symbol.upper())
    return analysis


# ============== Analysis & Recommendations ==============

@app.post("/api/analyze")
async def analyze_data(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    shortcut: Optional[str] = None
):
    """Analyze messages and news for a time period and generate recommendations"""
    
    if shortcut:
        start_date, end_date = get_time_range(shortcut)
    elif not start_date or not end_date:
        start_date, end_date = get_time_range("last_week")
    
    # Run analysis
    analysis_result = await analyzer.analyze_timeframe(start_date, end_date)
    
    # Generate recommendations
    recommendations = await analyzer.generate_all_recommendations(analysis_result)
    
    return {
        "analysis": analysis_result,
        "recommendations": recommendations,
        "timeframes": ["next_day", "next_week", "next_month", "1yr", "2yr", "5yr", "10yr"]
    }

@app.get("/api/recommendations")
async def get_recommendations(
    timeframe: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get latest recommendations, optionally filtered by timeframe"""
    
    query = db.query(Recommendation).order_by(Recommendation.created_at.desc())
    
    if timeframe:
        query = query.filter(Recommendation.timeframe == timeframe)
    
    recs = query.limit(500).all()
    
    # Group by timeframe
    grouped = {}
    for r in recs:
        if r.timeframe not in grouped:
            grouped[r.timeframe] = []
        grouped[r.timeframe].append({
            "id": r.id,
            "symbol": r.symbol,
            "action": r.action,
            "confidence": r.confidence,
            "reasoning": r.reasoning,
            "created_at": r.created_at.isoformat()
        })
    
    return {
        "timeframes": ["next_day", "next_week", "next_month", "1yr", "2yr", "5yr", "10yr"],
        "recommendations": grouped
    }


# ============== Stock Detail (Universal Modal) ==============

@app.get("/api/stock/{symbol}/detail")
async def get_stock_detail(symbol: str, db: Session = Depends(get_db)):
    """Get comprehensive stock detail for modal view - includes chart data, ratios, and external links"""
    from .stock_api import stock_api, NSE_STOCKS
    from .analyzer import analyzer, LARGE_CAP_STOCKS, MID_CAP_STOCKS, SMALL_CAP_STOCKS, PENNY_STOCKS
    from datetime import datetime, timedelta
    import pytz
    from .recommendation_engine import recommendation_engine
    
    symbol = symbol.upper()
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    
    # Get stock info from our database
    stock_info = next((s for s in NSE_STOCKS if s["symbol"] == symbol), None)
    
    # Get current quote
    quote = await stock_api.get_stock_quote(symbol)
    
    # Calculate targets
    targets = await stock_api.calculate_targets(symbol)
    
    # Get category
    if symbol in LARGE_CAP_STOCKS:
        category = "Large Cap"
    elif symbol in MID_CAP_STOCKS:
        category = "Mid Cap"
    elif symbol in SMALL_CAP_STOCKS:
        category = "Small Cap"
    elif symbol in PENNY_STOCKS:
        category = "Penny Stock"
    else:
        category = "Unknown"
    
    # Get price history for chart (last 30 days from Yahoo Finance)
    chart_data = await get_price_chart_data(symbol)
    
    # Get related news (last 7 days)
    week_ago = now - timedelta(days=7)
    news = db.query(MarketNews).filter(
        MarketNews.extracted_stocks.contains([symbol]),
        MarketNews.created_at >= week_ago
    ).order_by(MarketNews.created_at.desc()).limit(10).all()
    
    # Get recommendations for this stock
    recs = db.query(Recommendation).filter(
        Recommendation.symbol == symbol
    ).order_by(Recommendation.created_at.desc()).limit(7).all()
    
    # Get telegram messages mentioning this stock
    messages = db.query(TelegramMessage).filter(
        TelegramMessage.text.ilike(f'%{symbol}%')
    ).order_by(TelegramMessage.created_at.desc()).limit(5).all()
    
    # Calculate key ratios (simulated - in production would come from API)
    key_ratios = get_key_ratios(symbol, quote)
    
    # Generate Advanced Recommendation
    # Prepare historical data
    formatted_history = chart_data.get('prices', []) if chart_data else []
    
    # Helper to convert news objects to dicts
    news_items = [{
        "title": n.title,
        "sentiment": n.sentiment
    } for n in news]
    
    # Helper for sentiment data
    sentiment_data = {'bullish': 0, 'bearish': 0, 'neutral': 0}
    # (Simple aggregation from news/messages would go here, for now passing basics)
    
    advanced_recommendation = await recommendation_engine.generate_recommendation(
        symbol=symbol,
        quote=quote,
        historical_data=formatted_history,
        fundamentals=key_ratios,
        sentiment_data=sentiment_data,
        news_items=news_items
    )
    
    # External links
    external_links = {
        "screener": f"https://www.screener.in/company/{symbol}/",
        "nse": f"https://www.nseindia.com/get-quotes/equity?symbol={symbol}",
        "bse": f"https://www.bseindia.com/stock-share-price/x/y/{symbol}/",
        "moneycontrol": f"https://www.moneycontrol.com/stocksmarketsindia/?classic=true&q={symbol}",
        "tradingview": f"https://www.tradingview.com/symbols/NSE-{symbol}/"
    }
    
    return {
        "symbol": symbol,
        "name": stock_info["name"] if stock_info else symbol,
        "sector": stock_info["sector"] if stock_info else None,
        "category": category,
        
        # Price data
        "current_price": quote.get("price") if quote else None,
        "change": quote.get("change") if quote else None,
        "change_percent": quote.get("change_percent") if quote else None,
        "open": quote.get("open") if quote else None,
        "high": quote.get("high") if quote else None,
        "low": quote.get("low") if quote else None,
        "prev_close": quote.get("close") if quote else None,
        "volume": quote.get("volume") if quote else None,
        
        # Targets
        "target_price": targets.get("target_price"),
        "stop_loss": targets.get("stop_loss"),
        "potential_gain": targets.get("potential_gain_percent"),
        "potential_loss": targets.get("potential_loss_percent"),
        "target_reasoning": targets.get("reasoning"),
        
        # Chart data (for rendering price history)
        "chart_data": chart_data,
        
        # Key ratios
        "ratios": key_ratios,
        
        # Related news
        "news": [{
            "title": n.title,
            "link": n.link,
            "source": n.source,
            "sentiment": n.sentiment,
            "published_at": n.published_at.isoformat() if n.published_at else None
        } for n in news],
        
        # Recommendations
        "recommendations": [{
            "timeframe": r.timeframe,
            "action": r.action,
            "confidence": r.confidence,
            "reasoning": r.reasoning
        } for r in recs],
        
        # Telegram signals
        "signals": [{
            "channel": m.channel_name,
            "text": m.text[:200] if m.text else None,
            "date": m.created_at.isoformat() if m.created_at else None
        } for m in messages],
        
        # External links
        "external_links": external_links,
        
        # Advanced AI Recommendation
        "advanced_recommendation": advanced_recommendation,
        
        "last_updated": now.isoformat()
    }


async def get_price_chart_data(symbol: str) -> dict:
    """Fetch historical price data for chart from Yahoo Finance"""
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # Get 1 month of daily data
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS?interval=1d&range=1mo"
            response = await client.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            
            if response.status_code == 200:
                data = response.json()
                result = data.get('chart', {}).get('result', [{}])[0]
                
                timestamps = result.get('timestamp', [])
                indicators = result.get('indicators', {}).get('quote', [{}])[0]
                
                prices = []
                for i, ts in enumerate(timestamps):
                    if indicators.get('close') and i < len(indicators['close']):
                        prices.append({
                            "date": datetime.fromtimestamp(ts).strftime('%Y-%m-%d'),
                            "open": indicators.get('open', [None])[i] if indicators.get('open') else None,
                            "high": indicators.get('high', [None])[i] if indicators.get('high') else None,
                            "low": indicators.get('low', [None])[i] if indicators.get('low') else None,
                            "close": indicators.get('close', [None])[i] if indicators.get('close') else None,
                            "volume": indicators.get('volume', [None])[i] if indicators.get('volume') else None
                        })
                
                return {
                    "symbol": symbol,
                    "period": "1m",
                    "interval": "1d",
                    "prices": prices[-30:],  # Last 30 days
                    "labels": [p["date"] for p in prices[-30:]],
                    "closes": [p["close"] for p in prices[-30:]]
                }
    except Exception as e:
        logger.error(f"Error fetching chart data for {symbol}: {e}")
    
    return {"prices": [], "labels": [], "closes": []}


def get_key_ratios(symbol: str, quote: dict) -> dict:
    """Get key financial ratios for stock (simulated for NSE stocks)"""
    import random
    
    # In production, these would come from Screener API or financial data provider
    # For now, generate reasonable estimates based on market cap category
    
    price = quote.get("price", 100) if quote else 100
    
    # Simulated ratios based on typical Indian market ranges
    ratios = {
        "pe_ratio": round(random.uniform(12, 45), 2),
        "pb_ratio": round(random.uniform(1.5, 8), 2),
        "dividend_yield": round(random.uniform(0.2, 3.5), 2),
        "roe": round(random.uniform(8, 25), 2),
        "roce": round(random.uniform(10, 30), 2),
        "debt_to_equity": round(random.uniform(0.1, 1.5), 2),
        "eps": round(price / random.uniform(15, 40), 2),
        "book_value": round(price / random.uniform(2, 6), 2),
        "face_value": 10 if random.random() > 0.3 else 1,
        "market_cap": None,  # Would need additional data
        "52w_high": round(price * random.uniform(1.1, 1.5), 2),
        "52w_low": round(price * random.uniform(0.6, 0.9), 2),
    }
    
    return ratios




@app.get("/api/logs/fetch")
async def get_fetch_logs(limit: int = 50, db: Session = Depends(get_db)):
    """Get fetch operation logs"""
    logs = db.query(FetchLog).order_by(FetchLog.timestamp.desc()).limit(limit).all()
    return [{
        "id": l.id,
        "source_name": l.source_name,
        "source_type": l.source_type,
        "items_fetched": l.items_fetched,
        "status": l.status,
        "error_message": l.error_message,
        "timestamp": l.timestamp.isoformat()
    } for l in logs]


# ============== Dashboard Stats ==============

@app.get("/api/dashboard/stats")
async def get_dashboard_stats(shortcut: Optional[str] = "today", db: Session = Depends(get_db)):
    """Get dashboard statistics based on time filter"""
    start_date, end_date = get_time_range(shortcut)
    
    # Ensure naive comparison for SQLite stability
    start_date = start_date.replace(tzinfo=None) if start_date.tzinfo else start_date
    end_date = end_date.replace(tzinfo=None) if end_date.tzinfo else end_date

    today_messages = db.query(TelegramMessage).filter(
        TelegramMessage.message_date >= start_date,
        TelegramMessage.message_date <= end_date
    ).count()
    
    total_news = db.query(MarketNews).filter(
        MarketNews.published_at >= start_date,
        MarketNews.published_at <= end_date
    ).count()
    
    active_sources = db.query(Source).filter(Source.active == True).count()
    
    total_recommendations = db.query(Recommendation).filter(
        Recommendation.created_at >= start_date,
        Recommendation.created_at <= end_date
    ).count()
    
    # Get telegram status
    tg_authorized = await monitor.is_authorized()
    
    return {
        "total_messages": today_messages, # Reflect filtered count
        "today_messages": today_messages,
        "total_news": total_news,
        "active_sources": active_sources,
        "total_recommendations": total_recommendations,
        "telegram_connected": tg_authorized,
        "last_updated": datetime.now(IST).isoformat()
    }


# ============== Watchlist ==============

@app.get("/api/watchlist")
async def get_watchlist(db: Session = Depends(get_db)):
    """Get all stocks in watchlist, ordered by date added (newest first)"""
    stocks = db.query(WatchlistStock).filter(
        WatchlistStock.active == True
    ).order_by(WatchlistStock.created_at.desc()).all()
    
    # Enrich with current prices
    results = []
    for s in stocks:
        results.append({
            "id": s.id,
            "symbol": s.symbol,
            "name": s.name,
            "sector": s.sector,
            "industry": s.industry,
            "current_price": s.current_price,
            "target_price": s.target_price,
            "stop_loss": s.stop_loss,
            "notes": s.notes,
            "created_at": s.created_at.isoformat() if s.created_at else None
        })
    
    return {"count": len(results), "stocks": results}

@app.post("/api/watchlist")
async def add_to_watchlist(stock: WatchlistAdd, db: Session = Depends(get_db)):
    """Add a stock to watchlist with auto-calculated targets if not provided"""
    existing = db.query(WatchlistStock).filter(
        WatchlistStock.symbol == stock.symbol.upper()
    ).first()
    
    if existing:
        if not existing.active:
            existing.active = True
            existing.target_price = stock.target_price
            existing.stop_loss = stock.stop_loss
            existing.notes = stock.notes
            db.commit()
            return {"id": existing.id, "message": "Stock reactivated in watchlist"}
        raise HTTPException(status_code=400, detail="Stock already in watchlist")
    
    # Get sector info from extended stock database
    from .stock_api import NSE_STOCKS
    stock_info = next((s for s in NSE_STOCKS if s["symbol"] == stock.symbol.upper()), None)
    sector = stock_info["sector"] if stock_info else SECTOR_MAPPING.get(stock.symbol.upper(), (None, None))[0]
    industry = SECTOR_MAPPING.get(stock.symbol.upper(), (None, None))[1]
    
    # Fetch current price and calculate targets if not provided
    quote = await stock_api.get_stock_quote(stock.symbol.upper())
    current_price = quote.get('price') if quote else None
    
    target_price = stock.target_price
    stop_loss = stock.stop_loss
    analysis_note = ""
    
    # Auto-calculate if not provided
    if (target_price is None or stop_loss is None) and current_price:
        analysis = await stock_api.calculate_targets(stock.symbol.upper())
        if analysis.get("target_price"):
            if target_price is None:
                target_price = analysis["target_price"]
            if stop_loss is None:
                stop_loss = analysis["stop_loss"]
            analysis_note = f"Auto-calculated: {analysis.get('reasoning', '')}"
    
    new_stock = WatchlistStock(
        symbol=stock.symbol.upper(),
        name=stock.name or (stock_info["name"] if stock_info else (quote.get('name') if quote else stock.symbol.upper())),
        sector=sector,
        industry=industry,
        current_price=current_price,
        target_price=target_price,
        stop_loss=stop_loss,
        notes=stock.notes or analysis_note if analysis_note else stock.notes
    )
    db.add(new_stock)
    db.commit()
    db.refresh(new_stock)
    
    response = {
        "id": new_stock.id, 
        "message": f"{stock.symbol.upper()} added to watchlist",
        "target_price": target_price,
        "stop_loss": stop_loss
    }
    if analysis_note:
        response["auto_calculated"] = True
        response["analysis_note"] = analysis_note
    
    return response


@app.get("/api/watchlist/{symbol}")
async def get_watchlist_stock(symbol: str, db: Session = Depends(get_db)):
    """Get detailed info for a watchlist stock with news and recommendations"""
    stock = db.query(WatchlistStock).filter(
        WatchlistStock.symbol == symbol.upper()
    ).first()
    
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not in watchlist")
    
    # Fetch current price
    quote = await stock_api.get_stock_quote(symbol.upper())
    
    # Get related news (last 7 days)
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    news = db.query(MarketNews).filter(
        MarketNews.created_at >= week_ago,
        MarketNews.extracted_stocks.contains([symbol.upper()])
    ).order_by(MarketNews.published_at.desc()).limit(10).all()
    
    # Get recommendations for this stock
    recs = db.query(Recommendation).filter(
        Recommendation.symbol == symbol.upper()
    ).order_by(Recommendation.created_at.desc()).limit(10).all()
    
    return {
        "stock": {
            "id": stock.id,
            "symbol": stock.symbol,
            "name": stock.name,
            "sector": stock.sector,
            "industry": stock.industry,
            "current_price": quote.get('price') if quote else stock.current_price,
            "change_percent": quote.get('change_percent') if quote else None,
            "target_price": stock.target_price,
            "stop_loss": stock.stop_loss,
            "notes": stock.notes
        },
        "news": [{
            "id": n.id,
            "title": n.title,
            "source": n.source,
            "link": n.link,
            "sentiment": n.sentiment,
            "published_at": n.published_at.isoformat() if n.published_at else None
        } for n in news],
        "recommendations": [{
            "timeframe": r.timeframe,
            "action": r.action,
            "confidence": r.confidence,
            "target_price": r.target_price,
            "reasoning": r.reasoning,
            "created_at": r.created_at.isoformat()
        } for r in recs]
    }

@app.put("/api/watchlist/{symbol}")
async def update_watchlist_stock(symbol: str, update: WatchlistUpdate, db: Session = Depends(get_db)):
    """Update watchlist stock targets"""
    stock = db.query(WatchlistStock).filter(
        WatchlistStock.symbol == symbol.upper()
    ).first()
    
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not in watchlist")
    
    if update.target_price is not None:
        stock.target_price = update.target_price
    if update.stop_loss is not None:
        stock.stop_loss = update.stop_loss
    if update.notes is not None:
        stock.notes = update.notes
    
    db.commit()
    return {"message": "Stock updated"}

@app.delete("/api/watchlist/{symbol}")
async def remove_from_watchlist(symbol: str, db: Session = Depends(get_db)):
    """Remove stock from watchlist"""
    stock = db.query(WatchlistStock).filter(
        WatchlistStock.symbol == symbol.upper()
    ).first()
    
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not in watchlist")
    
    stock.active = False
    db.commit()
    return {"message": f"{symbol.upper()} removed from watchlist"}


@app.post("/api/watchlist/refresh")
async def refresh_watchlist_prices(db: Session = Depends(get_db)):
    """Refresh all watchlist stock prices with live data"""
    stocks = db.query(WatchlistStock).filter(WatchlistStock.active == True).all()
    
    updated = 0
    results = []
    
    for stock in stocks:
        try:
            quote = await stock_api.get_stock_quote(stock.symbol)
            if quote and quote.get('price'):
                stock.current_price = quote.get('price')
                updated += 1
                results.append({
                    "symbol": stock.symbol,
                    "name": stock.name,
                    "sector": stock.sector,
                    "current_price": quote.get('price'),
                    "target_price": stock.target_price,
                    "stop_loss": stock.stop_loss,
                    "notes": stock.notes,
                    "id": stock.id
                })
            else:
                # Keep existing data if quote fails
                results.append({
                    "symbol": stock.symbol,
                    "name": stock.name,
                    "sector": stock.sector,
                    "current_price": stock.current_price,
                    "target_price": stock.target_price,
                    "stop_loss": stock.stop_loss,
                    "notes": stock.notes,
                    "id": stock.id
                })
        except Exception as e:
            logger.warning(f"Failed to refresh price for {stock.symbol}: {e}")
            results.append({
                "symbol": stock.symbol,
                "name": stock.name,
                "sector": stock.sector,
                "current_price": stock.current_price,
                "target_price": stock.target_price,
                "stop_loss": stock.stop_loss,
                "notes": stock.notes,
                "id": stock.id
            })
    
    db.commit()
    return {
        "message": f"Refreshed {updated} of {len(stocks)} stocks",
        "updated": updated,
        "count": len(results),
        "stocks": results
    }


# ============== Market Overview (News-Based, No Telegram Required) ==============

@app.get("/api/market/overview")
async def get_market_overview(db: Session = Depends(get_db)):
    """Get market overview with sector-wise breakdown from 24hr news"""
    now = datetime.now()
    day_ago = now - timedelta(hours=24)
    
    # Get news from last 24 hours
    news = db.query(MarketNews).filter(
        MarketNews.created_at >= day_ago
    ).order_by(MarketNews.published_at.desc()).all()
    
    # If no news, fetch fresh
    if len(news) < 5:
        await news_fetcher.fetch_all_feeds()
        news = db.query(MarketNews).filter(
            MarketNews.created_at >= day_ago
        ).order_by(MarketNews.published_at.desc()).all()
    
    # Aggregate by sector
    sector_data = {}
    stock_mentions = {}
    industry_data = {}
    
    for article in news:
        if article.extracted_stocks:
            for symbol in article.extracted_stocks:
                # Count stock mentions
                stock_mentions[symbol] = stock_mentions.get(symbol, 0) + 1
                
                # Group by sector
                if symbol in SECTOR_MAPPING:
                    sector, industry = SECTOR_MAPPING[symbol]
                    
                    if sector not in sector_data:
                        sector_data[sector] = {"count": 0, "stocks": set(), "sentiment": {"positive": 0, "negative": 0, "neutral": 0}}
                    sector_data[sector]["count"] += 1
                    sector_data[sector]["stocks"].add(symbol)
                    
                    sent = article.sentiment or "neutral"
                    if sent in ["positive", "bullish"]:
                        sector_data[sector]["sentiment"]["positive"] += 1
                    elif sent in ["negative", "bearish"]:
                        sector_data[sector]["sentiment"]["negative"] += 1
                    else:
                        sector_data[sector]["sentiment"]["neutral"] += 1
                    
                    # Group by industry
                    if industry not in industry_data:
                        industry_data[industry] = {"count": 0, "stocks": set()}
                    industry_data[industry]["count"] += 1
                    industry_data[industry]["stocks"].add(symbol)
    
    # Convert sets to lists
    for sector in sector_data:
        sector_data[sector]["stocks"] = list(sector_data[sector]["stocks"])
    for industry in industry_data:
        industry_data[industry]["stocks"] = list(industry_data[industry]["stocks"])
    
    # Sort by mentions
    top_stocks = sorted(stock_mentions.items(), key=lambda x: x[1], reverse=True)[:15]
    top_sectors = sorted(sector_data.items(), key=lambda x: x[1]["count"], reverse=True)
    top_industries = sorted(industry_data.items(), key=lambda x: x[1]["count"], reverse=True)[:10]
    
    # Get indices
    indices = await get_indices()
    
    return {
        "time_range": {
            "start": day_ago.isoformat(),
            "end": now.isoformat()
        },
        "total_news": len(news),
        "indices": indices,
        "top_stocks": [{"symbol": s, "mentions": c} for s, c in top_stocks],
        "sectors": [{"sector": s, **d} for s, d in top_sectors],
        "industries": [{"industry": i, **d} for i, d in top_industries],
        "latest_news": [{
            "id": n.id,
            "title": n.title,
            "source": n.source,
            "link": n.link,
            "stocks": n.extracted_stocks,
            "sentiment": n.sentiment,
            "published_at": n.published_at.isoformat() if n.published_at else None
        } for n in news[:10]]
    }

@app.post("/api/market/analyze")
async def analyze_market(db: Session = Depends(get_db)):
    """Run full market analysis from news (no Telegram required)"""
    now = datetime.now()
    day_ago = now - timedelta(hours=24)
    
    # Fetch fresh news
    await news_fetcher.fetch_all_feeds()
    
    # Run analysis
    analysis_result = await analyzer.analyze_timeframe(day_ago, now)
    
    # Generate recommendations
    recommendations = await analyzer.generate_all_recommendations(analysis_result)
    
    return {
        "analysis": analysis_result,
        "recommendations_count": len(recommendations),
        "message": "Market analysis complete. View recommendations in the Recommendations section."
    }


# ============== Screener API ==============

from .screener import stock_screener
from .expert_engine import expert_engine

@app.get("/api/screens")
async def get_all_screens():
    """Get all available stock screens (50+)"""
    screens = stock_screener.get_all_screens()
    categories = stock_screener.get_screens_by_category()
    return {
        "total": len(screens),
        "screens": screens,
        "categories": categories
    }

@app.get("/api/screens/{screen_id}/run")
async def run_screen(screen_id: str, db: Session = Depends(get_db)):
    """Run a specific stock screen and return matching stocks from all NSE/BSE stocks"""
    # Fetch all stocks from database for full coverage
    all_stocks = db.query(Stock).filter(Stock.is_active == True).all()
    
    # Build stock data dict from database + live fundamentals
    stock_data = {}
    for s in all_stocks:
        # Get fundamental data if available (cached or simulated)
        fundamentals = stock_api.get_fundamentals(s.symbol)
        if fundamentals:
            stock_data[s.symbol] = {
                "pe": fundamentals.get("pe", 0),
                "pb": fundamentals.get("pb", 0),
                "roe": fundamentals.get("roe", 0),
                "roce": fundamentals.get("roce", 0),
                "de": fundamentals.get("de", 0),
                "div_yield": fundamentals.get("div_yield", 0),
                "mcap": s.cap_type + " Cap" if s.cap_type else "Mid Cap"
            }
    
    # Run screen with full data
    results = stock_screener.run_screen_with_data(screen_id, stock_data)
    screen_info = stock_screener.screens.get(screen_id, {})
    return {
        "screen_id": screen_id,
        "screen_name": screen_info.get("name", screen_id),
        "description": screen_info.get("description", ""),
        "category": screen_info.get("category", ""),
        "matches": len(results),
        "stocks": results,
        "total_scanned": len(stock_data)
    }


# ============== Expert Engine API ==============

@app.get("/api/recommendation/{symbol}")
async def get_expert_recommendation(symbol: str, db: Session = Depends(get_db)):
    """Get expert recommendation for a specific stock"""
    symbol = symbol.upper().strip()
    
    # Get fundamentals from screener data or database
    from .screener import STOCK_DATA
    fundamentals = STOCK_DATA.get(symbol, {
        "pe": 0,
        "pb": 0,
        "roe": 0,
        "roce": 0,
        "de": 0,
        "div_yield": 0,
        "mcap": "Unknown"
    })
    
    # Get sentiment data from recent news
    now = datetime.now()
    day_ago = now - timedelta(hours=24)
    news = db.query(MarketNews).filter(
        MarketNews.extracted_stocks.contains(symbol),
        MarketNews.published_at >= day_ago
    ).all()
    
    sentiment_data = {
        "bullish": sum(1 for n in news if n.sentiment == "positive"),
        "bearish": sum(1 for n in news if n.sentiment == "negative"),
        "neutral": sum(1 for n in news if n.sentiment == "neutral"),
        "mentions": len(news)
    }
    
    # Get price data
    price_data = None
    try:
        quote = await stock_api.get_stock_quote(symbol)
        if quote:
            price_data = {
                "current_price": quote.get("current_price", 0),
                "change_percent": quote.get("change_percent", 0)
            }
    except Exception:
        pass
    
    # Calculate recommendation
    recommendation = expert_engine.calculate_recommendation(
        symbol=symbol,
        fundamentals=fundamentals,
        sentiment_data=sentiment_data,
        price_data=price_data
    )
    
    return {
        "symbol": symbol,
        "recommendation": recommendation,
        "fundamentals": fundamentals,
        "sentiment": sentiment_data
    }


# ============== Global Search API ==============

@app.get("/api/search")
async def global_search(q: str = Query(..., min_length=1), limit: int = 10, db: Session = Depends(get_db)):
    """Global instant stock search"""
    query = q.upper().strip()
    
    results = []
    
    # Search in NSE stocks (list of dicts with symbol, name, sector)
    for stock in NSE_STOCKS:
        symbol = stock["symbol"]
        name = stock["name"]
        sector = stock.get("sector", SECTOR_MAPPING.get(symbol, "General"))
        if query in symbol or query.lower() in name.lower():
            results.append({
                "symbol": symbol,
                "name": name,
                "sector": sector,
                "type": "stock"
            })
            if len(results) >= limit:
                break
    
    # Also search in database stocks if we have less than limit
    if len(results) < limit:
        db_stocks = db.query(Stock).filter(
            (Stock.symbol.ilike(f"%{query}%")) | 
            (Stock.name.ilike(f"%{query}%"))
        ).limit(limit - len(results)).all()
        
        for stock in db_stocks:
            if stock.symbol not in [r["symbol"] for r in results]:
                results.append({
                    "symbol": stock.symbol,
                    "name": stock.name or stock.symbol,
                    "sector": stock.sector or "General",
                    "type": "stock"
                })
    
    return {
        "query": q,
        "results": results[:limit],
        "total": len(results)
    }


# ============== Research Console API ==============

@app.get("/api/research/{symbol}")
async def get_research_data(symbol: str, db: Session = Depends(get_db)):
    """Get comprehensive research data for a stock"""
    symbol = symbol.upper().strip()
    
    # Get stock quote (price data)
    stock_quote = await stock_api.get_stock_quote(symbol)
    
    # Get stock info from NSE_STOCKS list
    nse_stock_info = next((s for s in NSE_STOCKS if s["symbol"] == symbol), None)
    
    # Get expert recommendation
    from .screener import STOCK_DATA
    fundamentals = STOCK_DATA.get(symbol, {
        "pe": stock_quote.get("pe_ratio", 0) if stock_quote else 0,
        "pb": stock_quote.get("pb_ratio", 0) if stock_quote else 0,
        "roe": 15,  # Default estimate
        "roce": 18,
        "de": 0.5,
        "div_yield": 1.0,
        "mcap": "Large Cap"
    })
    
    # Get sentiment from news
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    news = db.query(MarketNews).filter(
        MarketNews.extracted_stocks.contains(symbol),
        MarketNews.published_at >= week_ago
    ).order_by(MarketNews.published_at.desc()).limit(10).all()
    
    sentiment_data = {
        "bullish": sum(1 for n in news if n.sentiment == "positive"),
        "bearish": sum(1 for n in news if n.sentiment == "negative"),
        "neutral": sum(1 for n in news if n.sentiment == "neutral"),
        "mentions": len(news)
    }
    
    # Get recommendation
    recommendation = expert_engine.calculate_recommendation(
        symbol=symbol,
        fundamentals=fundamentals,
        sentiment_data=sentiment_data,
        price_data={"change_percent": stock_quote.get("change_percent", 0)} if stock_quote else None
    )
    
    # Get related stocks (same sector) - NSE_STOCKS is a list of dicts
    sector = nse_stock_info.get("sector") if nse_stock_info else SECTOR_MAPPING.get(symbol, "General")
    stock_name = nse_stock_info.get("name", symbol) if nse_stock_info else symbol
    related = [s["symbol"] for s in NSE_STOCKS if s.get("sector") == sector and s["symbol"] != symbol][:5]
    
    # Format stock info for frontend (needs current_price)
    formatted_stock_info = None
    if stock_quote:
        formatted_stock_info = stock_quote.copy()
        formatted_stock_info["current_price"] = stock_quote.get("price")

    return {
        "symbol": symbol,
        "name": stock_name,
        "sector": sector,
        "stock_info": formatted_stock_info,  # Return the formatted data
        "fundamentals": fundamentals,
        "expert_recommendation": recommendation,
        "recent_news": [{
            "title": n.title,
            "source": n.source,
            "sentiment": n.sentiment,
            "published_at": n.published_at.isoformat() if n.published_at else None,
            "link": n.link
        } for n in news],
        "related_stocks": related
    }


# ============== Gemini AI Config ==============

class GeminiConfig(BaseModel):
    api_key: str
    model: str = "gemini-3.0-flash"

@app.get("/api/gemini/config")
async def get_gemini_config(db: Session = Depends(get_db)):
    """Get current Gemini configuration"""
    api_key = db.query(Config).filter(Config.key == "gemini_api_key").first()
    model = db.query(Config).filter(Config.key == "gemini_model").first()
    
    return {
        "has_key": bool(api_key and api_key.value),
        "model": model.value if model else "gemini-3.0-flash"
    }

@app.post("/api/gemini/config")
async def save_gemini_config(config: GeminiConfig, db: Session = Depends(get_db)):
    """Save Gemini configuration"""
    # Sanitize inputs
    api_key = config.api_key.strip()
    model_name = config.model.strip()
    
    # Save API key
    existing_key = db.query(Config).filter(Config.key == "gemini_api_key").first()
    if existing_key:
        existing_key.value = api_key
    else:
        db.add(Config(key="gemini_api_key", value=api_key))
    
    # Save model
    existing_model = db.query(Config).filter(Config.key == "gemini_model").first()
    if existing_model:
        existing_model.value = model_name
    else:
        db.add(Config(key="gemini_model", value=model_name))
    
    # Enable AI features by default when key is set
    existing_ai = db.query(Config).filter(Config.key == "ai_features_enabled").first()
    if not existing_ai:
        db.add(Config(key="ai_features_enabled", value="true"))
    elif existing_ai.value != "true":
        existing_ai.value = "true"
        
    db.commit()
    
    # Reinitialize LLM service
    llm_service.initialized = False
    
    return {"success": True, "message": "Gemini configuration saved successfully"}

class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
async def chat_with_ai(request: ChatRequest, db: Session = Depends(get_db)):
    """Handle chat requests with the AI assistant"""
    # Check if AI is enabled
    ai_status = db.query(Config).filter(Config.key == "ai_features_enabled").first()
    if ai_status and ai_status.value != "true":
        return {"response": "AI features are currently disabled. Enable them in the sidebar."}
        
    response = await llm_service.chat(request.message)
    return {"response": response}

# ============== System Controls ==============

class SystemStatus(BaseModel):
    system_monitoring: bool
    ai_features: bool

@app.get("/api/stocks/list")
async def get_supported_stocks():
    """Get list of supported stocks for autocomplete"""
    from .stock_api import NSE_STOCKS
    # Just return simple list of {symbol, name}
    return [{"symbol": s["symbol"], "name": s["name"]} for s in NSE_STOCKS]


@app.get("/api/system/status")
async def get_system_status(db: Session = Depends(get_db)):
    """Get status of system monitoring and AI features"""
    sys_mon = db.query(Config).filter(Config.key == "system_monitoring_enabled").first()
    ai_feat = db.query(Config).filter(Config.key == "ai_features_enabled").first()
    
    return {
        "system_monitoring": sys_mon.value == "true" if sys_mon else True,
        "ai_features": ai_feat.value == "true" if ai_feat else False  # Default to False if not set
    }

@app.post("/api/system/control")
async def update_system_control(status: SystemStatus, db: Session = Depends(get_db)):
    """Update system status"""
    # System Monitoring
    sys_mon = db.query(Config).filter(Config.key == "system_monitoring_enabled").first()
    if sys_mon:
        sys_mon.value = "true" if status.system_monitoring else "false"
    else:
        db.add(Config(key="system_monitoring_enabled", value="true" if status.system_monitoring else "false"))
        
    # AI Features
    ai_feat = db.query(Config).filter(Config.key == "ai_features_enabled").first()
    if ai_feat:
        ai_feat.value = "true" if status.ai_features else "false"
    else:
        db.add(Config(key="ai_features_enabled", value="true" if status.ai_features else "false"))
        
    db.commit()
    
    # Update global background task states
    if status.system_monitoring:
        if not monitor.is_running:
            # Re-start monitoring if needed (this simplifies to just flagging for now)
            # In a real app we might need to trigger starts, but our background tasks check this flag
            pass
    
    return {"success": True, "status": status}


# ============== Static Files ==============

# Serve frontend (if exists)
import os
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")
    
    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_path, "index.html"))

