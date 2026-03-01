from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from datetime import datetime, UTC, timedelta
from database import get_db
from models import Prediction, AccuracyStats

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/accuracy")
def get_overall_accuracy(sport: str = Query("football", description="Sport to fetch stats for"), db: Session = Depends(get_db)):
    """Get overall accuracy stats across all time."""
    all_settled = db.query(Prediction).filter(
        and_(
            Prediction.status.in_(["won", "lost"]),
            Prediction.sport == sport
        )
    ).all()

    total = len(all_settled)
    correct = sum(1 for p in all_settled if p.status == "won")
    incorrect = total - correct

    # Win streak calculation
    recent_preds = db.query(Prediction).filter(
        and_(
            Prediction.status.in_(["won", "lost"]),
            Prediction.sport == sport
        )
    ).order_by(Prediction.date.desc(), Prediction.id.desc()).all()

    current_streak = 0
    for p in recent_preds:
        if p.status == "won":
            current_streak += 1
        else:
            break

    # Best and worst day
    daily_stats = db.query(AccuracyStats).filter(
        AccuracyStats.sport == sport
    ).order_by(AccuracyStats.date.desc()).all()

    best_day = None
    worst_day = None
    if daily_stats:
        best = max(daily_stats, key=lambda s: s.accuracy_pct if s.accuracy_pct is not None else 0)
        worst = min(daily_stats, key=lambda s: s.accuracy_pct if s.accuracy_pct is not None else 100)
        best_day = {
            "date": best.date.isoformat() if best.date else None,
            "accuracy_pct": best.accuracy_pct,
            "correct": best.correct,
            "total": best.total_predictions
        }
        worst_day = {
            "date": worst.date.isoformat() if worst.date else None,
            "accuracy_pct": worst.accuracy_pct,
            "correct": worst.correct,
            "total": worst.total_predictions
        }

    return {
        "total_predictions": total,
        "correct": correct,
        "incorrect": incorrect,
        "accuracy_pct": round((correct / total) * 100, 1) if total > 0 else 0.0,
        "current_win_streak": current_streak,
        "best_day": best_day,
        "worst_day": worst_day,
        "total_days_tracked": len(daily_stats)
    }


@router.get("/accuracy/league")
def get_accuracy_by_league(sport: str = Query("football", description="Sport to fetch stats for"), db: Session = Depends(get_db)):
    """Get accuracy broken down by league."""
    settled = db.query(Prediction).filter(
        and_(
            Prediction.status.in_(["won", "lost"]),
            Prediction.sport == sport
        )
    ).all()

    by_league = {}
    for p in settled:
        league = p.league
        if league not in by_league:
            by_league[league] = {"total": 0, "correct": 0, "incorrect": 0}
        by_league[league]["total"] += 1
        if p.status == "won":
            by_league[league]["correct"] += 1
        else:
            by_league[league]["incorrect"] += 1

    for league in by_league:
        t = by_league[league]["total"]
        c = by_league[league]["correct"]
        by_league[league]["accuracy_pct"] = round((c / t) * 100, 1) if t > 0 else 0.0

    return {"by_league": by_league}


@router.get("/accuracy/market")
def get_accuracy_by_market(sport: str = Query("football", description="Sport to fetch stats for"), db: Session = Depends(get_db)):
    """Get accuracy broken down by market type."""
    settled = db.query(Prediction).filter(
        and_(
            Prediction.status.in_(["won", "lost"]),
            Prediction.sport == sport
        )
    ).all()

    by_market = {}
    for p in settled:
        market = p.market
        if market not in by_market:
            by_market[market] = {"total": 0, "correct": 0, "incorrect": 0}
        by_market[market]["total"] += 1
        if p.status == "won":
            by_market[market]["correct"] += 1
        else:
            by_market[market]["incorrect"] += 1

    for market in by_market:
        t = by_market[market]["total"]
        c = by_market[market]["correct"]
        by_market[market]["accuracy_pct"] = round((c / t) * 100, 1) if t > 0 else 0.0

    return {"by_market": by_market}


@router.get("/daily")
def get_daily_stats(
    sport: str = Query("football", description="Sport to fetch stats for"),
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get daily accuracy stats for the last N days (for charting)."""
    cutoff = datetime.now(UTC) - timedelta(days=days)

    stats = db.query(AccuracyStats).filter(
        and_(
            AccuracyStats.date >= cutoff,
            AccuracyStats.sport == sport
        )
    ).order_by(AccuracyStats.date.asc()).all()

    return {
        "days": days,
        "stats": [
            {
                "date": s.date.isoformat() if s.date else None,
                "total_predictions": s.total_predictions,
                "correct": s.correct,
                "incorrect": s.incorrect,
                "accuracy_pct": s.accuracy_pct,
                "by_league": s.by_league,
                "by_market": s.by_market
            }
            for s in stats
        ]
    }
