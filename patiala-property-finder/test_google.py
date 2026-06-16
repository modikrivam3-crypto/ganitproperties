"""Test what Google search actually returns."""
import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
}

MOBILE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.0 Mobile/15E148 Safari/604.1"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
}

url = "https://www.google.com/search?q=patiala+punjab+property+for+sale+site%3Amagicbricks.com&num=20&hl=en&gl=in"

for hdrs, label in [(HEADERS, "Desktop"), (MOBILE_HEADERS, "Mobile")]:
    s = requests.Session()
    s.headers.update(hdrs)
    try:
        r = s.get(url, timeout=15)
        print(f"\n=== {label}: HTTP {r.status_code} | {len(r.text)} bytes ===")
        soup = BeautifulSoup(r.text, "lxml")
        print(f"Title: {soup.title.string.strip() if soup.title else 'NONE'}")
        
        # Save HTML for inspection
        with open(f"google_{label.lower()}.html", "w", encoding="utf-8") as f:
            f.write(r.text)
        print(f"Saved to google_{label.lower()}.html")
        
        # Look for links
        links = soup.find_all("a", href=True)
        print(f"Total links: {len(links)}")
        
        property_links = []
        for a in links:
            h = a.get("href", "")
            if "patiala" in h.lower() and any(d in h.lower() for d in ["magicbricks","99acres","housing","commonfloor","property","realestate"]):
                property_links.append((h, a.get_text(strip=True)[:80]))
        
        print(f"Property links with 'patiala': {len(property_links)}")
        for href, text in property_links[:5]:
            print(f"  {href[:120]}")
            print(f"  -> {text}")
        
        # Check for any Google result-like divs
        for sel in ["div.g", "div[data-hveid]", "div#search", "div[jsname]", "div[data-sokoban]"]:
            els = soup.select(sel)
            if els:
                print(f"  Selector '{sel}': {len(els)} elements")
                if els:
                    sample = els[0].get_text(" ", strip=True)[:100]
                    print(f"    Sample: {sample}")
        
        # Check for h3s (usually result titles)
        h3s = soup.find_all("h3")
        print(f"h3s: {len(h3s)}")
        for h3 in h3s[:5]:
            print(f"  h3: {h3.get_text(strip=True)[:80]}")
        
    except Exception as e:
        print(f"{label}: ERROR {e}")