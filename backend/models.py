from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, Float, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base


class Config(Base):
    """Configuration key-value store for app settings"""
    __tablename__ = "configs"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    value = Column(String)
    json_value = Column(JSON, nullable=True)


class Stock(Base):
    """Stock metadata reference"""
    __tablename__ = "stocks"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    sector = Column(String, nullable=True)
    cap_type = Column(String, nullable=True)  # Large, Mid, Small, Penny
    is_active = Column(Boolean, default=True)


class Source(Base):
    """Telegram channels to monitor for stock signals"""
    __tablename__ = "sources"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    channel_id = Column(String, unique=True, index=True)
    channel_username = Column(String, nullable=True)
    active = Column(Boolean, default=True)
    last_fetched = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TelegramMessage(Base):
    """Messages captured from Telegram channels"""
    __tablename__ = "telegram_messages"
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, nullable=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True)
    channel_id = Column(String, index=True)
    channel_name = Column(String, nullable=True)
    text = Column(Text, nullable=True)
    urls = Column(JSON, nullable=True)
    extracted_stocks = Column(JSON, nullable=True)  # Stock symbols mentioned
    sentiment = Column(String, nullable=True)  # positive/negative/neutral
    processed = Column(Boolean, default=False)
    message_date = Column(DateTime(timezone=True), nullable=True)  # Original message time
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MarketNews(Base):
    """News articles fetched from RSS feeds"""
    __tablename__ = "market_news"
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False)  # economictimes, moneycontrol, nse
    title = Column(String, nullable=False)
    link = Column(String, unique=True, index=True)
    summary = Column(Text, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    extracted_stocks = Column(JSON, nullable=True)
    sentiment = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class StockPrice(Base):
    """Historical stock price data"""
    __tablename__ = "stock_prices"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    name = Column(String, nullable=True)
    exchange = Column(String, default="NSE")  # NSE or BSE
    open_price = Column(Float, nullable=True)
    high_price = Column(Float, nullable=True)
    low_price = Column(Float, nullable=True)
    close_price = Column(Float, nullable=True)
    volume = Column(Integer, nullable=True)
    change_percent = Column(Float, nullable=True)
    date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Analysis(Base):
    """Analysis results for a time period"""
    __tablename__ = "analyses"
    id = Column(Integer, primary_key=True, index=True)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    messages_analyzed = Column(Integer, default=0)
    news_analyzed = Column(Integer, default=0)
    stocks_mentioned = Column(JSON, nullable=True)  # List of stock symbols
    overall_sentiment = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Recommendation(Base):
    """Stock recommendations for different timeframes"""
    __tablename__ = "recommendations"
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=True)
    symbol = Column(String, nullable=False)
    name = Column(String, nullable=True)
    timeframe = Column(String, nullable=False)  # next_day, next_week, next_month, 1yr, 2yr, 5yr, 10yr
    action = Column(String, nullable=False)  # BUY, SELL, HOLD
    confidence = Column(Float, nullable=True)  # 0-100 confidence score
    current_price = Column(Float, nullable=True)
    target_price = Column(Float, nullable=True)
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Log(Base):
    """System logs"""
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String)
    message = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class FetchLog(Base):
    """Logs for source fetch operations"""
    __tablename__ = "fetch_logs"
    id = Column(Integer, primary_key=True, index=True)
    source_name = Column(String, nullable=True)
    source_type = Column(String, default="telegram")  # telegram, rss, api
    items_fetched = Column(Integer, default=0)
    status = Column(String, default="success")
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class WatchlistStock(Base):
    """User's watchlist of stocks to monitor"""
    __tablename__ = "watchlist_stocks"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    sector = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    current_price = Column(Float, nullable=True)
    target_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class AllStarPick(Base):
    """Daily All Star stock picks - refreshes at 3:30 PM IST next day"""
    __tablename__ = "allstar_picks"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, nullable=False)
    name = Column(String, nullable=True)
    category = Column(String, nullable=True)  # Large Cap, Mid Cap, Small Cap, Penny Stock
    action = Column(String, nullable=False)  # BUY, SELL, HOLD
    confidence = Column(Float, default=0)
    reasoning = Column(Text, nullable=True)
    current_price = Column(Float, nullable=True)
    target_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    news_count = Column(Integer, default=0)  # Number of news mentions
    sentiment_score = Column(Float, nullable=True)  # Combined sentiment
    valid_until = Column(DateTime(timezone=True), nullable=False)  # Expires at 3:30 PM IST next day
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# Sector classification for Indian stocks
SECTOR_MAPPING = {
    # IT
    'TCS': ('IT', 'Software Services'), 'INFY': ('IT', 'Software Services'),
    'WIPRO': ('IT', 'Software Services'), 'HCLTECH': ('IT', 'Software Services'),
    'TECHM': ('IT', 'Software Services'), 'LTIM': ('IT', 'Software Services'),
    # Banking
    'HDFCBANK': ('Banking', 'Private Banks'), 'ICICIBANK': ('Banking', 'Private Banks'),
    'KOTAKBANK': ('Banking', 'Private Banks'), 'AXISBANK': ('Banking', 'Private Banks'),
    'SBIN': ('Banking', 'Public Banks'), 'INDUSINDBK': ('Banking', 'Private Banks'),
    # Auto
    'MARUTI': ('Auto', 'Passenger Vehicles'), 'TATAMOTORS': ('Auto', 'Commercial Vehicles'),
    'M&M': ('Auto', 'Passenger Vehicles'), 'BAJAJ-AUTO': ('Auto', 'Two Wheelers'),
    'HEROMOTOCO': ('Auto', 'Two Wheelers'), 'EICHERMOT': ('Auto', 'Two Wheelers'),
    # Pharma
    'SUNPHARMA': ('Pharma', 'Pharmaceuticals'), 'DRREDDY': ('Pharma', 'Pharmaceuticals'),
    'CIPLA': ('Pharma', 'Pharmaceuticals'), 'DIVISLAB': ('Pharma', 'Pharmaceuticals'),
    'APOLLOHOSP': ('Pharma', 'Healthcare'),
    # FMCG
    'HINDUNILVR': ('FMCG', 'Personal Care'), 'ITC': ('FMCG', 'Tobacco & FMCG'),
    'NESTLEIND': ('FMCG', 'Food Products'), 'BRITANNIA': ('FMCG', 'Food Products'),
    'TATACONSUM': ('FMCG', 'Beverages'),
    # Energy & Power
    'RELIANCE': ('Energy', 'Oil & Gas'), 'ONGC': ('Energy', 'Oil & Gas'),
    'BPCL': ('Energy', 'Oil & Gas'), 'POWERGRID': ('Power', 'Power Transmission'),
    'NTPC': ('Power', 'Power Generation'), 'COALINDIA': ('Energy', 'Mining'),
    'ADANIENT': ('Energy', 'Diversified'),
    # Metals
    'TATASTEEL': ('Metals', 'Steel'), 'JSWSTEEL': ('Metals', 'Steel'),
    'HINDALCO': ('Metals', 'Aluminium'),
    # Finance
    'BAJFINANCE': ('Finance', 'NBFC'), 'BAJAJFINSV': ('Finance', 'NBFC'),
    'SBILIFE': ('Finance', 'Insurance'), 'HDFCLIFE': ('Finance', 'Insurance'),
    # Infrastructure
    'LT': ('Infrastructure', 'Construction'), 'ULTRACEMCO': ('Infrastructure', 'Cement'),
    'GRASIM': ('Infrastructure', 'Cement'), 'ADANIPORTS': ('Infrastructure', 'Ports'),
    # Others
    'ASIANPAINT': ('Consumer', 'Paints'), 'TITAN': ('Consumer', 'Jewellery'),
    'BHARTIARTL': ('Telecom', 'Telecom Services'), 'UPL': ('Chemicals', 'Agrochemicals'),
}

