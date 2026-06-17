"""
Google Custom Search API scraper for Patiala properties.
Uses the official Google Custom Search JSON API to find property listings.
Requires GOOGLE_API_KEY and GOOGLE_CX environment variables.
"""
import os
import re
import time
import requests
from .base import BaseScraper
from .contact_extractor import extract_phone, extract_contact_name

PROP_TYPE_MAP = [
    ("agriculture", "Agricultural"), ("agricultural", "Agricultural"), ("farm", "Agricultural"),
    ("farmland", "Agricultural"), ("farm land", "Agricultural"), ("khet", "Agricultural"),
    ("industrial", "Industrial"), ("factory", "Factory"),
    ("warehouse", "Warehouse"), ("godown", "Warehouse"),
    ("commercial", "Commercial"), ("showroom", "Showroom"),
    ("office", "Office"),
    ("shop", "Shop"),
    ("plot", "Plot"), ("land", "Plot"),
    ("house", "House"), ("independent house", "House"), ("builder floor", "House"),
    ("villa", "Villa"), ("bunglow", "Villa"), ("bungalow", "Villa"),
    ("apartment", "Flat"), ("flat", "Flat"), ("bhk", "Flat"), ("studio", "Flat"),
    ("penthouse", "Penthouse"),
    ("hotel", "Hotel"), ("resort", "Hotel"),
]


def detect_prop_type(text: str) -> str:
    t = text.lower()
    for kw, label in PROP_TYPE_MAP:
        if kw in t:
            return label
    return "Property"


def get_source_name(url: str) -> str:
    if not url:
        return "Google API"
    url_lower = url.lower()
    if "magicbricks" in url_lower:
        return "MagicBricks"
    elif "99acres" in url_lower or "99ac" in url_lower:
        return "99acres"
    elif "housing" in url_lower:
        return "Housing.com"
    elif "commonfloor" in url_lower:
        return "CommonFloor"
    elif "nobroker" in url_lower:
        return "NoBroker"
    else:
        return "Google API"


def extract_price(text: str) -> str:
    m = re.search(r"(?:Rs\.?|\u20b9)\s*([\d,]+(?:\s*(?:Lac|Lakh|Cr|Crore|K|Thousand))?(?:\s*/\s*(?:month|mo))?)", text, re.I)
    if m:
        return f"\u20b9{m.group(1).strip()}"
    m = re.search(r"\u20b9\s*[\d,]+(?:\s*(?:Lac|Lakh|Cr|Crore|K|Thousand))?", text)
    if m:
        return m.group(0)
    m = re.search(r"([\d,]+(?:\.\d+)?)\s*(?:Cr|Crore|Lac|Lakh)\b", text, re.I)
    if m:
        v = m.group(0)
        for suffix in ["cr", "crore"]:
            if suffix in v.lower():
                return f"\u20b9{m.group(1)} Cr"
        for suffix in ["lac", "lakh"]:
            if suffix in v.lower():
                return f"\u20b9{m.group(1)} Lakh"
    return ""


def extract_area(text: str) -> str:
    m = re.search(r"([\d,]+(?:\.\d+)?)\s*(sq\.?\s*(?:ft|feet|m|meter|y(?:ar)?d)|sqft|sqm|sqy(?:ar)?d|marla|kanal|acre|hectare)", text, re.I)
    if m:
        return m.group(0)
    return ""


def extract_location(text: str) -> str:
    m = re.search(r"\b(?:in|at|near|@)\s+([A-Za-z\s]+?)(?:,\s*Patiala|,\s*Punjab|\s*[-\u2013]|\s*\||\s*$)", text, re.I)
    if m:
        loc = m.group(1).strip()
        loc = re.sub(r"\s*(?:for\s+(?:sale|rent|buy).*|patiala.*)$", "", loc, flags=re.I)
        loc = loc.strip().strip(",").strip()
        if loc and len(loc) > 2 and "sq" not in loc.lower():
            return loc
    return "Patiala"


class GoogleAPIScraper(BaseScraper):
    """
    Uses Google Custom Search JSON API to find property listings in Patiala.
    Requires environment variables: GOOGLE_API_KEY, GOOGLE_CX
    """

    def fetch(self) -> list[dict]:
        api_key = os.environ.get("GOOGLE_API_KEY", "")
        cx = os.environ.get("GOOGLE_CX", "")

        if not api_key or not cx:
            print("[GoogleAPI] SKIPPED — GOOGLE_API_KEY or GOOGLE_CX not set")
            return []

        results = []
        seen_urls: set[str] = set()

        queries = [
            "site:99acres.com Patiala property",
            "site:housing.com Patiala property",
            "site:magicbricks.com Patiala property",
            "site:commonfloor.com Patiala property",
            "Patiala plot for sale",
            "Patiala land for sale",
            "Patiala commercial property for sale",
            "Patiala house for sale",
            "Patiala rental property",
        ]

        for query in queries:
            params = {
                "key": api_key,
                "cx": cx,
                "q": query,
                "num": 10,
                "gl": "in",
                "hl": "en",
            }
            try:
                resp = requests.get(
                    "https://www.googleapis.com/customsearch/v1",
                    params=params,
                    timeout=20,
                )
                if resp.status_code != 200:
                    print(f"[GoogleAPI] Query '{query[:50]}' returned {resp.status_code}")
                    continue
                data = resp.json()
                items = data.get("items", [])
            except Exception as e:
                print(f"[GoogleAPI] Error for query '{query[:50]}': {e}")
                continue

            for item in items:
                link = item.get("link", "")
                if not link or link in seen_urls:
                    continue
                # Skip non-Patiala results
                if "patiala" not in link.lower():
                    # Check title and snippet too
                    title_txt = item.get("title", "")
                    snippet_txt = item.get("snippet", "")
                    combined = (title_txt + " " + snippet_txt).lower()
                    if "patiala" not in combined:
                        continue

                seen_urls.add(link)

                title = item.get("title", "")
                snippet = item.get("snippet", "")
                all_text = title + " " + snippet

                # Determine listing_type from query
                listing_type = "Buy"
                if "rent" in query.lower():
                    listing_type = "Rent"

                price = extract_price(all_text)
                area = extract_area(all_text)
                loc = extract_location(title)
                if loc == "Patiala":
                    loc = extract_location(snippet)
                ptype = detect_prop_type(all_text)
                src_name = get_source_name(link)
                phone = extract_phone(all_text)
                contact_name = extract_contact_name(all_text)

                results.append({
                    "title": str(title)[:200],
                    "price": price,
                    "location": loc if loc else "Patiala",
                    "area": area,
                    "property_type": ptype,
                    "listing_type": listing_type,
                    "summary": snippet[:300] if snippet else f"{listing_type} | {ptype}",
                    "source_url": link,
                    "source_name": src_name,
                    "phone": phone,
                    "contact_name": contact_name,
                })

            # Rate limit: max 100 queries per day on free tier
            time.sleep(0.3)

        return results