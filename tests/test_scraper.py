from ua_dealer_intel.models import SeedRecord
from ua_dealer_intel.scraper import process_seed


class FakeClient:
    def fetch(self, url: str) -> tuple[str, str, str]:
        if url.endswith("/contacts"):
            return "", url, "error: 404 Client Error"
        if url.endswith("/about"):
            return "", url, "error: 404 Client Error"
        html = """
        <html lang="uk">
          <head><title>Test Dealer</title></head>
          <body>
            Toyota service sales
            info@example.ua
            +380 67 123 4567
          </body>
        </html>
        """
        return html, url, "ok"


class BlockedClient:
    def fetch(self, url: str) -> tuple[str, str, str]:
        return "", url, "blocked_by_robots"


def test_process_seed_keeps_ok_status_when_some_pages_fail() -> None:
    seed = SeedRecord(
        source_url="https://dealer.example.ua",
        company_hint="Dealer",
        city="Lviv",
        region="Lvivska",
        source_type="website",
    )
    result = process_seed(seed, FakeClient())

    assert result.row["fetch_status"] == "ok"
    assert "problem_s_fetchom" not in str(result.row["red_flags"])
    assert "404 Client Error" in str(result.row["error"])


def test_process_seed_uses_official_brand_hint_when_fetch_is_blocked() -> None:
    seed = SeedRecord(
        source_url="https://ford.example.ua",
        company_hint="Велет Авто [Ford]",
        city="Lviv",
        region="Lvivska",
        source_type="discovered_search",
        discovery_query="official:Ford",
        discovery_provider="ford_ua",
    )
    result = process_seed(seed, BlockedClient())

    assert result.row["fetch_status"] == "blocked_by_robots"
    assert result.row["brands"] == "Ford"
    assert result.row["entry_strength"] == "high"
    assert result.row["score_auto"] == 28
