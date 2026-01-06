
"""
Technical Analysis Module
Calculates indicators (RSI, MACD, MA) and detects chart patterns.
"""
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

class TechnicalAnalyzer:
    def _calculate_rsi(self, prices, period=14):
        """Calculate Relative Strength Index"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_macd(self, prices, fast=12, slow=26, signal=9):
        """Calculate MACD"""
        exp1 = prices.ewm(span=fast, adjust=False).mean()
        exp2 = prices.ewm(span=slow, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        return macd, signal_line

    def analyze(self, history_data: dict) -> dict:
        """
        Analyze stock history and return technical indicators and patterns.
        """
        if not history_data or not history_data.get('close'):
            return {}

        try:
            df = pd.DataFrame({
                'close': history_data['close'],
                'high': history_data['high'],
                'low': history_data['low'],
                'volume': history_data['volume']
            })
            
            # Ensure numeric
            df = df.apply(pd.to_numeric, errors='coerce').dropna()
            
            if len(df) < 50:
                return {}

            # Calculate Indicators
            df['rsi'] = self._calculate_rsi(df['close'])
            df['macd'], df['macd_signal'] = self._calculate_macd(df['close'])
            df['sma_50'] = df['close'].rolling(window=50).mean()
            df['sma_200'] = df['close'].rolling(window=200).mean()
            
            # Latest values
            current_price = df['close'].iloc[-1]
            rsi = df['rsi'].iloc[-1]
            macd = df['macd'].iloc[-1]
            macd_signal = df['macd_signal'].iloc[-1]
            sma_50 = df['sma_50'].iloc[-1]
            sma_200 = df['sma_200'].iloc[-1]
            
            # Pattern Detection
            patterns = []
            
            # 1. RSI Overbought/Oversold
            if rsi > 70:
                patterns.append("RSI Overbought (Bearish)")
            elif rsi < 30:
                patterns.append("RSI Oversold (Bullish)")
                
            # 2. MACD Crossover
            prev_macd = df['macd'].iloc[-2]
            prev_signal = df['macd_signal'].iloc[-2]
            if prev_macd < prev_signal and macd > macd_signal:
                patterns.append("MACD Bullish Crossover")
            elif prev_macd > prev_signal and macd < macd_signal:
                patterns.append("MACD Bearish Crossover")
                
            # 3. Golden/Death Cross
            if sma_50 > sma_200:
                if df['sma_50'].iloc[-2] <= df['sma_200'].iloc[-2]:
                    patterns.append("Golden Cross (Bullish)")
            elif sma_50 < sma_200:
                 if df['sma_50'].iloc[-2] >= df['sma_200'].iloc[-2]:
                    patterns.append("Death Cross (Bearish)")
                    
            # 4. 52-Week High Breakout (Proxy using available data max)
            period_high = df['high'].max()
            if current_price >= period_high * 0.98: # Near high
                patterns.append("Near 52-Week High")
                if current_price > df['high'].iloc[:-1].max():
                    patterns.append("Breakout Attempt")

            return {
                "rsi": round(rsi, 2),
                "macd": "Bullish" if macd > macd_signal else "Bearish",
                "trend": "Uptrend" if current_price > sma_50 else "Downtrend",
                "patterns": patterns,
                "support": round(df['low'].tail(20).min(), 2),
                "resistance": round(df['high'].tail(20).max(), 2)
            }

        except Exception as e:
            logger.error(f"Technical analysis failed: {e}")
            return {}

technical_analyzer = TechnicalAnalyzer()
