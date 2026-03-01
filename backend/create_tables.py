"""Script to create all database tables."""
import sys
import os

# Add the parent directory to the path so we can import the backend package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import engine, Base
from backend.models import Prediction, Result, AccuracyStats

if __name__ == "__main__":
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Done! All tables created successfully.")
