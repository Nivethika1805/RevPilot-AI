import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.core.database import SessionLocal
from app.seed.seed_data import seed_database

if __name__ == "__main__":
    db = SessionLocal()
    try:
        res = seed_database(db)
        print("Seed result:", res)
    finally:
        db.close()
