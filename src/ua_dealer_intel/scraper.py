"""Web scraping a orchestrace spracovania."""

from __future__ import annotations

import time
import urllib.robotparser
from dataclasses import asdict
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from ua_dealer_intel.constants import CLIENT_TARGET_BRANDS, EXCLUDED_REASON_COLUMN, TARGET_COLUMNS
from ua_dealer_intel.extraction import (
    extract_brands,
    extract_company_name,
    extract_emails,
    extract_languages,
    extract_phones,
    extract_services,
    extract_social_links,
    summarize_social_links,
)
from ua_dealer_intel.geo import classify_scope
from ua_dealer_intel.models import ScrapeResult, SeedRecord
from ua_dealer_intel.scoring import compute_score
from ua_dealer_intel.utils import slugify_text, split_unique, yes_no


class WebClient:
    """Konzervativny HTTP klient s podporou robots.txt."""

    def __init__(self, delay_seconds: int = 3, timeout_seconds: int = 20, retries: int = 2) -> None:
        self.delay_seconds = delay_seconds
        self.timeout_seconds = timeout_seconds
        self.retries = retries
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "ua-dealer-intel/0.1 (+respektuje robots.txt; kontakt cez maintainera repozitara)",
                "Accept-Language": "sk,en;q=0.8,uk;q=0.7",
            }
        )
        self._robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}

    def allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        parser = self._robots_cache.get(robots_url)
        if parser is None:
            parser = urllib.robotparser.RobotFileParser()
            parser.set_url(robots_url)
            try:
                parser.read()
            except Exception:
                return False
            self._robots_cache[robots_url] = parser
        return parser.can_fetch(self.session.headers["User-Agent"], url)

    def fetch(self, url: str) -> tuple[str, str, str]:
        if not self.allowed(url):
            return "", url, "blocked_by_robots"

        last_error = ""
        for attempt in range(self.retries + 1):
            if attempt > 0:
                time.sleep(self.delay_seconds)
            try:
                response = self.session.get(url, timeout=self.timeout_seconds)
                response.raise_for_status()
                time.sleep(self.delay_seconds)
                return response.text, response.url, "ok"
            except requests.RequestException as exc:
                last_error = str(exc)
        return "", url, f"error: {last_error}"


def build_empty_row(seed: SeedRecord) -> dict[str, object]:
    row: dict[str, object] = {column: "" for column in TARGET_COLUMNS}
    row.update(
        {
            "company_name": seed.company_hint or seed.company_name,
            "city": seed.city,
            "region": seed.region,
            "country": "Ukraine",
            "source_url": seed.source_url,
            "entry_channel": seed.source_type or "website",
            "score_manual": 0,
            "status": "new",
            "source_notes": _source_notes(seed),
        }
    )
    return row


def _candidate_pages(source_url: str) -> list[str]:
    if not source_url:
        return []
    root = source_url.rstrip("/")
    return [
        root,
        urljoin(root + "/", "contacts"),
        urljoin(root + "/", "about"),
    ]


