import re
import json
import time
import requests
from bs4 import BeautifulSoup
from .base import BaseScraper

BASE = "https://www.commonfloor.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
}

PROP_TYPE_MAP = [
    ("agriculture", "Agricultural"), ("agricultural", "Agricultural"), ("farm", "Agricultural"),
    ("farmland", "Agricultural"), ("farm land", "Agricultural"),
    ("industrial", "Industrial"), ("factory", "Factory"),
    ("warehouse", "Warehouse"), ("godown", "Warehouse"),
    ("commercial", "Commercial"), ("showroom", "Showroom"),
    ("office", "Office"),
    ("shop", "Shop"),
    ("plot", "Plot"), ("land", "Plot"), ("residential plot", "Plot"),
    ("house", "House"), ("independent house", "House"), ("builder floor", "House"),
    ("villa", "Villa"),
    ("apartment", "Flat"), ("flat", "Flat"), ("bhk", "Flat"), ("studio", "Flat"),
    ("penthouse", "Penthouse"),
]


def detect_prop_type(text: str) -> str:
    t = text.lower()
    for kw, label in PROP_TYPE_MAP:
        if kw in t:
            return label
    return "Property"


class CommonFloorScraper(BaseScraper):
    """
    CommonFloor uses heavy JavaScript rendering.
    Server-side requests return empty/placeholder pages.
    We report it as blocked since direct scraping is not possible.
    """

    def fetch(self) -> list[dict]:
        self.blocked = True
        print("[CommonFloor] Site uses JavaScript rendering - not scrapeable via HTTP requests")
        return []