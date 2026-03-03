import os
import json
import logging
from google import genai
from google.genai import types
from datetime import datetime, UTC
from sqlalchemy import and_
from database import SessionLocal
from models import Prediction
from search_utils import search_utils
from dotenv import load_dotenv

load_dotenv()

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini Client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FALLBACK_GEMINI_API_KEY = os.getenv("FALLBACK_GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

def _generate_with_fallback(prompt: str):
    """Generate content from Gemini, retrying with a fallback model if quota exhausted."""
    try:
        return client.models.generate_content(
            model="gemini-flash-latest",
            contents=prompt,
        )
    except Exception as e:
        msg = str(e)
        # look for resource exhausted error and try cheaper model
        if "RESOURCE_EXHAUSTED" in msg or "429" in msg:
            logger.warning("Primary Gemini model quota exhausted, attempting fallback model.")
            try:
                return client.models.generate_content(
                    model=os.getenv("GEMINI_FALLBACK_MODEL", "gemini-1.5-flash"),
                    contents=prompt,
                )
            except Exception as e2:
                logger.error(f"Fallback model also failed: {e2}")
                raise
        else:
            raise


def batch_analyze_fixtures(bbc_text, today_str):
    """
    Sends the raw BBC text to Gemini in ONE prompt to both extract fixtures 
    and provide predictions for all of them simultaneously.
    """
    prompt = f"""
    You are a professional football data scientist. Today is {today_str}.
    Below is the raw text scraped from the BBC Sport fixtures page for today.
    
    TASK:
    1. Identify ALL REAL, SCHEDULED football matches for today from the raw text. Include as many matches as you can accurately extract from the text.
    2. For EACH identified match, generate a high-confidence prediction. Use your extensive general knowledge about the teams' current form, injuries, and historical performance.
    
    RAW BBC TEXT:
    {bbc_text[:30000]} # Truncated to avoid massive context sizes, though Gemini 1.5 handles it easily.
    
    OUTPUT FORMAT REQUIREMENTS:
    Return ONLY a JSON object with a "predictions" key containing an array. Each object MUST have:
    - date: "{today_str}"
    - home_team: string
    - away_team: string
    - league: string
    - country: string
    - kickoff_time: ISO 8601 string in UTC (or best estimate if not found)
    - market: string (Choose one: "HT Over 0.5", "Total Over 1.5", "BTTS", "1X2")
    - prediction: string
    - confidence: integer (0-100)
    - odds: float (Realistic decimal odds)
    - source_link: "https://www.bbc.com/sport/football"
    - reasoning: string (2-3 sentences justifying the prediction based on typical form/stats)
    - risk_rating: string ("low", "medium", "high")
    
    Ensure the output is strictly valid JSON without markdown wrapping.
    """
    
    schema = {
        "type": "OBJECT",
        "properties": {
            "predictions": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "date": {"type": "STRING"},
                        "home_team": {"type": "STRING"},
                        "away_team": {"type": "STRING"},
                        "league": {"type": "STRING"},
                        "country": {"type": "STRING"},
                        "kickoff_time": {"type": "STRING"},
                        "market": {"type": "STRING"},
                        "prediction": {"type": "STRING"},
                        "confidence": {"type": "INTEGER"},
                        "odds": {"type": "NUMBER"},
                        "source_link": {"type": "STRING"},
                        "reasoning": {"type": "STRING"},
                        "risk_rating": {"type": "STRING"}
                    },
                    "required": ["date", "home_team", "away_team", "league", "country", "kickoff_time", "market", "prediction", "confidence", "odds", "source_link", "reasoning", "risk_rating"]
                }
            }
        },
        "required": ["predictions"]
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
                ),
            )
            raw_text = response.text.strip()
            return json.loads(raw_text)
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
            logger.error(f"Error in batch analysis: {e}")
            return None
    return None