def process_seed(seed: SeedRecord, client: WebClient) -> ScrapeResult:
    row = build_empty_row(seed)
    source = asdict(seed)
    logs: list[dict[str, object]] = []
    manual_queue: list[dict[str, object]] = []

    in_scope, scope_reason = classify_scope(seed.city, seed.region)
    if not in_scope:
        excluded_row = dict(row)
        excluded_row[EXCLUDED_REASON_COLUMN] = scope_reason
        return ScrapeResult(
            row=excluded_row,
            source=source,
            excluded=True,
            excluded_reason=scope_reason,
            logs=[{"uroven": "info", "sprava": f"Vylucene: {scope_reason}"}],
        )

    if not seed.source_url:
        row["fetch_status"] = "missing_url"
        row["error"] = "Chyba URL, potrebne manualne dohliadanie"
        row["next_action"] = "Doplnit web a preverit profil"
        manual_queue.append(
            {
                "company_name": row["company_name"],
                "city": row["city"],
                "region": row["region"],
                "missing_fields": "source_url; brands; contacts",
                "research_queries": f'{row["company_name"]} {row["city"]} dealer official site',
                "priority_level": "high",
            }
        )
        return ScrapeResult(row=row, source=source, manual_queue=manual_queue)

    pages = _candidate_pages(seed.source_url)[:3]
    all_text_parts: list[str] = []
    all_languages: list[str] = []
    all_emails: list[str] = []
    all_phones: list[str] = []
    merged_socials: dict[str, str] = {}
    final_url = seed.source_url
    fetch_status = "empty"
    page_errors: list[str] = []
    ok_pages = 0

    for page in pages:
        html, resolved_url, status = client.fetch(page)
        final_url = resolved_url or final_url
        logs.append({"uroven": "info", "sprava": f"{page} -> {status}"})
        if status != "ok" or not html:
            page_errors.append(f"{page}: {status}")
            continue

        ok_pages += 1
        fetch_status = "ok"
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)
        all_text_parts.append(text)
        all_languages.extend(extract_languages(soup, resolved_url))
        all_emails.extend(extract_emails(text))
        all_phones.extend(extract_phones(text))
        merged_socials.update(extract_social_links(soup, resolved_url))
        row["company_name"] = extract_company_name(soup, str(row["company_name"]), seed.source_url)

    seed_context = " ".join(
        [
            seed.company_hint,
            seed.company_name,
            seed.notes,
            seed.discovery_query,
            seed.discovery_provider,
        ]
    )
    combined_text = " ".join([seed_context, *all_text_parts])
    brands, has_chinese = extract_brands(combined_text)
    services = extract_services(combined_text)

    row["final_url"] = final_url
    row["fetch_status"] = "ok" if ok_pages else _final_fetch_status(fetch_status, page_errors)
    row["error"] = "; ".join(page_errors) if ok_pages and page_errors else row.get("error", "")
    row["brands"] = split_unique(brands)
    row["brand_count"] = len(brands)
    row["chinese_brand"] = yes_no(has_chinese)
    row["site_count"] = len(pages)
    row["services"] = split_unique(services)
    row["website_languages"] = split_unique(all_languages)
    row["emails"] = split_unique(all_emails)
    row["phones"] = split_unique(all_phones)
    row["social_links"] = summarize_social_links(merged_socials)
    row.update(merged_socials)
    row["linkedin_signal"] = "link_only" if row.get("linkedin_url") else "none"
    row["eu_footprint"] = yes_no(any(lang in {"en", "pl", "sk", "cs", "de", "hu", "ro"} for lang in all_languages))
    row["cross_border_evidence"] = "EU jazyk na webe" if row["eu_footprint"] == "yes" else ""
    row["entry_strength"] = "high" if len(brands) > 1 or row["eu_footprint"] == "yes" or _has_client_target_brand(brands) else "medium"
    row["intro_contact"] = row["emails"] or row["phones"]
    row["data_quality"] = _data_quality(row)
    row["red_flags"] = _red_flags(row)

    if _needs_manual_queue(row):
        manual_queue.append(
            {
                "company_name": row["company_name"],
                "city": row["city"],
                "region": row["region"],
                "missing_fields": _missing_fields(row),
                "research_queries": f'{row["company_name"]} owner OR founder OR contacts',
                "priority_level": "medium",
            }
        )

    compute_score(row)
    row["next_action"] = _next_action(row)
    return ScrapeResult(row=row, source=source, manual_queue=manual_queue, logs=logs)


def _data_quality(row: dict[str, object]) -> str:
    filled = 0
    for key in ("brands", "services", "emails", "phones", "website_languages", "social_links"):
        if row.get(key):
            filled += 1
    if filled >= 5:
        return "high"
    if filled >= 3:
        return "medium"
    return "low"


def _next_action(row: dict[str, object]) -> str:
    if not row.get("intro_contact"):
        return "Doplnit kontakt a preverit vlastnika"
    if _row_has_client_target_brand(row):
        return "Prioritne pripravit intro pre klientsky fit"
    if row.get("tier") == "A":
        return "Pripravit intro a manualne potvrdit rozhodovaca"
    return "Manualne preverit a doplnit signaly"


def _red_flags(row: dict[str, object]) -> str:
    flags: list[str] = []
    if row.get("fetch_status") not in {"ok", ""}:
        flags.append("problem_s_fetchom")
    if not row.get("emails") and not row.get("phones"):
        flags.append("chyba_kontakt")
    if not row.get("brands"):
        flags.append("chyba_znacka")
    return "; ".join(flags)


def _needs_manual_queue(row: dict[str, object]) -> bool:
    return bool(_missing_fields(row))


def _missing_fields(row: dict[str, object]) -> str:
    missing: list[str] = []
    for field in ("brands", "emails", "phones", "owner_name", "decision_power"):
        if not row.get(field):
            missing.append(field)
    return "; ".join(missing)


def _final_fetch_status(fetch_status: str, page_errors: list[str]) -> str:
    if not page_errors:
        return fetch_status
    if all("blocked_by_robots" in item for item in page_errors):
        return "blocked_by_robots"
    return page_errors[-1].split(": ", 1)[1]


def _has_client_target_brand(brands: list[str]) -> bool:
    return any(slugify_text(brand) in CLIENT_TARGET_BRANDS for brand in brands)


def _row_has_client_target_brand(row: dict[str, object]) -> bool:
    brands = [item for item in str(row.get("brands", "")).split("; ") if item]
    return _has_client_target_brand(brands)


def _source_notes(seed: SeedRecord) -> str:
    notes: list[str] = []
    if seed.notes:
        notes.append(seed.notes)
    if seed.discovery_provider:
        notes.append(f"provider={seed.discovery_provider}")
    if seed.discovery_query:
        notes.append(f"query={seed.discovery_query}")
    return "; ".join(notes)
