import os
import json
import logging
from google import genai
from google.genai import types
from datetime import datetime, UTC, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, exists
from database import SessionLocal
from models import Prediction, Result, AccuracyStats
from dotenv import load_dotenv

load_dotenv()

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini Client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FALLBACK_GEMINI_API_KEY = os.getenv("FALLBACK_GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

def batch_check_results(date_str: str, matches: list) -> dict:
    """
    Sends the BBC text for a specific date to Gemini to retrieve
    the HT and FT scores for a given list of matches in one shot.
    """
    from search_utils import search_utils
    bbc_text = search_utils.get_bbc_fixtures(date_str) or ""
    goal_text = search_utils.get_goal_fixtures(date_str) or ""
    espn_text = search_utils.get_espn_fixtures(date_str) or ""
    
    combined_text = bbc_text[:15000] + "\n\n---\n\n" + goal_text[:15000] + "\n\n---\n\n" + espn_text[:15000]
    
    if len(combined_text) < 100:
        logger.error(f"Failed to fetch results text for {date_str}.")
        return {}

    # Normalize match names for better matching
    normalized_matches = [_normalize_match(m) for m in matches]
    matches_list = "\n".join([f"- {m}" for m in normalized_matches])
    
    prompt = f"""
    You are a professional sports results verifier.
    Below is the raw text scraped from the BBC Sport fixtures/results page for {date_str}.
    
    YOUR TASK:
    Find the actual, fully completed Half Time (HT) and Full Time (FT) scores for ONLY the following matches:
    {matches_list}
    
    CRITICAL INSTRUCTION:
    You MUST provide a `match_status` for every match. It MUST be exactly one of the following strings:
    - "Finished" (or "FT" / "AET" / "Penalties" if the match is fully completed)
    - "Postponed" (or "Cancelled")
    - "Abandoned"
    - "Live" (if the match is currently playing but not finished)
    - "Pending" (if it hasn't started yet)

    RAW MATCH RESULTS TEXT:
    {combined_text}
    
    OUTPUT REQUIREMENTS:
    Return ONLY a JSON object mapping the match string to its results.
    Format exactly like this (If a match is postponed or hasn't finished, omit it or set scores to null):
    {{
        "Arsenal vs Chelsea": {{
            "ht_home": 1, "ht_away": 0, "ft_home": 2, "ft_away": 1, "match_status": "Finished"
        }}
    }}
    """
    
    schema = {
        "type": "OBJECT",
        "properties": {
            "results": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "match": {"type": "STRING"},
                        "ht_home": {"type": "INTEGER", "nullable": True},
                        "ht_away": {"type": "INTEGER", "nullable": True},
                        "ft_home": {"type": "INTEGER", "nullable": True},
                        "ft_away": {"type": "INTEGER", "nullable": True},
                        "match_status": {"type": "STRING", "nullable": True},
                    },
                    # Only match is required. Score fields are null if match isn't finished.
                    "required": ["match", "match_status"]
                }
            }
        },
        "required": ["results"]
    }
    
    import time
    global client
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                )
            )
            data = json.loads(response.text.strip())
            results = data.get("results", [])
            
            # Convert list back to match map for easier lookup downstream
            match_results = {r["match"]: r for r in results if "match" in r}
            logger.info(f"Gemini returned results for {len(match_results)} matches: {list(match_results.keys())}")
            return match_results
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                if attempt == 0 and FALLBACK_GEMINI_API_KEY:
                    logger.warning("Primary quota exhausted. Switching to fallback Gemini API key.")
                    client = genai.Client(api_key=FALLBACK_GEMINI_API_KEY)
                    continue
                if attempt < max_retries - 1:
                    sleep_time = 2 ** attempt * 10
                    logger.warning(f"Rate limited (429). Retrying in {sleep_time} seconds (Attempt {attempt+1}/{max_retries})...")
                    time.sleep(sleep_time)
                    continue
            logger.error(f"Error checking results for {date_str}: {e}")
            return {}
    return {}


