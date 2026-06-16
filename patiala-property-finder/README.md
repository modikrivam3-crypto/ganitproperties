# Patiala Property Finder

A local web app that collects and displays property listings for Patiala, Punjab — all in one place.

## Quick Start

### 1. Install Python dependencies (one time)
```bash
cd patiala-property-finder
pip install -r requirements.txt
```

### 2. Run the app
```bash
python run.py
```

### 3. Open in browser
- **Laptop:** http://127.0.0.1:5050
- **Phone (same Wi-Fi):** The startup output shows your laptop's IP — e.g. `http://192.168.1.42:5050`

---

## Features

- **Search** — keyword search across title, location, and summary
- **Filters** — Buy/Rent, Property Type, Area/Location
- **Property cards** — title, price, location, area, type, summary
- **Open listing** — links to original source, never copies full content
- **Deduplicate** — same URL is never saved twice
- **Admin Refresh** — button to re-run all scrapers and load new listings
- **Remove listing** — hide any listing from your local view
- **SQLite** — zero setup, single-file local database (`properties.db`)

---

## Adding Real Property Sources

The scraper system is designed to be extended. Each source is a separate file.

### Step 1 — Create a new scraper file

```python
# scrapers/magicbricks.py
import requests
from bs4 import BeautifulSoup
from .base import BaseScraper

class MagicBricksScraper(BaseScraper):
    def fetch(self):
        # Fetch search results page for Patiala
        url = "https://www.magicbricks.com/property-for-sale/residential-real-estate?proptype=Multistorey-Apartment,Builder-Floor-Apartment,Penthouse,Studio-Apartment&cityName=Patiala"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        listings = []
        for card in soup.select(".mb-srp__card"):
            title = card.select_one(".mb-srp__card--title")
            price = card.select_one(".mb-srp__card--price")
            link  = card.select_one("a")
            if not (title and link):
                continue
            listings.append({
                "title":         title.get_text(strip=True),
                "price":         price.get_text(strip=True) if price else "",
                "location":      "Patiala",
                "property_type": "Flat",
                "listing_type":  "Buy",
                "summary":       title.get_text(strip=True)[:200],
                "source_url":    link["href"],
                "source_name":   "MagicBricks",
            })
        return listings
```

### Step 2 — Register your scraper

In `scrapers/__init__.py`, add:

```python
from .magicbricks import MagicBricksScraper

def run_all_scrapers():
    scrapers = [
        DemoScraper(),
        MagicBricksScraper(),   # <-- add here
    ]
    ...
```

### Step 3 — Install any extra dependencies

```bash
pip install requests beautifulsoup4
```

> **Note:** Always scrape responsibly. Only collect publicly visible listing summaries and always link back to the original source. Do not reproduce full content, photos, or agent contact details.

---

## Database

The SQLite database is saved as `properties.db` in the same folder.

To reset all data:
```bash
rm properties.db
python run.py   # re-creates automatically
```

---

## Project Layout

```
patiala-property-finder/
├── app.py              Flask app + API routes
├── run.py              Startup script (auto-detects your Wi-Fi IP)
├── requirements.txt
├── properties.db       Created on first run
├── scrapers/
│   ├── __init__.py     Runs all scrapers
│   ├── base.py         BaseScraper contract
│   └── demo.py         Sample listings (runs on first refresh)
├── templates/
│   └── index.html
└── static/
    ├── css/style.css
    └── js/app.js
```
