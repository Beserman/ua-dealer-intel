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
