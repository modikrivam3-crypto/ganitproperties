import re
import time
import requests
from bs4 import BeautifulSoup
from .base import BaseScraper
from .contact_extractor import extract_phone, extract_contact_name

BASE = "https://www.99acres.com"

SEARCH_URLS = [
    (f"{BASE}/search/property/buy/patiala?preference=S&city=100", "Buy"),
    (f"{BASE}/search/property/rent/patiala?preference=S&city=100", "Rent"),
    (f"{BASE}/commercial-property-for-sale-in-patiala-ffid", "Buy"),
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.0 Mobile/15E148 Safari/604.1"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer": "https://www.google.com/",
}


class Acres99Scraper(BaseScraper):
    """
    Attempts to scrape 99acres for Patiala listings.
    99acres uses Cloudflare protection — may be blocked (403).
    Extracts publicly visible contact information when available.
    """

    def fetch(self) -> list[dict]:
        session = requests.Session()
        session.headers.update(HEADERS)
        results = []
        blocked = 0

        for url, listing_type in SEARCH_URLS:
            try:
                resp = session.get(url, timeout=18)
                if resp.status_code == 403:
                    blocked += 1
                    print(f"[99acres] {listing_type}: HTTP 403 (Cloudflare blocked)")
                    continue
                if resp.status_code != 200:
                    print(f"[99acres] {listing_type}: HTTP {resp.status_code}")
                    continue
            except Exception as e:
                print(f"[99acres] {listing_type}: {e}")
                continue

            soup = BeautifulSoup(resp.text, "lxml")

            # Extract phone from page HTML
            phone = extract_phone(resp.text)
            contact_name = extract_contact_name(resp.text)

            # Try JSON-LD ItemList
            import json
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    d = json.loads(script.string or "")
                    if isinstance(d, list): d = d[0]
                    if isinstance(d, dict) and d.get("@type") == "ItemList":
                        for item in d.get("itemListElement", []):
                            name = item.get("name", "")
                            url2 = item.get("url", "")
                            if name and url2:
                                # Try to get phone from URL if it's a detail page
                                item_phone = phone  # Use page-level phone
                                item_contact = contact_name
                                results.append({
                                    "title":         name,
                                    "price":         "",
                                    "location":      "Patiala",
                                    "area":          self._area_from_url(url2),
                                    "property_type": self._detect_type(name),
                                    "listing_type":  listing_type,
                                    "summary":       f"{listing_type} | {self._detect_type(name)} | Patiala",
                                    "source_url":    url2,
                                    "source_name":   "99acres",
                                    "phone":         item_phone,
                                    "contact_name":  item_contact,
                                })
                except Exception:
                    continue

            # Try HTML cards
            for sel in ["[class*='Tuple']", "[class*='tuple']", "article[class*='srp']"]:
                cards = soup.select(sel)
                if len(cards) > 1:
                    for card in cards:
                        txt = card.get_text(" ", strip=True)
                        if len(txt) < 30:
                            continue
                        link = card.select_one("a[href*='99acres']") or card.select_one("a[href]")
                        href = link.get("href", "") if link else ""
                        if href.startswith("/"): href = BASE + href
                        if not href: continue
                        title_el = card.select_one("h2, h3, [class*='title']")
                        title = title_el.get_text(strip=True)[:120] if title_el else txt[:80]
                        price_m = re.search(r"₹[\d,\.]+\s*(?:Lac|Cr|Lakh|lakh|cr)?", txt)
                        area_m  = re.search(r"[\d,]+\s*(?:sqft|sq\.?\s*ft|sq\s*yd|marla|kanal)", txt, re.I)
                        # Extract phone from card text
                        card_phone = extract_phone(txt)
                        card_contact = extract_contact_name(txt)
                        results.append({
                            "title":         title,
                            "price":         price_m.group(0) if price_m else "",
                            "location":      "Patiala",
                            "area":          area_m.group(0) if area_m else "",
                            "property_type": self._detect_type(title),
                            "listing_type":  listing_type,
                            "summary":       f"{listing_type} | Patiala",
                            "source_url":    href,
                            "source_name":   "99acres",
                            "phone":         card_phone or phone,
                            "contact_name":  card_contact or contact_name,
                        })
                    break

            time.sleep(1.5)

        if blocked == len(SEARCH_URLS):
            self.blocked = True
            print("[99acres] All URLs blocked by Cloudflare (403)")
        print(f"[99acres] Total: {len(results)}")
        return results

    def _area_from_url(self, url: str) -> str:
        m = re.search(r"(\d+)-Sq-?(?:ft|yrd|yard|m)", url, re.I)
        return m.group(0).replace("-", " ") if m else ""

    def _detect_type(self, text: str) -> str:
        t = text.lower()
        for kw, label in [
            ("villa","Villa"),("penthouse","Penthouse"),("studio","Flat"),
            ("flat","Flat"),("apartment","Flat"),("house","House"),
            ("plot","Plot"),("land","Plot"),("shop","Shop"),
            ("office","Office"),("warehouse","Warehouse"),("commercial","Commercial"),
            ("bhk","Flat"),
        ]:
            if kw in t: return label
        return "Property"