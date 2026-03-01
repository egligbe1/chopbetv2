import os
import json
import logging
from google import genai
from google.genai import types
from datetime import datetime, UTC, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
from database import SessionLocal
from models import Prediction, Result, AccuracyStats
from dotenv import load_dotenv

load_dotenv()

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini Client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

def check_results():
    """
    Queries the database for pending predictions, uses Gemini 
    with Search Grounding to find final scores, then updates prediction 
    statuses and computes daily accuracy stats.
    """
    logger.info("Starting evening results checking process (v2 - Strict Research)...")
    db = SessionLocal()
    
    try:
        # Get all pending predictions
        pending = db.query(Prediction).filter(Prediction.status == "pending").all()
        
        if not pending:
            logger.info("No pending predictions to check.")
            return

        # Build a list of matches to check
        matches_to_check = []
        for p in pending:
            match_str = f"{p.home_team} vs {p.away_team} ({p.league}, Date: {p.date.strftime('%Y-%m-%d')})"
            if match_str not in matches_to_check:
                matches_to_check.append(match_str)

        from search_utils import search_utils
        logger.info(f"Gathering search context for {len(matches_to_check)} matches...")
        search_contexts = []
        for match_str in matches_to_check:
            ctx = search_utils.search_tavily(f"final score result {match_str}", max_results=3)
            search_contexts.append({"match": match_str, "context": ctx})

        prompt = f"""
        You are a football results processor. Use the provided SEARCH CONTEXT to find the ACTUAL FINAL scores for these matches:
        {json.dumps(matches_to_check)}
        
        SEARCH CONTEXT:
        {json.dumps(search_contexts)}
        
        STRICT REQUIREMENTS:
        1. Find accurate Half-Time (HT) and Full-Time (FT) scores.
        2. If a match was postponed or cancelled, mark score as null or -1.
        
        OUTPUT FORMAT:
        Return a JSON object with a "results" key containing an array of objects. Each object MUST have:
        - match: the original match string provided
        - ht_score_home: integer
        - ht_score_away: integer
        - ft_score_home: integer
        - ft_score_away: integer
        - status: "finished" or "postponed"
        
        Important: Return ONLY the JSON object. No markdown, no preamble.
        """

        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        if not response or not response.text:
            logger.error("Failed to get results from Gemini.")
            return

        raw_text = response.text.strip()
        data = json.loads(raw_text)
        results_data = data.get("results", []) if isinstance(data, dict) else data

        # Map results back to predictions
        results_map = {r["match"]: r for r in results_data if "match" in r}
        
        for p in pending:
            match_str = f"{p.home_team} vs {p.away_team} ({p.league}, Date: {p.date.strftime('%Y-%m-%d')})"
            res = results_map.get(match_str)
            
            if not res or res.get("status") == "postponed":
                p.status = "void"
                continue

            # Check if result already exists
            existing = db.query(Result).filter(Result.prediction_id == p.id).first()
            if not existing:
                new_result = Result(
                    prediction_id=p.id,
                    ht_score_home=res["ht_score_home"],
                    ht_score_away=res["ht_score_away"],
                    ft_score_home=res["ft_score_home"],
                    ft_score_away=res["ft_score_away"]
                )
                db.add(new_result)
                
                # Evaluate prediction
                p.status = _evaluate_prediction(p, res["ht_score_home"], res["ht_score_away"], res["ft_score_home"], res["ft_score_away"])

        db.commit()
        
        # After updating results, recalculate daily stats
        _update_accuracy_stats(db, datetime.now(UTC).date(), sport="football")
        
        logger.info("Results checking process completed successfully.")

    except Exception as e:
        logger.error(f"Error in results checker: {str(e)}")
        db.rollback()
    finally:
        db.close()

