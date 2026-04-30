"""Autonomne objavovanie kandidatov z verejnych zdrojov."""

from __future__ import annotations

import json
import html as html_lib
import re
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


SAME_HOST_DETAIL_PROVIDERS = {
    "automoto_dongfeng",
    "automoto_forthing",
    "automoto_voyah",
    "chery_ua",
    "haval_gwm_ua",
    "mg_ua",
}

WESTMOTORS_TARGET_CITY_HOSTS = {
    "Lviv": ("Lvivska", "lviv.westmotors.com.ua"),
    "Ivano-Frankivsk": ("Ivano-Frankivska", "ivano.westmotors.com.ua"),
    "Chernivtsi": ("Chernivetska", "chernivtsi.westmotors.com.ua"),
}

KNOWN_TARGET_BRAND_SOURCES = {
    "electro_mobility_voyah": {
        "company": "Electro Mobility [Voyah]",
        "city": "Kyiv",
        "region": "Kyivska",
        "query": "public:Voyah",
    }
}


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
        seen_key = _discovery_seen_key(record.source_url, record.discovery_provider)
        if not seen_key or seen_key in seen_domains:
            if seen_key:
                logs.append(
                    {
                        "uroven": "info",
                        "sprava": f"Discovery zdroj preskakuje duplicitu: {seen_key}",
                    }
                )
            continue
        seen_domains.add(seen_key)
        results.append(record)
        logs.append(
            {
                "uroven": "info",
                "sprava": f"Discovery zdroj pridal kandidata: {record.company_hint} ({record.source_url})",
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
                seen_key = _discovery_seen_key(record.source_url, record.discovery_provider)
                if not seen_key:
                    logs.append(
                        {
                            "uroven": "warning",
                            "sprava": f"Discovery query '{query}' vratila zaznam bez domeny: {record.source_url}",
                        }
                    )
                    continue
                if seen_key in seen_domains:
                    logs.append(
                        {
                            "uroven": "info",
                            "sprava": f"Discovery query '{query}' preskakuje duplicitu: {seen_key}",
                        }
                    )
                    continue
                seen_domains.add(seen_key)
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
                "sprava": f"Zdroj objavovania {source['name']}: {status}",
            }
        )
        if status != "ok" or not html:
            continue

        if source["parser"] == "hyundai_listing":
            parsed_records, source_stats = parse_hyundai_directory_detailed(
                html=html,
                page_url=url,
                provider_name=str(source["name"]),
                brand=str(source["brand"]),
                fetcher=fetcher,
            )
        else:
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
                    f"Zdroj objavovania {source['name']} parser nasiel {source_stats['raw_candidates']} kandidatov, "
                    f"prijal {source_stats['accepted_candidates']}"
                ),
            }
        )
        if source_stats["sample_urls"]:
            logs.append(
                {
                    "uroven": "info",
                    "sprava": f"Zdroj objavovania {source['name']} ukazkova URL: {source_stats['sample_urls']}",
                }
            )
        for record in parsed_records:
            seen_key = _discovery_seen_key(record.source_url, str(source["name"]))
            if not seen_key or seen_key in local_seen:
                if seen_key:
                    logs.append(
                        {
                            "uroven": "info",
                            "sprava": f"Zdroj objavovania {source['name']} preskakuje duplicitu: {seen_key}",
                        }
                    )
                continue
            local_seen.add(seen_key)
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
    if parser_name == "kia_api":
        return _parse_kia_api(html, provider_name, brand)
    if parser_name == "mitsubishi_listing":
        return _parse_mitsubishi_listing(html, provider_name, brand)

    soup = BeautifulSoup(html, "html.parser")
    if parser_name == "toyota_listing":
        return _parse_toyota_listing(soup, page_url, provider_name, brand)
    if parser_name == "renault_listing":
        return _parse_renault_listing(soup, page_url, provider_name, brand)
    if parser_name == "opel_listing":
        return _parse_opel_listing(soup, page_url, provider_name, brand)
    if parser_name == "city_first_table":
        return _parse_city_first_table_listing(soup, page_url, provider_name, brand)
    if parser_name == "hyundai_listing":
        return _parse_hyundai_listing_without_detail(html, page_url, provider_name, brand)
    if parser_name == "ford_listing":
        return _parse_ford_listing(soup, page_url, provider_name, brand)
    if parser_name == "chery_regions":
        return _parse_chery_region_blocks(soup, page_url, provider_name, brand)
    if parser_name == "mg_table":
        return _parse_mg_table_listing(soup, page_url, provider_name, brand)
    if parser_name == "haval_cards":
        return _parse_haval_cards(soup, page_url, provider_name, brand)
    if parser_name == "automoto_brand_directory":
        return _parse_automoto_brand_directory(soup, page_url, provider_name, brand)
    if parser_name == "westmotors_target_brands":
        return _parse_westmotors_target_brands(soup, page_url, provider_name, brand)
    if parser_name == "known_target_brand_source":
        return _parse_known_target_brand_source(page_url, provider_name, brand)
    return [], _empty_discovery_stats()


