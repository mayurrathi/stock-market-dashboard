"""
IndiQuant - QVM (Quality-Valuation-Momentum) Engine
Inspired by Trendlyne's composite scoring system

Provides:
- Quality Score (ROE, Debt/Equity based)
- Valuation Score (P/E vs historical average)
- Momentum Score (Price vs 200 DMA, RSI)
- Composite Investability Score
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


def fetch_fundamentals(symbol: str) -> Dict:
    """
    Fetch fundamental data from Yahoo Finance.
    Returns P/E, P/B, ROE, Debt/Equity, and other key metrics.
    """
    if not symbol.endswith('.NS') and not symbol.endswith('.BO'):
        symbol = f"{symbol}.NS"
    
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        return {
            "pe_ratio": info.get("trailingPE", 0) or info.get("forwardPE", 0) or 0,
            "pb_ratio": info.get("priceToBook", 0) or 0,
            "roe": (info.get("returnOnEquity", 0) or 0) * 100,  # Convert to percentage
            "debt_to_equity": info.get("debtToEquity", 0) or 0,
            "current_price": info.get("currentPrice", 0) or info.get("regularMarketPrice", 0) or 0,
            "dividend_yield": (info.get("dividendYield", 0) or 0) * 100,
            "market_cap": info.get("marketCap", 0) or 0,
            "52w_high": info.get("fiftyTwoWeekHigh", 0) or 0,
            "52w_low": info.get("fiftyTwoWeekLow", 0) or 0,
            "revenue_growth": (info.get("revenueGrowth", 0) or 0) * 100,
            "profit_margin": (info.get("profitMargins", 0) or 0) * 100,
            "name": info.get("shortName", symbol),
            "sector": info.get("sector", "Unknown"),
            "industry": info.get("industry", "Unknown")
        }
    except Exception as e:
        logger.error(f"Failed to fetch fundamentals for {symbol}: {e}")
        return {}


def calculate_quality_score(roe: float, debt_to_equity: float, profit_margin: float = 0) -> Dict:
    """
    Calculate Quality Score (0-10).
    
    Scoring Logic:
    - ROE > 20%: +4 points, > 15%: +3 points, > 10%: +2 points
    - D/E < 0.5: +3 points, < 1: +2 points, < 1.5: +1 point
    - Profit Margin > 20%: +3 points, > 10%: +2 points, > 5%: +1 point
    """
    score = 0
    breakdown = []
    
    # ROE scoring (max 4 points)
    if roe > 20:
        score += 4
        breakdown.append(f"Excellent ROE ({roe:.1f}%): +4")
    elif roe > 15:
        score += 3
        breakdown.append(f"Good ROE ({roe:.1f}%): +3")
    elif roe > 10:
        score += 2
        breakdown.append(f"Moderate ROE ({roe:.1f}%): +2")
    elif roe > 5:
        score += 1
        breakdown.append(f"Low ROE ({roe:.1f}%): +1")
    else:
        breakdown.append(f"Poor ROE ({roe:.1f}%): +0")
    
    # Debt/Equity scoring (max 3 points)
    if debt_to_equity < 0.5:
        score += 3
        breakdown.append(f"Low Debt ({debt_to_equity:.2f}x): +3")
    elif debt_to_equity < 1:
        score += 2
        breakdown.append(f"Moderate Debt ({debt_to_equity:.2f}x): +2")
    elif debt_to_equity < 1.5:
        score += 1
        breakdown.append(f"High Debt ({debt_to_equity:.2f}x): +1")
    else:
        breakdown.append(f"Very High Debt ({debt_to_equity:.2f}x): +0")
    
    # Profit Margin scoring (max 3 points)
    if profit_margin > 20:
        score += 3
        breakdown.append(f"High Margins ({profit_margin:.1f}%): +3")
    elif profit_margin > 10:
        score += 2
        breakdown.append(f"Good Margins ({profit_margin:.1f}%): +2")
    elif profit_margin > 5:
        score += 1
        breakdown.append(f"Thin Margins ({profit_margin:.1f}%): +1")
    else:
        breakdown.append(f"Low/Negative Margins ({profit_margin:.1f}%): +0")
    
    # Rating
    if score >= 8:
        rating = "Excellent"
    elif score >= 6:
        rating = "Good"
    elif score >= 4:
        rating = "Average"
    else:
        rating = "Poor"
    
    return {
        "score": score,
        "max_score": 10,
        "rating": rating,
        "breakdown": breakdown
    }


def calculate_valuation_score(pe_ratio: float, pb_ratio: float, sector: str = "Unknown") -> Dict:
    """
    Calculate Valuation Score (0-10).
    
    Scoring Logic (sector-adjusted):
    - P/E below sector average: Higher score
    - P/B below 2: Higher score
    """
    score = 0
    breakdown = []
    
    # Sector P/E benchmarks (simplified)
    sector_pe = {
        "Technology": 30,
        "Financial Services": 15,
        "Healthcare": 25,
        "Consumer Cyclical": 20,
        "Industrials": 18,
        "Energy": 12,
        "Basic Materials": 15,
        "Default": 20
    }
    
    benchmark_pe = sector_pe.get(sector, sector_pe["Default"])
    
    # P/E scoring (max 5 points)
    if pe_ratio <= 0:
        breakdown.append("Loss-making/No P/E: +0")
    elif pe_ratio < benchmark_pe * 0.5:
        score += 5
        breakdown.append(f"Deep Value P/E ({pe_ratio:.1f}x vs {benchmark_pe}x avg): +5")
    elif pe_ratio < benchmark_pe * 0.75:
        score += 4
        breakdown.append(f"Undervalued P/E ({pe_ratio:.1f}x vs {benchmark_pe}x avg): +4")
    elif pe_ratio < benchmark_pe:
        score += 3
        breakdown.append(f"Fair Value P/E ({pe_ratio:.1f}x vs {benchmark_pe}x avg): +3")
    elif pe_ratio < benchmark_pe * 1.25:
        score += 2
        breakdown.append(f"Slightly Overvalued P/E ({pe_ratio:.1f}x vs {benchmark_pe}x avg): +2")
    elif pe_ratio < benchmark_pe * 1.5:
        score += 1
        breakdown.append(f"Overvalued P/E ({pe_ratio:.1f}x vs {benchmark_pe}x avg): +1")
    else:
        breakdown.append(f"Expensive P/E ({pe_ratio:.1f}x vs {benchmark_pe}x avg): +0")
    
    # P/B scoring (max 5 points)
    if pb_ratio <= 0:
        breakdown.append("No P/B data: +0")
    elif pb_ratio < 1:
        score += 5
        breakdown.append(f"Below Book Value ({pb_ratio:.2f}x): +5")
    elif pb_ratio < 2:
        score += 4
        breakdown.append(f"Low P/B ({pb_ratio:.2f}x): +4")
    elif pb_ratio < 3:
        score += 3
        breakdown.append(f"Moderate P/B ({pb_ratio:.2f}x): +3")
    elif pb_ratio < 5:
        score += 2
        breakdown.append(f"High P/B ({pb_ratio:.2f}x): +2")
    else:
        breakdown.append(f"Very High P/B ({pb_ratio:.2f}x): +0")
    
    # Rating
    if score >= 8:
        rating = "Deep Value"
    elif score >= 6:
        rating = "Undervalued"
    elif score >= 4:
        rating = "Fair Value"
    else:
        rating = "Overvalued"
    
    return {
        "score": score,
        "max_score": 10,
        "rating": rating,
        "breakdown": breakdown,
        "sector_pe_benchmark": benchmark_pe
    }


def calculate_momentum_score(symbol: str) -> Dict:
    """
    Calculate Momentum Score (0-10).
    
    Scoring Logic:
    - Price > 200 DMA: +3 points
    - Price > 50 DMA: +2 points
    - RSI between 50-70: +3 points (healthy momentum)
    - Near 52-week high: +2 points
    """
    if not symbol.endswith('.NS') and not symbol.endswith('.BO'):
        symbol = f"{symbol}.NS"
    
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1y")
        
        if df.empty or len(df) < 200:
            return {"score": 0, "max_score": 10, "rating": "Insufficient Data", "breakdown": []}
        
        close = df['Close']
        current_price = close.iloc[-1]
        
        # Calculate indicators
        sma_50 = close.rolling(window=50).mean().iloc[-1]
        sma_200 = close.rolling(window=200).mean().iloc[-1]
        high_52w = close.max()
        low_52w = close.min()
        
        # RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]
        
        score = 0
        breakdown = []
        
        # Price vs 200 DMA (max 3 points)
        if current_price > sma_200:
            score += 3
            pct_above = ((current_price / sma_200) - 1) * 100
            breakdown.append(f"Above 200 DMA ({pct_above:+.1f}%): +3")
        else:
            pct_below = ((current_price / sma_200) - 1) * 100
            breakdown.append(f"Below 200 DMA ({pct_below:.1f}%): +0")
        
        # Price vs 50 DMA (max 2 points)
        if current_price > sma_50:
            score += 2
            breakdown.append(f"Above 50 DMA: +2")
        else:
            breakdown.append(f"Below 50 DMA: +0")
        
        # RSI scoring (max 3 points)
        if 50 <= current_rsi <= 70:
            score += 3
            breakdown.append(f"Healthy RSI ({current_rsi:.0f}): +3")
        elif 40 <= current_rsi < 50:
            score += 2
            breakdown.append(f"Neutral RSI ({current_rsi:.0f}): +2")
        elif current_rsi > 70:
            score += 1
            breakdown.append(f"Overbought RSI ({current_rsi:.0f}): +1")
        else:
            breakdown.append(f"Weak RSI ({current_rsi:.0f}): +0")
        
        # 52-week position (max 2 points)
        range_52w = high_52w - low_52w
        position = (current_price - low_52w) / range_52w if range_52w > 0 else 0
        
        if position >= 0.8:
            score += 2
            breakdown.append(f"Near 52W High ({position*100:.0f}% of range): +2")
        elif position >= 0.5:
            score += 1
            breakdown.append(f"Mid 52W Range ({position*100:.0f}% of range): +1")
        else:
            breakdown.append(f"Near 52W Low ({position*100:.0f}% of range): +0")
        
        # Rating
        if score >= 8:
            rating = "Strong Uptrend"
        elif score >= 6:
            rating = "Bullish"
        elif score >= 4:
            rating = "Neutral"
        else:
            rating = "Bearish"
        
        return {
            "score": score,
            "max_score": 10,
            "rating": rating,
            "breakdown": breakdown,
            "current_rsi": round(current_rsi, 1),
            "sma_50": round(sma_50, 2),
            "sma_200": round(sma_200, 2),
            "52w_position": round(position * 100, 1)
        }
        
    except Exception as e:
        logger.error(f"Failed to calculate momentum for {symbol}: {e}")
        return {"score": 0, "max_score": 10, "rating": "Error", "breakdown": [str(e)]}


def calculate_investability_score(quality: Dict, valuation: Dict, momentum: Dict) -> Dict:
    """
    Calculate composite Investability Score (0-100).
    
    Weights:
    - Quality: 40%
    - Valuation: 35%
    - Momentum: 25%
    """
    q_score = quality.get("score", 0)
    v_score = valuation.get("score", 0)
    m_score = momentum.get("score", 0)
    
    # Normalize to 100 and apply weights
    q_weighted = (q_score / 10) * 40
    v_weighted = (v_score / 10) * 35
    m_weighted = (m_score / 10) * 25
    
    total = q_weighted + v_weighted + m_weighted
    
    # Rating
    if total >= 80:
        rating = "Excellent"
        recommendation = "Strong Buy"
    elif total >= 65:
        rating = "Good"
        recommendation = "Buy"
    elif total >= 50:
        rating = "Average"
        recommendation = "Hold"
    elif total >= 35:
        rating = "Below Average"
        recommendation = "Reduce"
    else:
        rating = "Poor"
        recommendation = "Avoid"
    
    return {
        "score": round(total, 1),
        "max_score": 100,
        "rating": rating,
        "recommendation": recommendation,
        "components": {
            "quality": {"score": q_score, "weight": 40, "weighted": round(q_weighted, 1)},
            "valuation": {"score": v_score, "weight": 35, "weighted": round(v_weighted, 1)},
            "momentum": {"score": m_score, "weight": 25, "weighted": round(m_weighted, 1)}
        }
    }


def analyze_qvm(symbol: str) -> Dict:
    """
    Complete QVM analysis for a stock.
    Returns Quality, Valuation, Momentum scores and composite Investability Score.
    """
    # Fetch fundamentals
    fundamentals = fetch_fundamentals(symbol)
    
    if not fundamentals:
        return {"error": f"No data available for {symbol}"}
    
    # Calculate individual scores
    quality = calculate_quality_score(
        roe=fundamentals.get("roe", 0),
        debt_to_equity=fundamentals.get("debt_to_equity", 0),
        profit_margin=fundamentals.get("profit_margin", 0)
    )
    
    valuation = calculate_valuation_score(
        pe_ratio=fundamentals.get("pe_ratio", 0),
        pb_ratio=fundamentals.get("pb_ratio", 0),
        sector=fundamentals.get("sector", "Unknown")
    )
    
    momentum = calculate_momentum_score(symbol)
    
    # Calculate composite score
    investability = calculate_investability_score(quality, valuation, momentum)
    
    return {
        "symbol": symbol.replace('.NS', '').replace('.BO', ''),
        "name": fundamentals.get("name", symbol),
        "sector": fundamentals.get("sector", "Unknown"),
        "industry": fundamentals.get("industry", "Unknown"),
        "fundamentals": fundamentals,
        "quality": quality,
        "valuation": valuation,
        "momentum": momentum,
        "investability": investability,
        "radar_data": {
            "quality": quality["score"],
            "valuation": valuation["score"],
            "momentum": momentum["score"]
        },
        "summary": f"Investability Score: {investability['score']}/100 ({investability['recommendation']})"
    }
