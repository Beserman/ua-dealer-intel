"""Datove modely."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class SeedRecord:
    source_url: str = ""
    company_hint: str = ""
    city: str = ""
    region: str = ""
    source_type: str = ""
    company_name: str = ""
    notes: str = ""
    discovery_query: str = ""
    discovery_provider: str = ""


@dataclass(slots=True)
class ScrapeResult:
    row: dict[str, object]
    source: dict[str, object]
    excluded: bool = False
    excluded_reason: str = ""
    manual_queue: list[dict[str, object]] = field(default_factory=list)
    logs: list[dict[str, object]] = field(default_factory=list)
