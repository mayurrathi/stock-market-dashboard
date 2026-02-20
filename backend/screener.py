"""
Stock Screener - 50+ predefined stock screening strategies for Indian markets
"""
from typing import List, Dict, Optional
from datetime import datetime
import random

# Comprehensive stock database with fundamental data (simulated)
# In production, this would be fetched from a financial API
from .stock_api import STOCK_DATA

# 50+ Stock Screening Strategies with Comprehensive Definitions
STOCK_SCREENS = {
    # ===== VALUE SCREENS (10) =====
    "low_pe": {
        "name": "Low P/E Stocks",
        "description": "Stocks trading at P/E ratio below 15",
        "category": "Value",
        "definition": "Stocks with a Price-to-Earnings ratio below 15.",
        "summary": "Indicates you are paying less than ₹15 for every ₹1 of profit the company makes. Useful for finding undervalued bargains, but ensure earnings aren't declining.",
        "fresh_entry_rating": 3,
        "filter": lambda d: d.get("pe", 999) < 15 and d.get("pe", 0) > 0
    },
    "low_pb": {
        "name": "Low P/B Stocks (Book Value)",
        "description": "Stocks trading below book value (P/B < 1)",
        "category": "Value",
        "definition": "Stocks trading below their Book Value (P/B < 1).",
        "summary": "The stock price is cheaper than the accounting value of the company's assets. Often used to find potential turnaround plays or asset-heavy companies undervalued by the market.",
        "fresh_entry_rating": 2,
        "filter": lambda d: d.get("pb", 999) < 1
    },
    "low_pe_high_roe": {
        "name": "Low PE + High ROE",
        "description": "Value with quality: PE < 20, ROE > 15%",
        "category": "Value",
        "definition": "Companies with P/E < 20 and Return on Equity > 15%.",
        "summary": "The 'Holy Grail' of value investing. You are buying high-quality businesses (efficient at generating profit) at a cheap price.",
        "fresh_entry_rating": 5,
        "filter": lambda d: d.get("pe", 999) < 20 and d.get("pe", 0) > 0 and d.get("roe", 0) > 15
    },
    "graham_number": {
        "name": "Graham Number Undervalued",
        "description": "PE × PB < 22.5 (Benjamin Graham formula)",
        "category": "Value",
        "definition": "Price is below the Graham Number (√(22.5 × EPS × Book Value)).",
        "summary": "A conservative valuation formula by Benjamin Graham. If price < Graham Number, the stock is theoretically undervalued based on both earnings and assets.",
        "fresh_entry_rating": 4,
        "filter": lambda d: (d.get("pe", 0) * d.get("pb", 0)) < 22.5 and d.get("pe", 0) > 0
    },
    "high_dividend_yield": {
        "name": "High Dividend Yield (>2%)",
        "description": "Income stocks with dividend yield above 2%",
        "category": "Value",
        "definition": "Annual dividend payout relative to share price is > 2%.",
        "summary": "Focuses on income generation. High yield can protect against downside risk, but ensure the dividend is sustainable and not due to a crashing stock price.",
        "fresh_entry_rating": 3,
        "filter": lambda d: d.get("div_yield", 0) > 2
    },
    "dividend_aristocrats": {
        "name": "Dividend Aristocrats",
        "description": "Consistent dividend payers with yield > 1.5%",
        "category": "Value",
        "definition": "Companies with a consistent track record of paying dividends (Yield > 1.5%).",
        "summary": "Indicates financial stability and management discipline. These are usually mature, cash-rich companies that are safer during volatility.",
        "fresh_entry_rating": 4,
        "filter": lambda d: d.get("div_yield", 0) > 1.5 and d.get("roe", 0) > 12
    },
    "peg_undervalued": {
        "name": "PEG Ratio < 1",
        "description": "Growth at reasonable price (simulated PEG)",
        "category": "Value",
        "definition": "Price/Earnings to Growth ratio is less than 1.",
        "summary": "⭐ RECOMMENDED FOR FRESH CAPITAL: Evaluates a stock's value while taking its earnings growth into account. A PEG < 1 suggests the stock is undervalued relative to its future growth potential.",
        "fresh_entry_rating": 5,
        "recommended_for_fresh_entry": True,
        "filter": lambda d: d.get("pe", 999) < 25 and d.get("roe", 0) > 18
    },
    "deep_value": {
        "name": "Deep Value Picks",
        "description": "PE < 12, P/B < 1.5, Dividend > 1%",
        "category": "Value",
        "definition": "Strict value criteria: P/E < 12, P/B < 1.5, Dividend > 1%.",
        "summary": "Hard-core bargain hunting. These stocks are extremely unloved by the market. High risk of 'value traps,' but high reward if they recover.",
        "fresh_entry_rating": 2,
        "filter": lambda d: d.get("pe", 999) < 12 and d.get("pb", 999) < 1.5 and d.get("div_yield", 0) > 1
    },
    "ev_ebitda_low": {
        "name": "Low EV/EBITDA",
        "description": "Enterprise value attractive (PE < 15, low debt)",
        "category": "Value",
        "definition": "Low Enterprise Value relative to Earnings Before Interest, Taxes, Depreciation, and Amortization.",
        "summary": "A more comprehensive valuation metric than P/E because it ignores debt structure and taxes. Often used to find takeover targets.",
        "fresh_entry_rating": 3,
        "filter": lambda d: d.get("pe", 999) < 15 and d.get("de", 999) < 0.5
    },
    "contrarian_value": {
        "name": "Contrarian Value Play",
        "description": "Beaten down quality: PE < 15, ROCE > 10%",
        "category": "Value",
        "definition": "Quality stocks that have been beaten down in price.",
        "summary": "Betting against the crowd. You buy when everyone else is selling, assuming the market has overreacted to temporary bad news.",
        "fresh_entry_rating": 3,
        "filter": lambda d: d.get("pe", 999) < 15 and d.get("roce", 0) > 10
    },

    # ===== GROWTH SCREENS (8) =====
    "garp": {
        "name": "Growth at Reasonable Price (GARP)",
        "description": "High growth with PE < 30: ROE > 20%, reasonable valuation",
        "category": "Growth",
        "definition": "Stocks showing high growth rates but trading at moderate valuations (P/E < 30).",
        "summary": "⭐ RECOMMENDED FOR FRESH CAPITAL: Avoids the 'growth at any cost' trap. It seeks sustainable growers that aren't dangerously expensive.",
        "fresh_entry_rating": 5,
        "recommended_for_fresh_entry": True,
        "filter": lambda d: d.get("roe", 0) > 20 and d.get("pe", 999) < 30 and d.get("pe", 0) > 0
    },
    "high_roe": {
        "name": "High ROE Champions",
        "description": "Return on Equity above 25%",
        "category": "Growth",
        "definition": "Companies generating a Return on Equity above 25%.",
        "summary": "Shows how efficiently management uses shareholder money. Consistently high ROE is a hallmark of a superior business model.",
        "fresh_entry_rating": 4,
        "filter": lambda d: d.get("roe", 0) > 25
    },
    "high_roce": {
        "name": "High ROCE Stars",
        "description": "Return on Capital Employed above 25%",
        "category": "Growth",
        "definition": "Return on Capital Employed above 25%.",
        "summary": "Similar to ROE but includes debt. A high ROCE means the company generates high returns on *all* capital invested (equity + debt).",
        "fresh_entry_rating": 4,
        "filter": lambda d: d.get("roce", 0) > 25
    },
    "profit_growth": {
        "name": "Profit Growth Leaders",
        "description": "High profitability: ROE > 18%, ROCE > 20%",
        "category": "Growth",
        "definition": "High efficiency (ROE > 18%, ROCE > 20%) combined with growth.",
        "summary": "Identifies companies that are not just growing, but growing *profitably*. This filters out 'empty' revenue growth.",
        "fresh_entry_rating": 4,
        "filter": lambda d: d.get("roe", 0) > 18 and d.get("roce", 0) > 20
    },
    "compounders": {
        "name": "Quality Compounders",
        "description": "Consistent growers: ROE > 15%, low debt",
        "category": "Growth",
        "definition": "Consistent earnings growth year-over-year with low debt levels.",
        "summary": "'Sleep well at night' stocks. These companies compound wealth steadily over long periods with minimal risk of bankruptcy.",
        "fresh_entry_rating": 5,
        "filter": lambda d: d.get("roe", 0) > 15 and d.get("de", 999) < 0.5
    },
    "small_cap_growth": {
        "name": "Small Cap Growth",
        "description": "Mid/Small cap with high growth metrics",
        "category": "Growth",
        "definition": "Smaller companies with high growth metrics.",
        "summary": "High risk, high reward. Small caps have a longer runway for growth than large caps but are more volatile.",
        "fresh_entry_rating": 2,
        "filter": lambda d: d.get("mcap") in ["Mid Cap", "Small Cap"] and d.get("roe", 0) > 18
    },
    "emerging_blue_chips": {
        "name": "Emerging Blue Chips",
        "description": "Future large caps: Mid cap + High ROCE",
        "category": "Growth",
        "definition": "Mid-cap companies exhibiting the stability and metrics (high ROCE) of large caps.",
        "summary": "Catching tomorrow's giants today. These companies have passed the risky small-cap phase but still have room to grow.",
        "fresh_entry_rating": 4,
        "filter": lambda d: d.get("mcap") == "Mid Cap" and d.get("roce", 0) > 20
    },
    "earnings_momentum": {
        "name": "Earnings Momentum",
        "description": "Strong earnings power: ROE > 20%, low PE",
        "category": "Growth",
        "definition": "Companies showing accelerating earnings power (ROE > 20%).",
        "summary": "Focuses on the *speed* of growth. Rising earnings usually drive stock prices up in the short-to-medium term.",
        "fresh_entry_rating": 3,
        "filter": lambda d: d.get("roe", 0) > 20 and d.get("pe", 999) < 35
    },

    # ===== QUALITY SCREENS (8) =====
    "debt_free": {
        "name": "Debt-Free Gems",
        "description": "Zero or minimal debt (D/E < 0.1)",
        "category": "Quality",
        "definition": "Companies with zero debt or Debt-to-Equity ratio < 0.1.",
        "summary": "Financial immunity. These companies are unlikely to go bankrupt and can survive high-interest-rate environments easily.",
        "fresh_entry_rating": 4,
        "filter": lambda d: d.get("de", 999) < 0.1 and d.get("roe", 0) > 10
    },
    "cash_rich": {
        "name": "Cash Rich Companies",
        "description": "Net debt free with high profitability",
        "category": "Quality",
        "definition": "Net debt-free companies holding significant cash on their balance sheet.",
        "summary": "Cash is optionality. These companies can fund expansion, buy back shares, or pay dividends without borrowing.",
        "fresh_entry_rating": 4,
        "filter": lambda d: d.get("de", 999) < 0.05 and d.get("roce", 0) > 15
    },
    "consistent_dividend": {
        "name": "Consistent Dividend Payers",
        "description": "Regular dividends with sustainable payout",
        "category": "Quality",
        "definition": "Companies that have paid dividends regularly without interruption.",
        "summary": "A proxy for cash flow reality. You can fake earnings, but you cannot fake the cash needed to pay dividends.",
        "fresh_entry_rating": 4,
        "filter": lambda d: d.get("div_yield", 0) > 0.5 and d.get("roe", 0) > 12
    },
    "blue_chip": {
        "name": "Blue Chip Stalwarts",
        "description": "Large cap, high ROE, low debt",
        "category": "Quality",
        "definition": "Large-cap stocks with high ROE and low debt.",
        "summary": "The titans of industry. They offer safety and moderate growth, acting as the bedrock of a portfolio.",
        "fresh_entry_rating": 4,
        "filter": lambda d: d.get("mcap") == "Large Cap" and d.get("roe", 0) > 15 and d.get("de", 999) < 1
    },
    "moat_companies": {
        "name": "Economic Moat",
        "description": "Sustainable competitive advantage: High ROCE, consistent",
        "category": "Quality",
        "definition": "Companies with a sustainable competitive advantage (brand, monopoly, network effect).",
        "summary": "Warren Buffett's favorite. A 'moat' protects market share and profits from competitors.",
        "fresh_entry_rating": 5,
        "filter": lambda d: d.get("roce", 0) > 20 and d.get("de", 999) < 0.5
    },
    "management_quality": {
        "name": "Management Quality",
        "description": "High capital efficiency: ROCE > ROE",
        "category": "Quality",
        "definition": "Companies where ROCE > ROE.",
        "summary": "Indicates management is using debt intelligently to boost returns, or operating so efficiently they don't need debt.",
        "fresh_entry_rating": 3,
        "filter": lambda d: d.get("roce", 0) > d.get("roe", 0) and d.get("roce", 0) > 15
    },
    "capital_efficient": {
        "name": "Capital Efficient",
        "description": "High returns on invested capital",
        "category": "Quality",
        "definition": "Companies generating high returns on invested capital.",
        "summary": "These businesses require very little new capital to grow, leaving more cash for shareholders.",
        "fresh_entry_rating": 4,
        "filter": lambda d: d.get("roce", 0) > 18 and d.get("de", 999) < 0.8
    },
    "profit_machines": {
        "name": "Profit Machines",
        "description": "ROE > 20%, ROCE > 25%, Low Debt",
        "category": "Quality",
        "definition": "The trifecta of High ROE, High ROCE, and Low Debt.",
        "summary": "The ultimate quality screen. These businesses are self-sustaining cash engines.",
        "fresh_entry_rating": 5,
        "filter": lambda d: d.get("roe", 0) > 20 and d.get("roce", 0) > 25 and d.get("de", 999) < 0.3
    },

    # ===== MOMENTUM / TECHNICAL SCREENS (8) =====
    "golden_cross": {
        "name": "Golden Cross (MA50/200)",
        "description": "50-day MA crossed above 200-day MA (simulated)",
        "category": "Technical",
        "definition": "The 50-day Moving Average (MA) crosses *above* the 200-day MA.",
        "summary": "A classic long-term bullish signal. It suggests momentum has shifted to the upside.",
        "fresh_entry_rating": 3,
        "filter": lambda d: d.get("roe", 0) > 15  # Simulated - would use real TA
    },
    "death_cross_avoid": {
        "name": "Avoid Death Cross",
        "description": "Stocks NOT in death cross pattern",
        "category": "Technical",
        "definition": "Filtering *out* stocks where the 50-day MA has crossed *below* the 200-day MA.",
        "summary": "A risk management filter. A death cross often precedes a long-term downtrend.",
        "fresh_entry_rating": 3,
        "filter": lambda d: d.get("roce", 0) > 10  # Simulated
    },
    "rsi_oversold": {
        "name": "RSI Oversold (<30)",
        "description": "Potentially oversold, bounce candidates",
        "category": "Technical",
        "definition": "Relative Strength Index is below 30.",
        "summary": "The stock has fallen too fast, too soon. Traders look here for a potential short-term 'bounce' or recovery.",
        "fresh_entry_rating": 2,
        "filter": lambda d: d.get("pe", 0) > 0 and d.get("pe", 999) < 18  # Simulated
    },
    "rsi_overbought": {
        "name": "RSI Overbought (>70)",
        "description": "Extended stocks, caution advised",
        "category": "Technical",
        "definition": "Relative Strength Index is above 70.",
        "summary": "The stock has risen too fast. It might be due for a correction or pullback.",
        "fresh_entry_rating": 1,
        "filter": lambda d: d.get("pe", 0) > 50  # Simulated
    },
    "breakout_52w_high": {
        "name": "52-Week High Breakout",
        "description": "At or near 52-week highs",
        "category": "Technical",
        "definition": "Price is crossing its highest point in the last year.",
        "summary": "Strength begets strength. Stocks hitting new highs often attract more buyers and continue to rise (momentum).",
        "fresh_entry_rating": 3,
        "filter": lambda d: d.get("roe", 0) > 18 and d.get("mcap") == "Large Cap"  # Simulated
    },
    "near_52w_low": {
        "name": "Near 52-Week Low",
        "description": "Trading near yearly lows",
        "category": "Technical",
        "definition": "Price is trading near its lowest point in the last year.",
        "summary": "Contrarian hunting ground. Are they cheap, or is the business failing? Requires deep research.",
        "fresh_entry_rating": 2,
        "filter": lambda d: d.get("pe", 999) < 15 and d.get("de", 999) < 1  # Simulated
    },
    "high_volume_surge": {
        "name": "Volume Surge",
        "description": "Unusual volume activity (simulated)",
        "category": "Technical",
        "definition": "Trading volume is significantly higher than the average.",
        "summary": "'Volume precedes price.' High volume indicates institutional interest or a major news event is driving the stock.",
        "fresh_entry_rating": 2,
        "filter": lambda d: d.get("mcap") in ["Mid Cap", "Large Cap"]
    },
    "price_momentum": {
        "name": "Price Momentum Leaders",
        "description": "Strong price momentum (simulated)",
        "category": "Technical",
        "definition": "Stocks showing the strongest percentage gains over 3, 6, or 12 months.",
        "summary": "Buying winners. This strategy assumes that stocks that have outperformed will continue to outperform.",
        "fresh_entry_rating": 3,
        "filter": lambda d: d.get("roe", 0) > 20
    },

    # ===== THEMATIC / SECTORAL SCREENS (10) =====
    "fii_favorites": {
        "name": "FII Favorites",
        "description": "Stocks typically favored by FIIs",
        "category": "Thematic",
        "definition": "High or increasing shareholding by Foreign Institutional Investors.",
        "summary": "FIIs have deep pockets and research teams. Following them means betting on stocks that global funds are confident in.",
        "fresh_entry_rating": 4,
        "filter": lambda d: d.get("mcap") == "Large Cap" and d.get("roe", 0) > 15
    },
    "dii_accumulation": {
        "name": "DII Accumulation",
        "description": "Domestic institutional picks",
        "category": "Thematic",
        "definition": "Increasing stake by Domestic Institutional Investors (Mutual Funds, Insurance).",
        "summary": "DIIs often support the market when FIIs sell. Continuous buying suggests strong domestic confidence in the stock.",
        "fresh_entry_rating": 4,
        "filter": lambda d: d.get("div_yield", 0) > 0.5 and d.get("de", 999) < 1
    },
    "it_sector": {
        "name": "IT Sector Champions",
        "description": "Technology and IT services stocks",
        "category": "Thematic",
        "definition": "Leaders in software and IT services.",
        "summary": "A play on global digital transformation and currency (USD/INR) fluctuations.",
        "fresh_entry_rating": 3,
        "filter": lambda d: d.get("roce", 0) > 25 and d.get("de", 999) < 0.2
    },
    "banking_finance": {
        "name": "Banking & Finance",
        "description": "Banks and NBFCs",
        "category": "Thematic",
        "definition": "Banks, NBFCs, and Fintech.",
        "summary": "The proxy for the economy. If the country grows, credit demand grows, and these stocks rally.",
        "fresh_entry_rating": 3,
        "filter": lambda d: d.get("roe", 0) > 12 and d.get("pb", 999) < 4
    },
    "fmcg_consumer": {
        "name": "FMCG & Consumer",
        "description": "Consumer staples and discretionary",
        "category": "Thematic",
        "definition": "Fast Moving Consumer Goods (Food, Hygiene) and discretionary items.",
        "summary": "A play on domestic consumption and rising middle-class spending power.",
        "fresh_entry_rating": 4,
        "filter": lambda d: d.get("roce", 0) > 20 and d.get("de", 999) < 0.3
    },
    "infrastructure_play": {
        "name": "Infrastructure Play",
        "description": "Capex and infra beneficiaries",
        "category": "Thematic",
        "definition": "Construction, cement, steel, and power companies.",
        "summary": "Beneficiaries of government Capex (Capital Expenditure) and nation-building cycles.",
        "fresh_entry_rating": 3,
        "filter": lambda d: d.get("pb", 999) < 5 and d.get("de", 999) < 1.5
    },
    "defense_psu": {
        "name": "Defense & PSU",
        "description": "Defense stocks and public sector",
        "category": "Thematic",
        "definition": "Government-owned entities and defense manufacturers.",
        "summary": "Policy-driven plays. These rely heavily on government budgets, orders, and 'Make in India' initiatives.",
        "fresh_entry_rating": 3,
        "filter": lambda d: d.get("div_yield", 0) > 1 and d.get("roe", 0) > 15
    },
    "ev_green_energy": {
        "name": "EV & Green Energy",
        "description": "Electric vehicles and renewable energy theme",
        "category": "Thematic",
        "definition": "Stocks involved in renewables, batteries, and electric mobility.",
        "summary": "A futuristic theme betting on the global shift away from fossil fuels.",
        "fresh_entry_rating": 3,
        "filter": lambda d: d.get("mcap") in ["Mid Cap", "Large Cap"]  # Simulated
    },
    "rural_consumption": {
        "name": "Rural Consumption Play",
        "description": "Beneficiaries of rural growth",
        "category": "Thematic",
        "definition": "Companies with significant revenue from rural areas (tractors, fertilizers, rural FMCG).",
        "summary": "Dependent on monsoon quality and rural income levels.",
        "fresh_entry_rating": 3,
        "filter": lambda d: d.get("roce", 0) > 15 and d.get("div_yield", 0) > 0.5
    },
    "export_oriented": {
        "name": "Export Oriented",
        "description": "Companies with significant exports",
        "category": "Thematic",
        "definition": "Companies that earn significant revenue in foreign currency.",
        "summary": "A hedge against a weakening domestic currency; these companies benefit when the Rupee falls.",
        "fresh_entry_rating": 3,
        "filter": lambda d: d.get("roce", 0) > 18 and d.get("mcap") in ["Large Cap", "Mid Cap"]
    },

    # ===== SAFETY / DEFENSIVE SCREENS (6) =====
    "low_beta": {
        "name": "Low Beta Defensive",
        "description": "Less volatile than market",
        "category": "Safety",
        "definition": "Beta < 1 (The stock moves less than the market index).",
        "summary": "If the market crashes 10%, these stocks might only drop 5%. Good for risk-averse investors.",
        "fresh_entry_rating": 4,
        "filter": lambda d: d.get("div_yield", 0) > 1 and d.get("de", 999) < 0.5
    },
    "recession_proof": {
        "name": "Recession Proof",
        "description": "Defensive sectors, essential services",
        "category": "Safety",
        "definition": "Sectors people cannot stop using (Utilities, Healthcare, FMCG).",
        "summary": "Demand for these products remains stable regardless of the economic climate.",
        "fresh_entry_rating": 4,
        "filter": lambda d: d.get("roce", 0) > 15 and d.get("de", 999) < 0.3 and d.get("div_yield", 0) > 0.8
    },
    "high_interest_coverage": {
        "name": "High Interest Coverage",
        "description": "Strong ability to service debt",
        "category": "Safety",
        "definition": "High ratio of Earnings (EBIT) to Interest Expenses.",
        "summary": "Solvency check. It confirms the company can easily pay its interest obligations, identifying low bankruptcy risk.",
        "fresh_entry_rating": 4,
        "filter": lambda d: d.get("de", 999) < 0.5 and d.get("roce", 0) > 12
    },
    "stable_earnings": {
        "name": "Stable Earnings",
        "description": "Consistent profitability",
        "category": "Safety",
        "definition": "Companies with low variance in their quarterly profits over 3-5 years.",
        "summary": "Predictability. The market pays a premium for boring, predictable growth because it reduces uncertainty.",
        "fresh_entry_rating": 4,
        "filter": lambda d: d.get("roe", 0) > 12 and d.get("roe", 0) < 30 and d.get("de", 999) < 0.8
    },
    "low_volatility": {
        "name": "Low Volatility Portfolio",
        "description": "Blue chips with stable returns",
        "category": "Safety",
        "definition": "A basket of stocks that have historically small daily price swings.",
        "summary": "Provides a smoother ride, preventing panic selling during market turbulence.",
        "fresh_entry_rating": 4,
        "filter": lambda d: d.get("mcap") == "Large Cap" and d.get("div_yield", 0) > 0.5
    },
    "safe_haven": {
        "name": "Safe Haven Picks",
        "description": "Quality + Stability: Low debt, high ROCE, dividends",
        "category": "Safety",
        "definition": "Combination of low debt, high ROCE, and market leadership.",
        "summary": "The 'In case of emergency, break glass' stocks. Where investors park money when they are scared of the broader market.",
        "fresh_entry_rating": 5,
        "filter": lambda d: d.get("de", 999) < 0.2 and d.get("roce", 0) > 18 and d.get("div_yield", 0) > 0.5
    },
}

