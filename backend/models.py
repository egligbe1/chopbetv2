from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime(timezone=True), index=True)
    home_team = Column(String, index=True)
    away_team = Column(String, index=True)
    league = Column(String, index=True)
    country = Column(String)
    sport = Column(String, default="football", index=True)
    kickoff_time = Column(DateTime(timezone=True))
    market = Column(String)  # e.g. "HT Over 0.5"
    prediction = Column(String)  # e.g. "Yes"
    confidence = Column(Integer)
    reasoning = Column(Text)
    risk_rating = Column(String)  # Low / Medium / High
    odds = Column(Float, nullable=True)  # Decimal odds (e.g. 1.85)
    source_link = Column(String, nullable=True)  # Link to real schedule/source
    status = Column(String, default="pending")  # pending / won / lost / void
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    result = relationship("Result", back_populates="prediction", uselist=False)

class Result(Base):
    __tablename__ = "results"

    id = Column(Integer, primary_key=True, index=True)
    prediction_id = Column(Integer, ForeignKey("predictions.id"), unique=True)
    ht_score_home = Column(Integer)
    ht_score_away = Column(Integer)
    ft_score_home = Column(Integer)
    ft_score_away = Column(Integer)
    result_checked_at = Column(DateTime(timezone=True), server_default=func.now())

    prediction = relationship("Prediction", back_populates="result")

class AccuracyStats(Base):
    __tablename__ = "accuracy_stats"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime(timezone=True), index=True)
    sport = Column(String, default="football", index=True)
    total_predictions = Column(Integer)
    correct = Column(Integer)
    incorrect = Column(Integer)
    accuracy_pct = Column(Float)
    by_league = Column(JSON)  # Break down accuracy by league
    by_market = Column(JSON)  # Break down accuracy by market type
