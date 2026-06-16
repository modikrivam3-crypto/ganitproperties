import re
import time
import random
import requests
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from .base import BaseScraper

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
        return "Google Search"
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
        return "Google Search"


def parse_price(text: str) -> str:
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


def parse_area(text: str) -> str:
    m = re.search(r"([\d,]+(?:\.\d+)?)\s*(sq\.?\s*(?:ft|feet|m|meter|y(?:ar)?d)|sqft|sqm|sqy(?:ar)?d|marla|kanal|acre|hectare)", text, re.I)
    if m:
        return m.group(0)
    return ""


def parse_location(text: str) -> str:
    m = re.search(r"\b(?:in|at|near|@)\s+([A-Za-z\s]+?)(?:,\s*Patiala|,\s*Punjab|\s*[-\u2013]|\s*\||\s*$)", text, re.I)
    if m:
        loc = m.group(1).strip()
        loc = re.sub(r"\s*(?:for\s+(?:sale|rent|buy).*|patiala.*)$", "", loc, flags=re.I)
        loc = loc.strip().strip(",").strip()
        if loc and len(loc) > 2 and "sq" not in loc.lower():
            return loc
    return "Patiala"


class GoogleSearchScraper(BaseScraper):
    """
    Fallback scraper: uses Google Search to find property listings in Patiala.
    Helps when direct site scraping is blocked.
    Note: Google may block automated requests.
    """

    def fetch(self) -> list[dict]:
        results = []
        seen_urls: set[str] = set()

        queries = [
            "patiala punjab property for sale site magicbricks.com",
            "patiala punjab property for rent site magicbricks.com",
            "patiala punjab flats houses for sale site 99acres.com",
            "patiala punjab property for rent site 99acres.com",
            "patiala punjab property site housing.com",
            "patiala punjab property site commonfloor.com",
            "patiala punjab property site nobroker.in",
            "patiala punjab plots land agricultural farm for sale",
            "patiala punjab commercial property shop office warehouse factory",
            "patiala punjab flat apartment villa penthouse for sale",
            "patiala punjab property for rent flat house commercial",
            "patiala punjab agricultural land farm land for sale",
            "patiala punjab industrial shed godown factory plot",
        ]

        session = requests.Session()
        session.headers.update(HEADERS)

        for query in queries:
            search_url = (
                f"https://www.google.com/search?q={quote_plus(query)}"
                f"&num=15&hl=en&gl=in&source=lnms"
            )
            try:
                resp = session.get(search_url, timeout=20)
                if resp.status_code != 200:
                    continue
            except Exception:
                continue

            soup = BeautifulSoup(resp.text, "lxml")

            # Google search results
            selectors = [
                "div.g",
                "div[data-hveid]",
                "div[data-sokoban-container]",
            ]

            items = []
            for sel in selectors:
                for g in soup.select(sel):
                    link_el = g.select_one("a[href^='http']")
                    if not link_el:
                        continue
                    href = link_el.get("href", "")
                    if "patiala" not in href.lower():
                        continue
                    if href in seen_urls:
                        continue
                    seen_urls.add(href)

                    title_el = g.select_one("h3")
                    title = title_el.get_text(strip=True) if title_el else ""
                    if not title:
                        continue

                    snippet_el = g.select_one("[data-sncf], .VwiC3b, .st")
                    snippet = snippet_el.get_text(" ", strip=True) if snippet_el else ""

                    listing_type = "Buy"
                    if "rent" in query.lower():
                        listing_type = "Rent"

                    all_text = title + " " + snippet
                    price = parse_price(all_text)
                    area = parse_area(all_text)
                    loc = parse_location(title)
                    if loc == "Patiala":
                        loc = parse_location(snippet)
                    ptype = detect_prop_type(all_text)
                    src_name = get_source_name(href)

                    items.append({
                        "title": str(title)[:120],
                        "price": price,
                        "location": loc if loc else "Patiala",
                        "area": area,
                        "property_type": ptype,
                        "listing_type": listing_type,
                        "summary": (snippet[:200] if snippet else f"{listing_type} | {ptype}"),
                        "source_url": href,
                        "source_name": src_name,
                    })

                if items:
                    results.extend(items)

            time.sleep(random.uniform(2.0, 3.5))

        # Deduplicate
        seen = set()
        unique = []
        for r in results:
            u = r["source_url"]
            if u not in seen:
                seen.add(u)
                unique.append(r)

        print(f"[GoogleSearch] Total: {len(unique)}")
        return unique