"""Input validation and sanitization."""

import re
from datetime import date, datetime


def parse_date(date_str: str) -> date:
    """Parse DD/MM/YYYY (or DD-MM-YYYY, DD.MM.YYYY) to datetime.date."""
    date_str = date_str.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Invalid date '{date_str}'. Use DD/MM/YYYY format.")


def sanitize_party_name(name: str) -> str:
    """Uppercase, strip, limit to 31 chars (Excel sheet name limit for export)."""
    name = name.strip().upper()
    name = re.sub(r"[^\w\s&\-]", "", name)  # keep letters, digits, spaces, &, -
    name = re.sub(r"\s+", " ", name)
    if not name:
        raise ValueError("Party name cannot be empty.")
    return name[:31]


def sanitize_vehicle_no(v: str) -> str:
    if not v or not v.strip():
        return ""
    return re.sub(r"\s+", "", v.strip().upper())


def sanitize_text(text: str, max_length: int = 200) -> str:
    return text.strip()[:max_length]
