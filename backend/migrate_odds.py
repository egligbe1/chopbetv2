import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv('backend/.env')
engine = create_engine(os.getenv('DATABASE_URL'))

def migrate():
    print("Adding 'odds' column to predictions table...")
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE predictions ADD COLUMN odds FLOAT;"))
            conn.commit()
            print("Successfully added 'odds' column.")
        except Exception as e:
            print(f"Failed to add column (it might already exist): {e}")

if __name__ == "__main__":
    migrate()
