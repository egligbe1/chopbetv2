import os
import sqlite3
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

def migrate():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL not found.")
        return

    print(f"Connecting to {database_url}...")
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        print("Adding 'source_link' column to predictions table...")
        try:
            conn.execute(text("ALTER TABLE predictions ADD COLUMN source_link VARCHAR;"))
            conn.commit()
            print("Successfully added 'source_link' column.")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("Column 'source_link' already exists.")
            else:
                print(f"Error: {e}")

if __name__ == "__main__":
    migrate()