def _parse_duckduckgo(
    soup: BeautifulSoup,
    city: str,
    region: str,
    query: str,
    provider_name: str,
) -> tuple[list[SeedRecord], dict[str, object]]:
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
) -> tuple[list[SeedRecord], dict[str, object]]:
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
) -> tuple[list[SeedRecord], dict[str, object]]:
    records: list[SeedRecord] = []
    stats = _empty_discovery_stats()
    for anchor in soup.find_all("a", href=True):
        if not _is_toyota_website_link(anchor):
            continue
        stats["raw_candidates"] += 1
        title_tag = anchor.find_previous(["h2", "h3", "h4"])
        company = normalize_text(
            str(anchor.get("data-gt-dealername") or title_tag.get_text(" ", strip=True) if title_tag else "")
        )
        location_text = normalize_text(
            " ".join(
                [
                    str(anchor.get("data-gt-dealercity") or ""),
                    str(anchor.get("data-gt-dealerregion") or ""),
                    _collect_dealer_block_before_anchor(anchor),
                ]
            )
        )
        location = _match_location_from_text(location_text)
        if not location:
            continue
        city, region = location
        record = _build_discovery_record(
            href=urljoin(page_url, str(anchor["href"])),
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


def _parse_renault_listing(
    soup: BeautifulSoup,
    page_url: str,
    provider_name: str,
    brand: str,
) -> tuple[list[SeedRecord], dict[str, object]]:
    json_records, json_stats = _parse_renault_jsonld(soup, provider_name, brand)
    if json_stats["raw_candidates"]:
        return json_records, json_stats

    records: list[SeedRecord] = []
    stats = _empty_discovery_stats()
    for anchor in soup.find_all("a", href=True):
        company = normalize_text(anchor.get_text(" ", strip=True))
        href = clean_url(urljoin(page_url, anchor["href"]))
        if not _looks_like_external_dealer_site(href, page_url):
            continue
        if _is_navigation_label(company):
            continue
        stats["raw_candidates"] += 1
        block_text = _collect_text_after_anchor(anchor)
        location = _match_location_from_text(block_text)
        if not location:
            continue
        city, region = location
        record = _build_discovery_record(
            href=href,
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


def _parse_renault_jsonld(
    soup: BeautifulSoup,
    provider_name: str,
    brand: str,
) -> tuple[list[SeedRecord], dict[str, object]]:
    records: list[SeedRecord] = []
    stats = _empty_discovery_stats()
    for item in _iter_jsonld_objects(soup):
        if item.get("@type") != "AutomotiveBusiness":
            continue
        stats["raw_candidates"] += 1
        address = item.get("address") if isinstance(item.get("address"), dict) else {}
        location_text = normalize_text(
            " ".join(
                [
                    str(address.get("addressLocality") or ""),
                    str(address.get("streetAddress") or ""),
                ]
            )
        )
        location = _match_location_from_text(location_text)
        if not location:
            continue
        city, region = location
        record = _build_discovery_record(
            href=str(item.get("url") or item.get("@id") or ""),
            company=f"{normalize_text(str(item.get('name') or city))} [{brand}]",
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
) -> tuple[list[SeedRecord], dict[str, object]]:
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


def _parse_city_first_table_listing(
    soup: BeautifulSoup,
    page_url: str,
    provider_name: str,
    brand: str,
) -> tuple[list[SeedRecord], dict[str, object]]:
    records: list[SeedRecord] = []
    stats = _empty_discovery_stats()
    for row in soup.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) < 2:
            continue
        city_text = normalize_text(cells[0].get_text(" ", strip=True))
        company = normalize_text(cells[1].get_text(" ", strip=True))
        row_text = normalize_text(row.get_text(" ", strip=True))
        link = row.find("a", href=True)
        if not link:
            continue

        stats["raw_candidates"] += 1
        location = _match_location_from_text(f"{city_text} {row_text}")
        if not location:
            continue
        city, region = location
        record = _build_discovery_record(
            href=urljoin(page_url, str(link["href"])),
            company=f"{company or city} [{brand}]",
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


def _parse_kia_api(
    raw_json: str,
    provider_name: str,
    brand: str,
) -> tuple[list[SeedRecord], dict[str, object]]:
    records: list[SeedRecord] = []
    stats = _empty_discovery_stats()
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError:
        return records, stats

    rows = payload.get("dataInfo")
    if not isinstance(rows, list):
        return records, stats

    for row in rows:
        if not isinstance(row, dict):
            continue
        stats["raw_candidates"] += 1
        location_text = normalize_text(f"{row.get('city') or ''} {row.get('addr') or ''}")
        location = _match_location_from_text(location_text)
        if not location:
            continue
        city, region = location
        record = _build_discovery_record(
            href=str(row.get("url") or ""),
            company=f"{normalize_text(str(row.get('dealerNm') or city))} [{brand}]",
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


def parse_hyundai_directory_detailed(
    html: str,
    page_url: str,
    provider_name: str,
    brand: str,
    fetcher: object,
) -> tuple[list[SeedRecord], dict[str, object]]:
    records: list[SeedRecord] = []
    stats = _empty_discovery_stats()
    city_map = _extract_hyundai_city_map(html)
    dealers = _extract_hyundai_dealers(html)

    for city_id, city_dealers in dealers.items():
        city_name = city_map.get(str(city_id), "")
        location = _match_location_from_text(city_name)
        if not location or not isinstance(city_dealers, dict):
            stats["raw_candidates"] += len(city_dealers) if isinstance(city_dealers, dict) else 0
            continue
        city, region = location
        for dealer in city_dealers.values():
            if not isinstance(dealer, dict):
                continue
            stats["raw_candidates"] += 1
            nid = str(dealer.get("nid") or "")
            company = normalize_text(str(dealer.get("title") or city))
            href = _fetch_hyundai_dealer_site(fetcher, page_url, nid)
            if not href:
                continue
            record = _build_discovery_record(
                href=href,
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


def _parse_hyundai_listing_without_detail(
    html: str,
    page_url: str,
    provider_name: str,
    brand: str,
) -> tuple[list[SeedRecord], dict[str, object]]:
    records: list[SeedRecord] = []
    stats = _empty_discovery_stats()
    city_map = _extract_hyundai_city_map(html)
    dealers = _extract_hyundai_dealers(html)

    for city_id, city_dealers in dealers.items():
        city_name = city_map.get(str(city_id), "")
        location = _match_location_from_text(city_name)
        if not isinstance(city_dealers, dict):
            continue
        stats["raw_candidates"] += len(city_dealers)
        if not location:
            continue
        city, region = location
        for dealer in city_dealers.values():
            if not isinstance(dealer, dict):
                continue
            nid = str(dealer.get("nid") or "")
            if not nid:
                continue
            record = _build_discovery_record(
                href=urljoin(page_url, f"/node/{nid}"),
                company=f"{normalize_text(str(dealer.get('title') or city))} [{brand}]",
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


def _parse_mitsubishi_listing(
    html: str,
    provider_name: str,
    brand: str,
) -> tuple[list[SeedRecord], dict[str, object]]:
    records: list[SeedRecord] = []
    stats = _empty_discovery_stats()
    dealers = _extract_mitsubishi_dealers(html)

    for dealer in dealers:
        if not isinstance(dealer, dict):
            continue
        stats["raw_candidates"] += 1
        location_text = normalize_text(f"{dealer.get('city_name') or ''} {dealer.get('address') or ''}")
        location = _match_location_from_text(location_text)
        if not location:
            continue
        city, region = location
        record = _build_discovery_record(
            href=str(dealer.get("website_link") or ""),
            company=f"{normalize_text(str(dealer.get('title') or city))} [{brand}]",
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


def _parse_ford_listing(
    soup: BeautifulSoup,
    page_url: str,
    provider_name: str,
    brand: str,
) -> tuple[list[SeedRecord], dict[str, object]]:
    records: list[SeedRecord] = []
    stats = _empty_discovery_stats()
    cards = soup.select("#dealer-list > div[id^='dealer-']") or soup.select("div[id^='dealer-']")

    for card in cards:
        stats["raw_candidates"] += 1
        card_text = normalize_text(card.get_text(" ", strip=True))
        location = _match_location_from_text(card_text)
        if not location:
            continue

        website = _extract_first_external_link(str(card), page_url)
        if not website:
            continue

        company_tag = card.find(lambda tag: _has_classes(tag, {"text-darkBlue", "uppercase"}))
        company = normalize_text(company_tag.get_text(" ", strip=True)) if company_tag else ""
        city, region = location
        record = _build_discovery_record(
            href=website,
            company=f"{company or city} [{brand}]",
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


def _parse_mg_table_listing(
    soup: BeautifulSoup,
    page_url: str,
    provider_name: str,
    brand: str,
) -> tuple[list[SeedRecord], dict[str, object]]:
    records: list[SeedRecord] = []
    stats = _empty_discovery_stats()

    for row in soup.find_all("tr"):
        dealer_link = row.find("a", href=True)
        if not dealer_link:
            continue

        stats["raw_candidates"] += 1
        row_text = normalize_text(row.get_text(" ", strip=True))
        location = _match_location_from_text(row_text)
        if not location:
            continue

        city, region = location
        raw_company = _best_anchor_label(dealer_link)
        company = _remove_city_prefix(raw_company, city) or city
        record = _build_discovery_record(
            href=urljoin(page_url, str(dealer_link["href"])),
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


def _parse_chery_region_blocks(
    soup: BeautifulSoup,
    page_url: str,
    provider_name: str,
    brand: str,
) -> tuple[list[SeedRecord], dict[str, object]]:
    records: list[SeedRecord] = []
    stats = _empty_discovery_stats()
    region_links = _extract_chery_region_links(soup, page_url)

    for region_block in soup.select("div.l_d_m"):
        region_heading = region_block.find("h3")
        region_name = normalize_text(region_heading.get_text(" ", strip=True)) if region_heading else ""
        fallback_url = region_links.get(region_name, page_url)
        for dealer in region_block.select("div.dealer"):
            stats["raw_candidates"] += 1
            dealer_text = normalize_text(dealer.get_text(" ", strip=True))
            location = _match_location_from_text(dealer_text)
            if not location:
                continue

            city, region = location
            company_tag = dealer.select_one(".left_info h3")
            company = normalize_text(company_tag.get_text(" ", strip=True)) if company_tag else city
            href = _extract_first_external_link(str(dealer), page_url) or fallback_url
            record = _build_discovery_record(
                href=href,
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


def _parse_haval_cards(
    soup: BeautifulSoup,
    page_url: str,
    provider_name: str,
    brand: str,
) -> tuple[list[SeedRecord], dict[str, object]]:
    records: list[SeedRecord] = []
    stats = _empty_discovery_stats()

    for card in soup.select(".uk-card"):
        title = card.select_one("h4.uk-card-title")
        detail_link = card.select_one("a.uk-button[href]")
        if not title or not detail_link:
            continue

        stats["raw_candidates"] += 1
        card_text = normalize_text(card.get_text(" ", strip=True))
        location = _match_location_from_text(card_text)
        if not location:
            continue

        city, region = location
        company = normalize_text(title.get_text(" ", strip=True))
        record = _build_discovery_record(
            href=urljoin(page_url, str(detail_link["href"])),
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


def _parse_automoto_brand_directory(
    soup: BeautifulSoup,
    page_url: str,
    provider_name: str,
    brand: str,
) -> tuple[list[SeedRecord], dict[str, object]]:
    records: list[SeedRecord] = []
    stats = _empty_discovery_stats()
    seen_links: set[str] = set()

    for dealer_link in soup.select("div.card-name a[href*='/avtosalony/view/']"):
        href = clean_url(urljoin(page_url, str(dealer_link["href"])))
        if href in seen_links:
            continue
        seen_links.add(href)
        stats["raw_candidates"] += 1

        card = dealer_link.find_parent(lambda tag: tag.name == "div" and "card" in tag.get("class", []))
        card_text = normalize_text(card.get_text(" ", strip=True) if card else dealer_link.get_text(" ", strip=True))
        location = _match_location_from_text(card_text)
        if not location:
            continue

        city, region = location
        company = _clean_automoto_company(dealer_link.get_text(" ", strip=True)) or city
        record = _build_discovery_record(
            href=href,
            company=f"{company} [{brand}]",
            city=city,
            region=region,
            query=f"public:AutoMoto:{brand}",
            provider_name=provider_name,
        )
        if record:
            records.append(record)
            stats["accepted_candidates"] += 1
            _add_sample_url(stats, record.source_url)
    return records, stats


def _parse_westmotors_target_brands(
    soup: BeautifulSoup,
    page_url: str,
    provider_name: str,
    brand: str,
) -> tuple[list[SeedRecord], dict[str, object]]:
    records: list[SeedRecord] = []
    stats = _empty_discovery_stats()
    parsed_page = urlparse(page_url)
    target_path = parsed_page.path.rstrip("/")
    found_hosts: dict[str, str] = {}

    for anchor in soup.find_all("a", href=True):
        href = clean_url(urljoin(page_url, str(anchor["href"])))
        host = domain_from_url(href)
        for city, (_, expected_host) in WESTMOTORS_TARGET_CITY_HOSTS.items():
            if host == expected_host:
                found_hosts[city] = expected_host

    for city, host in found_hosts.items():
        stats["raw_candidates"] += 1
        region = WESTMOTORS_TARGET_CITY_HOSTS[city][0]
        href = f"{parsed_page.scheme or 'https'}://{host}{target_path}"
        record = _build_discovery_record(
            href=href,
            company=f"WESTMOTORS {city} [{brand}]",
            city=city,
            region=region,
            query=f"public:WestMotors:{brand}",
            provider_name=provider_name,
        )
        if record:
            records.append(record)
            stats["accepted_candidates"] += 1
            _add_sample_url(stats, record.source_url)
    return records, stats


def _parse_known_target_brand_source(
    page_url: str,
    provider_name: str,
    brand: str,
) -> tuple[list[SeedRecord], dict[str, object]]:
    stats = _empty_discovery_stats()
    source = KNOWN_TARGET_BRAND_SOURCES.get(provider_name)
    if not source:
        return [], stats

    stats["raw_candidates"] = 1
    record = _build_discovery_record(
        href=page_url,
        company=str(source["company"]),
        city=str(source["city"]),
        region=str(source["region"]),
        query=str(source.get("query") or f"public:{brand}"),
        provider_name=provider_name,
        allow_out_of_scope=True,
    )
    if not record:
        return [], stats

    stats["accepted_candidates"] = 1
    _add_sample_url(stats, record.source_url)
    return [record], stats


def _build_discovery_record(
    href: str,
    company: str,
    city: str,
    region: str,
    query: str,
    provider_name: str,
    allow_out_of_scope: bool = False,
) -> SeedRecord | None:
    parsed = urlparse(href)
    host = parsed.netloc.lower().removeprefix("www.")
    if not href or parsed.scheme not in {"http", "https"}:
        return None
    if not host or any(blocked in host for blocked in DISCOVERY_BLOCKLIST_HOSTS):
        return None
    if href.startswith("mailto:") or href.startswith("tel:"):
        return None
    if not allow_out_of_scope and not classify_scope(city, region)[0]:
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


def _discovery_seen_key(source_url: str, provider_name: str = "") -> str:
    domain = domain_from_url(source_url)
    if not domain:
        return ""
    if provider_name in SAME_HOST_DETAIL_PROVIDERS:
        parsed = urlparse(source_url)
        path = parsed.path.rstrip("/")
        if path:
            return f"{domain}{path}"
    return domain


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
        if any(_contains_location_variant(haystack, variant) for variant in variants):
            return city, region
    return None


def _contains_location_variant(haystack: str, variant: str) -> bool:
    normalized_variant = slugify_text(variant)
    if not normalized_variant:
        return False
    return re.search(rf"(?<![\w-]){re.escape(normalized_variant)}(?![\w-])", haystack) is not None


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


def _remove_city_prefix(value: str, city: str) -> str:
    company = normalize_text(value)
    for variant in sorted(DISCOVERY_CITY_VARIANTS.get(city, [city.lower()]), key=len, reverse=True):
        company = re.sub(rf"^\s*{re.escape(variant)}\s+", "", company, flags=re.IGNORECASE)
    return normalize_text(company)


def _clean_automoto_company(value: str) -> str:
    company = normalize_text(value)
    company = re.sub(r"^\s*Автосалон\s*", "", company, flags=re.IGNORECASE)
    return normalize_text(company.strip(" \"'“”«»"))


def _extract_chery_region_links(soup: BeautifulSoup, page_url: str) -> dict[str, str]:
    links: dict[str, str] = {}
    for anchor in soup.find_all("a", href=True):
        label = normalize_text(anchor.get_text(" ", strip=True))
        href = str(anchor.get("href") or "")
        if label and "/autosalon/" in href:
            links[label] = _normalize_source_url(urljoin(page_url, href))
    return links


def _best_anchor_label(anchor: object) -> str:
    title = normalize_text(str(anchor.get("title") or ""))
    text = normalize_text(anchor.get_text(" ", strip=True))
    return text if len(text) > len(title) else title


def _collect_dealer_block_after_heading(title_tag: object) -> tuple[str, str]:
    text_parts = [normalize_text(title_tag.get_text(" ", strip=True))]
    link = ""
    for sibling in title_tag.find_all_next():
        if sibling is not title_tag and sibling.name in {"h2", "h3"}:
            break
        text_parts.append(normalize_text(sibling.get_text(" ", strip=True)))
        if sibling.name == "a" and sibling.get("href") and not link:
            href = clean_url(str(sibling["href"]))
            if _looks_like_dealer_href(href):
                link = href
    return normalize_text(" ".join(text_parts)), link


def _collect_dealer_block_before_anchor(anchor: object) -> str:
    title_tag = anchor.find_previous(["h2", "h3", "h4"])
    if not title_tag:
        return ""
    text_parts = [normalize_text(title_tag.get_text(" ", strip=True))]
    for sibling in title_tag.find_all_next():
        if sibling is not title_tag and sibling.name == "a" and sibling is anchor:
            break
        if sibling is not title_tag and sibling.name in {"h2", "h3", "h4"}:
            break
        text_parts.append(normalize_text(sibling.get_text(" ", strip=True)))
    return normalize_text(" ".join(text_parts))


def _collect_text_after_anchor(anchor: object, max_parts: int = 10) -> str:
    text_parts = [normalize_text(anchor.get_text(" ", strip=True))]
    parts_seen = 0
    for sibling in anchor.find_all_next():
        if sibling is not anchor and sibling.name == "a":
            break
        text = normalize_text(sibling.get_text(" ", strip=True))
        if text:
            text_parts.append(text)
            parts_seen += 1
        if parts_seen >= max_parts:
            break
    return normalize_text(" ".join(text_parts))


def _looks_like_external_dealer_site(url: str, page_url: str) -> bool:
    host = domain_from_url(url)
    page_host = domain_from_url(page_url)
    if not host or host == page_host:
        return False
    if any(blocked in host for blocked in DISCOVERY_BLOCKLIST_HOSTS):
        return False
    return True


def _looks_like_dealer_href(href: str) -> bool:
    parsed = urlparse(href)
    if parsed.scheme and parsed.scheme not in {"http", "https"}:
        return False
    host = parsed.netloc.lower().removeprefix("www.")
    if not host:
        return False
    if any(blocked in host for blocked in DISCOVERY_BLOCKLIST_HOSTS):
        return False
    return True


def _has_classes(tag: object, required_classes: set[str]) -> bool:
    classes = set(getattr(tag, "get", lambda *_: [])("class", []))
    return all(required_class in classes for required_class in required_classes)


def _is_toyota_website_link(anchor: object) -> bool:
    href = clean_url(str(anchor.get("href") or ""))
    text = slugify_text(anchor.get_text(" ", strip=True))
    if str(anchor.get("data-gt-action") or "") == "view-dealer":
        return _looks_like_dealer_href(href)
    return "перейти на сайт" in text and _looks_like_dealer_href(href)


def _is_navigation_label(value: str) -> bool:
    label = slugify_text(value)
    ignored = {
        "",
        "1",
        "2",
        "facebook",
        "instagram",
        "youtube",
        "повернутися",
        "повернутись до початку сторінки",
    }
    return label in ignored


def _iter_jsonld_objects(soup: BeautifulSoup) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text()
        if not raw:
            continue
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError:
            continue
        items.extend(_flatten_jsonld(decoded))
    return items


def _extract_hyundai_city_map(html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    city_map: dict[str, str] = {}
    for option in soup.find_all("option", value=True):
        value = normalize_text(str(option.get("value") or ""))
        label = normalize_text(option.get_text(" ", strip=True))
        if value and label:
            city_map[value] = label
    return city_map


def _extract_hyundai_dealers(html: str) -> dict[str, object]:
    raw = _extract_json_object_after_key(html, '"hmuDealers":')
    if not raw:
        return {}
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return decoded if isinstance(decoded, dict) else {}


def _extract_json_object_after_key(text: str, key: str) -> str:
    start = text.find(key)
    if start < 0:
        return ""
    cursor = start + len(key)
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    if cursor >= len(text) or text[cursor] not in "{[":
        return ""

    opening = text[cursor]
    closing = "}" if opening == "{" else "]"
    depth = 0
    in_string = False
    escaped = False
    for index in range(cursor, len(text)):
        char = text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return text[cursor : index + 1]
    return ""


def _fetch_hyundai_dealer_site(fetcher: object, page_url: str, nid: str) -> str:
    if not nid or not hasattr(fetcher, "fetch"):
        return ""
    detail_url = urljoin(page_url, f"/node/get/ajax/{nid}")
    html, _, status = fetcher.fetch(detail_url)
    if status != "ok" or not html:
        return ""
    return _extract_first_external_link(html, page_url)


def _extract_first_external_link(html: str, page_url: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for anchor in soup.find_all("a", href=True):
        href = clean_url(urljoin(page_url, str(anchor["href"])))
        if _looks_like_external_dealer_site(href, page_url):
            return href
    return ""


def _extract_mitsubishi_dealers(html: str) -> list[dict[str, object]]:
    match = re.search(r":dealers='(\[.*?\])'", html, re.S)
    if not match:
        return []
    raw = html_lib.unescape(match.group(1)).replace(r"\"", '"').replace(r"\/", "/")
    if r"\u" in raw:
        raw = raw.encode().decode("unicode_escape")
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return [item for item in decoded if isinstance(item, dict)] if isinstance(decoded, list) else []


def _flatten_jsonld(value: object) -> list[dict[str, object]]:
    if isinstance(value, dict):
        graph = value.get("@graph")
        if isinstance(graph, list):
            return [item for item in graph if isinstance(item, dict)]
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


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
