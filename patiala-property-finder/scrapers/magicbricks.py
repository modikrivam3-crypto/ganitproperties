import re
import time
import math
import requests
from bs4 import BeautifulSoup
from .base import BaseScraper
from .contact_extractor import extract_phone, extract_contact_name

BASE = "https://www.magicbricks.com"
MAX_PAGES = 15
PAGE_DELAY = 1.2  # seconds between pages

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
    "Referer": "https://www.google.com/",
}

# (path_suffix, proptype_param, listing_type, category_label)
CATEGORIES = [
    (
        "property-for-sale/residential-real-estate",
        "Multistorey-Apartment,Builder-Floor-Apartment,Penthouse,Studio-Apartment,Villa,Residential-House",
        "Buy", "Residential"
    ),
    (
        "property-for-rent/residential-real-estate",
        "Multistorey-Apartment,Builder-Floor-Apartment,Penthouse,Studio-Apartment,Villa,Residential-House",
        "Rent", "Residential"
    ),
    (
        "property-for-sale/commercial-real-estate",
        "Office-Space,Retail-Shop-Showroom,Warehouse-Godown,Industrial-Shed,Industrial-Plot,Factory-Industrial-Building,Commercial-Plot,Hotel-Resort,Commercial-Building,Others",
        "Buy", "Commercial"
    ),
    (
        "property-for-rent/commercial-real-estate",
        "Office-Space,Retail-Shop-Showroom,Warehouse-Godown,Industrial-Shed,Hotel-Resort,Others",
        "Rent", "Commercial"
    ),
    (
        "property-for-sale/agricultural-real-estate",
        "",
        "Buy", "Agricultural"
    ),
    (
        "property-for-rent/agricultural-real-estate",
        "",
        "Rent", "Agricultural"
    ),
]

PROP_TYPE_MAP = [
    ("hotel",       "Hotel"),
    ("warehouse",   "Warehouse"),
    ("godown",      "Warehouse"),
    ("factory",     "Factory"),
    ("industrial",  "Industrial"),
    ("showroom",    "Showroom"),
    ("shop",        "Shop"),
    ("office",      "Office"),
    ("commercial",  "Commercial"),
    ("farmhouse",   "Farm House"),
    ("farm",        "Agricultural"),
    ("agriculture", "Agricultural"),
    ("villa",       "Villa"),
    ("penthouse",   "Penthouse"),
    ("studio",      "Flat"),
    ("flat",        "Flat"),
    ("apartment",   "Flat"),
    ("house",       "House"),
    ("floor",       "House"),
    ("plot",        "Plot"),
    ("land",        "Plot"),
    ("bhk",         "Flat"),
]


def _detect_prop_type(title: str) -> str:
    t = title.lower()
    for kw, label in PROP_TYPE_MAP:
        if kw in t:
            return label
    return "Property"


def _parse_location(title: str) -> str:
    m = re.search(r"\b(?:in|at|near)\s+(.+?)(?:,\s*Patiala|,\s*Punjab|\s*[-–]|\s*$)", title, re.I)
    if m:
        loc = m.group(1).strip()
        loc = re.sub(r"\s*(for\s+(?:sale|rent|buy).*|patiala.*)$", "", loc, flags=re.I)
        loc = loc.strip().strip(",").strip()
        if loc and len(loc) > 2:
            return loc
    return "Patiala"


def _get_summary_value(card, *labels) -> str:
    for label in labels:
        for item in card.select(".mb-srp__card__summary__list--item"):
            lbl = item.select_one(".mb-srp__card__summary--label")
            val = item.select_one(".mb-srp__card__summary--value")
            if lbl and val and label.lower() in lbl.get_text(strip=True).lower():
                return val.get_text(strip=True)
    return ""


def _parse_total(soup) -> int:
    text = soup.get_text(" ")
    m = re.search(r"(\d[\d,]+)\s+(?:properties|results|listings|flats|houses|plots|shops)", text, re.I)
    if m:
        return int(m.group(1).replace(",", ""))
    return 0


def _build_category_url(path_suffix: str, proptype: str, page: int) -> str:
    params = f"cityName=Patiala&page={page}"
    if proptype:
        params = f"proptype={proptype}&{params}"
    return f"{BASE}/{path_suffix}?{params}"


