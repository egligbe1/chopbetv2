import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime, UTC

logger = logging.getLogger(__name__)

class SearchUtils:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def get_bbc_fixtures(self, date_str: str) -> str:
        """
        Fetches the BBC Sport football fixtures page for a given date and
        returns all text content for downstream extraction.
        """
        url = f"https://www.bbc.com/sport/football/scores-fixtures/{date_str}"
        logger.info(f"Scraping BBC Sport fixtures from: {url}")
        
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # The most robust way without dealing with complex React hydration
            # is to simply grab all text and let Gemini extract the actual matches.
            text_content = soup.get_text(separator=' ', strip=True)
            logger.info(f"Successfully scraped {len(text_content)} characters from BBC.")
            
            return text_content
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch BBC fixtures: {e}")
            return ""

    def get_goal_fixtures(self, date_str: str) -> str:
        """
        Fetches the Goal.com live scores page for a given date as a fallback.
        """
        url = f"https://www.goal.com/en-gh/live-scores/{date_str}"
        logger.info(f"Scraping Goal.com fixtures from: {url}")
        
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            text_content = soup.get_text(separator=' ', strip=True)
            logger.info(f"Successfully scraped {len(text_content)} characters from Goal.com.")
            
            return text_content
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch Goal.com fixtures: {e}")
            return ""

search_utils = SearchUtils()
