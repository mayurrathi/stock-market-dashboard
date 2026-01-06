from backend.database import SessionLocal
from backend.models import Recommendation

def clear_data():
    db = SessionLocal()
    try:
        count = db.query(Recommendation).delete()
        db.commit()
        print(f"Cleared {count} old recommendations.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    clear_data()
