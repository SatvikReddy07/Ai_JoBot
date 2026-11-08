import re
import html
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from datetime import datetime
from pydantic import BaseModel

class RawJob(BaseModel):
    source: str
    source_job_id: str
    company: str
    title: str
    location: str
    city: Optional[str] = None
    country: Optional[str] = None
    employment_type: str = "Unknown"
    is_permanent_fulltime: bool = False
    description: str
    raw_description_html: Optional[str] = None
    url: str
    posted_date: Optional[datetime] = None

# Geo Mapping
COUNTRY_PATTERNS = {
    "India": [
        r"\bindia\b", r"\bhyderabad\b", r"\bbengaluru\b", r"\bbangalore\b",
        r"\bmumbai\b", r"\bdelhi\b", r"\bgurgaon\b", r"\bgurugram\b",
        r"\bnoida\b", r"\bpune\b", r"\bchennai\b", r"\bahmedabad\b",
        r"\bvadodara\b", r"\bkolkata\b"
    ],
    "Singapore": [
        r"\bsingapore\b", r"\bsg\b"
    ],
    "Germany": [
        r"\bgermany\b", r"\bdeutschland\b", r"\bberlin\b", r"\bmunich\b",
        r"\bmünchen\b", r"\bfrankfurt\b", r"\bhamburg\b", r"\bdüsseldorf\b",
        r"\bkoeln\b", r"\bcologne\b", r"\bstuttgart\b"
    ],
    "Netherlands": [
        r"\bnetherlands\b", r"\bnederland\b", r"\bamsterdam\b", r"\brotterdam\b",
        r"\butrecht\b", r"\bthe hague\b", r"\bden haag\b", r"\beindhoven\b", r"\bdelft\b"
    ],
    "Ireland": [
        r"\bireland\b", r"\bdublin\b", r"\bcork\b", r"\bgalway\b", r"\blimerick\b"
    ],
    "Australia": [
        r"\baustralia\b", r"\bsydney\b", r"\bmelbourne\b", r"\bbrisbane\b",
        r"\bperth\b", r"\badelaide\b", r"\bcanberra\b", r"\bnsw\b", r"\bvic\b", r"\bwa\b", r"\bqld\b"
    ],
    "United Kingdom": [
        r"\bunited kingdom\b", r"\buk\b", r"\blondon\b", r"\bmanchester\b", r"\bbirmingham\b"
    ],
    "Switzerland": [
        r"\bswitzerland\b", r"\bzurich\b", r"\bzürich\b", r"\bbalsthal\b", r"\bbasel\b", r"\bgeneva\b"
    ],
}

def clean_html(raw_html: str) -> str:
    """Strip HTML tags and unescape HTML entities to clean text."""
    if not raw_html:
        return ""
    # Convert breaks and paragraphs to newlines
    text = re.sub(r'<(br|p|div|li)[^>]*>', '\n', raw_html, flags=re.IGNORECASE)
    # Strip all other tags
    text = re.sub(r'<[^>]+>', ' ', text)
    # Unescape HTML entities
    text = html.unescape(text)
    # Normalize excessive spaces and lines
    lines = [line.strip() for line in text.split('\n')]
    cleaned = '\n'.join([l for l in lines if l])
    return cleaned

def parse_location(location_str: str) -> Tuple[Optional[str], Optional[str]]:
    """Intelligently extract City and Country from location string."""
    if not location_str:
        return None, "Unknown"

    loc_lower = location_str.lower()
    matched_country = None

    for country, patterns in COUNTRY_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, loc_lower):
                matched_country = country
                break
        if matched_country:
            break

    # Extract potential city (first element before comma if multiple)
    parts = [p.strip() for p in location_str.split(",") if p.strip()]
    city = parts[0] if parts else None

    # If first part equals country name, city might be None
    if city and matched_country and city.lower() == matched_country.lower():
        city = None

    return city, matched_country or "Unknown"

def parse_employment_type(text_sample: str) -> Tuple[str, bool]:
    """
    Parse employment type from job text, titles or categories.
    Accurately tags permanent / full-time, and leaves uncertain as 'Unknown'.
    """
    if not text_sample:
        return "Unknown", False

    lower = text_sample.lower()

    is_permanent = "permanent" in lower or "indefinite" in lower or "regular" in lower
    is_fulltime = "full-time" in lower or "full time" in lower or "fulltime" in lower
    is_contract = "contract" in lower or "temporary" in lower or "interim" in lower or "intern" in lower or "freelance" in lower

    if is_contract:
        return "Contract / Temporary", False

    if is_permanent and is_fulltime:
        return "Permanent Full-time", True
    elif is_fulltime:
        # Full-time confirmed, permanence typically standard unless specified temporary
        return "Full-time", True
    elif is_permanent:
        return "Permanent", True
    
    return "Unknown", False

class BaseConnector(ABC):
    def __init__(self, board_token: str, company_name: str):
        self.board_token = board_token
        self.company_name = company_name

    @abstractmethod
    async def fetch_jobs(self) -> List[RawJob]:
        """Fetch live jobs from employer career feed."""
        pass


def validate_feed_items(items, title_field, url_field):
    """Reject malformed/truncated snapshots rather than interpreting them as closures."""
    from urllib.parse import urlsplit
    if not isinstance(items, list):
        raise ValueError("Job feed must contain a complete list of postings.")
    for item in items:
        if not isinstance(item, dict) or item.get("id") is None:
            raise ValueError("Job feed contains a posting without a stable ID.")
        if not str(item["id"]).strip() or not isinstance(item.get(title_field), str) or not item[title_field].strip():
            raise ValueError("Job feed contains an invalid ID or title.")
        url = item.get(url_field)
        if not isinstance(url, str) or urlsplit(url).scheme not in {"http", "https"} or not urlsplit(url).hostname:
            raise ValueError("Job feed contains a posting without a valid source URL.")
    return items