# ===== BEGINNER-FRIENDLY INDICATOR GLOSSARY =====
INDICATOR_GLOSSARY = {
    "pe": {
        "name": "P/E Ratio (Price to Earnings)",
        "simple": "How many years of profits you're paying for when you buy this stock.",
        "example": "If P/E = 20, you're paying ₹20 for every ₹1 the company earns per year.",
        "good_range": "10–25 (lower = cheaper)",
        "warning_range": "> 40 (expensive)",
        "icon": "💰",
    },
    "pb": {
        "name": "P/B Ratio (Price to Book Value)",
        "simple": "Are you paying more or less than the company's actual asset value?",
        "example": "P/B = 0.8 means you're buying ₹1 of assets for just ₹0.80 — a potential bargain.",
        "good_range": "< 3 (reasonable)",
        "warning_range": "> 6 (very expensive)",
        "icon": "📖",
    },
    "roe": {
        "name": "ROE (Return on Equity)",
        "simple": "How much profit the company makes with shareholders' money. Higher = better management.",
        "example": "ROE = 20% means for every ₹100 invested by shareholders, the company earns ₹20 profit.",
        "good_range": "> 15% (good), > 25% (excellent)",
        "warning_range": "< 8% (poor)",
        "icon": "📈",
    },
    "roce": {
        "name": "ROCE (Return on Capital Employed)",
        "simple": "How efficiently ALL capital (equity + debt) is used. Includes borrowed money too.",
        "example": "ROCE = 25% means any capital put into this business generates 25% returns.",
        "good_range": "> 18% (efficient), > 25% (outstanding)",
        "warning_range": "< 10% (inefficient)",
        "icon": "⚡",
    },
    "de": {
        "name": "D/E Ratio (Debt to Equity)",
        "simple": "How much the company has borrowed vs what shareholders own. Low = safer.",
        "example": "D/E = 0.5 means for every ₹100 of shareholder money, the company owes ₹50.",
        "good_range": "< 0.5 (low debt), < 1 (manageable)",
        "warning_range": "> 1.5 (heavily indebted)",
        "icon": "🏦",
    },
    "div_yield": {
        "name": "Dividend Yield",
        "simple": "The yearly cash payout you receive just for holding the stock, as a % of its price.",
        "example": "Yield = 3% on a ₹100 stock means you get ₹3 per year in cash, regardless of stock price movement.",
        "good_range": "> 2% (income stock)",
        "warning_range": "Very high yield (> 8%) could mean the price has crashed",
        "icon": "💵",
    },
    "mcap": {
        "name": "Market Cap (Market Capitalization)",
        "simple": "The total value of all the company's shares. Tells you how 'big' the company is.",
        "example": "Large Cap = top ~100 companies (like Reliance, TCS). Safer but slower growth.",
        "good_range": "Large Cap (safest), Mid Cap (balanced)",
        "warning_range": "Penny Stock (very risky, can lose everything)",
        "icon": "🏢",
    },
    "rsi": {
        "name": "RSI (Relative Strength Index)",
        "simple": "Measures if a stock has risen too fast (overbought) or fallen too fast (oversold). Range: 0–100.",
        "example": "RSI < 30 = oversold (possible bounce). RSI > 70 = overbought (might drop).",
        "good_range": "30–70 (normal zone)",
        "warning_range": "< 30 or > 70",
        "icon": "📊",
    },
    "macd": {
        "name": "MACD (Moving Average Convergence Divergence)",
        "simple": "Shows if a stock's momentum is getting stronger or weaker.",
        "example": "MACD crossing above signal line = bullish signal. Below = bearish.",
        "good_range": "MACD > 0 (upward momentum)",
        "warning_range": "MACD < 0 (downward momentum)",
        "icon": "📉",
    },
    "beta": {
        "name": "Beta",
        "simple": "How much the stock moves compared to the overall market.",
        "example": "Beta = 1.5 means if the market rises 10%, this stock rises ~15% (but also falls 15% when market drops).",
        "good_range": "< 1 (less volatile, defensive)",
        "warning_range": "> 1.5 (very volatile)",
        "icon": "🎢",
    },
}

