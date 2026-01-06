
import asyncio
import os
from google import genai
from backend.database import SessionLocal
from backend.models import Config

async def list_models():
    db = SessionLocal()
    key_config = db.query(Config).filter(Config.key == "gemini_api_key").first()
    api_key = key_config.value if key_config else None
    db.close()

    if not api_key:
        print("No API Key found")
        return

    print(f"Using Key: {api_key[:5]}...")
    client = genai.Client(api_key=api_key)
    
    try:
        # Pager object, iterate to get models
        print("Fetching models...")
        for m in client.models.list(config={'page_size': 10}):
            print(f"- {m.name}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(list_models())
