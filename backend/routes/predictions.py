from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_
from datetime import datetime, UTC, timedelta
from typing import Optional
from database import get_db
from models import Prediction as PredictionModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("/accumulator")
def get_daily_accumulator(sport: str = Query("football", description="Sport to fetch accumulator for"), db: Session = Depends(get_db)):
    """
    Get a curated accumulator for today.
    Starts with the 5 highest-confidence picks and keeps adding more (up to 15)
    until total odds reach the 10.00–200.00 target range.
    """
    MIN_ODDS = 10.0
    MAX_ODDS = 200.0
    MIN_PICKS = 5
    MAX_PICKS = 15

    today = datetime.now(UTC).date()
    start_of_day = datetime(today.year, today.month, today.day, tzinfo=UTC) - timedelta(hours=1)
    end_of_day = start_of_day + timedelta(days=1, hours=2)

    candidates = db.query(PredictionModel).options(joinedload(PredictionModel.result)).filter(
        and_(
            PredictionModel.date >= start_of_day,
            PredictionModel.date < end_of_day,
            PredictionModel.sport == sport
        )
    ).order_by(PredictionModel.confidence.desc()).limit(MAX_PICKS).all()

    if not candidates:
        return {"accumulator": None, "total_odds": 0}

    # Start with MIN_PICKS, grow until odds hit the floor or we run out
    selected = candidates[:MIN_PICKS]
    total_odds = 1.0
    for p in selected:
        total_odds *= (p.odds or 1.0)

    for extra in candidates[MIN_PICKS:]:
        if total_odds >= MIN_ODDS:
            break
        selected.append(extra)
        total_odds *= (extra.odds or 1.0)
        # Safety cap — don't let odds balloon past ceiling
        if total_odds > MAX_ODDS:
            break

    return {
        "date": today.isoformat(),
        "total_odds": round(total_odds, 2),
        "count": len(selected),
        "predictions": [_serialize_prediction(p) for p in selected]
    }


@router.get("/today")
def get_today_predictions(sport: str = Query("football", description="Sport to fetch predictions for"), db: Session = Depends(get_db)):
    """Get all predictions for today."""
    today = datetime.now(UTC).date()
    start_of_day = datetime(today.year, today.month, today.day, tzinfo=UTC) - timedelta(hours=1)
    end_of_day = start_of_day + timedelta(days=1, hours=2)

    predictions = db.query(PredictionModel).options(joinedload(PredictionModel.result)).filter(
        and_(
            PredictionModel.date >= start_of_day,
            PredictionModel.date < end_of_day,
            PredictionModel.sport == sport
        )
    ).order_by(PredictionModel.kickoff_time.asc()).all()

    return {
        "date": today.isoformat(),
        "count": len(predictions),
        "predictions": [_serialize_prediction(p) for p in predictions]
    }


@router.get("/date/{date}")
def get_predictions_by_date(date: str, sport: str = Query("football", description="Sport to fetch predictions for"), db: Session = Depends(get_db)):
    """Get predictions for a specific date (YYYY-MM-DD)."""
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD."}

    start_of_day = datetime(target_date.year, target_date.month, target_date.day, tzinfo=UTC)
    end_of_day = start_of_day + timedelta(days=1)

    predictions = db.query(PredictionModel).filter(
        and_(
            PredictionModel.date >= start_of_day,
            PredictionModel.date < end_of_day,
            PredictionModel.sport == sport
        )
    ).order_by(PredictionModel.kickoff_time.asc()).all()

    # Compute daily stats
    settled = [p for p in predictions if p.status in ("won", "lost")]
    correct = sum(1 for p in settled if p.status == "won")
    total_settled = len(settled)

    return {
        "date": target_date.isoformat(),
        "count": len(predictions),
        "settled": total_settled,
        "correct": correct,
        "accuracy_pct": round((correct / total_settled) * 100, 1) if total_settled > 0 else None,
        "predictions": [_serialize_prediction(p) for p in predictions]
    }


@router.get("/history")
def get_prediction_history(
    sport: str = Query("football", description="Sport to fetch history for"),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get paginated list of all past prediction days."""
    from sqlalchemy import func, cast, Date

    # Get distinct dates that have predictions, ordered most recent first
    distinct_dates = (
        db.query(func.date(PredictionModel.date).label("pred_date"))
        .filter(PredictionModel.sport == sport)
        .group_by(func.date(PredictionModel.date))
        .order_by(func.date(PredictionModel.date).desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    total_days = (
        db.query(func.count(func.distinct(func.date(PredictionModel.date))))
        .filter(PredictionModel.sport == sport)
        .scalar()
    )

    days = []
    for row in distinct_dates:
        pred_date = row.pred_date
        if isinstance(pred_date, str):
            pred_date = datetime.strptime(pred_date, "%Y-%m-%d").date()

        start = datetime(pred_date.year, pred_date.month, pred_date.day, tzinfo=UTC)
        end = start + timedelta(days=1)

        preds = db.query(PredictionModel).filter(
            and_(
                PredictionModel.date >= start,
                PredictionModel.date < end,
                PredictionModel.sport == sport
            )
        ).all()

        settled = [p for p in preds if p.status in ("won", "lost")]
        correct = sum(1 for p in settled if p.status == "won")
        total_settled = len(settled)

        days.append({
            "date": pred_date.isoformat() if hasattr(pred_date, 'isoformat') else str(pred_date),
            "total_predictions": len(preds),
            "settled": total_settled,
            "correct": correct,
            "accuracy_pct": round((correct / total_settled) * 100, 1) if total_settled > 0 else None,
            "predictions": [_serialize_prediction(p) for p in preds]
        })

    return {
        "page": page,
        "per_page": per_page,
        "total_days": total_days or 0,
        "total_pages": max(1, ((total_days or 0) + per_page - 1) // per_page),
        "days": days
    }


def _serialize_prediction(p):
    """Convert a Prediction ORM object to a dict for JSON response."""
    result_data = None
    if p.result:
        result_data = {
            "ht_score_home": p.result.ht_score_home,
            "ht_score_away": p.result.ht_score_away,
            "ft_score_home": p.result.ft_score_home,
            "ft_score_away": p.result.ft_score_away,
            "result_checked_at": p.result.result_checked_at.isoformat() if p.result.result_checked_at else None
        }

    return {
        "id": p.id,
        "date": p.date.isoformat() if p.date else None,
        "home_team": p.home_team,
        "away_team": p.away_team,
        "league": p.league,
        "country": p.country,
        "kickoff_time": p.kickoff_time.isoformat() if p.kickoff_time else None,
        "market": p.market,
        "prediction": p.prediction,
        "confidence": p.confidence,
        "odds": p.odds,
        "source_link": p.source_link,
        "reasoning": p.reasoning,
        "risk_rating": p.risk_rating,
        "status": p.status,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "result": result_data
    }