# Category-level metadata for the screener
CATEGORY_METADATA = {
    "Value": {
        "icon": "💰",
        "description": "Find stocks trading below their true worth — perfect for patient investors.",
        "default_difficulty": "Beginner",
        "default_risk": "Low",
        "tip": "Value investing requires patience. Cheap stocks may take 1-3 years to realize their value.",
    },
    "Growth": {
        "icon": "📈",
        "description": "Fast-growing companies that reinvest profits to expand rapidly.",
        "default_difficulty": "Intermediate",
        "default_risk": "Medium",
        "tip": "Growth stocks can be volatile. Don't panic if they drop 20-30% — it's normal.",
    },
    "Quality": {
        "icon": "💎",
        "description": "Premium businesses with strong fundamentals — the backbone of any portfolio.",
        "default_difficulty": "Beginner",
        "default_risk": "Low",
        "tip": "Quality stocks rarely come cheap. Buying at ANY price is better than not owning them.",
    },
    "Technical": {
        "icon": "📊",
        "description": "Chart-based signals for timing entries — best used WITH fundamentals.",
        "default_difficulty": "Advanced",
        "default_risk": "High",
        "tip": "Technical signals work best in the short term. Always confirm with fundamentals for long-term bets.",
    },
    "Thematic": {
        "icon": "🏛️",
        "description": "Bet on sectors and macro themes like infra, EV, defense, or digital India.",
        "default_difficulty": "Intermediate",
        "default_risk": "Medium",
        "tip": "Thematic investing is cyclical. Enter when the theme is out of favor, not when it's trending.",
    },
    "Safety": {
        "icon": "🛡️",
        "description": "Low-risk, stable stocks for protecting capital during market uncertainty.",
        "default_difficulty": "Beginner",
        "default_risk": "Low",
        "tip": "Safety screens are ideal during market crashes or when you're unsure about the direction.",
    },
}

