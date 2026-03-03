"""
Stats Scraper — Fetches team performance data from Understat.com
(No Cloudflare blocking, high-quality xG and xGA stats for major European leagues)

Usage:
    scraper = StatsScraper()
    stats = scraper.get_match_stats("Arsenal", "Chelsea")
"""

import re
import json
import logging
from typing import Optional

import requests
from bs4 import BeautifulSoup
from fuzzywuzzy import process  # We'll use this (or simple difflib) for team name matching
import difflib

logger = logging.getLogger(__name__)

# Understat leagues to pull from
LEAGUES = ["EPL", "La_liga", "Bundesliga", "Serie_A", "Ligue_1", "RFPL"]
YEAR = "2024"  # Current European calendar season

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


class StatsScraper:
    """Scrapes Understat.com for robust xG and season form data."""

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": USER_AGENT})
        self._team_stats_cache = {}
        self._cache_populated = False

    def _populate_cache(self):
        """Fetch and parse the league table data for all 6 major leagues at once."""
        if self._cache_populated:
            return

        logger.info("Initializing Understat data cache for 6 major leagues...")
        for league in LEAGUES:
            url = f"https://understat.com/league/{league}/{YEAR}"
            try:
                resp = self._session.get(url, timeout=10)
                if resp.status_code != 200:
                    logger.warning(f"Failed to load {league} from Understat (HTTP {resp.status_code})")
                    continue
                
                # The data is stored in a JSON string assigned to the `teamsData` JS variable
                soup = BeautifulSoup(resp.content, "html.parser")
                scripts = soup.find_all("script")
                teams_data_raw = None
                
                for script in scripts:
                    if script.string and "var teamsData" in script.string:
                        # Extract the JSON hex string
                        match = re.search(r"var teamsData\s*=\s*JSON\.parse\('([^']+)'\)", script.string)
                        if match:
                            # It's usually a standard hex-encoded string in JS (\x22). 
                            # We can just evaluate it or decode it.
                            # Understat encodes it like \x22 => "
                            encoded = match.group(1)
                            decoded = encoded.encode('utf-8').decode('unicode_escape')
                            teams_data_raw = json.loads(decoded)
                            break
                
                if not teams_data_raw:
                    continue

                # Process the data into our clean cache
                for team_id, team_info in teams_data_raw.items():
                    name = team_info.get("title", "")
                    
                    # Compute season totals by aggregating match history
                    history = team_info.get("history", [])
                    if not history:
                        continue
                    
                    # Accumulators
                    w = d = l = pts = matches = 0
                    gf = ga = 0
                    xg = xga = 0.0
                    
                    recent_form = []
                    
                    for match in history:
                        matches += 1
                        pts += match.get("pts", 0)
                        w += match.get("wins", 0)
                        d += match.get("draws", 0)
                        l += match.get("loses", 0)
                        gf += match.get("scored", 0)
                        ga += match.get("missed", 0)
                        xg += match.get("xG", 0.0)
                        xga += match.get("xGA", 0.0)
                        
                        # Save for recent form
                        recent_form.append({
                            "result": match.get("result"), # W, D, L
                            "score": f"{match.get('scored')} - {match.get('missed')}",
                            "xg": round(match.get("xG", 0.0), 2),
                            "xga": round(match.get("xGA", 0.0), 2),
                            "date": match.get("date")
                        })
                    
                    # Sort recent form by date (newest first) and keep last 5
                    recent_form.sort(key=lambda x: x["date"], reverse=True)
                    
                    self._team_stats_cache[name] = {
                        "league": league,
                        "matches_played": matches,
                        "points": pts,
                        "wins": w,
                        "draws": d,
                        "losses": l,
                        "goals_scored": gf,
                        "goals_conceded": ga,
                        "xg_season": round(xg, 2),
                        "xga_season": round(xga, 2),
                        "xg_per_90": round(xg / matches, 2) if matches else 0,
                        "xga_per_90": round(xga / matches, 2) if matches else 0,
                        "last_5": recent_form[:5]
                    }

            except Exception as e:
                logger.error(f"Error parsing Understat data for {league}: {e}")
                
        self._cache_populated = True
        logger.info(f"Understat cache populated with {len(self._team_stats_cache)} teams.")

    def _find_team(self, query: str) -> Optional[dict]:
        """Fuzzy match a team name against our populated cache."""
        self._populate_cache()
        if not self._team_stats_cache:
            return None

        # Clean query
        q = query.lower().replace("fc", "").strip()
        
        # 1. Exact or simple substring match
        for name, stats in self._team_stats_cache.items():
            n = name.lower()
            if q == n or q in n or n in q:
                return {"name": name, "stats": stats}
                
        # 2. Fuzzy match
        team_names = list(self._team_stats_cache.keys())
        matches = difflib.get_close_matches(query, team_names, n=1, cutoff=0.6)
        if matches:
            best = matches[0]
            return {"name": best, "stats": self._team_stats_cache[best]}
            
        return None

    def get_match_stats(self, home_team: str, away_team: str) -> Optional[dict]:
        """Return cached Understat data for both teams."""
        home_data = self._find_team(home_team)
        away_data = self._find_team(away_team)
        
        # If neither is found in the top 6 leagues, just return None
        if not home_data and not away_data:
            return None
            
        return {
            "home": {
                "name": home_data["name"] if home_data else home_team,
                "season_stats": home_data["stats"] if home_data else {},
                "last_5": home_data["stats"]["last_5"] if home_data else []
            },
            "away": {
                "name": away_data["name"] if away_data else away_team,
                "season_stats": away_data["stats"] if away_data else {},
                "last_5": away_data["stats"]["last_5"] if away_data else []
            }
        }

# Module-level singleton
stats_scraper = StatsScraper()