def _evaluate_prediction(prediction: Prediction, ht_home: int, ht_away: int,
                          ft_home: int, ft_away: int) -> str:
    """Evaluates whether a prediction was correct based on the actual scores."""
    market = prediction.market
    pred_value = prediction.prediction

    if prediction.sport == "basketball":
        return _evaluate_nba_prediction(prediction, ft_home, ft_away)
    market = prediction.market
    pred_value = prediction.prediction

    try:
        if market == "HT Over 0.5":
            ht_total = (ht_home or 0) + (ht_away or 0)
            return "won" if ht_total > 0 else "lost"

        elif market == "Total Over 1.5":
            ft_total = (ft_home or 0) + (ft_away or 0)
            return "won" if ft_total > 1 else "lost"

        elif market == "Total Over 2.5":
            ft_total = (ft_home or 0) + (ft_away or 0)
            return "won" if ft_total > 2 else "lost"

        elif market == "BTTS":
            both_scored = (ft_home or 0) > 0 and (ft_away or 0) > 0
            if pred_value.lower() == "yes":
                return "won" if both_scored else "lost"
            else:
                return "won" if not both_scored else "lost"

        elif market == "1X2":
            if (ft_home or 0) > (ft_away or 0):
                actual_outcome = "home"
            elif (ft_away or 0) > (ft_home or 0):
                actual_outcome = "away"
            else:
                actual_outcome = "draw"

            pv_lower = pred_value.lower()
            home_lower = prediction.home_team.lower()
            away_lower = prediction.away_team.lower()
            
            # Dynamically handle multiple formats: "Arsenal", "Home Win", "1"
            if "home" in pv_lower or pv_lower == "1" or home_lower in pv_lower or pv_lower in home_lower:
                pred_outcome = "home"
            elif "away" in pv_lower or pv_lower == "2" or away_lower in pv_lower or pv_lower in away_lower:
                pred_outcome = "away"
            elif "draw" in pv_lower or pv_lower == "x":
                pred_outcome = "draw"
            else:
                # Fallback if unmatchable
                return "lost"
                
            return "won" if pred_outcome == actual_outcome else "lost"

        else:
            logger.warning(f"Unknown market type: {market}")
            return "void"

    except Exception as e:
        logger.error(f"Error evaluating prediction {prediction.id}: {str(e)}")
        return "void"

def _evaluate_nba_prediction(prediction: Prediction, ft_home: int, ft_away: int) -> str:
    market = prediction.market
    pred_value = prediction.prediction.lower()
    
    try:
        if "moneyline" in market.lower() or "winner" in market.lower():
            actual_winner = "home" if ft_home > ft_away else "away"
            
            if "home" in pred_value or prediction.home_team.lower() in pred_value:
                pred_winner = "home"
            elif "away" in pred_value or prediction.away_team.lower() in pred_value:
                pred_winner = "away"
            else:
                return "lost"
                
            return "won" if pred_winner == actual_winner else "lost"
            
        elif "spread" in market.lower():
            # Oversimplified spread evaluation for now; assume pred_value contains the team and spread
            # Real implementation would parse the float spread and apply it.
            # E.g. "Lakers -5.5" -> If Lakers are home, ft_home - 5.5 > ft_away
            # As a basic fallback:
            return "void" # Implement proper spread parsing logic later if needed
            
        elif "over" in market.lower() or "under" in market.lower():
            # e.g market = "Total Over 220.5"
            total = ft_home + ft_away
            try:
                line_val = float(market.split()[-1])
                if "over" in market.lower() or "over" in pred_value:
                    return "won" if total > line_val else "lost"
                elif "under" in market.lower() or "under" in pred_value:
                    return "won" if total < line_val else "lost"
            except:
                pass
                
        return "void"
    except Exception as e:
        logger.error(f"Error evaluating NBA prediction {prediction.id}: {str(e)}")
        return "void"

def _update_accuracy_stats(db: Session, date, sport: str = "football"):
    """Computes and saves/updates the accuracy stats for a given date."""
    start_of_day = datetime(date.year, date.month, date.day, tzinfo=UTC)
    end_of_day = start_of_day + timedelta(days=1)

    all_preds = db.query(Prediction).filter(
        and_(
            Prediction.date >= start_of_day,
            Prediction.date < end_of_day,
            Prediction.status.in_(["won", "lost"]),
            Prediction.sport == sport
        )
        )
    ).all()

    if not all_preds:
        logger.info("No settled predictions to compute accuracy for.")
        return

    total = len(all_preds)
    correct = sum(1 for p in all_preds if p.status == "won")
    incorrect = total - correct
    accuracy_pct = round((correct / total) * 100, 1) if total > 0 else 0.0

    # By league
    by_league = {}
    for p in all_preds:
        league = p.league
        if league not in by_league:
            by_league[league] = {"total": 0, "correct": 0}
        by_league[league]["total"] += 1
        if p.status == "won":
            by_league[league]["correct"] += 1
    for league in by_league:
        t = by_league[league]["total"]
        c = by_league[league]["correct"]
        by_league[league]["accuracy_pct"] = round((c / t) * 100, 1) if t > 0 else 0.0

    # By market
    by_market = {}
    for p in all_preds:
        market = p.market
        if market not in by_market:
            by_market[market] = {"total": 0, "correct": 0}
        by_market[market]["total"] += 1
        if p.status == "won":
            by_market[market]["correct"] += 1
    for market in by_market:
        t = by_market[market]["total"]
        c = by_market[market]["correct"]
        by_market[market]["accuracy_pct"] = round((c / t) * 100, 1) if t > 0 else 0.0

    # Upsert accuracy stats for today
    existing_stats = db.query(AccuracyStats).filter(
        and_(
            AccuracyStats.date >= start_of_day,
            AccuracyStats.date < end_of_day,
            AccuracyStats.sport == sport
        )
    ).first()

    if existing_stats:
        existing_stats.total_predictions = total
        existing_stats.correct = correct
        existing_stats.incorrect = incorrect
        existing_stats.accuracy_pct = accuracy_pct
        existing_stats.by_league = by_league
        existing_stats.by_market = by_market
    else:
        new_stats = AccuracyStats(
            date=start_of_day,
            sport=sport,
            total_predictions=total,
            correct=correct,
            incorrect=incorrect,
            accuracy_pct=accuracy_pct,
            by_league=by_league,
            by_market=by_market
        )
        db.add(new_stats)

    db.commit()
    logger.info(f"Accuracy stats updated: {correct}/{total} = {accuracy_pct}%")

