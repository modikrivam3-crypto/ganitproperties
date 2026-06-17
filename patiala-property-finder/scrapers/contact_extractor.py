"""
Shared utility to extract phone numbers / contact names from text.
Used by all scrapers to pick up publicly visible contact information.
"""
import re

# Indian mobile: +91-XXXXXXXXXX, 91XXXXXXXXXX, 0XXXXXXXXXX, XXXXXXXXXX
PHONE_PATTERNS = [
    re.compile(r'(?:\+?91[-.\s]?)?[6-9]\d{9}'),
    re.compile(r'0[6-9]\d{9}'),
    re.compile(r'\+\d{1,3}[-.\s]?\d{6,14}'),
]

# Common contact labels in listings
CONTACT_LABELS = [
    r'(?:call|contact|phone|mobile|tel|whatsapp|what\'?s\s*app)\s*[:\-]?\s*(\+?\d[\d\s\-\(\)]{7,})',
    r'(?:reach|ring|dial|talk)\s*(?:us|me|owner|broker|agent)?\s*(?:at|on)?\s*(\+?\d[\d\s\-\(\)]{7,})',
]

NAME_PATTERNS = [
    r'(?:contact|owner|broker|agent|seller|landlord|person)\s*(?::|is|name)?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
    r'(?:listed\s+by|posted\s+by|managed\s+by)\s*:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
    r'(?:mr\.|ms\.|mrs\.|dr\.)\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
]


def extract_phone(text: str) -> str:
    """Extract the first Indian mobile number found in text. Returns '' if none."""
    if not text:
        return ""
    # Try specific contact labels first
    for pat in CONTACT_LABELS:
        m = re.search(pat, text, re.I)
        if m:
            num = re.sub(r'[\s\-\(\)]', '', m.group(1))
            # Validate it's a phone-like number
            if len(num) >= 10 and any(c.isdigit() for c in num):
                digits = re.sub(r'\D', '', num)
                if len(digits) >= 10:
                    return digits[-10:] if len(digits) >= 10 else digits
    # Fallback: find any Indian mobile pattern
    for pat in PHONE_PATTERNS:
        m = pat.search(text)
        if m:
            digits = re.sub(r'\D', '', m.group(0))
            if len(digits) >= 10:
                # Return last 10 digits prepended with +91 if not already
                last10 = digits[-10:]
                if last10.startswith('0'):
                    last10 = last10[1:]
                return '+91' + last10[-10:] if len(last10) == 10 else last10
    return ""


def extract_contact_name(text: str) -> str:
    """Extract a likely owner/broker name from text. Returns '' if none."""
    if not text:
        return ""
    for pat in NAME_PATTERNS:
        m = pat.search(text, re.I)
        if m:
            name = m.group(1).strip()
            # Filter out non-name words
            skip_words = {'the', 'for', 'and', 'this', 'with', 'from', 'more', 'patiala', 'property', 'details', 'price', 'area', 'size', 'call', 'contact', 'view'}
            if name.lower() not in skip_words and len(name) > 2:
                return name
    return ""


def extract_phone_from_page_html(html: str) -> str:
    """
    Try to extract phone from listing detail page HTML.
    Looks for common patterns in buttons, hidden elements, and structured data.
    """
    if not html:
        return ""
    # JSON-LD structured data
    m = re.search(r'"telephone"\s*:\s*"([^"]+)"', html)
    if m:
        return m.group(1)
    # Data attributes
    m = re.search(r'data-phone[=:]\s*["\']?(\+?\d[\d\s\-\(\)]{7,})', html, re.I)
    if m:
        return m.group(1)
    # Button/link href with tel:
    m = re.search(r'href="tel:(\+?\d[\d\s\-\(\)]{7,})"', html, re.I)
    if m:
        return m.group(1)
    # Common "Show Phone" / click-to-reveal patterns
    m = re.search(r'class="[^"]*phone[^"]*"[^>]*>[^<]*((?:\+?\d[\d\s\-\(\)]{7,15}))', html, re.I)
    if m:
        return m.group(1)
    return ""