"""Pomocne utility."""

from __future__ import annotations

import re
from urllib.parse import urlparse


TRACKING_QUERY_PREFIXES = ("utm_", "fbclid", "gclid", "msclkid")


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def slugify_text(value: str) -> str:
    return normalize_text(value).lower().replace("’", "'")


def split_unique(values: list[str]) -> str:
    seen: list[str] = []
    for value in values:
        cleaned = normalize_text(value)
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    return "; ".join(seen)


def domain_from_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    return parsed.netloc.lower().removeprefix("www.")


def clean_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url.strip())
    cleaned_query_parts = []
    for item in parsed.query.split("&"):
        if not item:
            continue
        key = item.split("=", 1)[0].lower()
        if key.startswith(TRACKING_QUERY_PREFIXES) or key in TRACKING_QUERY_PREFIXES:
            continue
        cleaned_query_parts.append(item)
    query = "&".join(cleaned_query_parts)
    return parsed._replace(query=query, fragment="").geturl()


def yes_no(value: bool) -> str:
    return "yes" if value else "no"


def safe_int(value: object) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0
