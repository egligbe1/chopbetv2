"""
ChopBet Gemini Prediction Engine (v6 — Data-Driven with FBref Stats)

Pipeline:
  Phase 1  →  Extract raw fixtures from BBC/Goal.com text (Gemini)
  Phase 2  →  Enrich each fixture with real team stats from FBref
  Phase 3  →  Send enriched fixtures to Gemini for data-driven prediction

Hard cap: max 25 predictions saved per run.
"""

import os
import json
import time
import logging
from google import genai
from google.genai import types
from datetime import datetime, UTC
from sqlalchemy import and_
from database import SessionLocal
from models import Prediction
from search_utils import search_utils
from ddgs import DDGS
from dotenv import load_dotenv

load_dotenv()

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini Client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FALLBACK_GEMINI_API_KEY = os.getenv("FALLBACK_GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

MAX_PREDICTIONS = 25  # Hard cap on daily predictions saved


# ============================================================================
# Gemini helpers
# ============================================================================

def _gemini_generate(prompt: str, schema: dict, model: str = "gemini-2.5-flash"):
    """Call Gemini with structured JSON output, retry on rate limit with fallback key."""
    global client
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )
            return json.loads(response.text.strip())
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                if attempt == 0 and FALLBACK_GEMINI_API_KEY:
                    logger.warning("Primary quota exhausted. Switching to fallback Gemini API key.")
                    client = genai.Client(api_key=FALLBACK_GEMINI_API_KEY)
                    continue
                if attempt < max_retries - 1:
                    sleep_time = 2 ** attempt * 10
                    logger.warning(f"Rate limited (429). Retrying in {sleep_time}s (attempt {attempt+1}/{max_retries})...")
                    time.sleep(sleep_time)
                    continue
            logger.error(f"Gemini generation failed: {e}")
            return None
    return None


# ============================================================================
# Phase 1 — Extract fixtures from raw text
# ============================================================================

FIXTURE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "fixtures": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "home_team": {"type": "STRING"},
                    "away_team": {"type": "STRING"},
                    "league": {"type": "STRING"},
                    "country": {"type": "STRING"},
                    "kickoff_time": {"type": "STRING"},
                },
                "required": ["home_team", "away_team", "league", "country", "kickoff_time"],
            },
        }
    },
    "required": ["fixtures"],
}


def extract_fixtures(raw_text: str, today_str: str) -> list[dict]:
    """Phase 1: Use Gemini to extract a clean list of today's fixtures from raw text."""
    prompt = f"""
    You are a football data extraction specialist. Today is {today_str}.
    Below is raw text scraped from a football fixtures page.

    TASK: Extract ALL real, scheduled football matches for today.
    Return ONLY the fixture data — no predictions, no analysis.

    RAW TEXT:
    {raw_text[:30000]}

    OUTPUT: A JSON object with a "fixtures" key containing an array.
    Each fixture object MUST have:
    - home_team: string (official team name)
    - away_team: string (official team name)
    - league: string (e.g. "Premier League", "La Liga")
    - country: string (e.g. "England", "Spain")
    - kickoff_time: string (ISO 8601 UTC, or best estimate like "15:00")
    """

    result = _gemini_generate(prompt, FIXTURE_SCHEMA)
    if result and "fixtures" in result:
        logger.info(f"Phase 1: Extracted {len(result['fixtures'])} fixtures from raw text.")
        return result["fixtures"]
    return []


# ============================================================================
# Phase 2 — Enrich fixtures with AI Search Context (DuckDuckGo)
# ============================================================================

def enrich_with_stats(fixtures: list[dict]) -> list[dict]:
    """
    Phase 2: For each fixture, use DuckDuckGo Search to fetch granular stats:
    last 5 form, goals scored/conceded, expected goals (xG), and injury news.
    Returns the same fixtures list with a 'search_context' key added to each.
    """
    logger.info(f"Phase 2: Enriching {len(fixtures)} fixtures with detailed search context...")
    enriched = []
    
    # We use a single DDGS instance
    ddgs = DDGS()

    for fixture in fixtures:
        home = fixture.get("home_team", "")
        away = fixture.get("away_team", "")
        
        # Granular queries based on user request
        queries = [
            f"{home} vs {away} last 5 matches form recent results",
            f"{home} vs {away} goals scored goals conceded stats",
            f"{home} vs {away} expected goals xG stat",
            f"{home} vs {away} injury news missing players"
        ]
        
        snippets = []
        for q in queries:
            try:
                # Slight delay between rapid searches to avoid blocking
                time.sleep(1.5)
                results = ddgs.text(q, max_results=1)
                for r in results:
                    if r.get('body'):
                        snippets.append(f"[{q}] " + r['body'].strip())
            except Exception as e:
                logger.warning(f"DuckDuckGo search failed for query '{q}': {e}")
                
        if snippets:
            fixture["search_context"] = " | ".join(snippets)
        else:
            fixture["search_context"] = None

        enriched.append(fixture)

    logger.info(f"Phase 2 complete: Enriched {len(enriched)} fixtures.")
    return enriched


