"""
football-data.org (v4) client — free-forever structured stats for the
prediction engine.

Provides real recency data for the top competitions the engine prioritizes:
  - each team's last-5 form (W/D/L) + table position, points, goals for/against
    (from the competition standings — one call covers every team in the league)
  - head-to-head history for the specific fixture

Free tier: 10 requests/minute, no cost, no card. Set FOOTBALL_DATA_API_KEY.
When the key is absent the client is disabled and every method degrades to
empty results so the engine transparently falls back to its BBC scrape.
"""

import os
import re
import time
import logging
import unicodedata

import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

API_BASE = "https://api.football-data.org/v4"
API_KEY = os.getenv("FOOTBALL_DATA_API_KEY", "").strip()

# Stay comfortably under the free tier's 10 requests/minute.
_MIN_INTERVAL_S = 6.5

# Common club-name suffixes/prefixes to strip so BBC names line up with
# football-data's official names ("Manchester United FC" -> "manchester united").
_SUFFIXES = re.compile(
    r"\b(fc|cf|afc|sc|ac|as|ss|ssd|calcio|club|cd|ud|rcd|sd|bk|if|fk)\b",
    re.IGNORECASE,
)

_ALIASES = {
    "man utd": "manchester united", "man united": "manchester united",
    "man city": "manchester city",
    "spurs": "tottenham hotspur", "tottenham": "tottenham hotspur",
    "wolves": "wolverhampton wanderers",
    "nottm forest": "nottingham forest", "nott m forest": "nottingham forest",
    "brighton": "brighton hove albion", "brighton and hove albion": "brighton hove albion",
    "west ham": "west ham united", "newcastle": "newcastle united",
    "leicester": "leicester city", "leeds": "leeds united",
    "psg": "paris saint germain", "paris sg": "paris saint germain",
    "inter": "inter milan", "internazionale": "inter milan",
    "atletico madrid": "atletico de madrid", "atleti": "atletico de madrid",
    "athletic bilbao": "athletic club", "athletic": "athletic club",
    "bayern": "bayern munich", "fc bayern": "bayern munich",
    "bayern munchen": "bayern munich",
    "dortmund": "borussia dortmund", "bvb": "borussia dortmund",
    "gladbach": "borussia monchengladbach",
    "monchengladbach": "borussia monchengladbach",
    "leipzig": "rb leipzig", "rasenballsport leipzig": "rb leipzig",
    "sporting": "sporting cp", "sporting lisbon": "sporting cp",
    "koln": "fc koln", "cologne": "fc koln",
}


def _strip_accents(text: str) -> str:
    """Transliterate accented characters (München -> Munchen, Atlético -> Atletico)."""
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch)
    )


