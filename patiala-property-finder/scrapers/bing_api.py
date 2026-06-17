"""
Bing Search API scraper for Patiala properties.
Uses Azure Cognitive Services Bing Search API.
Requires BING_API_KEY environment variable.
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
    ("office", "Office"), ("shop", "Shop"),
    ("plot", "Plot"), ("land", "Plot"), ("residential plot", "Plot"),
    ("house", "House"), ("independent house", "House"), ("builder floor", "House"),
    ("villa", "Villa"), ("bunglow", "Villa"), ("bungalow", "Villa"),
    ("apartment", "Flat"), ("flat", "Flat"), ("bhk", "Flat"), ("studio", "Flat"),
    ("penthouse", "Penthouse"), ("hotel", "Hotel"), ("resort", "Hotel"),
]


def detect_prop_type(text: str) -> str:
    t = text.lower()
    for kw, label in PROP_TYPE_MAP:
        if kw in t:
            return label
    return "Property"


def get_source_name(url: str) -> str:
    if not url:
        return "Bing API"
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
        return "Bing API"


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
    t = text.lower()
    if "patiala" in t:
        m = re.search(r'([A-Za-z][A-Za-z\s.]+)(?:,\s*)?patiala', t, re.I)
        if m:
            loc = m.group(1).strip().strip(",").strip()
            skip = {'for', 'the', 'in', 'at', 'near', 'property', 'sale', 'rent', 'buy', 'price', 'area', 'size', 'new', 'old', 'super', 'carpet'}
            words = loc.split()
            if len(words) >= 2 and words[0].lower() not in skip:
                return loc.title()[:50] + ", Patiala"
        return "Patiala"
    return "Patiala"


class BingAPIScraper(BaseScraper):
    """
    Uses Azure Bing Search API to find property listings in Patiala.
    Requires environment variable: BING_API_KEY
    """

    def fetch(self) -> list[dict]:
        api_key = os.environ.get("BING_API_KEY", "")

        if not api_key:
            print("[BingAPI] SKIPPED — BING_API_KEY not set")
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

        headers = {"Ocp-Apim-Subscription-Key": api_key}
        total_raw = 0

        for query in queries:
            params = {
                "q": query,
                "count": 15,
                "offset": 0,
                "mkt": "en-IN",
            }
            try:
                resp = requests.get(
                    "https://api.bing.microsoft.com/v7.0/search",
                    headers=headers,
                    params=params,
                    timeout=20,
                )
                if resp.status_code != 200:
                    print(f"[BingAPI] Query '{query[:50]}' returned {resp.status_code}")
                    continue
                data = resp.json()
                items = data.get("webPages", {}).get("value", [])
            except Exception as e:
                print(f"[BingAPI] Error for query '{query[:50]}': {e}")
                continue

            query_results = 0
            for item in items:
                link = item.get("url", "")
                if not link or link in seen_urls:
                    continue

                seen_urls.add(link)

                title = item.get("name", "")
                snippet = item.get("snippet", "")
                all_text = title + " " + snippet

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

                if not price:
                    price = "Price on request"
                if not area:
                    area = "N/A"
                if not loc:
                    loc = "Patiala"

                results.append({
                    "title": str(title)[:200],
                    "price": price,
                    "location": loc,
                    "area": area,
                    "property_type": ptype,
                    "listing_type": listing_type,
                    "summary": snippet[:300] if snippet else f"{listing_type} | {ptype} | Patiala",
                    "source_url": link,
                    "source_name": src_name,
                    "phone": phone,
                    "contact_name": contact_name,
                })
                query_results += 1

            total_raw += len(items)
            print(f"[BingAPI] Query '{query[:50]}': {len(items)} raw, {query_results} kept")
            time.sleep(0.3)

        print(f"[BingAPI] TOTAL: {len(results)} results (from {total_raw} raw items)")
        return results