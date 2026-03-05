import requests
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO)
headers = {"User-Agent": "Mozilla/5.0"}
url = "https://www.bbc.com/sport/football/scores-fixtures/2026-03-05"

res = requests.get(url, headers=headers)
soup = BeautifulSoup(res.content, "html.parser")

links = soup.select('a[class*="OnwardJourneyLink"]')
match_urls = []
for a in links:
    href = a.get('href')
    if href and ('/live/' in href or '/football/' in href):
        full_url = f"https://www.bbc.com{href}" if href.startswith('/') else href
        match_urls.append((a.get_text(strip=True), full_url))

print(f"Parsed {len(match_urls)} actual match links.")
for name, link in match_urls[:5]:
    print(f" - {name}: {link}")

if match_urls:
    print(f"\n--- Testing fetch for {match_urls[0][1]} ---")
    m_res = requests.get(match_urls[0][1], headers=headers)
    m_soup = BeautifulSoup(m_res.content, "html.parser")
    
    stats_text = []
    h2h = m_soup.find(lambda t: t.name in ["h2", "h3", "div"] and "Head-to-head" in t.text)
    if h2h and h2h.parent:
        stats_text.append(f"H2H found:\n{h2h.parent.get_text(separator=' ', strip=True)[:300]}")
    else:
        print("NO H2H found exactly. Trying broader search...")
    
    mf = m_soup.find(lambda t: t.name in ["h2", "h3", "div"] and "Match facts" in t.text)
    if mf and mf.parent:
        stats_text.append(f"Match facts found:\n{mf.parent.get_text(separator=' ', strip=True)[:300]}")
    else:
        print("NO Match facts found exactly.")

    if stats_text:
        print("\n".join(stats_text))
    else:
        main = m_soup.find('main') or m_soup.find('article')
        if main:
            print(f"Fallback Main content: {main.get_text(separator=' ', strip=True)[:500]}")
        else:
            print("No main content either. Just dumping first 500 chars of body.")
            print(m_soup.body.get_text(separator=' ', strip=True)[:500])
