"""Extrakcna logika nad HTML."""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

import phonenumbers
from bs4 import BeautifulSoup

from ua_dealer_intel.constants import CHINESE_BRANDS, EU_LANGUAGE_CODES, SERVICE_KEYWORDS, SOCIAL_HOSTS, WESTERN_BRANDS
from ua_dealer_intel.utils import domain_from_url, normalize_text, slugify_text, split_unique

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{7,}\d)")


def extract_company_name(soup: BeautifulSoup, company_hint: str, source_url: str) -> str:
    if company_hint:
        return company_hint

    meta_candidates = [
        soup.find("meta", attrs={"property": "og:site_name"}),
        soup.find("meta", attrs={"property": "og:title"}),
        soup.find("meta", attrs={"name": "title"}),
    ]
    for tag in meta_candidates:
        if tag and tag.get("content"):
            return normalize_text(tag["content"])

    if soup.title and soup.title.text:
        return normalize_text(soup.title.text)

    return domain_from_url(source_url) or "Neznamy dealer"


def extract_brands(text: str) -> tuple[list[str], bool]:
    haystack = slugify_text(text)
    found: list[str] = []
    for brand in sorted(WESTERN_BRANDS | CHINESE_BRANDS):
        if brand in haystack:
            found.append(brand.title())
    chinese = any(slugify_text(item) in CHINESE_BRANDS for item in found)
    return found, chinese


def extract_services(text: str) -> list[str]:
    haystack = slugify_text(text)
    found: list[str] = []
    for service, keywords in SERVICE_KEYWORDS.items():
        if any(keyword in haystack for keyword in keywords):
            found.append(service)
    return found


def extract_languages(soup: BeautifulSoup, page_url: str) -> list[str]:
    langs: list[str] = []
    html_tag = soup.find("html")
    if html_tag and html_tag.get("lang"):
        langs.append(html_tag["lang"].split("-")[0].lower())

    for tag in soup.find_all("link", attrs={"hreflang": True}):
        langs.append(tag["hreflang"].split("-")[0].lower())

    parsed = urlparse(page_url)
    for piece in parsed.path.split("/"):
        code = piece.lower()
        if code in EU_LANGUAGE_CODES or code in {"uk", "ru"}:
            langs.append(code)

    unique: list[str] = []
    for lang in langs:
        if lang and lang not in unique:
            unique.append(lang)
    return unique


def extract_emails(text: str) -> list[str]:
    return sorted(set(EMAIL_RE.findall(text)))


def _is_valid_phone(candidate: str) -> bool:
    try:
        parsed = phonenumbers.parse(candidate, "UA")
    except phonenumbers.NumberParseException:
        return False
    return phonenumbers.is_possible_number(parsed)


def extract_phones(text: str) -> list[str]:
    phones: list[str] = []
    for match in PHONE_RE.findall(text):
        if _is_valid_phone(match):
            normalized = normalize_text(match)
            if normalized not in phones:
                phones.append(normalized)
    return phones


def extract_social_links(soup: BeautifulSoup, page_url: str) -> dict[str, str]:
    socials: dict[str, str] = {}
    for link in soup.find_all("a", href=True):
        href = urljoin(page_url, link["href"].strip())
        host = urlparse(href).netloc.lower().removeprefix("www.")
        for social_host, column in SOCIAL_HOSTS.items():
            if social_host in host and column not in socials:
                socials[column] = href
    return socials


def summarize_social_links(socials: dict[str, str]) -> str:
    return split_unique(list(socials.values()))

