from ua_dealer_intel.geo import classify_scope, geography_score


def test_primary_city_is_in_scope() -> None:
    assert classify_scope("Lviv", "Lvivska") == (True, "Primarna lokalita")


def test_secondary_region_is_in_scope() -> None:
    in_scope, reason = classify_scope("Unknown", "Ternopilska")
    assert in_scope is True
    assert "Region v rozsahu" in reason


def test_out_of_scope_city_is_excluded() -> None:
    assert classify_scope("Odesa", "Odeska") == (False, "Mimo geografickeho rozsahu")


def test_geography_score_values() -> None:
    assert geography_score("Lviv", "Lvivska") == 10
    assert geography_score("Lutsk", "Volynska") == 6
    assert geography_score("Odesa", "Odeska") == 0

