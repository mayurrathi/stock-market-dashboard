
import asyncio
from datetime import datetime, timedelta
import pytz
import logging
from backend.analyzer import analyzer
from backend.database import SessionLocal, engine, Base

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure tables exist
Base.metadata.create_all(bind=engine)

async def test_analyzer():
    print("Starting analyzer test...")
    try:
        IST = pytz.timezone('Asia/Kolkata')
        now = datetime.now(IST)
        start_date = now - timedelta(days=7)
        end_date = now
        
        print(f"Analyzing from {start_date} to {end_date}")
        
        # Test analyze_timeframe
        analysis_result = await analyzer.analyze_timeframe(start_date, end_date)
        print("analyze_timeframe successful")
        print(f"Messages analyzed: {analysis_result.get('messages_analyzed')}")
        print(f"Top stocks: {analysis_result.get('top_stocks')}")
        
        # Test generate_all_recommendations
        print("Generating recommendations...")
        recommendations = await analyzer.generate_all_recommendations(analysis_result)
        print(f"generate_all_recommendations successful. Generated {len(recommendations)} recommendations")
        
    except Exception as e:
        print(f"Analyzer test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_analyzer())
