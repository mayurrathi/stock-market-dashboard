#!/usr/bin/env python3
"""
Script to generate comprehensive NSE/BSE stock list
Downloads and combines stock data from multiple sources
"""
import json
import os
import urllib.request
import ssl

# Disable SSL verification for GitHub raw content
ssl._create_default_https_context = ssl._create_unverified_context

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), 'all_stocks.json')

# GitHub source for NSE stocks
NSE_STOCKS_URL = "https://raw.githubusercontent.com/akashgiri/stocks-list/master/nse-listed-stocks.json"

# Sector mapping based on common patterns in company names
SECTOR_PATTERNS = {
    "Bank": "Banking",
    "Finance": "Finance",
    "Pharma": "Pharma",
    "Pharmaceutical": "Pharma",
    "Healthcare": "Healthcare",
    "Hospital": "Healthcare",
    "IT": "IT",
    "Software": "IT",
    "Tech": "IT",
    "Infotech": "IT",
    "Computer": "IT",
    "Infosys": "IT",
    "Steel": "Metals",
    "Metal": "Metals",
    "Aluminium": "Metals",
    "Copper": "Metals",
    "Iron": "Metals",
    "Cement": "Cement",
    "Power": "Power",
    "Energy": "Energy",
    "Oil": "Energy",
    "Gas": "Energy",
    "Petro": "Energy",
    "Auto": "Auto",
    "Motor": "Auto",
    "Vehicle": "Auto",
    "Tyre": "Auto",
    "Sugar": "Sugar",
    "Textile": "Textiles",
    "Cotton": "Textiles",
    "Spinning": "Textiles",
    "Fabric": "Textiles",
    "Chemical": "Chemicals",
    "Fertilizer": "Chemicals",
    "Fertiliser": "Chemicals",
    "Agro": "Agriculture",
    "Tea": "FMCG",
    "Food": "FMCG",
    "Consumer": "FMCG",
    "Hotel": "Hotels",
    "Hospitality": "Hotels",
    "Realty": "Real Estate",
    "Housing": "Real Estate",
    "Infrastructure": "Infrastructure",
    "Construction": "Infrastructure",
    "Engineering": "Engineering",
    "Telecom": "Telecom",
    "Communication": "Telecom",
    "Media": "Media",
    "Entertainment": "Media",
    "Insurance": "Insurance",
    "Shipping": "Logistics",
    "Logistics": "Logistics",
    "Transport": "Logistics",
}

def guess_sector(name):
    """Guess sector based on company name patterns"""
    name_upper = name.upper()
    for pattern, sector in SECTOR_PATTERNS.items():
        if pattern.upper() in name_upper:
            return sector
    return "General"

