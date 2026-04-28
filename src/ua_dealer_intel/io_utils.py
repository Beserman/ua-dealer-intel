"""Nacitanie vstupov."""

from __future__ import annotations

import csv
from pathlib import Path

from ua_dealer_intel.models import SeedRecord


def load_seed_urls(path: str | Path) -> list[SeedRecord]:
    records: list[SeedRecord] = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            records.append(
                SeedRecord(
                    source_url=(row.get("source_url") or "").strip(),
                    company_hint=(row.get("company_hint") or "").strip(),
                    city=(row.get("city") or "").strip(),
                    region=(row.get("region") or "").strip(),
                    source_type=(row.get("source_type") or "website").strip(),
                )
            )
    return records


def load_seed_companies(path: str | Path) -> list[SeedRecord]:
    records: list[SeedRecord] = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            records.append(
                SeedRecord(
                    company_name=(row.get("company_name") or "").strip(),
                    city=(row.get("city") or "").strip(),
                    region=(row.get("region") or "").strip(),
                    notes=(row.get("notes") or "").strip(),
                    source_type="company",
                )
            )
    return records

