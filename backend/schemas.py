from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List, Dict, Any

class PredictionBase(BaseModel):
    date: datetime
    home_team: str
    away_team: str
    league: str
    country: str
    kickoff_time: datetime
    market: str
    prediction: str
    confidence: int
    reasoning: str
    risk_rating: str
    odds: Optional[float] = None
    source_link: Optional[str] = None

class PredictionCreate(PredictionBase):
    pass

class Prediction(PredictionBase):
    id: int
    status: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ResultBase(BaseModel):
    ht_score_home: int
    ht_score_away: int
    ft_score_home: int
    ft_score_away: int

class ResultCreate(ResultBase):
    prediction_id: int

class Result(ResultBase):
    id: int
    prediction_id: int
    result_checked_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AccuracyStatsBase(BaseModel):
    date: datetime
    total_predictions: int
    correct: int
    incorrect: int
    accuracy_pct: float
    by_league: Dict[str, Any]
    by_market: Dict[str, Any]

class AccuracyStats(AccuracyStatsBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