def check_nba_results():
    """
    Queries the database for pending NBA predictions and evaluates them.
    """
    logger.info("Starting evening results checking process for NBA...")
    db = SessionLocal()
    
    try:
        # Get all pending NBA predictions
        pending = db.query(Prediction).filter(
            and_(
                Prediction.status == "pending",
                Prediction.sport == "basketball"
            )
        ).all()
        
        if not pending:
            logger.info("No pending NBA predictions to check.")
            return

        # Build a list of matches to check
        matches_to_check = []
        for p in pending:
            match_str = f"{p.home_team} vs {p.away_team} ({p.league}, Date: {p.date.strftime('%Y-%m-%d')})"
            if match_str not in matches_to_check:
                matches_to_check.append(match_str)

        from search_utils import search_utils
        logger.info(f"Gathering NBA search context for {len(matches_to_check)} matches...")
        search_contexts = []
        for match_str in matches_to_check:
            ctx = search_utils.search_tavily(f"NBA final score result {match_str} ESPN", max_results=3)
            search_contexts.append({"match": match_str, "context": ctx})

        prompt = f"""
        You are an NBA results processor. Use the provided SEARCH CONTEXT to find the ACTUAL FINAL scores for these matches:
        {json.dumps(matches_to_check)}
        
        SEARCH CONTEXT:
        {json.dumps(search_contexts)}
        
        STRICT REQUIREMENTS:
        1. Find accurate Full-Time (FT) scores, including overtime if played.
        2. Give half time scores roughly if you can find them (or just put 0).
        3. If a match was postponed or cancelled, mark score as null or -1.
        
        OUTPUT FORMAT:
        Return a JSON object with a "results" key containing an array of objects. Each object MUST have:
        - match: the original match string provided
        - ht_score_home: integer
        - ht_score_away: integer
        - ft_score_home: integer
        - ft_score_away: integer
        - status: "finished" or "postponed"
        
        Important: Return ONLY the JSON object. No markdown, no preamble.
        """

        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        if not response or not response.text:
            logger.error("Failed to get NBA results from Gemini.")
            return

        raw_text = response.text.strip()
        data = json.loads(raw_text)
        results_data = data.get("results", []) if isinstance(data, dict) else data

        results_map = {r["match"]: r for r in results_data if "match" in r}
        
        for p in pending:
            match_str = f"{p.home_team} vs {p.away_team} ({p.league}, Date: {p.date.strftime('%Y-%m-%d')})"
            res = results_map.get(match_str)
            
            if not res or res.get("status") == "postponed":
                p.status = "void"
                continue

            existing = db.query(Result).filter(Result.prediction_id == p.id).first()
            if not existing:
                new_result = Result(
                    prediction_id=p.id,
                    ht_score_home=res.get("ht_score_home", 0),
                    ht_score_away=res.get("ht_score_away", 0),
                    ft_score_home=res.get("ft_score_home", 0),
                    ft_score_away=res.get("ft_score_away", 0)
                )
                db.add(new_result)
                
                # Evaluate prediction
                p.status = _evaluate_prediction(
                    p, 
                    res.get("ht_score_home", 0), 
                    res.get("ht_score_away", 0), 
                    res.get("ft_score_home", 0), 
                    res.get("ft_score_away", 0)
                )

        db.commit()
        _update_accuracy_stats(db, datetime.now(UTC).date(), sport="basketball")
        logger.info("NBA Results checking process completed successfully.")

    except Exception as e:
        logger.error(f"Error in NBA results checker: {str(e)}")
        db.rollback()
    finally:
        db.close()
