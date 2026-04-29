"""Autonomne objavovanie kandidatov z verejnych zdrojov."""

from __future__ import annotations

from dataclasses import asdict
from urllib.parse import quote_plus, urljoin, urlparse

from bs4 import BeautifulSoup

from ua_dealer_intel.constants import (
    DISCOVERY_BLOCKLIST_HOSTS,
    DISCOVERY_CITY_VARIANTS,
    DISCOVERY_LOCATIONS,
    DISCOVERY_OFFICIAL_SOURCES,
    DISCOVERY_PROVIDERS,
)
from ua_dealer_intel.geo import classify_scope
from ua_dealer_intel.models import SeedRecord
from ua_dealer_intel.utils import clean_url, domain_from_url, normalize_text, slugify_text


def discover_seed_records(
    fetcher: object,
    limit: int = 25,
    existing_seeds: list[SeedRecord] | None = None,
) -> tuple[list[SeedRecord], list[dict[str, object]]]:
    results: list[SeedRecord] = []
    logs: list[dict[str, object]] = []
    seen_domains = {domain_from_url(seed.source_url) for seed in (existing_seeds or []) if seed.source_url}

    official_records, official_logs = discover_from_official_sources(fetcher, seen_domains)
    logs.extend(official_logs)
    for record in official_records:
        domain = domain_from_url(record.source_url)
        if not domain or domain in seen_domains:
            if domain:
                logs.append(
                    {
                        "uroven": "info",
                        "sprava": f"Official discovery preskakuje duplicitu domeny: {domain}",
                    }
                )
            continue
        seen_domains.add(domain)
        results.append(record)
        logs.append(
            {
                "uroven": "info",
                "sprava": f"Official discovery pridal kandidata: {record.company_hint} ({record.source_url})",
            }
        )
        if len(results) >= limit:
            return results, logs

    for location in DISCOVERY_LOCATIONS:
        city = str(location["city"])
        region = str(location["region"])
        for query in location["queries"]:
            if len(results) >= limit:
                return results, logs

            provider_records: list[SeedRecord] = []
            provider_used = ""
            for provider in DISCOVERY_PROVIDERS:
                provider_name = str(provider["name"])
                provider_used = provider_name
                search_url = str(provider["url_template"]).format(query=quote_plus(query))
                html, _, status = fetcher.fetch(search_url)
                logs.append(
                    {
                        "uroven": "info",
                        "sprava": f"Discovery query '{query}' cez {provider_name}: {status}",
                    }
                )
                if status != "ok" or not html:
                    continue

                provider_records, provider_stats = parse_discovery_results_detailed(
                    html=html,
                    provider_name=provider_name,
                    city=city,
                    region=region,
                    query=query,
                )
                logs.append(
                    {
                        "uroven": "info",
                        "sprava": (
                            f"Discovery query '{query}' cez {provider_name}: "
                            f"parser nasiel {provider_stats['raw_candidates']} kandidatov, "
                            f"prijal {provider_stats['accepted_candidates']}"
                        ),
                    }
                )
                if provider_stats["sample_urls"]:
                    logs.append(
                        {
                            "uroven": "info",
                            "sprava": f"Discovery sample URL pre '{query}': {provider_stats['sample_urls']}",
                        }
                    )
                if provider_records:
                    break

            if not provider_records:
                if provider_used:
                    logs.append(
                        {
                            "uroven": "warning",
                            "sprava": f"Discovery query '{query}' nepriniesla ziadne vysledky",
                        }
                    )
                continue

            for record in provider_records:
                domain = domain_from_url(record.source_url)
                if not domain:
                    logs.append(
                        {
                            "uroven": "warning",
                            "sprava": f"Discovery query '{query}' vratila zaznam bez domeny: {record.source_url}",
                        }
                    )
                    continue
                if domain in seen_domains:
                    logs.append(
                        {
                            "uroven": "info",
                            "sprava": f"Discovery query '{query}' preskakuje duplicitu: {domain}",
                        }
                    )
                    continue
                seen_domains.add(domain)
                results.append(record)
                logs.append(
                    {
                        "uroven": "info",
                        "sprava": f"Objaveny kandidat: {record.company_hint or record.company_name} ({record.source_url})",
                    }
                )
                if len(results) >= limit:
                    return results, logs

    return results, logs