def check_results():
    """
    Queries the database for pending predictions, pulls BBC results for 
    the relevant dates, and uses Gemini to find final scores in batches, 
    then updates prediction statuses and computes daily accuracy stats.
    """
    logger.info("Starting evening results checking process (v3 - BBC Batch Scraper)...")
    db = SessionLocal()
    
    try:
        # Get all pending predictions (also look back 7 days to catch any missed ones, and include pending predictions that have results)
        lookback_date = datetime.now(UTC) - timedelta(days=7)
        pending = db.query(Prediction).filter(
            and_(
                Prediction.status == "pending",
                or_(
                    Prediction.date >= lookback_date,
                    exists().where(Result.prediction_id == Prediction.id)
                )
            )
        ).all()
        
        if not pending:
            logger.info("No pending predictions within lookback period to check.")
            return

        # Group matches by date
        # Use simple date string as key
        matches_by_date = {}
        for p in pending:
            d_str = p.date.strftime("%Y-%m-%d")
            match_str = _normalize_match(f"{p.home_team} vs {p.away_team}")
            if d_str not in matches_by_date:
                matches_by_date[d_str] = []
            
            # Find if this match is already in our plan for this date
            existing_group = next((m for m in matches_by_date[d_str] if m["match_str"] == match_str), None)
            if existing_group:
                existing_group["predictions"].append(p)
            else:
                matches_by_date[d_str].append({"match_str": match_str, "predictions": [p]})

        logger.info(f"Checking {len(pending)} pending predictions across {len(matches_by_date)} dates.")

        all_updated_dates = set()

        for date_str, match_groups in matches_by_date.items():
            matches_to_check = [m["match_str"] for m in match_groups]
            
            logger.info(f"Gathering results from BBC for {len(matches_to_check)} matches on {date_str}...")
            batch_results = batch_check_results(date_str, matches_to_check)
            
            if not batch_results:
                logger.warning(f"No results returned for {date_str}.")
                continue
                
            for m_group in match_groups:
                match_str = m_group["match_str"]
                if match_str in batch_results:
                    res = batch_results[match_str]
                    logger.info(f"Gemini result for {match_str}: {res}")
                    ht_h, ht_a = res.get("ht_home"), res.get("ht_away")
                    ft_h, ft_a = res.get("ft_home"), res.get("ft_away")
                    m_status = (res.get("match_status") or "").lower()
                    
                    # 1. Check if match was explicitly voided/abandoned
                    if any(s in m_status for s in ["postponed", "cancelled", "abandoned", "void"]):
                        for p in m_group["predictions"]:
                            p.status = "void"
                            logger.info(f"Updated {match_str} ({p.market}): Match {m_status.upper()} -> void")
                        continue

                    # 2. Match must be finished to settle results
                    if any(s in m_status for s in ["finished", "ft", "aet", "penalties"]):
                        if ft_h is not None and ft_a is not None:
                            all_updated_dates.add(date_str)
                            for p in m_group["predictions"]:
                                 # Save actual result details in the Results table
                                 existing_res = db.query(Result).filter(Result.prediction_id == p.id).first()
                                 if not existing_res:
                                     new_result = Result(
                                         prediction_id=p.id,
                                         ht_score_home=ht_h,
                                         ht_score_away=ht_a,
                                         ft_score_home=ft_h,
                                         ft_score_away=ft_a
                                     )
                                     db.add(new_result)
                                 else:
                                     # Update existing result if it was re-checked
                                     existing_res.ht_score_home = ht_h
                                     existing_res.ht_score_away = ht_a
                                     existing_res.ft_score_home = ft_h
                                     existing_res.ft_score_away = ft_a
                                     
                                 new_status = _evaluate_prediction(p, ht_h, ht_a, ft_h, ft_a)
                                 p.status = new_status
                                 logger.info(f"Updated {match_str} ({p.market}) ID {p.id}: HT {ht_h}-{ht_a}, FT {ft_h}-{ft_a} -> {p.status}")
                        else:
                            logger.info(f"Scores incomplete for {match_str} despite '{m_status}' status, keeping pending.")
                    else:
                        logger.info(f"Match {match_str} status is '{m_status}', keeping as pending.")

        db.commit()
        
        # After updating results, recalculate daily stats for all affected dates
        for d_str in all_updated_dates:
            try:
                dt_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
                _update_accuracy_stats(db, dt_obj, sport="football")
            except Exception as e:
                logger.error(f"Error updating stats for {d_str}: {e}")
        
        # Also re-evaluate any pending predictions that already have results (from past failed evaluations)
        pending_with_results = db.query(Prediction).join(Result).filter(
            Prediction.status == "pending"
        ).all()
        
        additional_updated_dates = set()
        for p in pending_with_results:
            res = p.result
            if res.ft_score_home is not None and res.ft_score_away is not None:
                new_status = _evaluate_prediction(p, res.ht_score_home, res.ht_score_away, res.ft_score_home, res.ft_score_away)
                if new_status != "pending":
                    p.status = new_status
                    logger.info(f"Re-evaluated past pending prediction {p.id} ({p.market}): -> {p.status}")
                    dt_obj = p.date.date()
                    additional_updated_dates.add(dt_obj)
        
        if additional_updated_dates:
            db.commit()
            for dt_obj in additional_updated_dates:
                try:
                    _update_accuracy_stats(db, dt_obj, sport="football")
                except Exception as e:
                    logger.error(f"Error updating stats for {dt_obj}: {e}")
        
        logger.info("Results checking process completed successfully.")

    except Exception as e:
        logger.error(f"Error in results checker: {str(e)}")
        db.rollback()
    finally:
        db.close()