# ============================================================================
# Phase 3 — Data-driven prediction with stats
# ============================================================================

PREDICTION_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "predictions": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
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
                    "risk_rating": {"type": "STRING"},
                },
                "required": [
                    "home_team", "away_team", "league", "country",
                    "kickoff_time", "market", "prediction", "confidence",
                    "odds", "source_link", "reasoning", "risk_rating",
                ],
            },
        }
    },
    "required": ["predictions"],
}


def predict_with_stats(enriched_fixtures: list[dict], today_str: str) -> list[dict]:
    """
    Phase 3: Send enriched fixtures (with search context) to Gemini for prediction.
    Returns a list of prediction dicts (max 25).
    """

    # Build a compact JSON representation of fixtures + search context for the prompt
    fixtures_json = []
    for f in enriched_fixtures:
        entry = {
            "home_team": f.get("home_team"),
            "away_team": f.get("away_team"),
            "league": f.get("league"),
            "country": f.get("country"),
            "kickoff_time": f.get("kickoff_time"),
        }
        if f.get("search_context"):
            entry["search_context"] = f["search_context"]
        fixtures_json.append(entry)

    fixtures_text = json.dumps(fixtures_json, indent=1, default=str)
    # Truncate if excessively long
    if len(fixtures_text) > 60000:
        fixtures_text = fixtures_text[:60000] + "\n... (truncated)"

    prompt = f"""
    You are an elite football betting analyst and data scientist. Today is {today_str}.

    Below is a list of today's football fixtures. Most have been enriched with 
    REAL search snippets ("search_context") grabbed from recent match previews across the web.
    These snippets contain clues about recent form, injuries, xG, and tactical points.

    FIXTURES AND SEARCH CONTEXT:
    {fixtures_text}

    YOUR TASK:
    1. Analyse ALL fixtures using the provided real-world search context — not general knowledge.
    2. Select the TOP 20–25 highest-value, highest-confidence bets.
    3. For each pick, base your reasoning EXPLICITLY on the search snippets provided:
       - Reference actual form mentions, specific player injuries, or stats highlighted.
       - Example reasoning: "Search snippets indicate Arsenal has won 4 of their last 5, while Chelsea is missing their starting CB due to injury."
    4. STRONGLY PRIORITIZE SAFER MARKETS over straight wins. Straight wins (1X2) are highly volatile.
       Instead, seek out high-probability outcomes like:
       - Double Chance (1X or X2)
       - Draw No Bet (Home DNB or Away DNB)
       - Over 1.5 Goals
       - Over 2.5 Goals (only if both teams are statistically high-scoring/conceding)
       - BTTS - Yes/No
       Only suggest a straight win if there is a massive, statistically proven disparity.
    5. Only include predictions with confidence ≥ 70.
    6. Prioritise "low" and "medium" risk picks. Include "high" risk only if strongly
       justified by the data.

    OUTPUT: Return a JSON object with a "predictions" key containing 20–25 objects.
    Each object MUST have:
    - home_team: string
    - away_team: string
    - league: string
    - country: string
    - kickoff_time: ISO 8601 string in UTC
    - market: string (e.g., "Double Chance 1X", "Over 1.5 Goals", "Draw No Bet", "BTTS - Yes")
    - prediction: string
    - confidence: integer (70–100)
    - odds: float (realistic decimal odds for these safer markets, typically 1.15–1.80)
    - source_link: "https://www.bbc.com/sport/football"
    - reasoning: string (2–3 sentences citing ACTUAL stats from the data provided)
    - risk_rating: string ("low", "medium", or "high")

    The final list must be curated and elite — quality over quantity.
    """

    result = _gemini_generate(prompt, PREDICTION_SCHEMA)
    if result and "predictions" in result:
        preds = result["predictions"]
        # Hard cap
        if len(preds) > MAX_PREDICTIONS:
            preds.sort(key=lambda p: p.get("confidence", 0), reverse=True)
            preds = preds[:MAX_PREDICTIONS]
        logger.info(f"Phase 3: Gemini returned {len(preds)} data-driven predictions.")
        return preds
    return []


# ============================================================================
# Main orchestration
# ============================================================================

def _deduplicate_fixtures(fixtures: list[dict]) -> list[dict]:
    """Remove duplicate fixtures (same home+away, case-insensitive)."""
    seen = set()
    unique = []
    for f in fixtures:
        key = (f.get("home_team", "").lower().strip(), f.get("away_team", "").lower().strip())
        if key not in seen and key[0] and key[1]:
            seen.add(key)
            unique.append(f)
    return unique


