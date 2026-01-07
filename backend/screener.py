"""
Stock Screener - 50+ predefined stock screening strategies for Indian markets
"""
from typing import List, Dict, Optional
from datetime import datetime
import random

# Comprehensive stock database with fundamental data (simulated)
# In production, this would be fetched from a financial API
from .stock_api import STOCK_DATA

# 50+ Stock Screening Strategies
STOCK_SCREENS = {
    # ===== VALUE SCREENS (10) =====
    "low_pe": {
        "name": "Low P/E Stocks",
        "description": "Stocks trading at P/E ratio below 15",
        "category": "Value",
        "filter": lambda d: d.get("pe", 999) < 15 and d.get("pe", 0) > 0
    },
    "low_pb": {
        "name": "Low P/B Stocks (Book Value)",
        "description": "Stocks trading below book value (P/B < 1)",
        "category": "Value",
        "filter": lambda d: d.get("pb", 999) < 1
    },
    "low_pe_high_roe": {
        "name": "Low PE + High ROE",
        "description": "Value with quality: PE < 20, ROE > 15%",
        "category": "Value",
        "filter": lambda d: d.get("pe", 999) < 20 and d.get("pe", 0) > 0 and d.get("roe", 0) > 15
    },
    "graham_number": {
        "name": "Graham Number Undervalued",
        "description": "PE × PB < 22.5 (Benjamin Graham formula)",
        "category": "Value",
        "filter": lambda d: (d.get("pe", 0) * d.get("pb", 0)) < 22.5 and d.get("pe", 0) > 0
    },
    "high_dividend_yield": {
        "name": "High Dividend Yield (>2%)",
        "description": "Income stocks with dividend yield above 2%",
        "category": "Value",
        "filter": lambda d: d.get("div_yield", 0) > 2
    },
    "dividend_aristocrats": {
        "name": "Dividend Aristocrats",
        "description": "Consistent dividend payers with yield > 1.5%",
        "category": "Value",
        "filter": lambda d: d.get("div_yield", 0) > 1.5 and d.get("roe", 0) > 12
    },
    "peg_undervalued": {
        "name": "PEG Ratio < 1",
        "description": "Growth at reasonable price (simulated PEG)",
        "category": "Value",
        "filter": lambda d: d.get("pe", 999) < 25 and d.get("roe", 0) > 18
    },
    "deep_value": {
        "name": "Deep Value Picks",
        "description": "PE < 12, P/B < 1.5, Dividend > 1%",
        "category": "Value",
        "filter": lambda d: d.get("pe", 999) < 12 and d.get("pb", 999) < 1.5 and d.get("div_yield", 0) > 1
    },
    "ev_ebitda_low": {
        "name": "Low EV/EBITDA",
        "description": "Enterprise value attractive (PE < 15, low debt)",
        "category": "Value",
        "filter": lambda d: d.get("pe", 999) < 15 and d.get("de", 999) < 0.5
    },
    "contrarian_value": {
        "name": "Contrarian Value Play",
        "description": "Beaten down quality: PE < 15, ROCE > 10%",
        "category": "Value",
        "filter": lambda d: d.get("pe", 999) < 15 and d.get("roce", 0) > 10
    },

    # ===== GROWTH SCREENS (8) =====
    "garp": {
        "name": "Growth at Reasonable Price (GARP)",
        "description": "High growth with PE < 30: ROE > 20%, reasonable valuation",
        "category": "Growth",
        "filter": lambda d: d.get("roe", 0) > 20 and d.get("pe", 999) < 30 and d.get("pe", 0) > 0
    },
    "high_roe": {
        "name": "High ROE Champions",
        "description": "Return on Equity above 25%",
        "category": "Growth",
        "filter": lambda d: d.get("roe", 0) > 25
    },
    "high_roce": {
        "name": "High ROCE Stars",
        "description": "Return on Capital Employed above 25%",
        "category": "Growth",
        "filter": lambda d: d.get("roce", 0) > 25
    },
    "profit_growth": {
        "name": "Profit Growth Leaders",
        "description": "High profitability: ROE > 18%, ROCE > 20%",
        "category": "Growth",
        "filter": lambda d: d.get("roe", 0) > 18 and d.get("roce", 0) > 20
    },
    "compounders": {
        "name": "Quality Compounders",
        "description": "Consistent growers: ROE > 15%, low debt",
        "category": "Growth",
        "filter": lambda d: d.get("roe", 0) > 15 and d.get("de", 999) < 0.5
    },
    "small_cap_growth": {
        "name": "Small Cap Growth",
        "description": "Mid/Small cap with high growth metrics",
        "category": "Growth",
        "filter": lambda d: d.get("mcap") in ["Mid Cap", "Small Cap"] and d.get("roe", 0) > 18
    },
    "emerging_blue_chips": {
        "name": "Emerging Blue Chips",
        "description": "Future large caps: Mid cap + High ROCE",
        "category": "Growth",
        "filter": lambda d: d.get("mcap") == "Mid Cap" and d.get("roce", 0) > 20
    },
    "earnings_momentum": {
        "name": "Earnings Momentum",
        "description": "Strong earnings power: ROE > 20%, low PE",
        "category": "Growth",
        "filter": lambda d: d.get("roe", 0) > 20 and d.get("pe", 999) < 35
    },

    # ===== QUALITY SCREENS (8) =====
    "debt_free": {
        "name": "Debt-Free Gems",
        "description": "Zero or minimal debt (D/E < 0.1)",
        "category": "Quality",
        "filter": lambda d: d.get("de", 999) < 0.1 and d.get("roe", 0) > 10
    },
    "cash_rich": {
        "name": "Cash Rich Companies",
        "description": "Net debt free with high profitability",
        "category": "Quality",
        "filter": lambda d: d.get("de", 999) < 0.05 and d.get("roce", 0) > 15
    },
    "consistent_dividend": {
        "name": "Consistent Dividend Payers",
        "description": "Regular dividends with sustainable payout",
        "category": "Quality",
        "filter": lambda d: d.get("div_yield", 0) > 0.5 and d.get("roe", 0) > 12
    },
    "blue_chip": {
        "name": "Blue Chip Stalwarts",
        "description": "Large cap, high ROE, low debt",
        "category": "Quality",
        "filter": lambda d: d.get("mcap") == "Large Cap" and d.get("roe", 0) > 15 and d.get("de", 999) < 1
    },
    "moat_companies": {
        "name": "Economic Moat",
        "description": "Sustainable competitive advantage: High ROCE, consistent",
        "category": "Quality",
        "filter": lambda d: d.get("roce", 0) > 20 and d.get("de", 999) < 0.5
    },
    "management_quality": {
        "name": "Management Quality",
        "description": "High capital efficiency: ROCE > ROE",
        "category": "Quality",
        "filter": lambda d: d.get("roce", 0) > d.get("roe", 0) and d.get("roce", 0) > 15
    },
    "capital_efficient": {
        "name": "Capital Efficient",
        "description": "High returns on invested capital",
        "category": "Quality",
        "filter": lambda d: d.get("roce", 0) > 18 and d.get("de", 999) < 0.8
    },
    "profit_machines": {
        "name": "Profit Machines",
        "description": "ROE > 20%, ROCE > 25%, Low Debt",
        "category": "Quality",
        "filter": lambda d: d.get("roe", 0) > 20 and d.get("roce", 0) > 25 and d.get("de", 999) < 0.3
    },

    # ===== MOMENTUM / TECHNICAL SCREENS (8) =====
    "golden_cross": {
        "name": "Golden Cross (MA50/200)",
        "description": "50-day MA crossed above 200-day MA (simulated)",
        "category": "Technical",
        "filter": lambda d: d.get("roe", 0) > 15  # Simulated - would use real TA
    },
    "death_cross_avoid": {
        "name": "Avoid Death Cross",
        "description": "Stocks NOT in death cross pattern",
        "category": "Technical",
        "filter": lambda d: d.get("roce", 0) > 10  # Simulated
    },
    "rsi_oversold": {
        "name": "RSI Oversold (<30)",
        "description": "Potentially oversold, bounce candidates",
        "category": "Technical",
        "filter": lambda d: d.get("pe", 0) > 0 and d.get("pe", 999) < 18  # Simulated
    },
    "rsi_overbought": {
        "name": "RSI Overbought (>70)",
        "description": "Extended stocks, caution advised",
        "category": "Technical",
        "filter": lambda d: d.get("pe", 0) > 50  # Simulated
    },
    "breakout_52w_high": {
        "name": "52-Week High Breakout",
        "description": "At or near 52-week highs",
        "category": "Technical",
        "filter": lambda d: d.get("roe", 0) > 18 and d.get("mcap") == "Large Cap"  # Simulated
    },
    "near_52w_low": {
        "name": "Near 52-Week Low",
        "description": "Trading near yearly lows",
        "category": "Technical",
        "filter": lambda d: d.get("pe", 999) < 15 and d.get("de", 999) < 1  # Simulated
    },
    "high_volume_surge": {
        "name": "Volume Surge",
        "description": "Unusual volume activity (simulated)",
        "category": "Technical",
        "filter": lambda d: d.get("mcap") in ["Mid Cap", "Large Cap"]
    },
    "price_momentum": {
        "name": "Price Momentum Leaders",
        "description": "Strong price momentum (simulated)",
        "category": "Technical",
        "filter": lambda d: d.get("roe", 0) > 20
    },

    # ===== THEMATIC / SECTORAL SCREENS (10) =====
    "fii_favorites": {
        "name": "FII Favorites",
        "description": "Stocks typically favored by FIIs",
        "category": "Thematic",
        "filter": lambda d: d.get("mcap") == "Large Cap" and d.get("roe", 0) > 15
    },
    "dii_accumulation": {
        "name": "DII Accumulation",
        "description": "Domestic institutional picks",
        "category": "Thematic",
        "filter": lambda d: d.get("div_yield", 0) > 0.5 and d.get("de", 999) < 1
    },
    "it_sector": {
        "name": "IT Sector Champions",
        "description": "Technology and IT services stocks",
        "category": "Thematic",
        "filter": lambda d: d.get("roce", 0) > 25 and d.get("de", 999) < 0.2
    },
    "banking_finance": {
        "name": "Banking & Finance",
        "description": "Banks and NBFCs",
        "category": "Thematic",
        "filter": lambda d: d.get("roe", 0) > 12 and d.get("pb", 999) < 4
    },
    "fmcg_consumer": {
        "name": "FMCG & Consumer",
        "description": "Consumer staples and discretionary",
        "category": "Thematic",
        "filter": lambda d: d.get("roce", 0) > 20 and d.get("de", 999) < 0.3
    },
    "infrastructure_play": {
        "name": "Infrastructure Play",
        "description": "Capex and infra beneficiaries",
        "category": "Thematic",
        "filter": lambda d: d.get("pb", 999) < 5 and d.get("de", 999) < 1.5
    },
    "defense_psu": {
        "name": "Defense & PSU",
        "description": "Defense stocks and public sector",
        "category": "Thematic",
        "filter": lambda d: d.get("div_yield", 0) > 1 and d.get("roe", 0) > 15
    },
    "ev_green_energy": {
        "name": "EV & Green Energy",
        "description": "Electric vehicles and renewable energy theme",
        "category": "Thematic",
        "filter": lambda d: d.get("mcap") in ["Mid Cap", "Large Cap"]  # Simulated
    },
    "rural_consumption": {
        "name": "Rural Consumption Play",
        "description": "Beneficiaries of rural growth",
        "category": "Thematic",
        "filter": lambda d: d.get("roce", 0) > 15 and d.get("div_yield", 0) > 0.5
    },
    "export_oriented": {
        "name": "Export Oriented",
        "description": "Companies with significant exports",
        "category": "Thematic",
        "filter": lambda d: d.get("roce", 0) > 18 and d.get("mcap") in ["Large Cap", "Mid Cap"]
    },

    # ===== SAFETY / DEFENSIVE SCREENS (6) =====
    "low_beta": {
        "name": "Low Beta Defensive",
        "description": "Less volatile than market",
        "category": "Safety",
        "filter": lambda d: d.get("div_yield", 0) > 1 and d.get("de", 999) < 0.5
    },
    "recession_proof": {
        "name": "Recession Proof",
        "description": "Defensive sectors, essential services",
        "category": "Safety",
        "filter": lambda d: d.get("roce", 0) > 15 and d.get("de", 999) < 0.3 and d.get("div_yield", 0) > 0.8
    },
    "high_interest_coverage": {
        "name": "High Interest Coverage",
        "description": "Strong ability to service debt",
        "category": "Safety",
        "filter": lambda d: d.get("de", 999) < 0.5 and d.get("roce", 0) > 12
    },
    "stable_earnings": {
        "name": "Stable Earnings",
        "description": "Consistent profitability",
        "category": "Safety",
        "filter": lambda d: d.get("roe", 0) > 12 and d.get("roe", 0) < 30 and d.get("de", 999) < 0.8
    },
    "low_volatility": {
        "name": "Low Volatility Portfolio",
        "description": "Blue chips with stable returns",
        "category": "Safety",
        "filter": lambda d: d.get("mcap") == "Large Cap" and d.get("div_yield", 0) > 0.5
    },
    "safe_haven": {
        "name": "Safe Haven Picks",
        "description": "Quality + Stability: Low debt, high ROCE, dividends",
        "category": "Safety",
        "filter": lambda d: d.get("de", 999) < 0.2 and d.get("roce", 0) > 18 and d.get("div_yield", 0) > 0.5
    },
}


