"""Hlavna pipeline aplikacie."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ua_dealer_intel.constants import EXCLUDED_REASON_COLUMN, SCORING_RULES, TARGET_COLUMNS
from ua_dealer_intel.discovery import discover_seed_records
from ua_dealer_intel.exporters import MANUAL_COLUMNS, export_outputs
from ua_dealer_intel.google_sheets import upload_workbook_to_google_sheets
from ua_dealer_intel.io_utils import load_seed_companies, load_seed_urls
from ua_dealer_intel.scraper import WebClient, process_seed


def run_pipeline(
    seeds_path: str | Path | None = None,
    companies_path: str | Path | None = None,
    output_dir: str | Path = "outputs",
    google_sheet_id: str | None = None,
    google_credentials: str | Path | None = None,
    discover: bool = False,
    discovery_limit: int = 25,
) -> dict[str, object]:
    seed_records = load_seed_urls(seeds_path) if seeds_path else []
    if companies_path:
        seed_records.extend(load_seed_companies(companies_path))

    client = WebClient()
    logs: list[dict[str, object]] = []

    if discover:
        discovered, discovery_logs = discover_seed_records(
            fetcher=client,
            limit=discovery_limit,
            existing_seeds=seed_records,
        )
        seed_records.extend(discovered)
        logs.extend(discovery_logs)

    targets: list[dict[str, object]] = []
    excluded: list[dict[str, object]] = []
    sources: list[dict[str, object]] = []
    manual_queue: list[dict[str, object]] = []

    for seed in seed_records:
        result = process_seed(seed, client)
        sources.append(result.source)
        logs.extend(result.logs)
        manual_queue.extend(result.manual_queue)
        if result.excluded:
            excluded.append(result.row)
        else:
            targets.append(result.row)

    output_paths = export_outputs(targets, excluded, sources, logs, manual_queue, output_dir)

    google_status = "preskocene"
    if google_sheet_id and google_credentials:
        dataframes = {
            "targets": pd.DataFrame(targets, columns=TARGET_COLUMNS),
            "excluded": pd.DataFrame(excluded, columns=TARGET_COLUMNS + [EXCLUDED_REASON_COLUMN]),
            "sources": pd.DataFrame(sources),
            "scoring_rules": pd.DataFrame(SCORING_RULES),
            "run_log": pd.DataFrame(logs),
            "manual_enrichment_queue": pd.DataFrame(manual_queue, columns=MANUAL_COLUMNS),
        }
        upload_workbook_to_google_sheets(google_sheet_id, google_credentials, dataframes)
        google_status = "nahrate"

    return {
        "targets_count": len(targets),
        "excluded_count": len(excluded),
        "manual_queue_count": len(manual_queue),
        "discovered_count": len([seed for seed in seed_records if seed.source_type == "discovered_search"]),
        "google_status": google_status,
        "outputs": output_paths,
    }
