from ua_dealer_intel.scoring import compute_score, tier_from_score


def test_compute_score_assigns_expected_band() -> None:
    row = {
        "city": "Lviv",
        "region": "Lvivska",
        "brands": "Skoda; Byd",
        "chinese_brand": "yes",
        "website_languages": "uk; en",
        "services": "sales; service; leasing; finance",
        "emails": "info@example.ua",
        "phones": "+380 67 123 45 67",
        "social_links": "https://facebook.com/dealer; https://instagram.com/dealer",
        "score_manual": 0,
    }
    result = compute_score(row)
    assert result["score_auto"] == 57
    assert result["score_total"] == 57
    assert result["tier"] == "A"


def test_tier_from_score() -> None:
    assert tier_from_score(50) == "A"
    assert tier_from_score(25) == "B"
    assert tier_from_score(24) == "C"
