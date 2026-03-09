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
            
            # Extract the raw JSON state which has all the fixtures
            script_data = ""
            for s in soup.find_all('script'):
                if s.string and 'window.__INITIAL_DATA__' in s.string:
                    script_data = s.string
                    break
                    
            text_content = soup.get_text(separator=' ', strip=True)
            
            if script_data:
                logger.info(f"Found BBC INITIAL_DATA script with {len(script_data)} chars.")
                # We append the script data to the text content so Gemini can parse it
                return text_content + "\n\n=== RAW JSON STATE ===\n" + script_data
            
            logger.info(f"Successfully scraped {len(text_content)} characters from BBC (no script state found).")
            return text_content
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch BBC fixtures: {e}")
            return ""

    def get_bbc_match_links(self, date_str: str) -> list[dict]:
        """
        Finds all match links on the BBC fixtures page for a specific date.
        Returns a list of dicts: {'teams': 'Home vs Away', 'url': '...'}
        """
        url = f"https://www.bbc.com/sport/football/scores-fixtures/{date_str}"
        links = []
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            
            # The selector found by the browser subagent
            anchor_tags = soup.select('a[class*="OnwardJourneyLink"]')
            
            for a in anchor_tags:
                href = a.get('href')
                if href and '/sport/football/live/' in href:
                    full_url = f"https://www.bbc.com{href}" if href.startswith('/') else href
                    # Extract team names from the text if possible
                    teams = a.get_text(strip=True)
                    links.append({"teams": teams, "url": full_url})
            
            logger.info(f"Found {len(links)} match links on BBC fixtures page.")
            return links
        except Exception as e:
            logger.error(f"Error finding BBC match links: {e}")
            return []

    def get_match_preview_stats(self, match_url: str) -> str:
        """
        Scrapes a BBC match preview/live page for 'Head-to-head' and 'Match facts'.
        """
        try:
            response = requests.get(match_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Look for Head-to-head and Match facts sections
            # BBC pages often have these in <div> or <section> tags with specific text
            stats_text = []
            
            # Look for H2H data
            h2h_section = soup.find(lambda tag: tag.name in ["h2", "h3", "div"] and "Head-to-head" in tag.text)
            if h2h_section:
                # Get the sibling content or parent content
                stats_text.append(f"--- Head-to-head ---\n{h2h_section.parent.get_text(separator=' ', strip=True)}")
            
            # Look for Match facts
            match_facts = soup.find(lambda tag: tag.name in ["h2", "h3", "div"] and "Match facts" in tag.text)
            if match_facts:
                 stats_text.append(f"--- Match facts ---\n{match_facts.parent.get_text(separator=' ', strip=True)}")
            
            # Fallback: grab all text if specific sections not found
            if not stats_text:
                logger.info(f"Specific sections not found for {match_url}, grabbing main content.")
                # Try to find the main article or live text area
                main_content = soup.find('main') or soup.find('article')
                if main_content:
                    return main_content.get_text(separator=' ', strip=True)[:10000]
                return soup.get_text(separator=' ', strip=True)[:5000]

            return "\n\n".join(stats_text)
            
        except Exception as e:
            logger.error(f"Error scraping match page {match_url}: {e}")
            return ""

    def get_goal_fixtures(self, date_str: str) -> str:
        """
        Fetches the Goal.com live scores page for a given date as a fallback.
        """
        url = f"https://www.goal.com/en/live-scores/{date_str}"
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

    def get_espn_fixtures(self, date_str: str) -> str:
        """
        Fetches the ESPN football fixtures/scoreboard page for a given date.
        ESPN uses YYYYMMDD format in their URLs.
        """
        # Convert 2026-03-04 to 20260304
        espn_date = date_str.replace("-", "")
        url = f"https://www.espn.com/soccer/scoreboard/_/date/{espn_date}"
        logger.info(f"Scraping ESPN fixtures from: {url}")
        
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            text_content = soup.get_text(separator=' ', strip=True)
            logger.info(f"Successfully scraped {len(text_content)} characters from ESPN.")
            
            return text_content
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch ESPN fixtures: {e}")
            return ""

search_utils = SearchUtils()