def _extract_contact_from_card(card, session) -> tuple[str, str]:
    """
    Try to extract phone and contact name from a MagicBricks listing card.
    Looks for contact buttons/labels in the card HTML.
    Only extracts publicly visible contact information.
    """
    card_html = str(card)
    phone = extract_phone(card_html)
    contact_name = extract_contact_name(card_html)

    # Look for specific MagicBricks contact patterns
    # Contact button with data attribute
    m = re.search(r'data-contact[=:]\s*["\']?(\+?\d[\d\s\-\(\)]{7,})', card_html, re.I)
    if m and not phone:
        digits = re.sub(r'\D', '', m.group(1))
        if len(digits) >= 10:
            phone = '+91' + digits[-10:]

    # "Posted by" or "Listed by" labels
    m = re.search(r'(?:Posted|Listed|Managed)\s+by\s*:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', card.get_text(" "), re.I)
    if m and not contact_name:
        contact_name = m.group(1).strip()

    return phone, contact_name


class MagicBricksScraper(BaseScraper):
    """
    Scrapes MagicBricks for ALL property types in Patiala:
    residential, commercial, agricultural, buy and rent.
    Paginates each category until no more cards are returned.
    Extracts publicly visible contact information when available.
    """

    def fetch(self) -> list[dict]:
        session = requests.Session()
        session.headers.update(HEADERS)
        results = []
        seen_urls: set[str] = set()

        for path_suffix, proptype, listing_type, category in CATEGORIES:
            cat_count = 0
            for page in range(1, MAX_PAGES + 1):
                url = _build_category_url(path_suffix, proptype, page)
                try:
                    resp = session.get(url, timeout=20)
                    if resp.status_code != 200:
                        print(f"[MB] {category} {listing_type} p{page}: HTTP {resp.status_code}")
                        break
                except Exception as e:
                    print(f"[MB] {category} {listing_type} p{page}: {e}")
                    break

                soup = BeautifulSoup(resp.text, "lxml")
                cards = soup.select(".mb-srp__card")

                if not cards:
                    break  # no more pages

                for card in cards:
                    try:
                        title_el = card.select_one("h2.mb-srp__card--title, h2[class*='title'], h2")
                        price_el = card.select_one(".mb-srp__card__price--amount")
                        link_el  = (
                            card.select_one("a.view-property-link") or
                            card.select_one("a[href*='propertyDetails']") or
                            card.select_one("a[href*='magicbricks']")
                        )
                        if not title_el:
                            continue

                        title = title_el.get_text(strip=True)
                        price = price_el.get_text(strip=True) if price_el else ""
                        area  = _get_summary_value(card, "Super Area", "Carpet Area", "Plot Area", "Area")
                        loc   = _parse_location(title)
                        ptype = _detect_prop_type(title)

                        href = link_el.get("href", "") if link_el else ""
                        if href and not href.startswith("http"):
                            href = BASE + href

                        # Fallback area from URL slug  e.g. "1200-Sq-ft"
                        if not area and href:
                            m = re.search(r"(\d+)-Sq-?(ft|yrd|yard|m)", href, re.I)
                            if m:
                                area = m.group(0).replace("-", " ")

                        if not href or href in seen_urls:
                            continue
                        seen_urls.add(href)

                        # Extract contact info from card
                        phone, contact_name = _extract_contact_from_card(card, session)

                        summary_parts = []
                        if price: summary_parts.append(price)
                        if area:  summary_parts.append(area)
                        if loc and loc != "Patiala": summary_parts.append(f"{loc}, Patiala")
                        summary_parts.append(f"{listing_type} · {ptype}")

                        results.append({
                            "title":         title,
                            "price":         price,
                            "location":      loc,
                            "area":          area,
                            "property_type": ptype,
                            "listing_type":  listing_type,
                            "summary":       " | ".join(summary_parts),
                            "source_url":    href,
                            "source_name":   "MagicBricks",
                            "phone":         phone,
                            "contact_name":  contact_name,
                        })
                        cat_count += 1
                    except Exception as e:
                        continue

                # Polite delay between pages
                if page < MAX_PAGES:
                    time.sleep(PAGE_DELAY)

            print(f"[MB] {category} {listing_type}: {cat_count} listings")

        print(f"[MB] Total: {len(results)}")
        return results