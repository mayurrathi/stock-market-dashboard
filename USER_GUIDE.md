# Stock Market Dashboard - User Guide

A comprehensive guide to using the Stock Market Dashboard for real-time stock analysis, Telegram signal monitoring, and AI-powered recommendations for Indian markets (NSE/BSE).

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Dashboard Overview](#dashboard-overview)
3. [Telegram Integration](#telegram-integration)
4. [Managing Sources](#managing-sources)
5. [All Star Picks](#all-star-picks)
6. [Recommendations](#recommendations)
7. [Market News](#market-news)
8. [Watchlist](#watchlist)
9. [Stock Detail Modal](#stock-detail-modal)
10. [Settings & Configuration](#settings--configuration)
11. [Troubleshooting](#troubleshooting)
12. [API Reference](#api-reference)

---

## Getting Started

### Prerequisites

- Python 3.9+
- pip (Python package manager)
- A Telegram account (for signal monitoring)
- Optional: Gemini API key (for AI-enhanced recommendations)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/mayurrathi/stock-market-dashboard.git
   cd stock-market-dashboard
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the server**
   ```bash
   sh launch.sh
   ```
   Or manually:
   ```bash
   python -m uvicorn backend.main:app --host 0.0.0.0 --port 8001
   ```

4. **Open the dashboard**
   
   Navigate to [http://localhost:8001](http://localhost:8001) in your browser.

---

## Dashboard Overview

The main dashboard provides a quick overview of market activity:

### Header Section
- **Section Title**: Shows current section name
- **Auto Refresh Toggle**: Enable/disable automatic data refresh every 32 seconds
- **Telegram Status**: Green dot = connected, Red dot = disconnected

### Index Cards
Three index cards display real-time data:
- **NIFTY 50**: NSE Nifty 50 index
- **SENSEX**: BSE Sensex index  
- **BANK NIFTY**: NSE Bank Nifty index

Each card shows:
- Current value
- Change percentage (green = positive, red = negative)

### Statistics Cards
- **Today's Signals**: Number of Telegram messages received
- **News Articles**: Number of fetched news articles
- **Active Sources**: Number of configured Telegram channels
- **Recommendations**: Number of generated recommendations

### Time Filter Shortcuts
Quick filters for data:
- **1Hr**: Last hour
- **Day**: Last 24 hours
- **Week**: Last 7 days
- **Month**: Last 30 days

---

## Telegram Integration

### Why Telegram?
Many stock analysts and tipsters share recommendations via private Telegram channels. This dashboard monitors those channels for signals.

### Setting Up Telegram

1. **Get API Credentials**
   - Visit [https://my.telegram.org](https://my.telegram.org)
   - Log in with your phone number
   - Go to "API Development Tools"
   - Create a new application
   - Note down your **API ID** and **API Hash**

2. **Configure in Dashboard**
   - Go to **Settings** section
   - Enter your **API ID** (numeric)
   - Enter your **API Hash** (alphanumeric string)
   - Enter your **Phone Number** (with country code, e.g., +91XXXXXXXXXX)
   - Click **Send Code**

3. **Verify**
   - Check your Telegram app for a verification code
   - Enter the code in the dashboard
   - Click **Verify**

4. **Success**
   - The Telegram status indicator will turn green
   - Your session is saved and will persist across restarts

### Troubleshooting Telegram

| Issue | Solution |
|-------|----------|
| Code not received | Check if Telegram app is up to date |
| Invalid credentials | Verify API ID/Hash at my.telegram.org |
| Session expired | Re-authenticate in Settings |
| 2FA required | Enter your 2FA password when prompted |

---

## Managing Sources

Sources are Telegram channels that the dashboard monitors for stock signals.

### Adding a Source

1. Go to **Sources** section
2. Click **Add Source**
3. Enter:
   - **Name**: Friendly name (e.g., "Stock Tips Channel")
   - **Channel Username**: The @username of the channel (e.g., @stocktips)
4. Click **Add**

### Fetching Messages

- Click **Fetch** on any source to pull recent messages
- Messages are analyzed for:
  - Stock symbols mentioned
  - Sentiment (bullish/bearish/neutral)
  - Price targets and stop losses

### Deleting a Source

- Click **Delete** on the source card
- Confirm the deletion

---

## All Star Picks

The "All Star Picks" section shows the **Top 10 stock recommendations** for the day.

### How It Works

1. Analyzes last 24 hours of:
   - Telegram messages
   - News articles
2. Extracts mentioned stocks
3. Calculates sentiment scores
4. Ranks by bullish mentions
5. Adds diversification picks from:
   - Large Cap stocks
   - Mid Cap stocks
   - Small Cap stocks
   - Penny stocks

### Pick Information

Each pick shows:
- **Rank**: #1 to #10
- **Symbol**: Stock ticker (e.g., RELIANCE)
- **Name**: Full company name
- **Category**: Large Cap / Mid Cap / Small Cap / Penny Stock
- **Action**: BUY / SELL / HOLD
- **Current Price**: Live price in ₹
- **Target Price**: Recommended target
- **Stop Loss**: Recommended stop loss
- **Confidence**: Percentage confidence score
- **Reasoning**: Why this stock was picked

### Validity

- Picks refresh at **3:30 PM IST** (market close) each trading day
- Timer shows when current picks expire

### Click to View Details

Click any All Star pick card to open the Stock Detail Modal.

---

## Recommendations

The Recommendations section provides stock picks across multiple timeframes.

### Timeframes

| Timeframe | Use Case |
|-----------|----------|
| **Next Day** | Intraday/swing trading |
| **Next Week** | Short-term positions |
| **Next Month** | Medium-term trading |
| **1 Year** | Investment horizon |
| **2 Years** | Mid-term investment |
| **5 Years** | Long-term wealth building |
| **10 Years** | Retirement/compounding |

### Generating Recommendations

1. Select a time filter (1Hr, Day, Week, Month)
2. Click **Fetch News** to get latest articles
3. Click **Analyze & Recommend**
4. Wait for analysis to complete
5. View recommendations by timeframe tab

### Recommendation Details

- **Symbol**: Stock ticker
- **Action**: BUY / SELL / HOLD
- **Confidence**: 0-100% score
- **Reasoning**: AI-generated explanation

---

## Market News

Aggregated news from multiple Indian financial sources.

### News Sources

- Economic Times Markets
- Economic Times Stocks
- Moneycontrol
- Business Standard
- Livemint
- Financial Express

### Features

- **Auto-fetch**: Background task fetches news every 30 minutes
- **Manual fetch**: Click **Fetch News** for immediate update
- **Stock extraction**: Mentioned stocks are tagged
- **Sentiment analysis**: Each article tagged as positive/negative/neutral

### Filtering

- Use time shortcuts (1Hr, Day, Week, Month)
- Or set custom date range and click **Apply**

### Click to View Stock

Click on any stock tag in a news article to view its details.

---

## Watchlist

Track specific stocks you're interested in.

### Adding to Watchlist

1. Open any Stock Detail Modal (click a stock)
2. Click **Add to Watchlist**
3. Optional: Set custom target price and stop loss

### Auto-Calculated Targets

If you don't set manual targets, the system calculates:
- **Target Price**: Based on 1:2 risk-reward ratio
- **Stop Loss**: Based on ATR (Average True Range) volatility

### Managing Watchlist

- View all watchlist stocks in the **Watchlist** section
- Click any stock to view full details
- Remove stocks by clicking the delete button

---

## Stock Detail Modal

A comprehensive view of any stock, accessible by clicking on:
- All Star Pick cards
- Recommendation cards
- Stock tags in news/messages
- Watchlist items

### Modal Sections

#### Header
- Stock symbol and name
- Sector and category
- Current price with change %

#### Price Chart
- 30-day price history
- Interactive line chart

#### Key Ratios
- P/E Ratio
- P/B Ratio
- ROE / ROCE
- Dividend Yield
- 52-week High/Low

#### Targets
- Recommended target price
- Stop loss level
- Potential gain/loss %

#### AI Recommendations
- Action by timeframe
- Confidence scores

#### Related News
- Recent news mentioning this stock

#### Expert AI Analysis (Expert Engine 2.0)
This section provides premium-grade analysis generated by our advanced multi-factor engine.

- **AI Verdict**: A punchy, expert-style conclusion (e.g., "💎 Hidden Gem", "🚀 Quality Compounder", "⚠️ Value Trap").
- **Analysis Tabs**:
  - **Rationale**: Detailed narrative explaining the recommendation.
  - **Bull Case 🐂**: Key arguments for why the stock price might rise (Upside Thesis).
  - **Bear Case 🐻**: Key risks and reasons why the stock might fall (Downside Thesis).
- **Factor Ratings**: Granular 0-100 scores for:
  - **Value**: Is the stock cheap regarding P/E and P/B vs peers?
  - **Growth**: Are earnings and revenues growing consistently?
  - **Safety**: Is the company financially stable (low debt, high dividends)?
  - **Quality**: Long-term reliability and market leadership.

#### External Links
Quick links to:
- [Screener.in](https://www.screener.in)
- [NSE India](https://www.nseindia.com)
- [BSE India](https://www.bseindia.com)
- [Moneycontrol](https://www.moneycontrol.com)
- [TradingView](https://www.tradingview.com)

---

## Settings & Configuration

### Telegram Configuration
See [Telegram Integration](#telegram-integration) section.

### Gemini AI (Optional)

For enhanced AI reasoning in recommendations:

1. Get API key from [Google AI Studio](https://aistudio.google.com)
2. Add to database Config table:
   - Key: `gemini_api_key`
   - Value: Your API key
3. Optional: Set custom model:
   - Key: `gemini_model`
   - Value: `gemini-pro` (default) or `gemini-1.5-pro`

---

## Troubleshooting

### Server Won't Start

```bash
# Check if port 8001 is in use
lsof -i :8001

# Kill existing process
lsof -ti:8001 | xargs kill -9

# Restart
sh launch.sh
```

### No Data Showing

1. **Fetch News**: Click the "Fetch News" button
2. **Add Sources**: Configure Telegram channels
3. **Analyze**: Click "Analyze & Recommend"

### Prices Not Loading

- Yahoo Finance API may be rate-limited
- Wait a few minutes and try again
- Check internet connectivity

### Database Issues

```bash
# Reset database (WARNING: Deletes all data)
rm data/stock_dashboard.db
# Restart server - tables will be recreated
```

---

## API Reference

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Server health check |
| `/api/dashboard/stats` | GET | Dashboard statistics |

### Telegram

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/telegram/login` | POST | Initiate Telegram auth |
| `/api/telegram/verify` | POST | Verify auth code |
| `/api/telegram/status` | GET | Check connection status |

### Sources

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sources` | GET | List all sources |
| `/api/sources` | POST | Add new source |
| `/api/sources/{id}` | DELETE | Delete source |
| `/api/sources/{id}/fetch` | POST | Fetch messages |

### Stock Data

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/stocks/indices` | GET | NIFTY, SENSEX, BANKNIFTY |
| `/api/stocks/quote/{symbol}` | GET | Stock quote |
| `/api/stocks/search` | GET | Search stocks |
| `/api/stock/{symbol}/detail` | GET | Full stock details |

### Analysis

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/allstar` | GET | Top 10 picks |
| `/api/analyze` | POST | Run analysis |
| `/api/recommendations` | GET | Get recommendations |

### News

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/news` | GET | Get news articles |
| `/api/news/fetch` | POST | Fetch from RSS |

### Watchlist

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/watchlist` | GET | List watchlist |
| `/api/watchlist` | POST | Add to watchlist |
| `/api/watchlist/{symbol}` | GET | Stock details |
| `/api/watchlist/{symbol}` | DELETE | Remove from watchlist |

---

## Disclaimer

⚠️ **IMPORTANT: This is NOT financial advice.**

- Recommendations are AI-generated based on market signals and news
- Always do your own research (DYOR) before investing
- Past performance does not guarantee future results
- The developers are not responsible for any financial losses
- Consult a SEBI-registered financial advisor for professional advice

---

## Support

For issues and feature requests, please open an issue on [GitHub](https://github.com/mayurrathi/stock-market-dashboard/issues).

---

*Last updated: January 2026*
