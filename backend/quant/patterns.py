"""
IndiQuant - Pattern Scout Module
Inspired by StockEdge technical pattern recognition

Provides:
- Relative Strength (RS) calculation vs NIFTY 50
- Momentum indicators (RSI, MACD)
- Pattern detection (Consolidation Breakout, Golden Cross)
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def fetch_stock_data(symbol: str, period: str = "1y") -> pd.DataFrame:
    """
    Fetch OHLCV data for a stock from Yahoo Finance.
    For Indian stocks, appends .NS suffix if not present.
    """
    if not symbol.endswith('.NS') and not symbol.endswith('.BO'):
        symbol = f"{symbol}.NS"
    
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)
        df.index = pd.to_datetime(df.index)
        return df
    except Exception as e:
        logger.error(f"Failed to fetch data for {symbol}: {e}")
        return pd.DataFrame()


def calculate_relative_strength(symbol: str, benchmark: str = "^NSEI", period: int = 50) -> Dict:
    """
    Calculate Relative Strength (RS) of a stock vs NIFTY 50.
    RS = (Stock Return / Benchmark Return) * 100
    
    Values > 100 indicate outperformance vs benchmark.
    """
    stock_df = fetch_stock_data(symbol, "6mo")
    bench_df = fetch_stock_data(benchmark, "6mo")
    
    if stock_df.empty or bench_df.empty:
        return {"rs_value": 0, "rs_rating": "N/A", "interpretation": "Data unavailable"}
    
    # Calculate returns over the period
    stock_return = (stock_df['Close'].iloc[-1] / stock_df['Close'].iloc[-period] - 1) * 100
    bench_return = (bench_df['Close'].iloc[-1] / bench_df['Close'].iloc[-period] - 1) * 100
    
    # RS calculation
    if bench_return != 0:
        rs_value = (stock_return / bench_return) * 100 if bench_return > 0 else 100 + (stock_return - bench_return)
    else:
        rs_value = 100 + stock_return
    
    # Rating based on RS
    if rs_value > 120:
        rating = "Strong Outperformer"
    elif rs_value > 100:
        rating = "Outperformer"
    elif rs_value > 80:
        rating = "Market Performer"
    else:
        rating = "Underperformer"
    
    return {
        "rs_value": round(rs_value, 2),
        "rs_rating": rating,
        "stock_return": round(stock_return, 2),
        "benchmark_return": round(bench_return, 2),
        "period_days": period,
        "interpretation": f"Stock returned {stock_return:.1f}% vs NIFTY's {bench_return:.1f}% over {period} days"
    }


def calculate_momentum_indicators(df: pd.DataFrame) -> Dict:
    """
    Calculate RSI (14) and MACD momentum indicators.
    """
    if df.empty or len(df) < 30:
        return {"rsi": 0, "macd": 0, "macd_signal": 0, "macd_histogram": 0}
    
    close = df['Close']
    
    # RSI Calculation (14-period)
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # MACD Calculation (12, 26, 9)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    histogram = macd - signal
    
    current_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
    current_macd = macd.iloc[-1] if not pd.isna(macd.iloc[-1]) else 0
    current_signal = signal.iloc[-1] if not pd.isna(signal.iloc[-1]) else 0
    
    # Interpretation
    rsi_zone = "Overbought" if current_rsi > 70 else ("Oversold" if current_rsi < 30 else "Neutral")
    macd_trend = "Bullish" if current_macd > current_signal else "Bearish"
    
    return {
        "rsi": round(current_rsi, 2),
        "rsi_zone": rsi_zone,
        "macd": round(current_macd, 4),
        "macd_signal": round(current_signal, 4),
        "macd_histogram": round(histogram.iloc[-1], 4) if not pd.isna(histogram.iloc[-1]) else 0,
        "macd_trend": macd_trend,
        "interpretation": f"RSI at {current_rsi:.0f} ({rsi_zone}), MACD is {macd_trend}"
    }


def detect_patterns(df: pd.DataFrame) -> List[Dict]:
    """
    Detect technical patterns in price data.
    
    Patterns detected:
    1. Consolidation Breakout: Narrow range for 10 days followed by volume spike
    2. Golden Cross: 50 SMA crosses above 200 SMA
    3. Death Cross: 50 SMA crosses below 200 SMA
    """
    patterns = []
    
    if df.empty or len(df) < 200:
        return patterns
    
    close = df['Close']
    high = df['High']
    low = df['Low']
    volume = df['Volume']
    
    # Calculate SMAs
    sma_50 = close.rolling(window=50).mean()
    sma_200 = close.rolling(window=200).mean()
    avg_volume = volume.rolling(window=20).mean()
    
    # 1. Consolidation Breakout Detection
    # Check if last 10 days had narrow range (< 5% of price)
    recent_high = high.iloc[-10:].max()
    recent_low = low.iloc[-10:].min()
    recent_range = (recent_high - recent_low) / recent_low * 100
    current_volume = volume.iloc[-1]
    avg_vol = avg_volume.iloc[-2] if not pd.isna(avg_volume.iloc[-2]) else volume.mean()
    
    if recent_range < 5 and current_volume > 2 * avg_vol:
        patterns.append({
            "pattern": "Consolidation Breakout",
            "type": "bullish",
            "reliability": "High",
            "date": df.index[-1].strftime("%Y-%m-%d"),
            "description": f"Price consolidated within {recent_range:.1f}% range with {current_volume/avg_vol:.1f}x volume spike",
            "action": "Potential breakout - watch for confirmation above recent high"
        })
    
    # 2. Golden Cross Detection (50 SMA crosses above 200 SMA)
    if len(sma_50) >= 5 and len(sma_200) >= 5:
        # Check last 5 days for crossover
        for i in range(-5, 0):
            if (sma_50.iloc[i-1] < sma_200.iloc[i-1] and 
                sma_50.iloc[i] > sma_200.iloc[i]):
                patterns.append({
                    "pattern": "Golden Cross",
                    "type": "bullish",
                    "reliability": "High",
                    "date": df.index[i].strftime("%Y-%m-%d"),
                    "description": "50-day SMA crossed above 200-day SMA",
                    "action": "Strong bullish signal - consider long positions"
                })
                break
    
    # 3. Death Cross Detection (50 SMA crosses below 200 SMA)
    if len(sma_50) >= 5 and len(sma_200) >= 5:
        for i in range(-5, 0):
            if (sma_50.iloc[i-1] > sma_200.iloc[i-1] and 
                sma_50.iloc[i] < sma_200.iloc[i]):
                patterns.append({
                    "pattern": "Death Cross",
                    "type": "bearish",
                    "reliability": "High",
                    "date": df.index[i].strftime("%Y-%m-%d"),
                    "description": "50-day SMA crossed below 200-day SMA",
                    "action": "Strong bearish signal - consider reducing exposure"
                })
                break
    
    # 4. RSI Divergence (simplified)
    # If price making new high but RSI not making new high
    if len(close) >= 20:
        price_high_20 = close.iloc[-20:].max()
        current_price = close.iloc[-1]
        
        # Calculate RSI for comparison
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        rsi_at_high = rsi.iloc[close.iloc[-20:].argmax() - len(close)]
        current_rsi = rsi.iloc[-1]
        
        if current_price >= price_high_20 * 0.99 and current_rsi < rsi_at_high - 10:
            patterns.append({
                "pattern": "Bearish RSI Divergence",
                "type": "bearish",
                "reliability": "Medium",
                "date": df.index[-1].strftime("%Y-%m-%d"),
                "description": "Price at highs but RSI declining - potential weakness",
                "action": "Watch for reversal signals"
            })
    
    return patterns


def generate_chart_data(symbol: str) -> Dict:
    """
    Generate chart data with price, SMAs, and detected patterns for Plotly visualization.
    """
    df = fetch_stock_data(symbol, "1y")
    
    if df.empty:
        return {"error": "No data available"}
    
    close = df['Close']
    sma_50 = close.rolling(window=50).mean()
    sma_200 = close.rolling(window=200).mean()
    
    # Prepare data for frontend chart
    dates = [d.strftime("%Y-%m-%d") for d in df.index]
    
    return {
        "dates": dates,
        "ohlc": {
            "open": df['Open'].tolist(),
            "high": df['High'].tolist(),
            "low": df['Low'].tolist(),
            "close": df['Close'].tolist(),
        },
        "volume": df['Volume'].tolist(),
        "sma_50": [None if pd.isna(v) else round(v, 2) for v in sma_50.tolist()],
        "sma_200": [None if pd.isna(v) else round(v, 2) for v in sma_200.tolist()],
        "current_price": round(close.iloc[-1], 2),
        "price_change": round(close.iloc[-1] - close.iloc[-2], 2) if len(close) > 1 else 0,
        "price_change_pct": round((close.iloc[-1] / close.iloc[-2] - 1) * 100, 2) if len(close) > 1 else 0
    }


def analyze_stock_patterns(symbol: str) -> Dict:
    """
    Complete pattern analysis for a stock.
    Returns RS, momentum indicators, detected patterns, and chart data.
    """
    df = fetch_stock_data(symbol, "1y")
    
    if df.empty:
        return {"error": f"No data available for {symbol}"}
    
    rs = calculate_relative_strength(symbol)
    momentum = calculate_momentum_indicators(df)
    patterns = detect_patterns(df)
    chart_data = generate_chart_data(symbol)
    
    # Overall signal based on analysis
    bullish_signals = sum(1 for p in patterns if p['type'] == 'bullish')
    bearish_signals = sum(1 for p in patterns if p['type'] == 'bearish')
    
    if momentum['rsi'] > 50 and rs['rs_value'] > 100:
        overall = "Bullish"
    elif momentum['rsi'] < 50 and rs['rs_value'] < 100:
        overall = "Bearish"
    else:
        overall = "Neutral"
    
    if bullish_signals > bearish_signals:
        overall = "Bullish"
    elif bearish_signals > bullish_signals:
        overall = "Bearish"
    
    return {
        "symbol": symbol.replace('.NS', '').replace('.BO', ''),
        "relative_strength": rs,
        "momentum": momentum,
        "patterns": patterns,
        "chart_data": chart_data,
        "overall_signal": overall,
        "summary": f"{len(patterns)} pattern(s) detected. RS: {rs['rs_rating']}. Momentum: {momentum['macd_trend']}."
    }