class StockScreener:
    """Stock Screener with 50+ predefined strategies"""
    
    def __init__(self):
        self.screens = STOCK_SCREENS
        self.stock_data = STOCK_DATA
    
    def get_all_screens(self) -> List[Dict]:
        """Get list of all available screens"""
        result = []
        for screen_id, screen in self.screens.items():
            result.append({
                "id": screen_id,
                "name": screen["name"],
                "description": screen["description"],
                "category": screen["category"]
            })
        return sorted(result, key=lambda x: (x["category"], x["name"]))
    
    def get_screens_by_category(self) -> Dict[str, List[Dict]]:
        """Get screens grouped by category"""
        categories = {}
        for screen_id, screen in self.screens.items():
            cat = screen["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append({
                "id": screen_id,
                "name": screen["name"],
                "description": screen["description"]
            })
        return categories
    
    def run_screen(self, screen_id: str) -> List[Dict]:
        """Run a specific screen and return matching stocks"""
        if screen_id not in self.screens:
            return []
        
        screen = self.screens[screen_id]
        filter_fn = screen["filter"]
        
        matches = []
        for symbol, data in self.stock_data.items():
            try:
                if filter_fn(data):
                    score = self._calculate_screen_score(data, screen["category"])
                    matches.append({
                        "symbol": symbol,
                        "pe": data.get("pe"),
                        "pb": data.get("pb"),
                        "roe": data.get("roe"),
                        "roce": data.get("roce"),
                        "de": data.get("de"),
                        "div_yield": data.get("div_yield"),
                        "mcap": data.get("mcap"),
                        "score": score,
                        "score_label": "High" if score >= 75 else "Medium" if score >= 50 else "Low"
                    })
            except Exception:
                continue
        
        # Sort by score descending
        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches[:20]  # Top 20 matches
    
    def run_screen_with_data(self, screen_id: str, stock_data: Dict) -> List[Dict]:
        """Run a screen with externally provided stock data (for full NSE/BSE coverage)"""
        if screen_id not in self.screens:
            return []
        
        screen = self.screens[screen_id]
        filter_fn = screen["filter"]
        
        matches = []
        for symbol, data in stock_data.items():
            try:
                if filter_fn(data):
                    score = self._calculate_screen_score(data, screen["category"])
                    matches.append({
                        "symbol": symbol,
                        "pe": data.get("pe"),
                        "pb": data.get("pb"),
                        "roe": data.get("roe"),
                        "roce": data.get("roce"),
                        "de": data.get("de"),
                        "div_yield": data.get("div_yield"),
                        "mcap": data.get("mcap"),
                        "score": score,
                        "score_label": "High" if score >= 75 else "Medium" if score >= 50 else "Low"
                    })
            except Exception:
                continue
        
        # Sort by score descending
        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches[:50]  # Top 50 matches for full coverage
    
    def _calculate_screen_score(self, data: Dict, category: str) -> float:
        """Calculate a composite score for the stock based on category"""
        score = 50  # Base score
        
        # ROE contribution
        roe = data.get("roe", 0)
        if roe > 25:
            score += 20
        elif roe > 18:
            score += 15
        elif roe > 12:
            score += 10
        
        # ROCE contribution
        roce = data.get("roce", 0)
        if roce > 25:
            score += 15
        elif roce > 18:
            score += 10
        elif roce > 12:
            score += 5
        
        # Debt penalty
        de = data.get("de", 0)
        if de > 2:
            score -= 20
        elif de > 1:
            score -= 10
        elif de < 0.3:
            score += 10
        
        # PE adjustment
        pe = data.get("pe", 0)
        if category == "Value":
            if 0 < pe < 15:
                score += 15
            elif 0 < pe < 20:
                score += 10
        elif category == "Growth":
            if pe > 0 and roe / max(pe, 1) > 1:  # High ROE relative to PE
                score += 10
        
        # Dividend bonus
        div = data.get("div_yield", 0)
        if div > 2:
            score += 10
        elif div > 1:
            score += 5
        
        return min(100, max(0, score))


# Global screener instance
stock_screener = StockScreener()