def discover_from_official_sources(
    fetcher: object,
    seen_domains: set[str] | None = None,
) -> tuple[list[SeedRecord], list[dict[str, object]]]:
    records: list[SeedRecord] = []
    logs: list[dict[str, object]] = []
    local_seen = set(seen_domains or set())

    for source in DISCOVERY_OFFICIAL_SOURCES:
        url = str(source["url"])
        html, _, status = fetcher.fetch(url)
        logs.append(
            {
                "uroven": "info",
                "sprava": f"Official discovery source {source['name']}: {status}",
            }
        )
        if status != "ok" or not html:
            continue

        parsed_records, source_stats = parse_official_directory_detailed(
            html=html,
            page_url=url,
            provider_name=str(source["name"]),
            parser_name=str(source["parser"]),
            brand=str(source["brand"]),
        )
        logs.append(
            {
                "uroven": "info",
                "sprava": (
                    f"Official source {source['name']} parser nasiel {source_stats['raw_candidates']} kandidatov, "
                    f"prijal {source_stats['accepted_candidates']}"
                ),
            }
        )
        if source_stats["sample_urls"]:
            logs.append(
                {
                    "uroven": "info",
                    "sprava": f"Official source {source['name']} sample URL: {source_stats['sample_urls']}",
                }
            )
        for record in parsed_records:
            domain = domain_from_url(record.source_url)
            if not domain or domain in local_seen:
                if domain:
                    logs.append(
                        {
                            "uroven": "info",
                            "sprava": f"Official source {source['name']} preskakuje duplicitu: {domain}",
                        }
                    )
                continue
            local_seen.add(domain)
            records.append(record)
    return records, logs


def parse_discovery_results(
    html: str,
    provider_name: str,
    city: str,
    region: str,
    query: str,
) -> list[SeedRecord]:
    items, _ = parse_discovery_results_detailed(html, provider_name, city, region, query)
    return items


def parse_discovery_results_detailed(
    html: str,
    provider_name: str,
    city: str,
    region: str,
    query: str,
) -> tuple[list[SeedRecord], dict[str, object]]:
    soup = BeautifulSoup(html, "html.parser")
    if provider_name == "duckduckgo_html":
        items, stats = _parse_duckduckgo(soup, city, region, query, provider_name)
    elif provider_name == "bing":
        items, stats = _parse_bing(soup, city, region, query, provider_name)
    else:
        items, stats = [], _empty_discovery_stats()
    return items, stats


def parse_official_directory(
    html: str,
    page_url: str,
    provider_name: str,
    parser_name: str,
    brand: str,
) -> list[SeedRecord]:
    items, _ = parse_official_directory_detailed(html, page_url, provider_name, parser_name, brand)
    return items


def parse_official_directory_detailed(
    html: str,
    page_url: str,
    provider_name: str,
    parser_name: str,
    brand: str,
) -> tuple[list[SeedRecord], dict[str, object]]:
    soup = BeautifulSoup(html, "html.parser")
    if parser_name == "toyota_listing":
        return _parse_toyota_listing(soup, page_url, provider_name, brand)
    if parser_name == "renault_listing":
        return _parse_renault_listing(soup, page_url, provider_name, brand)
    if parser_name == "opel_listing":
        return _parse_opel_listing(soup, page_url, provider_name, brand)
    return [], _empty_discovery_stats()


def _parse_duckduckgo(
    soup: BeautifulSoup,
    city: str,
    region: str,
    query: str,
    provider_name: str,
) -> list[SeedRecord]:
    records: list[SeedRecord] = []
    stats = _empty_discovery_stats()
    for anchor in soup.select("a.result__a"):
        stats["raw_candidates"] += 1
        href = clean_url(anchor.get("href", ""))
        company = _normalize_result_title(anchor.get_text(" ", strip=True))
        record = _build_discovery_record(href, company, city, region, query, provider_name)
        if record:
            records.append(record)
            stats["accepted_candidates"] += 1
            _add_sample_url(stats, record.source_url)
    return records, stats


def _parse_bing(
    soup: BeautifulSoup,
    city: str,
    region: str,
    query: str,
    provider_name: str,
) -> list[SeedRecord]:
    records: list[SeedRecord] = []
    stats = _empty_discovery_stats()
    for item in soup.select("li.b_algo h2 a"):
        stats["raw_candidates"] += 1
        href = clean_url(item.get("href", ""))
        company = _normalize_result_title(item.get_text(" ", strip=True))
        record = _build_discovery_record(href, company, city, region, query, provider_name)
        if record:
            records.append(record)
            stats["accepted_candidates"] += 1
            _add_sample_url(stats, record.source_url)
    return records, stats


def _parse_toyota_listing(
    soup: BeautifulSoup,
    page_url: str,
    provider_name: str,
    brand: str,
) -> list[SeedRecord]:
    records: list[SeedRecord] = []
    stats = _empty_discovery_stats()
    for anchor in soup.find_all("a", href=True):
        anchor_text = normalize_text(anchor.get_text(" ", strip=True)).lower()
        if "перейти на сайт" not in anchor_text:
            continue
        stats["raw_candidates"] += 1
        title_tag = anchor.find_previous(["h2", "h3", "h4"])
        block_text = normalize_text(anchor.parent.get_text(" ", strip=True) if anchor.parent else "")
        location = _match_location_from_text(block_text)
        if not location or not title_tag:
            continue
        city, region = location
        record = _build_discovery_record(
            href=urljoin(page_url, anchor["href"]),
            company=f"{title_tag.get_text(' ', strip=True)} [{brand}]",
            city=city,
            region=region,
            query=f"official:{brand}",
            provider_name=provider_name,
        )
        if record:
            records.append(record)
            stats["accepted_candidates"] += 1
            _add_sample_url(stats, record.source_url)
    return records, stats