def fetch_nse_stocks():
    """Fetch NSE stocks from GitHub"""
    print(f"Fetching NSE stocks from {NSE_STOCKS_URL}...")
    try:
        with urllib.request.urlopen(NSE_STOCKS_URL, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
            stocks = []
            for name, symbol in data.items():
                # Skip BE/BZ suffix stocks (suspended/no trading)
                if symbol.endswith('BE') or symbol.endswith('BZ'):
                    continue
                stocks.append({
                    "symbol": symbol.replace('and', '&'),
                    "name": name,
                    "sector": guess_sector(name)
                })
            print(f"Found {len(stocks)} active NSE stocks")
            return stocks
    except Exception as e:
        print(f"Error fetching NSE stocks: {e}")
        return []

# Additional popular stocks that may be missing
ADDITIONAL_STOCKS = [
    # Nifty 50 constituents - ensure all are present
    {"symbol": "RELIANCE", "name": "Reliance Industries Ltd", "sector": "Energy"},
    {"symbol": "TCS", "name": "Tata Consultancy Services", "sector": "IT"},
    {"symbol": "HDFCBANK", "name": "HDFC Bank Ltd", "sector": "Banking"},
    {"symbol": "INFY", "name": "Infosys Ltd", "sector": "IT"},
    {"symbol": "ICICIBANK", "name": "ICICI Bank Ltd", "sector": "Banking"},
    {"symbol": "HINDUNILVR", "name": "Hindustan Unilever Ltd", "sector": "FMCG"},
    {"symbol": "SBIN", "name": "State Bank of India", "sector": "Banking"},
    {"symbol": "BHARTIARTL", "name": "Bharti Airtel Ltd", "sector": "Telecom"},
    {"symbol": "ITC", "name": "ITC Ltd", "sector": "FMCG"},
    {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank", "sector": "Banking"},
    {"symbol": "LT", "name": "Larsen & Toubro Ltd", "sector": "Infrastructure"},
    {"symbol": "AXISBANK", "name": "Axis Bank Ltd", "sector": "Banking"},
    {"symbol": "ASIANPAINT", "name": "Asian Paints Ltd", "sector": "Consumer"},
    {"symbol": "MARUTI", "name": "Maruti Suzuki India Ltd", "sector": "Auto"},
    {"symbol": "BAJFINANCE", "name": "Bajaj Finance Ltd", "sector": "Finance"},
    {"symbol": "TITAN", "name": "Titan Company Ltd", "sector": "Consumer"},
    {"symbol": "SUNPHARMA", "name": "Sun Pharmaceutical", "sector": "Pharma"},
    {"symbol": "NESTLEIND", "name": "Nestle India Ltd", "sector": "FMCG"},
    {"symbol": "WIPRO", "name": "Wipro Ltd", "sector": "IT"},
    {"symbol": "ULTRACEMCO", "name": "UltraTech Cement Ltd", "sector": "Cement"},
    {"symbol": "HCLTECH", "name": "HCL Technologies Ltd", "sector": "IT"},
    {"symbol": "BAJAJFINSV", "name": "Bajaj Finserv Ltd", "sector": "Finance"},
    {"symbol": "POWERGRID", "name": "Power Grid Corporation", "sector": "Power"},
    {"symbol": "NTPC", "name": "NTPC Ltd", "sector": "Power"},
    {"symbol": "TATASTEEL", "name": "Tata Steel Ltd", "sector": "Metals"},
    {"symbol": "TECHM", "name": "Tech Mahindra Ltd", "sector": "IT"},
    {"symbol": "ONGC", "name": "Oil & Natural Gas Corp", "sector": "Energy"},
    {"symbol": "ADANIENT", "name": "Adani Enterprises Ltd", "sector": "Diversified"},
    {"symbol": "COALINDIA", "name": "Coal India Ltd", "sector": "Mining"},
    {"symbol": "JSWSTEEL", "name": "JSW Steel Ltd", "sector": "Metals"},
    {"symbol": "TATAMOTORS", "name": "Tata Motors Ltd", "sector": "Auto"},
    {"symbol": "INDUSINDBK", "name": "IndusInd Bank Ltd", "sector": "Banking"},
    {"symbol": "M&M", "name": "Mahindra & Mahindra Ltd", "sector": "Auto"},
    {"symbol": "HINDALCO", "name": "Hindalco Industries Ltd", "sector": "Metals"},
    {"symbol": "BAJAJ-AUTO", "name": "Bajaj Auto Ltd", "sector": "Auto"},
    {"symbol": "DRREDDY", "name": "Dr Reddy's Laboratories", "sector": "Pharma"},
    {"symbol": "APOLLOHOSP", "name": "Apollo Hospitals", "sector": "Healthcare"},
    {"symbol": "EICHERMOT", "name": "Eicher Motors Ltd", "sector": "Auto"},
    {"symbol": "GRASIM", "name": "Grasim Industries Ltd", "sector": "Cement"},
    {"symbol": "BRITANNIA", "name": "Britannia Industries", "sector": "FMCG"},
    {"symbol": "CIPLA", "name": "Cipla Ltd", "sector": "Pharma"},
    {"symbol": "DIVISLAB", "name": "Divi's Laboratories Ltd", "sector": "Pharma"},
    {"symbol": "SBILIFE", "name": "SBI Life Insurance", "sector": "Insurance"},
    {"symbol": "ADANIPORTS", "name": "Adani Ports & SEZ", "sector": "Infrastructure"},
    {"symbol": "TATACONSUM", "name": "Tata Consumer Products", "sector": "FMCG"},
    {"symbol": "BPCL", "name": "Bharat Petroleum Corp", "sector": "Energy"},
    {"symbol": "HEROMOTOCO", "name": "Hero MotoCorp Ltd", "sector": "Auto"},
    {"symbol": "UPL", "name": "UPL Ltd", "sector": "Chemicals"},
    {"symbol": "HDFCLIFE", "name": "HDFC Life Insurance", "sector": "Insurance"},
    {"symbol": "LTIM", "name": "LTIMindtree Ltd", "sector": "IT"},
    # Popular midcaps and new-age stocks
    {"symbol": "ZOMATO", "name": "Zomato Ltd", "sector": "Consumer Tech"},
    {"symbol": "PAYTM", "name": "One 97 Communications", "sector": "Fintech"},
    {"symbol": "NYKAA", "name": "FSN E-Commerce (Nykaa)", "sector": "E-commerce"},
    {"symbol": "POLICYBZR", "name": "PB Fintech (Policybazaar)", "sector": "Fintech"},
    {"symbol": "DELHIVERY", "name": "Delhivery Ltd", "sector": "Logistics"},
    {"symbol": "IRCTC", "name": "IRCTC Ltd", "sector": "Travel"},
    {"symbol": "TRENT", "name": "Trent Ltd (Westside)", "sector": "Retail"},
    {"symbol": "DMART", "name": "Avenue Supermarts (DMart)", "sector": "Retail"},
    {"symbol": "PIDILITIND", "name": "Pidilite Industries", "sector": "Chemicals"},
    {"symbol": "SIEMENS", "name": "Siemens Ltd", "sector": "Engineering"},
    {"symbol": "HAVELLS", "name": "Havells India Ltd", "sector": "Consumer Durables"},
    {"symbol": "ABB", "name": "ABB India Ltd", "sector": "Engineering"},
    {"symbol": "HAL", "name": "Hindustan Aeronautics", "sector": "Defence"},
    {"symbol": "BEL", "name": "Bharat Electronics Ltd", "sector": "Defence"},
    {"symbol": "ADANIGREEN", "name": "Adani Green Energy", "sector": "Renewable Energy"},
    {"symbol": "ADANIPOWER", "name": "Adani Power Ltd", "sector": "Power"},
    {"symbol": "TATAPOWER", "name": "Tata Power Company", "sector": "Power"},
    {"symbol": "IOC", "name": "Indian Oil Corporation", "sector": "Energy"},
    {"symbol": "GAIL", "name": "GAIL (India) Ltd", "sector": "Energy"},
    {"symbol": "PETRONET", "name": "Petronet LNG Ltd", "sector": "Energy"},
    {"symbol": "VEDL", "name": "Vedanta Ltd", "sector": "Metals"},
    {"symbol": "NMDC", "name": "NMDC Ltd", "sector": "Mining"},
    {"symbol": "SAIL", "name": "Steel Authority of India", "sector": "Metals"},
    {"symbol": "JINDALSTEL", "name": "Jindal Steel & Power", "sector": "Metals"},
    {"symbol": "PFC", "name": "Power Finance Corporation", "sector": "Finance"},
    {"symbol": "RECLTD", "name": "REC Ltd", "sector": "Finance"},
    {"symbol": "POLYCAB", "name": "Polycab India Ltd", "sector": "Consumer Durables"},
]

def main():
    # Fetch from GitHub
    nse_stocks = fetch_nse_stocks()
    
    # Create a dict to avoid duplicates (symbol as key)
    all_stocks = {}
    
    # Add fetched stocks
    for stock in nse_stocks:
        all_stocks[stock["symbol"]] = stock
    
    # Add/override with curated list (ensures Nifty 50 has correct info)
    for stock in ADDITIONAL_STOCKS:
        all_stocks[stock["symbol"]] = stock
    
    # Convert back to list and sort by symbol
    final_list = sorted(all_stocks.values(), key=lambda x: x["symbol"])
    
    # Write to file
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(final_list, f, indent=2)
    
    print(f"\nGenerated {len(final_list)} stocks")
    print(f"Output written to: {OUTPUT_FILE}")
    
    # Print sector distribution
    sectors = {}
    for stock in final_list:
        sector = stock.get("sector", "Unknown")
        sectors[sector] = sectors.get(sector, 0) + 1
    
    print("\nSector distribution:")
    for sector, count in sorted(sectors.items(), key=lambda x: -x[1])[:15]:
        print(f"  {sector}: {count}")

if __name__ == "__main__":
    main()