def _normalize_team(name: str) -> str:
    """Normalize team name to match common BBC/ESPN naming conventions."""
    name = name.lower().strip()
    # Common abbreviations / aliases
    aliases = {
        "man utd": "manchester united", "man united": "manchester united",
        "man city": "manchester city",
        "wolves": "wolverhampton wanderers", "wolverhampton": "wolverhampton wanderers",
        "spurs": "tottenham hotspur", "tottenham": "tottenham hotspur",
        "brighton": "brighton & hove albion", "brighton and hove albion": "brighton & hove albion",
        "west ham": "west ham united",
        "newcastle": "newcastle united",
        "nottm forest": "nottingham forest", "nott'm forest": "nottingham forest",
        "sheff utd": "sheffield united", "sheffield utd": "sheffield united",
        "leicester": "leicester city",
        "ipswich": "ipswich town",
        "luton": "luton town",
        "athletic bilbao": "athletic club", "athletic club": "athletic club",
        "atletico madrid": "atlético madrid", "atlético madrid": "atlético madrid",
        "inter": "inter milan", "internazionale": "inter milan",
        "psg": "paris saint-germain", "paris saint germain": "paris saint-germain",
        "bayern": "bayern munich", "fc bayern": "bayern munich", "bayern münchen": "bayern munich",
        "dortmund": "borussia dortmund", "bvb": "borussia dortmund",
        "gladbach": "borussia mönchengladbach", "borussia monchengladbach": "borussia mönchengladbach",
        "rb leipzig": "rasenballsport leipzig", "leipzig": "rasenballsport leipzig",
        "real madrid": "real madrid",
        "barcelona": "barcelona",
        "arsenal": "arsenal",
        "chelsea": "chelsea",
        "liverpool": "liverpool",
        "manchester united": "manchester united",
        "manchester city": "manchester city",
    }
    return aliases.get(name, name).title()

