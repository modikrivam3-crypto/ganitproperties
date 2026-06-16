from .base import BaseScraper


class NoBrokerScraper(BaseScraper):
    """
    NoBroker uses heavy JavaScript rendering (Next.js).
    Server-side requests return empty/placeholder pages without listing data.
    We report it as not scrapeable via simple HTTP requests.
    """

    def fetch(self) -> list[dict]:
        self.blocked = True
        print("[NoBroker] Site uses JavaScript rendering - not scrapeable via HTTP requests")
        return []