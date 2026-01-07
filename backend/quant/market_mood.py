"""
IndiQuant - Market Mood Sensor
Inspired by Tickertape's Market Mood Index (MMI)

Provides:
- India VIX-based fear/greed analysis
- NIFTY 50 momentum calculation
- Fear & Greed Index gauge
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def get_india_vix() -> Dict:
    """
    Fetch India VIX (Volatility Index) data.
    VIX measures market fear/volatility expectations.
    
    Interpretation:
    - VIX < 12: Low volatility, complacency (Greed zone)
    - VIX 12-18: Normal volatility
    - VIX 18-25: Elevated volatility (Fear building)
    - VIX > 25: High volatility, panic (Fear zone)
    """
    try:
        # India VIX ticker
        vix = yf.Ticker("^INDIAVIX")
        hist = vix.history(period="1mo")
        
        if hist.empty:
            # Fallback: Try alternate ticker
            vix = yf.Ticker("INDIAVIX.NS")
            hist = vix.history(period="1mo")
        
        if hist.empty:
            return {
                "current": 15.0,  # Default neutral value
                "change": 0,
                "zone": "Neutral",
                "available": False
            }
        
        current_vix = hist['Close'].iloc[-1]
        prev_vix = hist['Close'].iloc[-2] if len(hist) > 1 else current_vix
        change = current_vix - prev_vix
        change_pct = (change / prev_vix) * 100 if prev_vix != 0 else 0
        
        # Historical context
        vix_20d_avg = hist['Close'].rolling(window=20).mean().iloc[-1]
        vix_percentile = (hist['Close'] <= current_vix).mean() * 100
        
        # Zone determination
        if current_vix < 12:
            zone = "Extreme Complacency"
        elif current_vix < 15:
            zone = "Low Volatility"
        elif current_vix < 18:
            zone = "Normal"
        elif current_vix < 22:
            zone = "Elevated"
        elif current_vix < 28:
            zone = "High Fear"
        else:
            zone = "Extreme Fear"
        
        return {
            "current": round(current_vix, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "avg_20d": round(vix_20d_avg, 2) if not pd.isna(vix_20d_avg) else current_vix,
            "percentile": round(vix_percentile, 1),
            "zone": zone,
            "available": True
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch India VIX: {e}")
        return {
            "current": 15.0,
            "change": 0,
            "zone": "Unknown",
            "available": False,
            "error": str(e)
        }


def get_nifty_momentum() -> Dict:
    """
    Calculate NIFTY 50 momentum indicators.
    
    Uses:
    - Rate of Change (ROC) - 14-day
    - Distance from 50/200 DMA
    - RSI
    """
    try:
        nifty = yf.Ticker("^NSEI")
        hist = nifty.history(period="1y")
        
        if hist.empty:
            return {
                "roc_14": 0,
                "above_50dma": False,
                "above_200dma": False,
                "rsi": 50,
                "trend": "Unknown",
                "available": False
            }
        
        close = hist['Close']
        current_price = close.iloc[-1]
        
        # Rate of Change (14-day)
        roc_14 = ((current_price / close.iloc[-14]) - 1) * 100 if len(close) >= 14 else 0
        
        # SMAs
        sma_50 = close.rolling(window=50).mean().iloc[-1] if len(close) >= 50 else current_price
        sma_200 = close.rolling(window=200).mean().iloc[-1] if len(close) >= 200 else current_price
        
        # RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
        
        # Trend determination
        above_50dma = current_price > sma_50
        above_200dma = current_price > sma_200
        
        if above_200dma and above_50dma and roc_14 > 0:
            trend = "Strong Uptrend"
        elif above_200dma and roc_14 > 0:
            trend = "Uptrend"
        elif above_200dma:
            trend = "Consolidating"
        elif not above_200dma and roc_14 < 0:
            trend = "Downtrend"
        else:
            trend = "Weak"
        
        return {
            "current_price": round(current_price, 2),
            "roc_14": round(roc_14, 2),
            "sma_50": round(sma_50, 2),
            "sma_200": round(sma_200, 2),
            "above_50dma": above_50dma,
            "above_200dma": above_200dma,
            "rsi": round(current_rsi, 1),
            "trend": trend,
            "available": True
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch NIFTY momentum: {e}")
        return {
            "roc_14": 0,
            "trend": "Unknown",
            "available": False,
            "error": str(e)
        }


def calculate_fear_greed_index() -> Dict:
    """
    Calculate the Fear & Greed Index (0-100).
    
    Components:
    1. VIX Level (40% weight)
    2. NIFTY Momentum (30% weight)
    3. Market Breadth approximation (30% weight)
    
    Scale:
    0-20: Extreme Fear
    20-40: Fear
    40-60: Neutral
    60-80: Greed
    80-100: Extreme Greed
    """
    vix_data = get_india_vix()
    momentum_data = get_nifty_momentum()
    
    # VIX Score (inverted - low VIX = greed)
    vix = vix_data.get("current", 15)
    if vix < 10:
        vix_score = 100
    elif vix < 12:
        vix_score = 85
    elif vix < 15:
        vix_score = 70
    elif vix < 18:
        vix_score = 55
    elif vix < 22:
        vix_score = 40
    elif vix < 28:
        vix_score = 25
    else:
        vix_score = 10
    
    # Momentum Score
    roc = momentum_data.get("roc_14", 0)
    rsi = momentum_data.get("rsi", 50)
    above_200dma = momentum_data.get("above_200dma", False)
    
    momentum_score = 50  # Base
    if roc > 5:
        momentum_score += 25
    elif roc > 2:
        momentum_score += 15
    elif roc > 0:
        momentum_score += 5
    elif roc > -2:
        momentum_score -= 5
    elif roc > -5:
        momentum_score -= 15
    else:
        momentum_score -= 25
    
    if rsi > 70:
        momentum_score += 15
    elif rsi > 60:
        momentum_score += 10
    elif rsi < 30:
        momentum_score -= 15
    elif rsi < 40:
        momentum_score -= 10
    
    if above_200dma:
        momentum_score += 10
    else:
        momentum_score -= 10
    
    momentum_score = max(0, min(100, momentum_score))
    
    # Market Breadth Score (approximated from NIFTY structure)
    # In absence of real breadth data, use trend + momentum combination
    breadth_score = 50
    if momentum_data.get("trend") in ["Strong Uptrend", "Uptrend"]:
        breadth_score = 70
    elif momentum_data.get("trend") == "Consolidating":
        breadth_score = 50
    elif momentum_data.get("trend") == "Downtrend":
        breadth_score = 30
    else:
        breadth_score = 40
    
    # Weighted composite
    composite = (vix_score * 0.40) + (momentum_score * 0.30) + (breadth_score * 0.30)
    
    # Zone determination
    if composite >= 80:
        zone = "Extreme Greed"
        interpretation = "Market is extremely greedy. Time for caution."
        action = "Consider taking profits, avoid FOMO buying"
    elif composite >= 60:
        zone = "Greed"
        interpretation = "Market sentiment is greedy."
        action = "Be selective with new positions"
    elif composite >= 40:
        zone = "Neutral"
        interpretation = "Market sentiment is balanced."
        action = "Normal market conditions"
    elif composite >= 20:
        zone = "Fear"
        interpretation = "Market sentiment is fearful."
        action = "Opportunities may emerge"
    else:
        zone = "Extreme Fear"
        interpretation = "Market is extremely fearful. Potential opportunity."
        action = "Consider accumulating quality stocks"
    
    return {
        "score": round(composite, 1),
        "zone": zone,
        "interpretation": interpretation,
        "action": action,
        "components": {
            "vix": {
                "value": vix,
                "score": vix_score,
                "weight": 40
            },
            "momentum": {
                "roc_14": momentum_data.get("roc_14", 0),
                "rsi": momentum_data.get("rsi", 50),
                "score": momentum_score,
                "weight": 30
            },
            "breadth": {
                "trend": momentum_data.get("trend", "Unknown"),
                "score": breadth_score,
                "weight": 30
            }
        },
        "vix_data": vix_data,
        "momentum_data": momentum_data
    }


def get_market_mood() -> Dict:
    """
    Get complete market mood analysis.
    """
    fear_greed = calculate_fear_greed_index()
    
    return {
        "fear_greed_index": fear_greed,
        "summary": f"Market Mood: {fear_greed['zone']} ({fear_greed['score']}/100)",
        "timestamp": datetime.now().isoformat()
    }