def generate_predictions():
    """
    Orchestrates the full data-driven prediction pipeline:
      1. Scrape BBC + Goal.com for raw fixture text
      2. Extract structured fixtures via Gemini
      3. Enrich each fixture with FBref stats
      4. Send enriched data to Gemini for prediction
      5. Save top 25 predictions to DB
    """
    logger.info("Starting prediction engine (v6 — Data-Driven with FBref Stats)...")
    db = SessionLocal()
    today_str = datetime.now(UTC).strftime("%Y-%m-%d")

    try:
        # ── Phase 1: Extract fixtures from BBC + Goal.com ──────────────
        all_fixtures = []

        bbc_text = search_utils.get_bbc_fixtures(today_str)
        if bbc_text and len(bbc_text) > 100:
            logger.info("Phase 1a: Extracting fixtures from BBC text...")
            bbc_fixtures = extract_fixtures(bbc_text, today_str)
            all_fixtures.extend(bbc_fixtures)
        else:
            logger.warning("Failed to fetch meaningful BBC fixtures text.")

        logger.info("Waiting 10s before processing Goal.com...")
        time.sleep(10)

        goal_text = search_utils.get_goal_fixtures(today_str)
        if goal_text and len(goal_text) > 100:
            logger.info("Phase 1b: Extracting fixtures from Goal.com text...")
            goal_fixtures = extract_fixtures(goal_text, today_str)
            all_fixtures.extend(goal_fixtures)

        # Deduplicate across sources
        all_fixtures = _deduplicate_fixtures(all_fixtures)
        logger.info(f"Phase 1 complete: {len(all_fixtures)} unique fixtures extracted.")

        if not all_fixtures:
            logger.error("No fixtures extracted from any source. Aborting.")
            return

        # ── Phase 2: Enrich with FBref stats ───────────────────────────
        enriched = enrich_with_stats(all_fixtures)

        # ── Phase 3: Data-driven prediction ────────────────────────────
        logger.info("Phase 3: Sending enriched fixtures to Gemini for prediction...")
        all_preds = predict_with_stats(enriched, today_str)

        if not all_preds:
            logger.error("Phase 3 failed — no predictions returned from Gemini.")
            return

        # ── Phase 4: Save to database ──────────────────────────────────
        saved_count = 0
        duplicate_count = 0

        # Sort by confidence desc and take top MAX_PREDICTIONS
        all_preds.sort(key=lambda p: p.get("confidence", 0), reverse=True)
        all_preds = all_preds[:MAX_PREDICTIONS]

        logger.info(f"Saving top {len(all_preds)} predictions to database...")

        for p_data in all_preds:
            try:
                p_date_str = p_data.get("date", today_str)
                if not p_date_str:
                    p_date_str = today_str
                p_date = (
                    datetime.fromisoformat(p_date_str)
                    if "T" in p_date_str
                    else datetime.strptime(p_date_str, "%Y-%m-%d").replace(tzinfo=UTC)
                )
                home = p_data["home_team"]
                away = p_data["away_team"]

                # Handle kickoff time
                ko_str = p_data.get("kickoff_time", "00:00")
                if "T" in ko_str:
                    ko_time = datetime.fromisoformat(ko_str.replace("Z", "+00:00"))
                else:
                    ko_clean = ko_str.replace("Z", "")
                    parts = ko_clean.split(":")
                    if len(parts) == 2:
                        ko_clean += ":00"
                    elif len(parts) == 1:
                        ko_clean = "00:00:00"
                    ko_time = datetime.fromisoformat(f"{today_str}T{ko_clean}+00:00")

                # Check for duplicate
                from sqlalchemy import func, cast, Date

                existing = db.query(Prediction).filter(
                    and_(
                        func.lower(Prediction.home_team) == home.lower(),
                        func.lower(Prediction.away_team) == away.lower(),
                        cast(Prediction.date, Date) == p_date.date(),
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
                    market=p_data["market"],
                    prediction=p_data["prediction"],
                    confidence=p_data["confidence"],
                    odds=p_data.get("odds", 1.5),
                    source_link=p_data.get("source_link", "https://www.bbc.com/sport/football"),
                    reasoning=p_data["reasoning"],
                    risk_rating=p_data["risk_rating"],
                    status="pending",
                )
                db.add(prediction)
                saved_count += 1
            except Exception as e:
                logger.warning(f"Skipping invalid prediction data: {e}")
                continue

        db.commit()
        logger.info(
            f"Engine complete. Saved {saved_count} new predictions. "
            f"Skipped {duplicate_count} duplicates."
        )

    except Exception as e:
        logger.error(f"Engine failure: {str(e)}")
        db.rollback()
    finally:
        db.close()
