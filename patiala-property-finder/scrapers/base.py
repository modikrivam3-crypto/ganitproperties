class BaseScraper:
    """
    Base class for all property scrapers.

    To add a new source:
    1. Create a new file in scrapers/ (e.g. scrapers/magicbricks.py)
    2. Subclass BaseScraper and implement fetch()
    3. Return a list of dicts matching the schema below
    4. Register your scraper in scrapers/__init__.py

    Required fields in each dict:
        title        (str)  — property listing title
        source_url   (str)  — original listing URL (must be unique per property)
        source_name  (str)  — display name of the source site

    Optional fields:
        price        (str)  — e.g. "₹45 Lakh", "₹12,000/month"
        location     (str)  — neighbourhood / sector in Patiala
        area         (str)  — e.g. "1200 sq ft", "5 Marla"
        property_type(str)  — "Flat", "House", "Plot", "Commercial", "Villa"
        listing_type (str)  — "Buy" or "Rent"
        summary      (str)  — short description (max ~200 chars)
    """

    def fetch(self) -> list[dict]:
        raise NotImplementedError
