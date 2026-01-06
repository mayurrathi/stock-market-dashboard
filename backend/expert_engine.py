"""
Expert Engine - Multi-factor weighted recommendation system
Simulates 50 years of Indian market experience
"""
from typing import Dict, Optional, Tuple
from datetime import datetime
import random
import logging

logger = logging.getLogger(__name__)


class ExpertEngine:
    """
    Multi-factor weighted recommendation engine.
    Combines fundamental, technical, and sentiment analysis
    to generate expert-level stock recommendations.
    """
    
    # Factor weights based on historical Indian market patterns
    FACTOR_WEIGHTS = {
        'value': 0.25,      # P/E, P/B vs Historical
        'growth': 0.25,     # ROE, ROCE, EPS Growth
        'safety': 0.20,     # Debt/Equity, Interest Coverage
        'technicals': 0.15, # RSI, Moving Averages
        'sentiment': 0.10,  # News sentiment, FII/DII flow
        'quality': 0.05,    # Promoter holding, governance
    }
    
    # Industry benchmarks for Indian markets
    BENCHMARKS = {
        'pe_median': 22.0,
        'pb_median': 3.0,
        'roe_good': 15.0,
        'roce_good': 18.0,
        'de_safe': 0.5,
        'div_yield_good': 1.5,
    }
    
    # Recommendation thresholds
    THRESHOLDS = {
        'strong_buy': 75,
        'buy': 60,
        'hold_upper': 55,
        'hold_lower': 45,
        'sell': 35,
        'strong_sell': 0,
    }
    
    def __init__(self):
        self.rationale_templates = self._load_rationale_templates()
    
    def calculate_recommendation(
        self,
        symbol: str,
        fundamentals: Dict,
        sentiment_data: Optional[Dict] = None,
        price_data: Optional[Dict] = None
    ) -> Dict:
        """
        Calculate comprehensive recommendation for a stock.
        
        Returns:
            {
                'score': 0-100,
                'signal': 'STRONG BUY' | 'BUY' | 'HOLD' | 'SELL' | 'STRONG SELL' | 'WAIT',
                'factors': {...},
                'rationale': str,
                'confidence': 0-100
            }
        """
        # Calculate individual factor scores
        factors = {
            'value': self._score_value(fundamentals),
            'growth': self._score_growth(fundamentals),
            'safety': self._score_safety(fundamentals),
            'technicals': self._score_technicals(price_data),
            'sentiment': self._score_sentiment(sentiment_data),
            'quality': self._score_quality(fundamentals),
        }
        
        # Calculate weighted composite score
        composite_score = 0
        for factor, score in factors.items():
            weight = self.FACTOR_WEIGHTS.get(factor, 0)
            composite_score += score * weight
        
        # Determine signal
        signal = self._determine_signal(composite_score, factors)
        
        # Calculate confidence based on factor agreement
        confidence = self._calculate_confidence(factors)
        
        # Generate expert rationale
        rationale = self._generate_rationale(symbol, signal, factors, fundamentals, sentiment_data)
        
        return {
            'score': round(composite_score, 1),
            'signal': signal,
            'signal_class': signal.lower().replace(' ', '_'),
            'factors': {k: round(v, 1) for k, v in factors.items()},
            'rationale': rationale,
            'confidence': round(confidence, 1),
            'last_updated': datetime.now().isoformat()
        }
    
    def _score_value(self, data: Dict) -> float:
        """Score based on value metrics (P/E, P/B)"""
        score = 50  # Neutral baseline
        
        pe = data.get('pe', 0)
        pb = data.get('pb', 0)
        
        if pe > 0:
            # Lower PE is better for value
            pe_benchmark = self.BENCHMARKS['pe_median']
            if pe < pe_benchmark * 0.6:  # 40% below median
                score += 30
            elif pe < pe_benchmark * 0.8:
                score += 20
            elif pe < pe_benchmark:
                score += 10
            elif pe > pe_benchmark * 1.5:
                score -= 20
            elif pe > pe_benchmark * 1.2:
                score -= 10
        
        if pb > 0:
            pb_benchmark = self.BENCHMARKS['pb_median']
            if pb < 1:  # Below book value
                score += 20
            elif pb < pb_benchmark * 0.8:
                score += 10
            elif pb > pb_benchmark * 3:
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
        elif roe > self.BENCHMARKS['roe_good']:
            score += 10
        elif roe < 8:
            score -= 15
        
        # ROCE scoring
        if roce > 30:
            score += 20
        elif roce > 22:
            score += 15
        elif roce > self.BENCHMARKS['roce_good']:
            score += 10
        elif roce < 10:
            score -= 10
        
        return max(0, min(100, score))
    
    def _score_safety(self, data: Dict) -> float:
        """Score based on safety metrics (Debt, Coverage)"""
        score = 50
        
        de = data.get('de', 0)
        
        # Debt/Equity scoring
        if de < 0.1:  # Almost debt-free
            score += 30
        elif de < 0.3:
            score += 20
        elif de < self.BENCHMARKS['de_safe']:
            score += 10
        elif de > 2:
            score -= 30
        elif de > 1:
            score -= 15
        
        # Dividend as safety indicator
        div = data.get('div_yield', 0)
        if div > 2:
            score += 10
        elif div > 1:
            score += 5
        
        return max(0, min(100, score))
    
    def _score_technicals(self, price_data: Optional[Dict]) -> float:
        """Score based on technical indicators (simulated)"""
        if not price_data:
            # Return neutral with some variance
            return 50 + random.randint(-10, 10)
        
        score = 50
        
        # Would use real technical data here
        change_percent = price_data.get('change_percent', 0)
        
        if change_percent:
            if change_percent > 3:
                score += 15  # Strong momentum
            elif change_percent > 0:
                score += 5
            elif change_percent < -3:
                score -= 15
            elif change_percent < 0:
                score -= 5
        
        return max(0, min(100, score))
    
    def _score_sentiment(self, sentiment_data: Optional[Dict]) -> float:
        """Score based on news and market sentiment"""
        if not sentiment_data:
            return 50  # Neutral
        
        score = 50
        
        bullish = sentiment_data.get('bullish', 0)
        bearish = sentiment_data.get('bearish', 0)
        total = bullish + bearish + sentiment_data.get('neutral', 0)
        
        if total > 0:
            bullish_ratio = bullish / total
            bearish_ratio = bearish / total
            
            if bullish_ratio > 0.6:
                score += 25
            elif bullish_ratio > 0.4:
                score += 10
            
            if bearish_ratio > 0.6:
                score -= 25
            elif bearish_ratio > 0.4:
                score -= 10
        
        # Mention count as interest indicator
        mentions = sentiment_data.get('mentions', 0)
        if mentions > 10:
            score += 5
        
        return max(0, min(100, score))
    
    def _score_quality(self, data: Dict) -> float:
        """Score based on quality metrics"""
        score = 50
        
        # Consistent profitability (ROE + ROCE both positive)
        roe = data.get('roe', 0)
        roce = data.get('roce', 0)
        
        if roe > 15 and roce > 18:
            score += 25
        elif roe > 12 and roce > 15:
            score += 15
        elif roe < 0 or roce < 0:
            score -= 20
        
        # Market cap as stability indicator
        mcap = data.get('mcap', '')
        if mcap == 'Large Cap':
            score += 10
        elif mcap == 'Mid Cap':
            score += 5
        elif mcap == 'Penny Stock':
            score -= 10
        
        return max(0, min(100, score))
    
    def _determine_signal(self, score: float, factors: Dict) -> str:
        """Determine the recommendation signal"""
        # Check for conflicting signals
        high_factors = sum(1 for v in factors.values() if v >= 70)
        low_factors = sum(1 for v in factors.values() if v <= 30)
        
        # If mixed signals, recommend WAIT
        if high_factors >= 2 and low_factors >= 2:
            return 'WAIT'
        
        if score >= self.THRESHOLDS['strong_buy']:
            return 'STRONG BUY'
        elif score >= self.THRESHOLDS['buy']:
            return 'BUY'
        elif score >= self.THRESHOLDS['hold_upper']:
            return 'HOLD'
        elif score >= self.THRESHOLDS['hold_lower']:
            return 'HOLD'
        elif score >= self.THRESHOLDS['sell']:
            return 'SELL'
        else:
            return 'STRONG SELL'
    
    def _calculate_confidence(self, factors: Dict) -> float:
        """Calculate confidence based on factor agreement"""
        values = list(factors.values())
        mean = sum(values) / len(values)
        
        # Calculate variance
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = variance ** 0.5
        
        # Lower variance = higher agreement = higher confidence
        # Normalize to 0-100 scale
        max_std = 35  # Theoretical max for 0-100 range
        confidence = max(0, 100 - (std_dev / max_std * 100))
        
        # Add base confidence
        return 40 + (confidence * 0.6)
    
    def _generate_rationale(
        self, 
        symbol: str, 
        signal: str, 
        factors: Dict, 
        fundamentals: Dict,
        sentiment_data: Optional[Dict]
    ) -> str:
        """Generate expert-style rationale text"""
        
        # Find strongest and weakest factors
        sorted_factors = sorted(factors.items(), key=lambda x: x[1], reverse=True)
        strongest = sorted_factors[0]
        weakest = sorted_factors[-1]
        
        # Get key metrics
        pe = fundamentals.get('pe', 0)
        roe = fundamentals.get('roe', 0)
        de = fundamentals.get('de', 0)
        roce = fundamentals.get('roce', 0)
        
        # Build rationale
        parts = []
        
        if signal in ['STRONG BUY', 'BUY']:
            if strongest[0] == 'value' and strongest[1] > 70:
                parts.append(f"Attractive valuation with P/E of {pe:.1f}")
            elif strongest[0] == 'growth' and strongest[1] > 70:
                parts.append(f"Strong growth metrics with ROE of {roe:.1f}%")
            elif strongest[0] == 'safety' and strongest[1] > 70:
                parts.append(f"Low-risk profile with D/E of {de:.2f}")
            else:
                parts.append("Positive momentum across key factors")
            
            if weakest[1] < 40:
                parts.append(f"however {weakest[0]} metrics warrant monitoring")
                
        elif signal in ['SELL', 'STRONG SELL']:
            if weakest[0] == 'value' and weakest[1] < 40:
                parts.append(f"Overvalued with P/E of {pe:.1f} above sector average")
            elif weakest[0] == 'safety' and weakest[1] < 40:
                parts.append(f"High leverage concern with D/E of {de:.2f}")
            elif weakest[0] == 'growth' and weakest[1] < 40:
                parts.append(f"Weak profitability with ROE of {roe:.1f}%")
            else:
                parts.append("Multiple factors showing weakness")
                
        elif signal == 'HOLD':
            parts.append("Mixed signals suggest maintaining current position")
            if roe > 15:
                parts.append(f"Decent fundamentals with ROE of {roe:.1f}%")
            parts.append("wait for clearer directional signals")
            
        elif signal == 'WAIT':
            parts.append("Conflicting indicators across factors")
            parts.append("recommend patience for better entry/exit opportunity")
        
        # Add sentiment context if available
        if sentiment_data:
            mentions = sentiment_data.get('mentions', 0)
            if mentions > 5:
                bullish = sentiment_data.get('bullish', 0)
                bearish = sentiment_data.get('bearish', 0)
                if bullish > bearish:
                    parts.append("positive market sentiment adds tailwind")
                elif bearish > bullish:
                    parts.append("negative sentiment creates near-term headwind")
        
        rationale = "; ".join(parts) + "."
        return rationale.capitalize()
    
    def _load_rationale_templates(self) -> Dict:
        """Load rationale templates for different scenarios"""
        return {
            'value_buy': "Undervalued relative to intrinsic worth",
            'growth_buy': "Strong earnings trajectory supports premium",
            'safety_concern': "Debt levels warrant caution",
            'momentum_positive': "Technical setup favors upside",
            'sentiment_bullish': "Market sentiment turning positive",
        }
    
    def get_factor_explanation(self, factor: str) -> str:
        """Get explanation for a factor"""
        explanations = {
            'value': 'Valuation metrics (P/E, P/B) relative to historical and sector averages',
            'growth': 'Profitability and growth indicators (ROE, ROCE, earnings growth)',
            'safety': 'Financial stability metrics (Debt/Equity, interest coverage)',
            'technicals': 'Price patterns, momentum, and technical indicators',
            'sentiment': 'Market sentiment from news, analyst ratings, and flow data',
            'quality': 'Business quality, moat, and management efficiency',
        }
        return explanations.get(factor, 'Unknown factor')


# Global expert engine instance
expert_engine = ExpertEngine()