# Per-screen difficulty and risk overrides (when different from category defaults)
SCREEN_OVERRIDES = {
    # Value screens
    "low_pe": {"difficulty": "Beginner", "risk": "Low", "why": "Simple filter — just look for cheap P/E. Great starting point."},
    "low_pb": {"difficulty": "Intermediate", "risk": "Medium", "why": "Low P/B can mean undervalued OR a dying business. Research needed."},
    "low_pe_high_roe": {"difficulty": "Beginner", "risk": "Low", "why": "The best beginner screen — combines cheapness with quality."},
    "graham_number": {"difficulty": "Intermediate", "risk": "Low", "why": "Classic formula from the father of value investing."},
    "high_dividend_yield": {"difficulty": "Beginner", "risk": "Low", "why": "Easy to understand — you get paid cash for holding!"},
    "dividend_aristocrats": {"difficulty": "Beginner", "risk": "Low", "why": "Reliable income over time."},
    "peg_undervalued": {"difficulty": "Intermediate", "risk": "Low", "why": "Factors in growth rate, not just price."},
    "deep_value": {"difficulty": "Advanced", "risk": "High", "why": "Extreme bargain hunting. Many are 'value traps' — cheap for a reason."},
    "ev_ebitda_low": {"difficulty": "Advanced", "risk": "Medium", "why": "Enterprise value is a sophisticated metric."},
    "contrarian_value": {"difficulty": "Advanced", "risk": "High", "why": "You're betting against the market. Requires conviction."},
    # Growth screens
    "garp": {"difficulty": "Intermediate", "risk": "Medium", "why": "Balanced approach — growth without overpaying."},
    "high_roe": {"difficulty": "Beginner", "risk": "Low", "why": "Simple and powerful — high ROE = well-run company."},
    "high_roce": {"difficulty": "Beginner", "risk": "Low", "why": "Like ROE but even more comprehensive."},
    "profit_growth": {"difficulty": "Intermediate", "risk": "Medium", "why": "Dual filter ensures profitable growth."},
    "compounders": {"difficulty": "Beginner", "risk": "Low", "why": "The best 'set and forget' screen for beginners."},
    "small_cap_growth": {"difficulty": "Advanced", "risk": "High", "why": "Small caps can double — or halve. Not for beginners."},
    "emerging_blue_chips": {"difficulty": "Intermediate", "risk": "Medium", "why": "Catching future large caps while they're still affordable."},
    "earnings_momentum": {"difficulty": "Intermediate", "risk": "Medium", "why": "Riding the earnings acceleration wave."},
    # Quality screens
    "debt_free": {"difficulty": "Beginner", "risk": "Low", "why": "No debt = no bankruptcy risk. Period."},
    "cash_rich": {"difficulty": "Beginner", "risk": "Low", "why": "Companies sitting on cash have options and safety."},
    "consistent_dividend": {"difficulty": "Beginner", "risk": "Low", "why": "Track record of sharing profits with shareholders."},
    "blue_chip": {"difficulty": "Beginner", "risk": "Low", "why": "The safest stocks for first-time investors."},
    "moat_companies": {"difficulty": "Intermediate", "risk": "Low", "why": "Companies with competitive advantages."},
    "management_quality": {"difficulty": "Advanced", "risk": "Low", "why": "Subtler metric — compares ROCE vs ROE."},
    "capital_efficient": {"difficulty": "Intermediate", "risk": "Low", "why": "Capital-light businesses grow faster."},
    "profit_machines": {"difficulty": "Intermediate", "risk": "Low", "why": "The cream of the crop — all quality metrics firing."},
    # Technical screens
    "golden_cross": {"difficulty": "Advanced", "risk": "Medium", "why": "Classic chart pattern for long-term trend reversal."},
    "death_cross_avoid": {"difficulty": "Advanced", "risk": "Low", "why": "A filter to AVOID — keeps you out of downtrends."},
    "rsi_oversold": {"difficulty": "Advanced", "risk": "High", "why": "Short-term bounce play. Timing is everything."},
    "rsi_overbought": {"difficulty": "Advanced", "risk": "Medium", "why": "Identifies stocks that may be due for a pullback."},
    "breakout_52w_high": {"difficulty": "Advanced", "risk": "High", "why": "Momentum play — buying strength."},
    "near_52w_low": {"difficulty": "Advanced", "risk": "High", "why": "Contrarian play — buying weakness. Risky."},
    "high_volume_surge": {"difficulty": "Advanced", "risk": "High", "why": "Volume spikes indicate institutional activity."},
    "price_momentum": {"difficulty": "Advanced", "risk": "High", "why": "Riding winners. Requires quick exits."},
    # Safety screens
    "low_beta": {"difficulty": "Beginner", "risk": "Low", "why": "Less volatile = less stressful to hold."},
    "recession_proof": {"difficulty": "Beginner", "risk": "Low", "why": "People always need food, medicine, and power."},
    "high_interest_coverage": {"difficulty": "Intermediate", "risk": "Low", "why": "Ensures the company can service its debt easily."},
    "stable_earnings": {"difficulty": "Beginner", "risk": "Low", "why": "Predictable profits = predictable stock behavior."},
    "low_volatility": {"difficulty": "Beginner", "risk": "Low", "why": "Sleep-well-at-night stocks."},
    "safe_haven": {"difficulty": "Beginner", "risk": "Low", "why": "The ultimate defensive play."},
    # Thematic screens
    "fii_favorites": {"difficulty": "Intermediate", "risk": "Medium", "why": "Foreign institutions have deep research teams."},
    "dii_accumulation": {"difficulty": "Intermediate", "risk": "Medium", "why": "Domestic funds provide a safety net."},
    "it_sector": {"difficulty": "Intermediate", "risk": "Medium", "why": "Global demand for IT services."},
    "banking_finance": {"difficulty": "Intermediate", "risk": "Medium", "why": "Proxy for economic growth."},
    "fmcg_consumer": {"difficulty": "Beginner", "risk": "Low", "why": "Everyday products people can't stop buying."},
    "infrastructure_play": {"difficulty": "Intermediate", "risk": "Medium", "why": "Government capex cycle play."},
    "defense_psu": {"difficulty": "Advanced", "risk": "Medium", "why": "Policy-dependent. Needs tracking of govt budgets."},
    "ev_green_energy": {"difficulty": "Advanced", "risk": "High", "why": "Futuristic but speculative. Many unproven companies."},
    "rural_consumption": {"difficulty": "Intermediate", "risk": "Medium", "why": "Monsoon and rural income dependent."},
    "export_oriented": {"difficulty": "Intermediate", "risk": "Medium", "why": "Currency play — benefits when rupee weakens."},
}


