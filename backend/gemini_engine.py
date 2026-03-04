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
from cache import invalidate_cache
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
MIN_PREDICTIONS = 15  # Minimum target — retry if below this


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
    
    IMPORTANT: Extract EVERY match you can find. Do NOT skip any match.
    Look for matches from ALL leagues mentioned, not just top leagues.
    It is critical that you capture as many fixtures as possible.

    RAW TEXT:
    {raw_text[:300000]}

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

def enrich_with_stats(fixtures: list[dict], today_str: str) -> list[dict]:
    """
    Phase 2: For each fixture, find its BBC match link and scrape preview stats
    (H2H and Match Facts).
    """
    logger.info(f"Phase 2: Enriching {len(fixtures)} fixtures with BBC match page stats...")
    
    # 1. Get all available match links for today
    match_links = search_utils.get_bbc_match_links(today_str)
    
    enriched = []
    for fixture in fixtures:
        home = fixture.get("home_team", "").lower().strip()
        away = fixture.get("away_team", "").lower().strip()
        
        # 2. Match the extracted fixture to a BBC link
        match_url = None
        for link_data in match_links:
            link_text = link_data["teams"].lower()
            # Simple heuristic: if both home and away team names are in the link text
            if home in link_text and away in link_text:
                match_url = link_data["url"]
                break
        
        # 3. Scrape the match page if found
        if match_url:
            logger.info(f"Scraping BBC stats for: {fixture['home_team']} vs {fixture['away_team']}")
            fixture["search_context"] = search_utils.get_match_preview_stats(match_url)
            fixture["source_link"] = match_url
            # Small delay to be polite to BBC
            time.sleep(1)
        else:
            logger.warning(f"No BBC match page found for {fixture['home_team']} vs {fixture['away_team']}")
            fixture["search_context"] = None
            fixture["source_link"] = "https://www.bbc.com/sport/football"

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

    # Determine target based on available fixtures
    num_fixtures = len(enriched_fixtures)
    target_min = min(15, num_fixtures)  # Can't predict more than we have
    target_max = min(25, num_fixtures)

    prompt = f"""
    You are an elite football betting analyst and data scientist. Today is {today_str}.

    Below is a list of {num_fixtures} football fixtures for today. Most have been enriched with 
    REAL search snippets ("search_context") grabbed from recent match previews across the web.
    These snippets contain clues about recent form, injuries, xG, and tactical points.

    FIXTURES AND SEARCH CONTEXT:
    {fixtures_text}

    YOUR TASK:
    1. Analyse ALL {num_fixtures} fixtures using the provided real-world search context — not general knowledge.
    2. Select {target_min}–{target_max} highest-value, highest-confidence bets.
       YOU MUST PROVIDE AT LEAST {target_min} PREDICTIONS. This is a strict minimum.
       If there are {num_fixtures} fixtures available, you should predict on most of them.
    3. CRITICAL RULE: You MUST select exactly ONE prediction per match. NEVER include the same
       match (same home_team vs away_team) more than once. Pick the single best market for each match.
    4. For each pick, base your reasoning EXPLICITLY on the search snippets provided:
       - Reference actual form mentions, specific player injuries, or stats highlighted.
       - Example reasoning: "Search snippets indicate Arsenal has won 4 of their last 5, while Chelsea is missing their starting CB due to injury."
    5. STRONGLY PRIORITIZE SAFER MARKETS over straight wins. Straight wins (1X2) are highly volatile.
       Instead, seek out high-probability outcomes like:
       - Double Chance (1X or X2)
       - Draw No Bet (Home DNB or Away DNB)
       - Over 1.5 Goals
       - Over 2.5 Goals (only if both teams are statistically high-scoring/conceding)
       - BTTS - Yes/No
       Only suggest a straight win if there is a massive, statistically proven disparity.
    6. Only include predictions with confidence ≥ 65.
    7. Prioritise "low" and "medium" risk picks. Include "high" risk only if strongly
       justified by the data.

    OUTPUT: Return a JSON object with a "predictions" key containing {target_min}–{target_max} objects.
    REMEMBER: Each match must appear ONLY ONCE. No duplicate matches allowed.
    You MUST return at least {target_min} predictions.
    Each object MUST have:
    - home_team: string (use the full official team name consistently)
    - away_team: string (use the full official team name consistently)
    - league: string
    - country: string
    - kickoff_time: ISO 8601 string in UTC
    - market: string (e.g., "Double Chance 1X", "Over 1.5 Goals", "Draw No Bet", "BTTS - Yes")
    - prediction: string
    - confidence: integer (65–100)
    - odds: float (realistic decimal odds for these safer markets, typically 1.15–1.80)
    - source_link: "https://www.bbc.com/sport/football"
    - reasoning: string (2–3 sentences citing ACTUAL stats from the data provided)
    - risk_rating: string ("low", "medium", or "high")

    The final list must be curated and elite — quality over quantity. NO DUPLICATE MATCHES.
    """

    result = _gemini_generate(prompt, PREDICTION_SCHEMA)
    if result and "predictions" in result:
        preds = result["predictions"]
        # Deduplicate predictions (one per match, keep highest confidence)
        preds = _deduplicate_predictions(preds)
        # Hard cap
        if len(preds) > MAX_PREDICTIONS:
            preds.sort(key=lambda p: p.get("confidence", 0), reverse=True)
            preds = preds[:MAX_PREDICTIONS]
        logger.info(f"Phase 3: Gemini returned {len(preds)} unique data-driven predictions.")
        return preds
    return []


