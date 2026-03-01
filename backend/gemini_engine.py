import os
import json
import logging
from google import genai
from google.genai import types
from datetime import datetime, UTC
from sqlalchemy.orm import Session
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
client = genai.Client(api_key=GEMINI_API_KEY)

def extract_fixtures_from_search(search_results, today_str):
    """
    Uses Gemini to extract a clean list of 10-15 fixtures from rough search results.
    """
    prompt = f"""
    The following are search results for football fixtures on {today_str}.
    Extract exactly 10 to 15 REAL, SCHEDULED matches for today.
    Format your response as a JSON array of objects with "home_team" and "away_team" keys.
    Only include major European leagues (EPL, La Liga, Serie A, Bundesliga, Ligue 1).
    
    Search Results:
    {json.dumps(search_results)}
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=prompt,
        )
        
        raw_text = response.text.strip()
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0].strip()
            
        fixtures = json.loads(raw_text)
        if isinstance(fixtures, dict) and "fixtures" in fixtures:
            return fixtures["fixtures"]
        return fixtures if isinstance(fixtures, list) else []
    except Exception as e:
        logger.error(f"Error extracting fixtures: {e}")
        return []

def analyze_matches(bundled_context, today_str):
    """
    Final analysis stage: feeds search context into Gemini for structured predictions.
    """
    prompt = f"""
    You are a professional football data scientist. Today is {today_str}.
    Based on the SEARCH CONTEXT provided below, generate high-confidence predictions for each match.
    
    SEARCH CONTEXT (Real data on form, injuries, team news):
    {bundled_context}
    
    REQUIREMENTS:
    1. Output MUST be valid JSON.
    2. Zero Hallucination: Use ONLY the provided context to justify reasoning.
    3. Include realistic decimal odds.
    
    OUTPUT FORMAT:
    Return a JSON object with a "predictions" key containing an array. Each object MUST have:
    - date: "{today_str}"
    - home_team: string
    - away_team: string
    - league: string
    - country: string
    - kickoff_time: ISO 8601 string in UTC
    - market: string ("HT Over 0.5", "Total Over 1.5", "BTTS", "1X2")
    - prediction: string
    - confidence: integer (0-100)
    - odds: float
    - source_link: string (The URL from context where info was found)
    - reasoning: string (2-3 sentences based on stats in context)
    - risk_rating: string
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=prompt,
        )
        
        raw_text = response.text.strip()
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0].strip()
            
        return json.loads(raw_text)
    except Exception as e:
        logger.error(f"Error in final analysis: {e}")
        return None

def generate_predictions():
    """
    Orchestrates the Search-First prediction flow.
    """
    logger.info("Starting prediction generation engine (v4 - External Search Grounding)...")
    db = SessionLocal()
    today_str = datetime.now(UTC).strftime("%Y-%m-%d")
    
    try:
        # 1. Get Fixtures
        fixtures_raw = search_utils.get_fixtures_context(today_str)
        if not fixtures_raw:
            logger.error("No fixtures found in search.")
            return

        # 2. Extract structured list
        fixtures_list = extract_fixtures_from_search(fixtures_raw, today_str)
        if not fixtures_list:
            logger.error("Failed to extract structured fixtures.")
            return
            
        logger.info(f"Extracted {len(fixtures_list)} real fixtures.")

        # 3. Gather Context per Match
        bundled_context = []
        # Limit to 10 to stay within search tier safety
        for match in fixtures_list[:10]:
            home, away = match.get("home_team"), match.get("away_team")
            if not home or not away: continue
            
            logger.info(f"Gathering context for: {home} vs {away}")
            ctx = search_utils.get_match_context(home, away, today_str)
            bundled_context.append({
                "match": f"{home} vs {away}",
                "search_data": ctx
            })

        # 4. Final Analysis
        if not bundled_context:
            logger.error("No match context gathered.")
            return
            
        results = analyze_matches(json.dumps(bundled_context), today_str)
        if not results or "predictions" not in results:
            logger.error("Final analysis failed to produce predictions.")
            return

        # 5. Save to Database
        saved_count = 0
        for p_data in results["predictions"]:
            try:
                prediction = Prediction(
                    date=datetime.fromisoformat(p_data["date"]),
                    home_team=p_data["home_team"],
                    away_team=p_data["away_team"],
                    league=p_data["league"],
                    country=p_data["country"],
                    kickoff_time=datetime.fromisoformat(p_data["kickoff_time"]),
                    market=p_data["market"],
                    prediction=p_data["prediction"],
                    confidence=p_data["confidence"],
                    odds=p_data.get("odds", 1.5),
                    source_link=p_data.get("source_link"),
                    reasoning=p_data["reasoning"],
                    risk_rating=p_data["risk_rating"],
                    status="pending"
                )
                db.add(prediction)
                saved_count += 1
            except Exception as e:
                logger.warning(f"Skipping invalid prediction data: {e}")
                continue
                
        db.commit()
        logger.info(f"Successfully processed {saved_count} grounded predictions.")

    except Exception as e:
        logger.error(f"Engine failure: {str(e)}")
        db.rollback()
    finally:
        db.close()


