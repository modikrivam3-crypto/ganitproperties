import re
import time
import requests
from bs4 import BeautifulSoup
from .base import BaseScraper
from .contact_extractor import extract_phone, extract_contact_name

BASE = "https://housing.com"

SEARCH_URLS = [
    (f"{BASE}/in/buy/patiala/patiala", "Buy"),
    (f"{BASE}/in/rent/patiala/patiala", "Rent"),
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html",
    "Accept-Language": "en-IN",
    "Referer": "https://housing.com",
}


class HousingScraper(BaseScraper):
    """
    Attempts to scrape Housing.com for Patiala listings.
    Housing.com blocks server-side requests (HTTP 406).
    Reports status correctly. Extracts publicly visible contact info when possible.
    """

    def fetch(self) -> list[dict]:
        session = requests.Session()
        session.headers.update(HEADERS)
        results = []
        blocked = 0

        for url, listing_type in SEARCH_URLS:
            try:
                resp = session.get(url, timeout=18)
                if resp.status_code in (403, 406):
                    blocked += 1
                    print(f"[Housing.com] {listing_type}: HTTP {resp.status_code} (blocked)")
                    continue
                if resp.status_code != 200:
                    print(f"[Housing.com] {listing_type}: HTTP {resp.status_code}")
                    continue
            except Exception as e:
                print(f"[Housing.com] {listing_type}: {e}")
                continue

            import json
            import re as _re
            soup = BeautifulSoup(resp.text, "lxml")

            # Extract phone from page level
            page_phone = extract_phone(resp.text)
            page_contact = extract_contact_name(resp.text)

            m = _re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', resp.text, _re.S)
            if m:
                try:
                    data = json.loads(m.group(1))
                    listings_data = self._find_listings(data)
                    for item in listings_data:
                        entry = self._parse(item, listing_type, page_phone, page_contact)
                        if entry:
                            results.append(entry)
                except Exception as e:
                    print(f"[Housing.com] JSON parse error: {e}")

            time.sleep(1.5)

        if blocked == len(SEARCH_URLS):
            self.blocked = True
            print("[Housing.com] All URLs blocked (406 Not Acceptable)")
        print(f"[Housing.com] Total: {len(results)}")
        return results

    def _find_listings(self, obj, depth=0):
        if depth > 8: return []
        found = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, list) and len(v) > 2 and isinstance(v[0], dict):
                    if any(key in v[0] for key in ["id","price","title","name","slug"]):
                        found.extend(v)
                else:
                    found.extend(self._find_listings(v, depth+1))
        elif isinstance(obj, list):
            for i in obj:
                found.extend(self._find_listings(i, depth+1))
        return found

    def _parse(self, item: dict, listing_type: str, page_phone="", page_contact="") -> dict | None:
        title = item.get("name") or item.get("title") or item.get("displayName") or ""
        if not title: return None
        price = str(item.get("price") or item.get("expectedPrice") or "")
        area  = str(item.get("area") or item.get("carpetArea") or item.get("builtupArea") or "")
        loc   = item.get("localityName") or item.get("locality") or "Patiala"
        slug  = item.get("slug") or item.get("id") or ""
        url   = f"{BASE}/in/property/{slug}" if slug else BASE

        # Try to extract phone from item fields
        item_text = str(item)
        phone = extract_phone(item_text) or page_phone
        contact_name = extract_contact_name(item_text) or page_contact

        return {
            "title":         title,
            "price":         price,
            "location":      loc,
            "area":          area,
            "property_type": self._detect_type(title),
            "listing_type":  listing_type,
            "summary":       f"{listing_type} | {price} | {loc}".strip(" |"),
            "source_url":    url,
            "source_name":   "Housing.com",
            "phone":         phone,
            "contact_name":  contact_name,
        }

    def _detect_type(self, text: str) -> str:
        t = text.lower()
        for kw, label in [
            ("villa","Villa"),("penthouse","Penthouse"),("studio","Flat"),
            ("flat","Flat"),("apartment","Flat"),("house","House"),
            ("plot","Plot"),("land","Plot"),("shop","Shop"),("bhk","Flat"),
        ]:
            if kw in t: return label
        return "Property"