# ============================================================================
# Main orchestration
# ============================================================================

def _normalize_team(name: str) -> str:
    """Normalize team name for dedup comparison."""
    name = name.lower().strip()
    # Common abbreviations / aliases
    aliases = {
        "man utd": "manchester united", "man united": "manchester united",
        "man city": "manchester city",
        "wolves": "wolverhampton wanderers", "wolverhampton": "wolverhampton wanderers",
        "spurs": "tottenham hotspur", "tottenham": "tottenham hotspur",
        "brighton": "brighton and hove albion", "brighton & hove albion": "brighton and hove albion",
        "west ham": "west ham united",
        "newcastle": "newcastle united",
        "nottm forest": "nottingham forest", "nott'm forest": "nottingham forest",
        "sheff utd": "sheffield united", "sheffield utd": "sheffield united",
        "leicester": "leicester city",
        "ipswich": "ipswich town",
        "luton": "luton town",
        "athletic bilbao": "athletic club",
        "atletico madrid": "atletico de madrid", "atlético madrid": "atletico de madrid",
        "inter": "inter milan", "internazionale": "inter milan",
        "psg": "paris saint-germain", "paris saint germain": "paris saint-germain",
        "bayern": "bayern munich", "fc bayern": "bayern munich", "bayern münchen": "bayern munich",
        "dortmund": "borussia dortmund", "bvb": "borussia dortmund",
        "gladbach": "borussia monchengladbach",
        "rb leipzig": "rasenballsport leipzig", "leipzig": "rasenballsport leipzig",
    }
    for alias, canonical in aliases.items():
        if name == alias:
            return canonical
    return name


def _match_key(home: str, away: str) -> tuple:
    """Create a normalized dedup key for a match."""
    return (_normalize_team(home), _normalize_team(away))


def _deduplicate_fixtures(fixtures: list[dict]) -> list[dict]:
    """Remove duplicate fixtures (same home+away, case-insensitive with alias matching)."""
    seen = set()
    unique = []
    for f in fixtures:
        key = _match_key(f.get("home_team", ""), f.get("away_team", ""))
        if key not in seen and key[0] and key[1]:
            seen.add(key)
            unique.append(f)
    return unique


def _deduplicate_predictions(predictions: list[dict]) -> list[dict]:
    """Remove duplicate predictions for the same match (keep highest confidence)."""
    best = {}  # key -> prediction dict
    for p in predictions:
        key = _match_key(p.get("home_team", ""), p.get("away_team", ""))
        if key[0] and key[1]:
            existing = best.get(key)
            if existing is None or p.get("confidence", 0) > existing.get("confidence", 0):
                best[key] = p
    return list(best.values())


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
            logger.info("Phase 1a: Extracting fixtures from BBC text (including JSON state)...")
            bbc_fixtures = extract_fixtures(bbc_text, today_str)
            all_fixtures.extend(bbc_fixtures)
            logger.info(f"BBC: extracted {len(bbc_fixtures)} fixtures.")
        else:
            logger.warning("Failed to fetch meaningful BBC fixtures text.")

        # User requested ONLY BBC for now.
        # Deduplicate across sources (in case there are any dupes within BBC)
        all_fixtures = _deduplicate_fixtures(all_fixtures)
        logger.info(f"Phase 1 complete: {len(all_fixtures)} unique fixtures extracted.")

        if not all_fixtures:
            logger.error("No fixtures extracted from any source. Aborting.")
            return

        # ── Phase 2: Enrich with BBC match stats ───────────────────────
        enriched = enrich_with_stats(all_fixtures, today_str)

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

        # Pre-load today's existing predictions for fast duplicate checks
        from sqlalchemy import cast, Date
        today_date = datetime.strptime(today_str, "%Y-%m-%d").date()
        existing_preds = db.query(Prediction).filter(
            cast(Prediction.date, Date) == today_date
        ).all()

        # Build a set of normalized match keys already in the DB
        existing_keys = set()
        for ep in existing_preds:
            existing_keys.add(_match_key(ep.home_team, ep.away_team))

        # Also track keys we save in THIS batch to prevent within-batch duplicates
        batch_keys = set()

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

                # Check for duplicate (DB + current batch)
                match = _match_key(home, away)

                if match in existing_keys or match in batch_keys:
                    duplicate_count += 1
                    logger.debug(f"Skipping duplicate: {home} vs {away}")
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
                batch_keys.add(match)
                saved_count += 1
            except Exception as e:
                logger.warning(f"Skipping invalid prediction data: {e}")
                continue

        db.commit()
        logger.info(
            f"Engine complete. Saved {saved_count} new predictions. "
            f"Skipped {duplicate_count} duplicates."
        )
        
        # Invalidate cache so users see new predictions immediately
        invalidate_cache()

    except Exception as e:
        logger.error(f"Engine failure: {str(e)}")
        db.rollback()
    finally:
        db.close()