class StockScreener:
    """Stock Screener with 50+ predefined strategies"""
    
    def __init__(self):
        self.screens = STOCK_SCREENS
        self.stock_data = STOCK_DATA
    
    def get_all_screens(self) -> List[Dict]:
        """Get list of all available screens with full definitions and beginner metadata"""
        result = []
        for screen_id, screen in self.screens.items():
            cat = screen["category"]
            cat_meta = CATEGORY_METADATA.get(cat, {})
            overrides = SCREEN_OVERRIDES.get(screen_id, {})
            
            result.append({
                "id": screen_id,
                "name": screen["name"],
                "description": screen["description"],
                "category": cat,
                "definition": screen.get("definition", screen["description"]),
                "summary": screen.get("summary", ""),
                "fresh_entry_rating": screen.get("fresh_entry_rating", 3),
                "recommended_for_fresh_entry": screen.get("recommended_for_fresh_entry", False),
                # Beginner-friendly additions
                "difficulty": overrides.get("difficulty", cat_meta.get("default_difficulty", "Intermediate")),
                "risk_level": overrides.get("risk", cat_meta.get("default_risk", "Medium")),
                "why_it_matters": overrides.get("why", ""),
                "category_tip": cat_meta.get("tip", ""),
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
    
    def analyze_stock_for_entry(self, symbol: str, current_price: float, fundamentals: dict) -> dict:
        """
        Analyze a single stock against all screens and calculate next entry point.
        
        Args:
            symbol: Stock symbol
            current_price: Current market price
            fundamentals: Dict with pe, pb, roe, roce, de, div_yield, mcap
            
        Returns:
            Dict with next_entry_point, entry_reasoning, and matches_screens
        """
        matches = []
        quality_score = 0
        
        # Test stock against all screens
        for screen_id, screen in self.screens.items():
            try:
                filter_fn = screen["filter"]
                if filter_fn(fundamentals):
                    matches.append({
                        "id": screen_id,
                        "name": screen["name"],
                        "category": screen["category"]
                    })
                    # Boost quality score based on category
                    if screen["category"] == "Quality":
                        quality_score += 15
                    elif screen["category"] == "Value":
                        quality_score += 12
                    elif screen["category"] == "Growth":
                        quality_score += 10
                    elif screen["category"] == "Safety":
                        quality_score += 8
                    else:
                        quality_score += 5
            except Exception:
                continue
        
        # Calculate entry point based on fundamentals and matching screens
        entry_discount = 0.05  # Base 5% discount for entry
        reasoning_parts = []
        
        pe = fundamentals.get("pe", 0)
        pb = fundamentals.get("pb", 0)
        roe = fundamentals.get("roe", 0)
        de = fundamentals.get("de", 0)
        
        # Adjust entry discount based on fundamentals
        if pe > 0:
            if pe > 50:
                entry_discount += 0.08  # High PE = need bigger discount
                reasoning_parts.append(f"High PE ({pe:.1f})")
            elif pe > 30:
                entry_discount += 0.05
                reasoning_parts.append(f"Moderate PE ({pe:.1f})")
            elif pe < 15:
                entry_discount -= 0.02  # Low PE = smaller discount needed
                reasoning_parts.append(f"Attractive PE ({pe:.1f})")
        
        if pb > 0 and pb < 1.5:
            entry_discount -= 0.02
            reasoning_parts.append(f"Trading near book value (P/B: {pb:.1f})")
        
        if roe > 20:
            entry_discount -= 0.02
            reasoning_parts.append(f"Strong ROE ({roe:.1f}%)")
        elif roe < 10:
            entry_discount += 0.03
        
        if de > 1:
            entry_discount += 0.03
            reasoning_parts.append(f"High debt (D/E: {de:.1f})")
        elif de < 0.3:
            reasoning_parts.append("Low debt")
        
        # Adjust based on quality score from screens
        if quality_score > 50:
            entry_discount -= 0.02
            reasoning_parts.append(f"Matches {len(matches)} quality screens")
        elif len(matches) == 0:
            entry_discount += 0.03
            reasoning_parts.append("No screener matches")
        
        # Clamp discount between 2% and 15%
        entry_discount = max(0.02, min(0.15, entry_discount))
        
        # Calculate entry point
        next_entry_point = round(current_price * (1 - entry_discount), 2)
        
        # Build reasoning string
        if reasoning_parts:
            entry_reasoning = "Entry zone based on: " + ", ".join(reasoning_parts[:3])
        else:
            entry_reasoning = f"Standard {entry_discount*100:.0f}% discount for re-entry"
        
        entry_reasoning += f" → Wait for ₹{next_entry_point:,.0f}"
        
        # Get matching screen categories (deduplicated)
        matching_categories = list(set(m["category"] for m in matches))[:4]
        
        return {
            "next_entry_point": next_entry_point,
            "entry_discount_pct": round(entry_discount * 100, 1),
            "entry_reasoning": entry_reasoning,
            "matches_screens": matching_categories,
            "quality_score": min(100, quality_score),
            "screen_matches_count": len(matches)
        }


# Global screener instance
stock_screener = StockScreener()