def _parse_renault_listing(
    soup: BeautifulSoup,
    page_url: str,
    provider_name: str,
    brand: str,
) -> list[SeedRecord]:
    records: list[SeedRecord] = []
    stats = _empty_discovery_stats()
    for anchor in soup.find_all("a", href=True):
        anchor_text = normalize_text(anchor.get_text(" ", strip=True)).lower()
        if "веб-сайт" not in anchor_text:
            continue
        stats["raw_candidates"] += 1
        parent_text = normalize_text(anchor.parent.get_text(" ", strip=True)) if anchor.parent else ""
        location = _match_location_from_text(parent_text)
        if not location:
            continue
        city, region = location
        company = _extract_company_from_block(parent_text, city)
        record = _build_discovery_record(
            href=urljoin(page_url, anchor["href"]),
            company=f"{company} [{brand}]",
            city=city,
            region=region,
            query=f"official:{brand}",
            provider_name=provider_name,
        )
        if record:
            records.append(record)
            stats["accepted_candidates"] += 1
            _add_sample_url(stats, record.source_url)
    return records, stats


def _parse_opel_listing(
    soup: BeautifulSoup,
    page_url: str,
    provider_name: str,
    brand: str,
) -> list[SeedRecord]:
    records: list[SeedRecord] = []
    stats = _empty_discovery_stats()
    for row in soup.find_all("tr"):
        city_heading = row.find_previous(["h2", "h3", "h4"])
        row_text = normalize_text(
            f"{city_heading.get_text(' ', strip=True) if city_heading else ''} {row.get_text(' ', strip=True)}"
        )
        location = _match_location_from_text(row_text)
        if not location:
            continue
        link = row.find("a", href=True)
        if not link:
            continue
        stats["raw_candidates"] += 1
        cells = row.find_all(["td", "th"])
        if not cells:
            continue
        company = normalize_text(cells[0].get_text(" ", strip=True))
        city, region = location
        record = _build_discovery_record(
            href=urljoin(page_url, link["href"]),
            company=f"{company} [{brand}]",
            city=city,
            region=region,
            query=f"official:{brand}",
            provider_name=provider_name,
        )
        if record:
            records.append(record)
            stats["accepted_candidates"] += 1
            _add_sample_url(stats, record.source_url)
    return records, stats


def _build_discovery_record(
    href: str,
    company: str,
    city: str,
    region: str,
    query: str,
    provider_name: str,
) -> SeedRecord | None:
    parsed = urlparse(href)
    host = parsed.netloc.lower().removeprefix("www.")
    if not href or parsed.scheme not in {"http", "https"}:
        return None
    if not host or any(blocked in host for blocked in DISCOVERY_BLOCKLIST_HOSTS):
        return None
    if href.startswith("mailto:") or href.startswith("tel:"):
        return None
    if not classify_scope(city, region)[0]:
        return None
    return SeedRecord(
        source_url=_normalize_source_url(href),
        company_hint=company,
        city=city,
        region=region,
        source_type="discovered_search",
        notes=f"Autonomne objavene cez query '{query}'",
        discovery_query=query,
        discovery_provider=provider_name,
    )


def _normalize_result_title(title: str) -> str:
    normalized = normalize_text(title)
    for separator in ("|", " - ", " — ", " :: "):
        if separator in normalized:
            normalized = normalized.split(separator, 1)[0]
    return normalize_text(normalized)


def _normalize_source_url(url: str) -> str:
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    if parsed.path and parsed.path != "/":
        return urljoin(base, parsed.path)
    return base


def _match_location_from_text(text: str) -> tuple[str, str] | None:
    haystack = slugify_text(text)
    for location in DISCOVERY_LOCATIONS:
        city = str(location["city"])
        region = str(location["region"])
        variants = DISCOVERY_CITY_VARIANTS.get(city, [city.lower()])
        if any(variant in haystack for variant in variants):
            return city, region
    return None


def _extract_company_from_block(text: str, city: str) -> str:
    normalized = normalize_text(text)
    city_variants = DISCOVERY_CITY_VARIANTS.get(city, [city.lower()])
    lines = [normalize_text(part) for part in normalized.splitlines() if normalize_text(part)]
    if len(lines) <= 1:
        lines = [normalize_text(part) for part in normalized.split("  ") if normalize_text(part)]
    for line in lines:
        line_slug = slugify_text(line)
        if any(variant in line_slug for variant in city_variants):
            continue
        if "веб-сайт" in line_slug:
            continue
        if any(char.isalpha() for char in line):
            return line
    return city


def _empty_discovery_stats() -> dict[str, object]:
    return {
        "raw_candidates": 0,
        "accepted_candidates": 0,
        "sample_urls": "",
    }


def _add_sample_url(stats: dict[str, object], url: str) -> None:
    existing = str(stats["sample_urls"])
    urls = [item for item in existing.split("; ") if item]
    if url not in urls and len(urls) < 3:
        urls.append(url)
    stats["sample_urls"] = "; ".join(urls)