def generate_predictions():
    """
    Orchestrates the single-shot batch prediction flow using BBC data.
    """
    logger.info("Starting prediction generation engine (v5 - BBC Scraper Batch)...")
    db = SessionLocal()
    today_str = datetime.now(UTC).strftime("%Y-%m-%d")
    
    try:
        # 1. Get raw BBC Fixtures text
        all_preds = []
        bbc_text = search_utils.get_bbc_fixtures(today_str)
        if bbc_text and len(bbc_text) > 100:
            logger.info("Sending batch request to Gemini for BBC fixtures extraction and prediction...")
            results = batch_analyze_fixtures(bbc_text, today_str)
            if results and "predictions" in results:
                all_preds.extend(results["predictions"])
        else:
            logger.warning("Failed to fetch meaningful BBC fixtures text.")

        import time
        logger.info("Waiting 15 seconds before processing Goal.com to prevent rapid API calls...")
        time.sleep(15)

        # 2. Scrape Goal.com to combine fixtures
        logger.info("Scraping Goal.com for additional fixtures...")
        goal_text = search_utils.get_goal_fixtures(today_str)
        if goal_text and len(goal_text) > 100:
            logger.info("Sending batch request to Gemini for Goal.com extraction...")
            goal_results = batch_analyze_fixtures(goal_text, today_str)
            if goal_results and "predictions" in goal_results:
                all_preds.extend(goal_results["predictions"])

        if not all_preds:
            logger.error("Batch analysis failed to produce predictions from any source.")
            return

        # 3. Save to Database
        saved_count = 0
        duplicate_count = 0
        
        logger.info(f"Gemini returned {len(all_preds)} total predictions.")
        
        for p_data in all_preds:
            try:
                p_date_str = p_data["date"]
                p_date = datetime.fromisoformat(p_date_str) if "T" in p_date_str else datetime.strptime(p_date_str, "%Y-%m-%d").replace(tzinfo=UTC)
                home = p_data["home_team"]
                away = p_data["away_team"]
                market = p_data["market"]
                
                # Handle kickoff time which might just be '14:00' or '14:00:00Z'
                ko_str = p_data.get("kickoff_time", "00:00")
                if "T" in ko_str:
                    ko_time = datetime.fromisoformat(ko_str.replace("Z", "+00:00"))
                else:
                    # just a time
                    ko_clean = ko_str.replace("Z", "")
                    parts = ko_clean.split(":")
                    if len(parts) == 2: 
                        ko_clean += ":00"
                    elif len(parts) == 1:
                        ko_clean = "00:00:00"
                    ko_time = datetime.fromisoformat(f"{p_date_str[:10]}T{ko_clean}+00:00")

                # Check for duplicate strictly
                from sqlalchemy import func, cast, Date
                existing = db.query(Prediction).filter(
                    and_(
                        func.lower(Prediction.home_team) == home.lower(),
                        func.lower(Prediction.away_team) == away.lower(),
                        cast(Prediction.date, Date) == p_date.date()
                    )
                ).first()

                if existing:
                    duplicate_count += 1
                    continue

                prediction = Prediction(
                    date=p_date,
                    home_team=home,
                    away_team=away,
                    league=p_data["league"],
                    country=p_data["country"],
                    kickoff_time=ko_time,
                    market=market,
                    prediction=p_data["prediction"],
                    confidence=p_data["confidence"],
                    odds=p_data.get("odds", 1.5),
                    source_link=p_data.get("source_link", "https://www.bbc.com/sport/football"),
                    reasoning=p_data["reasoning"],
                    risk_rating=p_data["risk_rating"],
                    status="pending"
                )
                db.add(prediction)
                saved_count += 1
            except Exception as e:
                logger.warning(f"Skipping invalid prediction data format: {e}")
                continue
                
        db.commit()
        logger.info(f"Successfully saved {saved_count} new predictions. Skipped {duplicate_count} duplicates.")

    except Exception as e:
        logger.error(f"Engine failure: {str(e)}")
        db.rollback()
    finally:
        db.close()