def normalize_team(name: str) -> str:
    """Normalize a club name for cross-source matching."""
    if not name:
        return ""
    n = _strip_accents(name).lower().strip()
    n = n.replace("&", " and ").replace(".", " ").replace("-", " ")
    n = _SUFFIXES.sub(" ", n)
    n = re.sub(r"[^a-z0-9 ]", " ", n)
    # Drop a leading league-number prefix ("1. FC Köln" -> "köln", "1899 Hoffenheim" -> "hoffenheim").
    n = re.sub(r"^\s*\d+\s+", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    return _ALIASES.get(n, n)


class FootballDataClient:
    def __init__(self, api_key: str = API_KEY):
        self.api_key = api_key
        self.enabled = bool(api_key)
        self._last_call = 0.0
        self._standings_cache: dict = {}
        if not self.enabled:
            logger.info("FOOTBALL_DATA_API_KEY not set — football-data enrichment disabled.")

    # ── low-level request with throttle + 429 backoff ────────────────────────
    def _get(self, path: str, params: dict | None = None) -> dict | None:
        if not self.enabled:
            return None
        for attempt in range(3):
            # Simple client-side throttle to respect 10 req/min.
            wait = _MIN_INTERVAL_S - (time.time() - self._last_call)
            if wait > 0:
                time.sleep(wait)
            try:
                resp = requests.get(
                    f"{API_BASE}{path}",
                    headers={"X-Auth-Token": self.api_key},
                    params=params or {},
                    timeout=20,
                )
                self._last_call = time.time()
                if resp.status_code == 429:
                    logger.warning("football-data 429 rate limited; backing off 60s.")
                    time.sleep(60)
                    continue
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as e:
                logger.warning(f"football-data request failed ({path}): {e}")
                return None
        return None

    # ── fixtures for the day, indexed by normalized (home, away) ─────────────
    def get_todays_match_index(self, date_str: str) -> dict:
        """Return {(norm_home, norm_away): match} for all covered matches on date_str."""
        if not self.enabled:
            return {}
        data = self._get("/matches", {"dateFrom": date_str, "dateTo": date_str})
        if not data or "matches" not in data:
            return {}
        index = {}
        for m in data["matches"]:
            home = m.get("homeTeam", {}).get("name", "")
            away = m.get("awayTeam", {}).get("name", "")
            if home and away:
                index[(normalize_team(home), normalize_team(away))] = m
        logger.info(f"football-data: {len(index)} covered matches on {date_str}.")
        return index

    # ── standings: one call per competition gives form + position for all ────
    def get_standings_map(self, competition_code: str) -> dict:
        """
        Return {norm_team_name: {"TOTAL": row, "HOME": row, "AWAY": row}} for a
        competition. The single standings call already includes the home/away
        split tables — capturing them costs no extra requests.
        """
        if not self.enabled or not competition_code:
            return {}
        if competition_code in self._standings_cache:
            return self._standings_cache[competition_code]

        data = self._get(f"/competitions/{competition_code}/standings")
        table_map: dict = {}
        if data and "standings" in data:
            for block in data["standings"]:
                block_type = block.get("type")
                if block_type not in ("TOTAL", "HOME", "AWAY"):
                    continue
                for row in block.get("table", []):
                    name = row.get("team", {}).get("name", "")
                    if name:
                        table_map.setdefault(normalize_team(name), {})[block_type] = row
        self._standings_cache[competition_code] = table_map
        return table_map

    # ── head-to-head for a specific fixture ──────────────────────────────────
    def get_h2h_summary(self, match_id: int) -> dict | None:
        if not self.enabled or not match_id:
            return None
        data = self._get(f"/matches/{match_id}/head2head", {"limit": 10})
        if not data:
            return None
        agg = data.get("aggregates", {})
        return {
            "num_matches": agg.get("numberOfMatches"),
            "home_wins": agg.get("homeTeam", {}).get("wins"),
            "away_wins": agg.get("awayTeam", {}).get("wins"),
            "draws": agg.get("homeTeam", {}).get("draws"),
        }

    # ── build a compact, structured context string for one fixture ───────────
    def build_fixture_context(self, home: str, away: str, match_index: dict) -> str | None:
        """Return a human/LLM-readable stats block for a fixture, or None if not covered."""
        if not self.enabled:
            return None

        match = match_index.get((normalize_team(home), normalize_team(away)))
        if not match:
            return None

        comp = match.get("competition", {})
        comp_code = comp.get("code", "")
        standings = self.get_standings_map(comp_code)

        home_entry = standings.get(normalize_team(home)) or standings.get(normalize_team(match.get("homeTeam", {}).get("name", "")))
        away_entry = standings.get(normalize_team(away)) or standings.get(normalize_team(match.get("awayTeam", {}).get("name", "")))

        lines = [f"Competition: {comp.get('name', comp_code)}"]

        def _overall(label: str, row: dict | None) -> str:
            if not row:
                return f"{label}: no standings data."
            return (
                f"{label}: P{row.get('position','?')} overall, "
                f"{row.get('points','?')} pts / {row.get('playedGames','?')} games "
                f"(W{row.get('won','?')} D{row.get('draw','?')} L{row.get('lost','?')}), "
                f"GF {row.get('goalsFor','?')} GA {row.get('goalsAgainst','?')}, "
                f"form: {row.get('form') or 'n/a'}"
            )

        def _split(label: str, row: dict | None) -> str | None:
            if not row:
                return None
            gp = row.get("playedGames", "?")
            return (
                f"{label}: W{row.get('won','?')} D{row.get('draw','?')} L{row.get('lost','?')} "
                f"in {gp} games, GF {row.get('goalsFor','?')} GA {row.get('goalsAgainst','?')}"
            )

        # Home team: overall + its HOME-only record. Away team: overall + AWAY-only.
        lines.append(_overall(f"{home} (home side)", (home_entry or {}).get("TOTAL")))
        home_split = _split(f"  -> {home} at HOME", (home_entry or {}).get("HOME"))
        if home_split:
            lines.append(home_split)
        lines.append(_overall(f"{away} (away side)", (away_entry or {}).get("TOTAL")))
        away_split = _split(f"  -> {away} AWAY", (away_entry or {}).get("AWAY"))
        if away_split:
            lines.append(away_split)

        h2h = self.get_h2h_summary(match.get("id"))
        if h2h and h2h.get("num_matches"):
            lines.append(
                f"Head-to-head (last {h2h['num_matches']}): "
                f"{home} wins {h2h.get('home_wins','?')}, "
                f"{away} wins {h2h.get('away_wins','?')}, "
                f"draws {h2h.get('draws','?')}."
            )

        # Only worth returning if we actually got some standings signal.
        has_signal = (home_entry and home_entry.get("TOTAL")) or (away_entry and away_entry.get("TOTAL")) or (h2h and h2h.get("num_matches"))
        if not has_signal:
            return None
        return "\n".join(lines)


# Module-level singleton, mirroring search_utils.
football_data = FootballDataClient()