def extract_nba_fixtures_from_search(search_results, today_str):
    """Uses Gemini to extract a clean list of NBA fixtures from rough search results."""
    prompt = f"""
    The following are search results for NBA basketball fixtures on {today_str}.
    Extract the ACTUAL, SCHEDULED matches for today.
    Format your response as a JSON array of objects with "home_team" and "away_team" keys.
    
    Search Results:
    {json.dumps(search_results)}
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=prompt,
        )
        
        raw_text = response.text.strip()
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0].strip()
            
        fixtures = json.loads(raw_text)
        if isinstance(fixtures, dict) and "fixtures" in fixtures:
            return fixtures["fixtures"]
        return fixtures if isinstance(fixtures, list) else []
    except Exception as e:
        logger.error(f"Error extracting NBA fixtures: {e}")
        return []

def analyze_nba_matches(bundled_context, today_str):
    """Final analysis stage for NBA matches."""
    prompt = f"""
    You are a professional NBA data scientist. Today is {today_str}.
    Based on the SEARCH CONTEXT provided below, generate high-confidence predictions for each match.
    
    SEARCH CONTEXT (Real data on form, injuries, starting lineups):
    {bundled_context}
    
    REQUIREMENTS:
    1. Output MUST be valid JSON.
    2. Zero Hallucination: Use ONLY the provided context to justify reasoning.
    3. Include realistic decimal odds.
    
    OUTPUT FORMAT:
    Return a JSON object with a "predictions" key containing an array. Each object MUST have:
    - date: "{today_str}"
    - home_team: string
    - away_team: string
    - league: "NBA"
    - country: "USA"
    - kickoff_time: ISO 8601 string in UTC
    - market: string (e.g., "Moneyline", "Spread -5.5", "Total Over 220.5")
    - prediction: string (e.g., "LA Lakers", "Boston Celtics", "Over 220.5")
    - confidence: integer (0-100)
    - odds: float
    - source_link: string (The URL from context where info was found)
    - reasoning: string (2-3 sentences based on stats/injuries in context)
    - risk_rating: string
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=prompt,
        )
        
        raw_text = response.text.strip()
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0].strip()
            
        return json.loads(raw_text)
    except Exception as e:
        logger.error(f"Error in final NBA analysis: {e}")
        return None

def generate_nba_predictions():
    """Orchestrates the Search-First NBA prediction flow."""
    logger.info("Starting NBA prediction generation engine...")
    db = SessionLocal()
    today_str = datetime.now(UTC).strftime("%Y-%m-%d")
    
    try:
        # 1. Get Fixtures
        fixtures_raw = search_utils.get_nba_fixtures_context(today_str)
        if not fixtures_raw:
            logger.error("No NBA fixtures found in search.")
            return

        # 2. Extract structured list
        fixtures_list = extract_nba_fixtures_from_search(fixtures_raw, today_str)
        if not fixtures_list:
            logger.error("Failed to extract structured NBA fixtures.")
            return
            
        logger.info(f"Extracted {len(fixtures_list)} real NBA fixtures.")

        # 3. Gather Context per Match
        bundled_context = []
        for match in fixtures_list[:8]: # Limit for safety
            home, away = match.get("home_team"), match.get("away_team")
            if not home or not away: continue
            
            logger.info(f"Gathering context for: {home} vs {away}")
            ctx = search_utils.get_nba_match_context(home, away, today_str)
            bundled_context.append({
                "match": f"{home} vs {away}",
                "search_data": ctx
            })

        # 4. Final Analysis
        if not bundled_context:
            logger.error("No NBA match context gathered.")
            return
            
        results = analyze_nba_matches(json.dumps(bundled_context), today_str)
        if not results or "predictions" not in results:
            logger.error("Final analysis failed to produce NBA predictions.")
            return

        # 5. Save to Database
        saved_count = 0
        for p_data in results["predictions"]:
            try:
                prediction = Prediction(
                    date=datetime.fromisoformat(p_data["date"]),
                    home_team=p_data["home_team"],
                    away_team=p_data["away_team"],
                    league=p_data.get("league", "NBA"),
                    country=p_data.get("country", "USA"),
                    sport="basketball",
                    kickoff_time=datetime.fromisoformat(p_data["kickoff_time"]),
                    market=p_data["market"],
                    prediction=p_data["prediction"],
                    confidence=p_data["confidence"],
                    odds=p_data.get("odds", 1.85),
                    source_link=p_data.get("source_link"),
                    reasoning=p_data["reasoning"],
                    risk_rating=p_data["risk_rating"],
                    status="pending"
                )
                db.add(prediction)
                saved_count += 1
            except Exception as e:
                logger.warning(f"Skipping invalid NBA prediction data: {e}")
                continue
                
        db.commit()
        logger.info(f"Successfully processed {saved_count} grounded NBA predictions.")

    except Exception as e:
        logger.error(f"NBA Engine failure: {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    generate_predictions()
    generate_nba_predictions()
