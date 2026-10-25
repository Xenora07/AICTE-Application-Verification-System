"""
src/mappers/normalizers.py - Deterministic value normalizers for regulatory document extraction.
Converts extracted raw strings into canonical standardized representations.
"""

from datetime import datetime
import re
from typing import Optional


COMMON_ACRONYMS = {
    "IIT", "IIIT", "NIT", "BITS", "AICTE", "NBA", "NAAC", "UGC", "KGEC",
    "COEP", "VJTI", "DTU", "NSUT", "VIT", "MIT", "SRM", "PSG", "RVCE",
    "BMSCE", "MSRIT", "TIET", "ICT", "CBIT",
}


def normalize_institution_name(raw_val: str) -> str:
    """
    Clean whitespace and line breaks from institution name.
    If name is entirely uppercase, converts to readable Title Case,
    preserving lower case for standard prepositions/conjunctions
    and preserving established institution acronyms (e.g. 'IIT', 'NIT', 'KGEC').
    Preserves original mixed-case names without loss of casing nuance.
    """
    cleaned = re.sub(r"\s+", " ", raw_val).strip()
    # Strip any trailing commas, colons, or dashes
    cleaned = re.sub(r"[,:\-]+$", "", cleaned).strip()
    if cleaned.isupper() and len(cleaned) > 3:
        words = cleaned.split()
        minor_words = {"of", "and", "for", "in", "on", "the", "to", "at", "de"}
        result_words = []
        for i, w in enumerate(words):
            upper_w = w.upper()
            if upper_w in COMMON_ACRONYMS:
                result_words.append(upper_w)
            elif i > 0 and w.lower() in minor_words:
                result_words.append(w.lower())
            else:
                result_words.append(w.capitalize())
        return " ".join(result_words)
    return cleaned


def normalize_academic_year(raw_val: str) -> str:
    """
    Standardize academic year representation to 'YYYY-YYYY'.
    Converts '2026-27' to '2026-2027', and multi-year validity spans
    like '2022-2023 to 2026-2027' or '2021-22 to 2023-24' to '2022-2027' / '2021-2024'.
    """
    # Check for multi-period range e.g. '2022-2023 to 2026-2027'
    range_match = re.search(
        r"(\d{4})(?:\s*[-/]\s*\d{2,4})?\s+(?:to|and)\s+(?:\d{4}\s*[-/]\s*)?(\d{2,4})",
        raw_val,
        re.IGNORECASE,
    )
    if range_match:
        y1, y2 = range_match.groups()
        if len(y2) == 2:
            y2 = f"{y1[:2]}{y2}"
        return f"{y1}-{y2}"

    match = re.search(r"(\d{4})\s*[-/]\s*(\d{2,4})", raw_val)
    if match:
        y1, y2 = match.groups()
        if len(y2) == 2:
            y2 = f"{y1[:2]}{y2}"
        return f"{y1}-{y2}"
    return raw_val.strip()


def normalize_id(raw_val: str) -> str:
    """Standardize application or permanent institution ID."""
    cleaned = re.sub(r"\s+", "", raw_val).strip()
    return cleaned.upper()


def normalize_date_iso(raw_val: str) -> Optional[str]:
    """
    Standardize varied date formats to ISO 8601 'YYYY-MM-DD'.
    Handles formats like:
    - 'June 01, 2025' or 'May 1, 2024'
    - '16-Mar-2026' or '16-March-2026'
    - '30-06-2027' or '06 - 04 - 2022'
    - '2025-06-01'
    """
    cleaned = re.sub(r"\s+", " ", raw_val).strip()
    # Clean up spacing around hyphens or slashes: '06 - 04 - 2022' -> '06-04-2022'
    cleaned = re.sub(r"\s*([-/])\s*", r"\1", cleaned)

    formats = [
        "%Y-%m-%d",
        "%B %d, %Y",
        "%B %d %Y",
        "%b %d, %Y",
        "%b %d %Y",
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(cleaned, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Fallback regex search for embedded YYYY-MM-DD
    iso_match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", cleaned)
    if iso_match:
        return iso_match.group(0)

    return None


def normalize_cgpa(raw_val: str) -> Optional[float]:
    """
    Normalize CGPA to a float value [0.0 - 4.0] or [0.0 - 10.0].
    Resolves OCR ambiguity where 'O' or 'o' is misrecognized for '0'.
    """
    cleaned = raw_val.replace("O", "0").replace("o", "0").strip()
    match = re.search(r"(\d+\.\d+)", cleaned)
    if match:
        try:
            return round(float(match.group(1)), 2)
        except ValueError:
            pass
    return None


def normalize_grade(raw_val: str) -> str:
    """Normalize accreditation grade (e.g. 'A++', 'A+', 'A', 'B++', 'B+', 'B', 'C')."""
    cleaned = raw_val.strip().upper()
    match = re.search(r"\b([A-C](?:\+{1,2})?)(?!\w)", cleaned)
    if match:
        return match.group(1)
    return cleaned
