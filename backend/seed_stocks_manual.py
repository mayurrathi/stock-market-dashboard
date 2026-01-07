import asyncio
import sys
import os

# Add parent dir to path to find backend module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal
from backend.models import Stock
from backend.stock_api import NSE_STOCKS

async def seed():
    print("Connecting to database...")
    db = SessionLocal()
    try:
        count = db.query(Stock).count()
        print(f"Current stock count: {count}")
        
        # Always try to add missing NSE_STOCKS even if count > 0
        print(f"Checking {len(NSE_STOCKS)} NSE stocks against database...")
        
        existing_symbols = {s.symbol for s in db.query(Stock).all()}
        added = 0
        
        for s in NSE_STOCKS:
            if s['symbol'] not in existing_symbols:
                # Infer cap type roughly
                cap_type = "Large Cap" # Default
                
                stock = Stock(
                    symbol=s['symbol'],
                    name=s['name'],
                    sector=s['sector'],
                    cap_type=cap_type
                )
                db.add(stock)
                added += 1
        
        if added > 0:
            db.commit()
            print(f"Successfully added {added} new stocks.")
        else:
            print("No new stocks to add. Database is up to date.")
            
        final_count = db.query(Stock).count()
        print(f"Final stock count: {final_count}")
        
    except Exception as e:
        print(f"Error during seeding: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(seed())
