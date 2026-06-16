import threading
from .magicbricks import MagicBricksScraper
from .acres99 import Acres99Scraper
from .housing import HousingScraper
from .commonfloor import CommonFloorScraper
from .nobroker import NoBrokerScraper
from .google_search import GoogleSearchScraper

# Global scrape status — read by /api/scrape-status endpoint
scrape_status: dict = {
    "running": False,
    "sources": {},
    "total_added": 0,
    "total_skipped": 0,
    "started_at": None,
    "finished_at": None,
}

SCRAPERS = [
    ("MagicBricks",  MagicBricksScraper),
    ("99acres",      Acres99Scraper),
    ("Housing.com",  HousingScraper),
    ("CommonFloor",  CommonFloorScraper),
    ("NoBroker",     NoBrokerScraper),
    ("Google Search", GoogleSearchScraper),
]


def run_all_scrapers(on_source_done=None) -> tuple[list[dict], dict]:
    """
    Run all scrapers, collect listings and per-source status.
    Returns (all_listings, status_dict).
    on_source_done(name, status_dict) is called after each source finishes.
    """
    import datetime
    global scrape_status

    scrape_status["running"] = True
    scrape_status["started_at"] = datetime.datetime.now().isoformat()
    scrape_status["finished_at"] = None
    scrape_status["sources"] = {}
    scrape_status["total_added"] = 0
    scrape_status["total_skipped"] = 0

    all_listings: list[dict] = []

    for name, ScraperClass in SCRAPERS:
        scrape_status["sources"][name] = {
            "status":  "fetching",
            "count":   0,
            "message": "",
        }
        try:
            scraper = ScraperClass()
            scraper.blocked = False
            listings = scraper.fetch()
            status = "blocked" if getattr(scraper, "blocked", False) else "completed"
            scrape_status["sources"][name] = {
                "status":  status,
                "count":   len(listings),
                "message": "Blocked by site protection" if status == "blocked" else f"{len(listings)} listings fetched",
            }
            all_listings.extend(listings)
        except Exception as e:
            scrape_status["sources"][name] = {
                "status":  "failed",
                "count":   0,
                "message": str(e)[:120],
            }
            print(f"[Scraper] {name} failed: {e}")

        if on_source_done:
            on_source_done(name, scrape_status["sources"][name])

    scrape_status["running"] = False
    scrape_status["finished_at"] = datetime.datetime.now().isoformat()
    return all_listings, scrape_status
