"""Skorovanie cielov."""

from __future__ import annotations

from ua_dealer_intel.constants import CLIENT_TARGET_BRANDS, EU_LANGUAGE_CODES
from ua_dealer_intel.geo import geography_score
from ua_dealer_intel.utils import safe_int, slugify_text


def compute_score(row: dict[str, object]) -> dict[str, object]:
    brands = [item for item in str(row.get("brands", "")).split("; ") if item]
    languages = [item for item in str(row.get("website_languages", "")).split("; ") if item]
    services = [item for item in str(row.get("services", "")).split("; ") if item]
    emails = [item for item in str(row.get("emails", "")).split("; ") if item]
    phones = [item for item in str(row.get("phones", "")).split("; ") if item]
    socials = [item for item in str(row.get("social_links", "")).split("; ") if item]

    score = 0

    if len(brands) > 1:
        score += 18
    elif len(brands) == 1:
        score += 8

    if str(row.get("chinese_brand", "")).lower() == "yes" or _has_client_target_brand(brands):
        score += 10

    eu_languages = [lang for lang in languages if lang.lower() in EU_LANGUAGE_CODES]
    score += min(10, len(eu_languages) * 5)

    score += min(16, len(services) * 2)

    digital_score = 0
    if emails:
        digital_score += 2
    if phones:
        digital_score += 2
    digital_score += min(4, len(socials))
    score += digital_score

    score += geography_score(str(row.get("city", "")), str(row.get("region", "")))

    manual = safe_int(row.get("score_manual"))
    total = min(72, score + manual)

    row["score_auto"] = score
    row["score_total"] = total
    row["tier"] = tier_from_score(total)
    return row


def _has_client_target_brand(brands: list[str]) -> bool:
    return any(slugify_text(brand) in CLIENT_TARGET_BRANDS for brand in brands)


def tier_from_score(score: int) -> str:
    if score >= 50:
        return "A"
    if score >= 25:
        return "B"
    return "C"
