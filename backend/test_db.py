import logging
logging.basicConfig(level=logging.INFO)
from database import SessionLocal
from models import Prediction

db = SessionLocal()
count = db.query(Prediction).count()
print(f"Total predictions in DB: {count}")

acca = db.query(Prediction).order_by(Prediction.confidence.desc()).limit(15).all()
total_odds = 1.0
for p in acca:
    total_odds *= (p.odds or 1.0)
print(f"Loaded {len(acca)} top candidates. Total odds: {total_odds:.2f}")

if acca:
    print(f"Top pick: {acca[0].home_team} vs {acca[0].away_team} - {acca[0].prediction} ({acca[0].confidence}%)")