def _normalize_match(match_str: str) -> str:
    """Normalize a match string like 'Home Team vs Away Team'."""
    parts = match_str.split(" vs ")
    if len(parts) == 2:
        home = _normalize_team(parts[0])
        away = _normalize_team(parts[1])
        return f"{home} vs {away}"
    return match_str
    """Evaluates whether a prediction was correct based on the actual scores."""
    market = prediction.market.lower()
    pred_value = prediction.prediction.lower()
    home_team = prediction.home_team.lower()
    away_team = prediction.away_team.lower()

    # Log evaluation attempt
    logger.info(f"Evaluating {prediction.id}: {market} | Pred: {pred_value} | FT: {ft_home}-{ft_away} (HT: {ht_home}-{ht_away})")

    try:
        # Half Time Markets
        if "1st half over 0.5" in market or "ht over 0.5" in market:
            ht_total = (ht_home if ht_home is not None else 0) + (ht_away if ht_away is not None else 0)
            if "1h over 0.5" in pred_value or "yes" in pred_value:
                return "won" if ht_total > 0 else "lost"
            elif "1h under 0.5" in pred_value:
                return "won" if ht_total < 1 else "lost"

        elif "1st half over 1.5" in market or "ht over 1.5" in market:
            ht_total = (ht_home if ht_home is not None else 0) + (ht_away if ht_away is not None else 0)
            if "1h over 1.5" in pred_value or "yes" in pred_value:
                return "won" if ht_total > 1 else "lost"
            elif "1h under 1.5" in pred_value:
                return "won" if ht_total < 2 else "lost"

        # 1. Goal Markets - Full Time
        if "over 0.5 goals" in market or ("over 0.5" in market and "goals" in market):
            ft_total = (ft_home if ft_home is not None else 0) + (ft_away if ft_away is not None else 0)
            if "over 0.5" in pred_value:
                return "won" if ft_total > 0 else "lost"
            elif "under 0.5" in pred_value:
                return "won" if ft_total < 1 else "lost"

        elif "over 1.5 goals" in market or ("over 1.5" in market and "goals" in market):
            ft_total = (ft_home if ft_home is not None else 0) + (ft_away if ft_away is not None else 0)
            if "over 1.5" in pred_value:
                return "won" if ft_total > 1 else "lost"
            elif "under 1.5" in pred_value:
                return "won" if ft_total < 2 else "lost"

        elif "over 2.5 goals" in market or ("over 2.5" in market and "goals" in market):
            ft_total = (ft_home if ft_home is not None else 0) + (ft_away if ft_away is not None else 0)
            if "over 2.5" in pred_value:
                return "won" if ft_total > 2 else "lost"
            elif "under 2.5" in pred_value:
                return "won" if ft_total < 3 else "lost"

        elif "over 3.5 goals" in market or ("over 3.5" in market and "goals" in market):
            ft_total = (ft_home if ft_home is not None else 0) + (ft_away if ft_away is not None else 0)
            if "over 3.5" in pred_value:
                return "won" if ft_total > 3 else "lost"
            elif "under 3.5" in pred_value:
                return "won" if ft_total < 4 else "lost"

        # Legacy over markets without "goals"
        elif "over 0.5" in market and "goals" not in market:
            ft_total = (ft_home if ft_home is not None else 0) + (ft_away if ft_away is not None else 0)
            if "yes" in pred_value:
                return "won" if ft_total > 0 else "lost"

        elif "over 1.5" in market and "goals" not in market:
            ft_total = (ft_home if ft_home is not None else 0) + (ft_away if ft_away is not None else 0)
            if "yes" in pred_value:
                return "won" if ft_total > 1 else "lost"

        elif "over 2.5" in market and "goals" not in market:
            ft_total = (ft_home if ft_home is not None else 0) + (ft_away if ft_away is not None else 0)
            if "yes" in pred_value:
                return "won" if ft_total > 2 else "lost"

        elif "over 3.5" in market and "goals" not in market:
            ft_total = (ft_home if ft_home is not None else 0) + (ft_away if ft_away is not None else 0)
            if "yes" in pred_value:
                return "won" if ft_total > 3 else "lost"

        elif "under 1.5" in market:
            ft_total = (ft_home if ft_home is not None else 0) + (ft_away if ft_away is not None else 0)
            if "yes" in pred_value:
                return "won" if ft_total < 2 else "lost"

        elif "under 2.5" in market:
            ft_total = (ft_home if ft_home is not None else 0) + (ft_away if ft_away is not None else 0)
            if "yes" in pred_value:
                return "won" if ft_total < 3 else "lost"
                
        elif "under 3.5" in market:
            ft_total = (ft_home if ft_home is not None else 0) + (ft_away if ft_away is not None else 0)
            if "yes" in pred_value:
                return "won" if ft_total < 4 else "lost"

        # BTTS
        elif "btts" in market or "both teams to score" in market:
            both_scored = (ft_home or 0) > 0 and (ft_away or 0) > 0
            if "btts - no" in pred_value or ("no" in pred_value and "btts" in market):
                return "won" if not both_scored else "lost"
            elif "btts - yes" in pred_value or ("yes" in pred_value and ("btts" in market or "both teams to score" in market)):
                return "won" if both_scored else "lost"

        # 2. Result Markets
        if ft_home is None or ft_away is None:
             return "pending"

        if ft_home > ft_away:
            actual_res = "1" # Home
        elif ft_away > ft_home:
            actual_res = "2" # Away
        else:
            actual_res = "x" # Draw

        # 1X2 / Match Result / Full Time / To Win
        if any(m in market for m in ["1x2", "match result", "full time", "to win"]):
            if any(v in pred_value for v in ["home win", "home", "1"]) or home_team in pred_value:
                return "won" if actual_res == "1" else "lost"
            elif any(v in pred_value for v in ["away win", "away", "2"]) or away_team in pred_value:
                return "won" if actual_res == "2" else "lost"
            elif any(v in pred_value for v in ["draw", "x"]):
                return "won" if actual_res == "x" else "lost"

        # Double Chance
        elif "double chance" in market:
            if "1x" in pred_value:
                return "won" if actual_res in ["1", "x"] else "lost"
            elif "x2" in pred_value:
                return "won" if actual_res in ["2", "x"] else "lost"
            elif "12" in pred_value:
                return "won" if actual_res in ["1", "2"] else "lost"

        # Draw No Bet
        elif "draw no bet" in market or "dnb" in market:
            if actual_res == "x":
                return "void"
            if any(v in pred_value for v in ["home", "1"]) or home_team in pred_value or "home dnb" in pred_value:
                return "won" if actual_res == "1" else "lost"
            elif any(v in pred_value for v in ["away", "2"]) or away_team in pred_value or "away dnb" in pred_value:
                return "won" if actual_res == "2" else "lost"

        logger.warning(f"Unknown market or unmatchable prediction for ID {prediction.id}: {market} | {pred_value}")
        return "pending" # Keep as pending if we can't decide, maybe we lack data

    except Exception as e:
        logger.error(f"Error evaluating prediction {prediction.id}: {str(e)}")
        return "pending"


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
    from routes.stats import normalize_market
    by_market = {}
    for p in all_preds:
        market = normalize_market(p.market)
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

