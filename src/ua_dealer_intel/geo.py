"""Geograficke pravidla a filtrovanie."""

from __future__ import annotations

from ua_dealer_intel.constants import PRIMARY_CITIES, PRIORITY_REGIONS, SECONDARY_CITIES
from ua_dealer_intel.utils import slugify_text


def classify_scope(city: str, region: str) -> tuple[bool, str]:
    city_norm = slugify_text(city)
    region_norm = slugify_text(region)

    if city_norm == "kyiv" or region_norm == "kyivska":
        return False, "Kyiv nie je povoleny bez explicitneho zadania"

    if city_norm in PRIMARY_CITIES:
        return True, "Primarna lokalita"

    if city_norm in SECONDARY_CITIES:
        return True, "Sekundarna lokalita"

    if region_norm in PRIORITY_REGIONS:
        return True, f"Region v rozsahu: {PRIORITY_REGIONS[region_norm]}"

    return False, "Mimo geografickeho rozsahu"


def geography_score(city: str, region: str) -> int:
    city_norm = slugify_text(city)
    region_norm = slugify_text(region)
    if city_norm in PRIMARY_CITIES or PRIORITY_REGIONS.get(region_norm) == "primary":
        return 10
    if city_norm in SECONDARY_CITIES or PRIORITY_REGIONS.get(region_norm) == "secondary":
        return 6
    return 0

