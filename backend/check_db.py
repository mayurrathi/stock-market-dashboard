from backend.database import SessionLocal
from backend.models import Config

def check_config():
    db = SessionLocal()
    try:
        keys = db.query(Config).all()
        print(f"Found {len(keys)} config items:")
        for k in keys:
            val = k.value
            if "key" in k.key:  # mask keys
                 val = val[:4] + "***" + val[-4:] if val and len(val) > 8 else "***"
            print(f"- {k.key}: {val}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_config()
