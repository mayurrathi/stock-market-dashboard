"""
Robust Stock Recommendation Engine
Multi-factor analysis with technical indicators, fundamentals, sentiment, and risk assessment
"""
import logging
import math
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import random

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Comprehensive stock recommendation engine that analyzes multiple factors
    to generate actionable investment recommendations across different timeframes.
    """
    
    # Factor weights for composite score
    WEIGHTS = {
        'technical': 0.30,    # Technical analysis weight
        'fundamental': 0.35,  # Fundamentals weight
        'sentiment': 0.15,    # Market sentiment weight
        'risk': 0.20,         # Risk-adjusted weight
    }
    
    # Signal thresholds
    SIGNAL_THRESHOLDS = {
        'strong_buy': 80,
        'buy': 65,
        'hold': 45,
        'sell': 30,
        'avoid': 0,
    }
    
    # Indian market benchmarks
    BENCHMARKS = {
        'nifty_pe': 22.5,
        'nifty_pb': 3.2,
        'risk_free_rate': 7.0,  # 10-year G-Sec yield
        'market_return': 12.0,   # Long-term Nifty CAGR
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def generate_recommendation(
        self,
        symbol: str,
        quote: Optional[Dict],
        historical_data: Optional[List[Dict]],
        fundamentals: Dict,
        sentiment_data: Optional[Dict] = None,
        news_items: Optional[List] = None
    ) -> Dict:
        """
        Generate comprehensive stock recommendation.
        
        Args:
            symbol: Stock symbol
            quote: Current price quote
            historical_data: List of historical price data
            fundamentals: Fundamental ratios (P/E, ROE, etc.)
            sentiment_data: News/social sentiment scores
            news_items: Recent news articles
        
        Returns:
            Complete recommendation object
        """
        # Calculate individual factor scores
        technical_analysis = self._analyze_technicals(quote, historical_data)
        fundamental_analysis = self._analyze_fundamentals(fundamentals)
        sentiment_analysis = self._analyze_sentiment(sentiment_data, news_items)
        risk_analysis = self._analyze_risk(quote, historical_data, fundamentals)
        
        # Calculate composite score
        composite_score = (
            technical_analysis['score'] * self.WEIGHTS['technical'] +
            fundamental_analysis['score'] * self.WEIGHTS['fundamental'] +
            sentiment_analysis['score'] * self.WEIGHTS['sentiment'] +
            risk_analysis['score'] * self.WEIGHTS['risk']
        )
        
        # Determine overall signal
        overall_signal = self._determine_signal(composite_score)
        
        # Calculate confidence based on factor agreement
        confidence = self._calculate_confidence([
            technical_analysis['score'],
            fundamental_analysis['score'],
            sentiment_analysis['score'],
            risk_analysis['score']
        ])
        
        # Generate timeframe-specific recommendations
        timeframe_recs = self._generate_timeframe_recommendations(
            symbol, quote, technical_analysis, fundamental_analysis, risk_analysis
        )
        
        # Identify key factors driving the recommendation
        key_factors = self._identify_key_factors(
            technical_analysis, fundamental_analysis, sentiment_analysis, risk_analysis
        )
        
        # Generate expert rationale
        rationale = self._generate_expert_rationale(
            symbol, overall_signal, key_factors, fundamentals, technical_analysis
        )
        
        # Generate action summary
        action_summary = self._generate_action_summary(
            symbol, overall_signal, timeframe_recs, quote
        )
        
        return {
            'overall_signal': overall_signal,
            'signal_class': overall_signal.lower().replace(' ', '_'),
            'composite_score': round(composite_score, 1),
            'confidence': round(confidence, 1),
            
            'score_breakdown': {
                'technical_score': round(technical_analysis['score'], 1),
                'fundamental_score': round(fundamental_analysis['score'], 1),
                'sentiment_score': round(sentiment_analysis['score'], 1),
                'risk_score': round(risk_analysis['score'], 1),
            },
            
            'technical_indicators': technical_analysis.get('indicators', {}),
            'fundamental_metrics': fundamental_analysis.get('metrics', {}),
            
            'factor_ratings': fundamental_analysis.get('factors', {}),
            
            'timeframe_recommendations': timeframe_recs,
            'key_factors': key_factors,
            
            'ai_verdict': self._generate_verdict(symbol, overall_signal, composite_score, fundamental_analysis['factors']),
            'scenarios': self._generate_scenarios(fundamental_analysis['factors'], technical_analysis),
            
            'risk_metrics': {
                'volatility_30d': risk_analysis.get('volatility_30d'),
                'beta': risk_analysis.get('beta'),
                'max_drawdown': risk_analysis.get('max_drawdown'),
                'risk_level': risk_analysis.get('risk_level', 'MODERATE'),
                'var_95': risk_analysis.get('var_95'),
            },
            
            'expert_rationale': rationale,
            'action_summary': action_summary,
            'generated_at': datetime.now().isoformat(),
        }
    
    def _analyze_technicals(
        self, 
        quote: Optional[Dict], 
        historical_data: Optional[List[Dict]]
    ) -> Dict:
        """Analyze technical indicators"""
        score = 50  # Neutral baseline
        indicators = {}
        
        if not historical_data or len(historical_data) < 5:
            # Limited data - use basic analysis from quote
            if quote:
                change_pct = quote.get('change_percent') or 0
                if change_pct > 2:
                    score += 15
                elif change_pct > 0:
                    score += 5
                elif change_pct < -2:
                    score -= 15
                elif change_pct < 0:
                    score -= 5
            
            return {
                'score': max(0, min(100, score)),
                'indicators': {'data_available': False}
            }
        
        # Extract close prices
        closes = [d.get('close') for d in historical_data if d.get('close')]
        
        if len(closes) >= 14:
            # Calculate RSI
            rsi = self._calculate_rsi(closes, 14)
            indicators['rsi'] = round(rsi, 1)
            
            if rsi < 30:
                score += 20  # Oversold - bullish
                indicators['rsi_signal'] = 'OVERSOLD'
            elif rsi < 40:
                score += 10
                indicators['rsi_signal'] = 'APPROACHING_OVERSOLD'
            elif rsi > 70:
                score -= 20  # Overbought - bearish
                indicators['rsi_signal'] = 'OVERBOUGHT'
            elif rsi > 60:
                score -= 10
                indicators['rsi_signal'] = 'APPROACHING_OVERBOUGHT'
            else:
                indicators['rsi_signal'] = 'NEUTRAL'
        
        # Calculate Moving Averages
        if len(closes) >= 20:
            ma_20 = sum(closes[-20:]) / 20
            indicators['ma_20'] = round(ma_20, 2)
            
            current_price = closes[-1]
            ma_20_pct = ((current_price - ma_20) / ma_20) * 100
            indicators['price_vs_ma20'] = round(ma_20_pct, 2)
            
            if current_price > ma_20:
                score += 10
                indicators['ma_20_signal'] = 'ABOVE'
            else:
                score -= 10
                indicators['ma_20_signal'] = 'BELOW'
        
        if len(closes) >= 50:
            ma_50 = sum(closes[-50:]) / 50
            indicators['ma_50'] = round(ma_50, 2)
            
            current_price = closes[-1]
            if current_price > ma_50:
                score += 10
                indicators['ma_50_signal'] = 'ABOVE'
            else:
                score -= 10
                indicators['ma_50_signal'] = 'BELOW'
        
        # Calculate MACD
        if len(closes) >= 26:
            macd, signal, histogram = self._calculate_macd(closes)
            indicators['macd'] = round(macd, 2)
            indicators['macd_signal'] = round(signal, 2)
            indicators['macd_histogram'] = round(histogram, 2)
            
            if histogram > 0:
                score += 10
                indicators['macd_trend'] = 'BULLISH'
            else:
                score -= 10
                indicators['macd_trend'] = 'BEARISH'
        
        # Calculate momentum
        if len(closes) >= 10:
            momentum = ((closes[-1] - closes[-10]) / closes[-10]) * 100
            indicators['momentum_10d'] = round(momentum, 2)
            
            if momentum > 5:
                score += 15
            elif momentum > 0:
                score += 5
            elif momentum < -5:
                score -= 15
            elif momentum < 0:
                score -= 5
        
        # Volume analysis if available
        volumes = [d.get('volume') for d in historical_data if d.get('volume')]
        if len(volumes) >= 10:
            avg_volume = sum(volumes[-10:]) / 10
            recent_volume = volumes[-1] if volumes else 0
            
            if recent_volume > avg_volume * 1.5:
                indicators['volume_signal'] = 'HIGH'
                # High volume on up day is bullish
                change_pct = quote.get('change_percent') or 0
                if quote and change_pct > 0:
                    score += 5
            elif recent_volume < avg_volume * 0.5:
                indicators['volume_signal'] = 'LOW'
            else:
                indicators['volume_signal'] = 'NORMAL'
        
        indicators['data_available'] = True
        
        return {
            'score': max(0, min(100, score)),
            'indicators': indicators
        }
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_macd(
        self, 
        prices: List[float], 
        fast: int = 12, 
        slow: int = 26, 
        signal: int = 9
    ) -> Tuple[float, float, float]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        if len(prices) < slow:
            return 0.0, 0.0, 0.0
        
        # Calculate EMAs
        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)
        
        macd_line = ema_fast - ema_slow
        
        # For signal line, we'd need historical MACD values
        # Simplified: use recent MACD as approximation
        signal_line = macd_line * 0.9  # Approximation
        
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        
        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period  # Start with SMA
        
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    def _analyze_fundamentals(self, fundamentals: Dict) -> Dict:
        """Analyze fundamental metrics with factor breakdown"""
        
        # Sub-factor scores
        value_score = self._score_value(fundamentals)
        growth_score = self._score_growth(fundamentals)
        safety_score = self._score_safety(fundamentals)
        quality_score = self._score_quality(fundamentals)
        
        # Weighted Fundamental Score
        # Value: 30%, Growth: 30%, Safety: 20%, Quality: 20%
        overall_score = (
            value_score * 0.30 +
            growth_score * 0.30 +
            safety_score * 0.20 +
            quality_score * 0.20
        )
        
        return {
            'score': round(overall_score, 1),
            'metrics': fundamentals,  # Keep original metrics for display
            'factors': {
                'value': round(value_score, 1),
                'growth': round(growth_score, 1),
                'safety': round(safety_score, 1),
                'quality': round(quality_score, 1)
            }
        }

    def _score_value(self, data: Dict) -> float:
        """Score based on value metrics (P/E, P/B)"""
        score = 50  # Neutral baseline
        
        pe = data.get('pe', 0)
        pb = data.get('pb', 0)
        
        # Indian Market Benchmarks
        median_pe = self.BENCHMARKS['nifty_pe']
        median_pb = self.BENCHMARKS['nifty_pb']
        
        if pe > 0:
            if pe < median_pe * 0.6:  # Significantly undervalued
                score += 30
            elif pe < median_pe * 0.8:
                score += 20
            elif pe < median_pe:
                score += 10
            elif pe > median_pe * 1.5:
                score -= 20
            elif pe > median_pe * 1.2:
                score -= 10
        
        if pb > 0:
            if pb < 1:  # Below book value
                score += 20
            elif pb < median_pb * 0.8:
                score += 10
            elif pb > median_pb * 3:
                score -= 15
        
        return max(0, min(100, score))
    
    def _score_growth(self, data: Dict) -> float:
        """Score based on growth metrics (ROE, ROCE)"""
        score = 50
        
        roe = data.get('roe', 0)
        roce = data.get('roce', 0)
        
        # ROE scoring
        if roe > 25:
            score += 25
        elif roe > 20:
            score += 20
        elif roe > 15:
            score += 10
        elif roe < 8:
            score -= 15
        
        # ROCE scoring
        if roce > 30:
            score += 20
        elif roce > 22:
            score += 15
        elif roce > 18:
            score += 10
        elif roce < 10:
            score -= 10
        
        return max(0, min(100, score))
    
    def _score_safety(self, data: Dict) -> float:
        """Score based on safety metrics (Debt, Stability)"""
        score = 50
        
        de = data.get('de', 0)
        
        # Debt/Equity scoring
        if de is not None:
            if de < 0.1:  # Almost debt-free
                score += 30
            elif de < 0.3:
                score += 20
            elif de < 1.0:
                score += 10
            elif de > 2:
                score -= 30
            elif de > 1.5:
                score -= 15
        
        # Dividend as safety indicator
        div = data.get('div_yield', 0)
        if div > 2:
            score += 10
        elif div > 1:
            score += 5
        
        return max(0, min(100, score))

    def _score_quality(self, data: Dict) -> float:
        """Score based on quality metrics"""
        score = 50
        
        # Consistent profitability
        roe = data.get('roe', 0)
        roce = data.get('roce', 0)
        
        if roe > 15 and roce > 18:
            score += 25
        elif roe > 12 and roce > 15:
            score += 15
        elif roe < 0 or roce < 0:
            score -= 20
        
        # Market cap stability
        mcap = data.get('mcap', '')
        if mcap == 'Large Cap':
            score += 10
        elif mcap == 'Mid Cap':
            score += 5
        elif mcap == 'Penny Stock':
            score -= 10
        
        return max(0, min(100, score))
    
    def _analyze_sentiment(
        self, 
        sentiment_data: Optional[Dict], 
        news_items: Optional[List]
    ) -> Dict:
        """Analyze market sentiment"""
        score = 50  # Neutral baseline
        
        if sentiment_data:
            bullish = sentiment_data.get('bullish', 0)
            bearish = sentiment_data.get('bearish', 0)
            total = bullish + bearish + sentiment_data.get('neutral', 0)
            
            if total > 0:
                bullish_ratio = bullish / total
                bearish_ratio = bearish / total
                
                if bullish_ratio > 0.7:
                    score += 25
                elif bullish_ratio > 0.5:
                    score += 15
                elif bearish_ratio > 0.7:
                    score -= 25
                elif bearish_ratio > 0.5:
                    score -= 15
        
        # Analyze recent news sentiment
        if news_items:
            positive_news = sum(1 for n in news_items if n.get('sentiment') == 'positive')
            negative_news = sum(1 for n in news_items if n.get('sentiment') == 'negative')
            
            if positive_news > negative_news * 2:
                score += 15
            elif positive_news > negative_news:
                score += 5
            elif negative_news > positive_news * 2:
                score -= 15
            elif negative_news > positive_news:
                score -= 5
        
        return {
            'score': max(0, min(100, score))
        }
    
    def _analyze_risk(
        self, 
        quote: Optional[Dict], 
        historical_data: Optional[List[Dict]],
        fundamentals: Dict
    ) -> Dict:
        """Analyze risk metrics"""
        score = 50  # Neutral - moderate risk
        
        volatility_30d = None
        max_drawdown = None
        beta = None
        var_95 = None
        
        if historical_data and len(historical_data) >= 20:
            closes = [d.get('close') for d in historical_data if d.get('close')]
            
            if len(closes) >= 20:
                # Calculate daily returns
                returns = [(closes[i] - closes[i-1]) / closes[i-1] * 100 
                          for i in range(1, len(closes))]
                
                # 30-day volatility (annualized)
                if len(returns) >= 20:
                    recent_returns = returns[-20:]
                    mean_return = sum(recent_returns) / len(recent_returns)
                    variance = sum((r - mean_return) ** 2 for r in recent_returns) / len(recent_returns)
                    daily_vol = math.sqrt(variance)
                    volatility_30d = daily_vol * math.sqrt(252)  # Annualized
                    
                    # VaR at 95% confidence (parametric)
                    var_95 = mean_return - (1.645 * daily_vol)
                
                # Max drawdown
                peak = closes[0]
                max_dd = 0
                for price in closes:
                    if price > peak:
                        peak = price
                    drawdown = (peak - price) / peak * 100
                    if drawdown > max_dd:
                        max_dd = drawdown
                max_drawdown = -max_dd
                
                # Simplified beta calculation (vs market proxy)
                # In production, would use actual Nifty data
                beta = 1.0 + (volatility_30d - 15) / 20 if volatility_30d else 1.0
                beta = max(0.5, min(2.0, beta))
        
        # Score based on volatility
        if volatility_30d:
            if volatility_30d < 15:
                score += 20
                risk_level = 'LOW'
            elif volatility_30d < 25:
                score += 10
                risk_level = 'MODERATE'
            elif volatility_30d < 40:
                score -= 10
                risk_level = 'HIGH'
            else:
                score -= 25
                risk_level = 'VERY_HIGH'
        else:
            # Use fundamentals as proxy
            de = fundamentals.get('de', 0)
            mcap = fundamentals.get('mcap', '')
            
            if de > 1.5:
                score -= 15
                risk_level = 'HIGH'
            elif mcap == 'Large Cap':
                score += 10
                risk_level = 'LOW'
            elif mcap == 'Penny Stock':
                score -= 20
                risk_level = 'VERY_HIGH'
            else:
                risk_level = 'MODERATE'
        
        return {
            'score': max(0, min(100, score)),
            'volatility_30d': round(volatility_30d, 2) if volatility_30d else None,
            'beta': round(beta, 2) if beta else None,
            'max_drawdown': round(max_drawdown, 2) if max_drawdown else None,
            'var_95': round(var_95, 2) if var_95 else None,
            'risk_level': risk_level if 'risk_level' in locals() else 'MODERATE'
        }
    
    def _determine_signal(self, score: float) -> str:
        """Determine the overall signal based on composite score"""
        if score >= self.SIGNAL_THRESHOLDS['strong_buy']:
            return 'STRONG BUY'
        elif score >= self.SIGNAL_THRESHOLDS['buy']:
            return 'BUY'
        elif score >= self.SIGNAL_THRESHOLDS['hold']:
            return 'HOLD'
        elif score >= self.SIGNAL_THRESHOLDS['sell']:
            return 'SELL'
        else:
            return 'AVOID'
    
    def _calculate_confidence(self, scores: List[float]) -> float:
        """Calculate confidence based on factor agreement"""
        if not scores:
            return 50.0
        
        mean = sum(scores) / len(scores)
        variance = sum((s - mean) ** 2 for s in scores) / len(scores)
        std_dev = math.sqrt(variance)
        
        # Lower variance = higher agreement = higher confidence
        max_std = 30
        agreement_factor = max(0, 100 - (std_dev / max_std * 100))
        
        # Scale confidence
        confidence = 40 + (agreement_factor * 0.55)
        
        return min(95, confidence)
    
    def _generate_timeframe_recommendations(
        self,
        symbol: str,
        quote: Optional[Dict],
        technical: Dict,
        fundamental: Dict,
        risk: Dict
    ) -> Dict:
        """Generate recommendations for different timeframes"""
        current_price = quote.get('price', 0) if quote else 0
        
        if not current_price:
            return {}
        
        tech_score = technical.get('score', 50)
        fund_score = fundamental.get('score', 50)
        risk_level = risk.get('risk_level', 'MODERATE')
        
        # Risk-based target multipliers
        risk_multipliers = {
            'LOW': {'upside': 1.15, 'downside': 0.95},
            'MODERATE': {'upside': 1.12, 'downside': 0.93},
            'HIGH': {'upside': 1.20, 'downside': 0.88},
            'VERY_HIGH': {'upside': 1.30, 'downside': 0.80},
        }
        
        multipliers = risk_multipliers.get(risk_level, risk_multipliers['MODERATE'])
        
        timeframes = {}
        
        # Intraday (heavily technical)
        intraday_score = tech_score * 0.8 + fund_score * 0.2
        timeframes['intraday'] = {
            'signal': self._determine_signal(intraday_score),
            'target': round(current_price * 1.02, 2),  # 2% target
            'stoploss': round(current_price * 0.985, 2),  # 1.5% SL
            'score': round(intraday_score, 1)
        }
        
        # Short-term (1-4 weeks)
        short_term_score = tech_score * 0.6 + fund_score * 0.4
        timeframes['short_term'] = {
            'signal': self._determine_signal(short_term_score),
            'target': round(current_price * 1.08, 2),  # 8% target
            'stoploss': round(current_price * 0.95, 2),  # 5% SL
            'score': round(short_term_score, 1)
        }
        
        # Medium-term (1-3 months)
        medium_term_score = tech_score * 0.4 + fund_score * 0.6
        timeframes['medium_term'] = {
            'signal': self._determine_signal(medium_term_score),
            'target': round(current_price * multipliers['upside'], 2),
            'stoploss': round(current_price * multipliers['downside'], 2),
            'score': round(medium_term_score, 1)
        }
        
        # Long-term (1+ year) - fundamentals dominate
        long_term_score = tech_score * 0.2 + fund_score * 0.8
        timeframes['long_term'] = {
            'signal': self._determine_signal(long_term_score),
            'target': round(current_price * (multipliers['upside'] ** 2), 2),  # Squared for longer term
            'stoploss': round(current_price * multipliers['downside'], 2),
            'score': round(long_term_score, 1)
        }
        
        return timeframes
    
    def _identify_key_factors(
        self,
        technical: Dict,
        fundamental: Dict,
        sentiment: Dict,
        risk: Dict
    ) -> List[Dict]:
        """Identify key factors driving the recommendation"""
        factors = []
        
        # Technical factors
        indicators = technical.get('indicators', {})
        
        if indicators.get('rsi'):
            rsi = indicators['rsi']
            if rsi < 30:
                factors.append({
                    'factor': 'RSI Oversold',
                    'description': f'RSI at {rsi:.1f} indicates oversold conditions',
                    'impact': 'positive',
                    'score': 85
                })
            elif rsi > 70:
                factors.append({
                    'factor': 'RSI Overbought',
                    'description': f'RSI at {rsi:.1f} indicates overbought conditions',
                    'impact': 'negative',
                    'score': 25
                })
        
        if indicators.get('macd_trend') == 'BULLISH':
            factors.append({
                'factor': 'MACD Bullish Crossover',
                'description': 'MACD showing positive momentum',
                'impact': 'positive',
                'score': 70
            })
        elif indicators.get('macd_trend') == 'BEARISH':
            factors.append({
                'factor': 'MACD Bearish Signal',
                'description': 'MACD showing negative momentum',
                'impact': 'negative',
                'score': 30
            })
        
        # Fundamental factors
        metrics = fundamental.get('metrics', {})
        
        if metrics.get('pe_assessment') == 'SIGNIFICANTLY_UNDERVALUED':
            factors.append({
                'factor': 'Attractive Valuation',
                'description': f"P/E of {metrics.get('pe', 0):.1f} well below industry average",
                'impact': 'positive',
                'score': 90
            })
        elif metrics.get('pe_assessment') == 'SIGNIFICANTLY_OVERVALUED':
            factors.append({
                'factor': 'High Valuation',
                'description': f"P/E of {metrics.get('pe', 0):.1f} significantly above average",
                'impact': 'negative',
                'score': 20
            })
        
        if metrics.get('roe_assessment') == 'EXCELLENT':
            factors.append({
                'factor': 'Strong Profitability',
                'description': f"ROE of {metrics.get('roe', 0):.1f}% shows excellent returns",
                'impact': 'positive',
                'score': 85
            })
        elif metrics.get('roe_assessment') == 'POOR':
            factors.append({
                'factor': 'Weak Profitability',
                'description': f"ROE of {metrics.get('roe', 0):.1f}% is below acceptable levels",
                'impact': 'negative',
                'score': 25
            })
        
        if metrics.get('de_assessment') == 'DEBT_FREE':
            factors.append({
                'factor': 'Debt-Free Balance Sheet',
                'description': 'Company has minimal debt, strong financial position',
                'impact': 'positive',
                'score': 90
            })
        elif metrics.get('de_assessment') == 'HIGH_DEBT':
            factors.append({
                'factor': 'High Leverage Concern',
                'description': f"D/E of {metrics.get('de', 0):.2f} poses financial risk",
                'impact': 'negative',
                'score': 20
            })
        
        # Risk factors
        risk_level = risk.get('risk_level', 'MODERATE')
        if risk_level == 'LOW':
            factors.append({
                'factor': 'Low Volatility',
                'description': 'Stable price movements reduce investment risk',
                'impact': 'positive',
                'score': 75
            })
        elif risk_level in ['HIGH', 'VERY_HIGH']:
            factors.append({
                'factor': 'High Volatility',
                'description': 'Significant price swings increase investment risk',
                'impact': 'negative',
                'score': 35
            })
        
        # Sort by absolute score deviation from neutral (50)
        factors.sort(key=lambda x: abs(x['score'] - 50), reverse=True)
        
        return factors[:6]  # Return top 6 factors
    
    def _generate_expert_rationale(
        self,
        symbol: str,
        signal: str,
        key_factors: List[Dict],
        fundamentals: Dict,
        technical: Dict
    ) -> str:
        """Generate expert-style rationale"""
        parts = []
        
        # Opening statement based on signal
        signal_intros = {
            'STRONG BUY': f"{symbol} presents a compelling investment opportunity with multiple factors aligning positively.",
            'BUY': f"{symbol} shows favorable characteristics warranting accumulation at current levels.",
            'HOLD': f"{symbol} presents mixed signals suggesting maintaining existing positions.",
            'SELL': f"{symbol} shows concerning trends that warrant reducing exposure.",
            'AVOID': f"{symbol} displays significant red flags across multiple factors.",
        }
        parts.append(signal_intros.get(signal, f"Analysis of {symbol}:"))
        
        # Add key factor summaries
        positive_factors = [f for f in key_factors if f['impact'] == 'positive']
        negative_factors = [f for f in key_factors if f['impact'] == 'negative']
        
        if positive_factors:
            strengths = ", ".join([f['factor'].lower() for f in positive_factors[:2]])
            parts.append(f"Key strengths include {strengths}.")
        
        if negative_factors:
            concerns = ", ".join([f['factor'].lower() for f in negative_factors[:2]])
            parts.append(f"Areas of concern: {concerns}.")
        
        # Technical context
        indicators = technical.get('indicators', {})
        if indicators.get('rsi'):
            rsi = indicators['rsi']
            if rsi < 40 or rsi > 60:
                parts.append(f"Technical indicators (RSI: {rsi:.0f}) suggest {'buying' if rsi < 40 else 'selling'} pressure.")
        
        # Fundamental context
        pe = fundamentals.get('pe', 0)
        roe = fundamentals.get('roe', 0)
        if pe > 0 and roe > 0:
            parts.append(f"Fundamentally, trading at {pe:.1f}x P/E with {roe:.1f}% ROE.")
        
        # Closing recommendation
        signal_closings = {
            'STRONG BUY': "Recommend aggressive accumulation for medium to long-term gains.",
            'BUY': "Consider adding on dips with defined risk parameters.",
            'HOLD': "Wait for clearer directional signals before taking action.",
            'SELL': "Consider booking profits and reducing position size.",
            'AVOID': "Stay on sidelines until fundamentals or technicals improve significantly.",
        }
        parts.append(signal_closings.get(signal, ""))
        
        return " ".join(parts)
    
    def _generate_action_summary(
        self,
        symbol: str,
        signal: str,
        timeframe_recs: Dict,
        quote: Optional[Dict]
    ) -> str:
        """Generate concise action summary"""
        current_price = quote.get('price', 0) if quote else 0
        
        if not current_price:
            return f"Signal: {signal}. Await price confirmation."
        
        short_term = timeframe_recs.get('short_term', {})
        medium_term = timeframe_recs.get('medium_term', {})
        
        target = medium_term.get('target', current_price * 1.1)
        stoploss = medium_term.get('stoploss', current_price * 0.95)
        
        upside = ((target - current_price) / current_price) * 100
        risk = ((current_price - stoploss) / current_price) * 100
        
        if signal in ['STRONG BUY', 'BUY']:
            return f"{signal} at ₹{current_price:,.0f}. Target: ₹{target:,.0f} (+{upside:.1f}%). SL: ₹{stoploss:,.0f} (-{risk:.1f}%). Risk-Reward: {upside/risk:.1f}:1"
        elif signal == 'HOLD':
            return f"{signal}. Current: ₹{current_price:,.0f}. Monitor for breakout above ₹{target:,.0f} or breakdown below ₹{stoploss:,.0f}."
        else:
            return f"{signal}. Consider exit above ₹{current_price:,.0f}. Support at ₹{stoploss:,.0f}."

    def _generate_verdict(self, symbol: str, signal: str, score: float, factors: Dict) -> str:
        """Generate a punchy 2-3 word verdict"""
        
        # High Quality + Good Value = Hidden Gem
        if factors.get('quality', 0) > 70 and factors.get('value', 0) > 60:
            return "💎 Hidden Gem"
            
        # High Quality + High Growth = Compounder
        if factors.get('quality', 0) > 70 and factors.get('growth', 0) > 70:
            return "🚀 Quality Compounder"
            
        # Low Value + Low Growth = Value Trap
        if factors.get('value', 0) < 40 and factors.get('growth', 0) < 40:
            return "⚠️ Value Trap"
            
        # High Momentum
        if signal == 'STRONG BUY' and score > 80:
            return "🔥 Strong Momentum"
            
        # Oversold
        if signal == 'BUY' and factors.get('value', 0) > 80:
            return "💰 Deep Value"
            
        # Safe Bet
        if factors.get('safety', 0) > 80 and factors.get('quality', 0) > 70:
            return "🛡️ Safe Haven"
            
        # Speculative
        if factors.get('growth', 0) > 80 and factors.get('safety', 0) < 40:
            return "🎰 High Risk High Reward"
            
        # Default based on signal
        if signal == 'STRONG BUY': return "🌟 Strong Buy"
        if signal == 'BUY': return "✅ Buy"
        if signal == 'SELL': return "🔻 Sell"
        if signal == 'STRONG SELL': return "🛑 Avoid"
        return "⚖️ Hold & Watch"

    def _generate_scenarios(self, factors: Dict, technicals: Dict) -> Dict:
        """Generate Bull and Bear case scenarios"""
        bull_case = []
        bear_case = []
        
        # Fundamental Scenarios
        if factors.get('growth', 0) > 70:
            bull_case.append("Strong earnings momentum continues")
        else:
            bear_case.append("Earnings growth slows down")
            
        if factors.get('value', 0) > 70:
            bull_case.append("Valuation re-rating potential")
        elif factors.get('value', 0) < 40:
            bear_case.append("High valuation limits upside")
            
        if factors.get('safety', 0) > 80:
            bear_case.append("Defensive traits limit downside") # Actually a positive for bear case
        elif factors.get('safety', 0) < 40:
            bear_case.append("Balance sheet stress increases risk")

        # Technical Scenarios
        rsi = technicals.get('indicators', {}).get('rsi', 50)
        if rsi > 70:
            bear_case.append("Technical overbought conditions trigger correction")
            bull_case.append("Strong momentum pushes into breakout")
        elif rsi < 30:
            bull_case.append("Oversold bounce expected")
            bear_case.append("Negative momentum continues")
            
        # Defaults if empty
        if not bull_case: bull_case.append("Sector tailwinds improve sentiment")
        if not bear_case: bear_case.append("Market volatility impacts stock")
        
        return {
            "bull_case": bull_case[:3],
            "bear_case": bear_case[:3]
        }
# Global instance
recommendation_engine = RecommendationEngine()
