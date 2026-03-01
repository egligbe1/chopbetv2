import os
import logging
from tavily import TavilyClient
from duckduckgo_search import DDGS
from datetime import datetime, UTC

logger = logging.getLogger(__name__)

class SearchUtils:
    def __init__(self):
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        self.tavily_client = TavilyClient(api_key=self.tavily_api_key) if self.tavily_api_key else None
        self.ddgs = DDGS()

    def search_tavily(self, query: str, max_results: int = 5):
        """Primary search using Tavily."""
        if not self.tavily_client:
            logger.warning("Tavily API Key not found. Falling back to DuckDuckGo.")
            return self.search_ddg(query, max_results)
        
        try:
            logger.info(f"Searching Tavily for: {query}")
            response = self.tavily_client.search(query=query, search_depth="advanced", max_results=max_results)
            return [
                {
                    "title": result.get("title"),
                    "content": result.get("content"),
                    "url": result.get("url")
                }
                for result in response.get("results", [])
            ]
        except Exception as e:
            logger.error(f"Tavily search failed: {str(e)}. Falling back to DuckDuckGo.")
            return self.search_ddg(query, max_results)

    def search_ddg(self, query: str, max_results: int = 5):
        """Fallback search using DuckDuckGo."""
        try:
            logger.info(f"Searching DuckDuckGo for: {query}")
            # Use DDGS with modern settings
            with DDGS() as ddgs:
                results = ddgs.text(query, max_results=max_results, region="wt-wt", safesearch="off", timelimit="y")
                return [
                    {
                        "title": r.get("title"),
                        "content": r.get("body"),
                        "url": r.get("href")
                    }
                    for r in results
                ]
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {str(e)}")
            return []

    def get_fixtures_context(self, date_str: str):
        """Get today's fixtures and major news."""
        query = f"football fixtures {date_str} premier league la liga bundesliga serie a ligue 1 bbc sport espn"
        return self.search_tavily(query, max_results=8)

    def get_match_context(self, home_team: str, away_team: str, date_str: str):
        """Get specific match details: form, injuries, team news."""
        query = f"{home_team} vs {away_team} match preview team news injuries form {date_str} sky sports"
        return self.search_tavily(query, max_results=3)

    def get_nba_fixtures_context(self, date_str: str):
        """Get today's NBA fixtures and major news."""
        query = f"NBA schedule matches {"today" if date_str == datetime.now(UTC).strftime('%Y-%m-%d') else date_str} espn cbs sports"
        return self.search_tavily(query, max_results=6)

    def get_nba_match_context(self, home_team: str, away_team: str, date_str: str):
        """Get specific NBA match details: injuries, starting lineups, form."""
        query = f"{home_team} vs {away_team} NBA match preview injury report starting lineups {date_str} action network covers"
        return self.search_tavily(query, max_results=3)

search_utils = SearchUtils()
