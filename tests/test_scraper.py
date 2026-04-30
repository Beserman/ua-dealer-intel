from ua_dealer_intel.models import SeedRecord
from ua_dealer_intel.scraper import _robots_allowed_by_text, process_seed


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


class BrandNoiseClient:
    def fetch(self, url: str) -> tuple[str, str, str]:
        html = """
        <html lang="uk">
          <head><title>AutoMoto detail</title></head>
          <body>
            Навігація: Audi BMW BYD Chery Ford GWM Haval MG Voyah Zeekr
            Основний дилер Dongfeng у Львівській області
            +380 67 111 2233
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


def test_process_seed_keeps_brand_hint_for_excluded_candidate() -> None:
    seed = SeedRecord(
        source_url="https://electro-mobility.example.ua/listing-make/voyah/",
        company_hint="Electro Mobility [Voyah]",
        city="Kyiv",
        region="Kyivska",
        source_type="discovered_search",
        discovery_query="public:Voyah",
        discovery_provider="electro_mobility_voyah",
    )
    result = process_seed(seed, BlockedClient())

    assert result.excluded is True
    assert result.row["brands"] == "Voyah"
    assert result.row["chinese_brand"] == "yes"
    assert result.row["entry_strength"] == "high"


def test_process_seed_prioritizes_public_directory_brand_hint() -> None:
    seed = SeedRecord(
        source_url="https://automoto.ua/uk/avtosalony/view/AgroTeh",
        company_hint="ТРАКТОР №1 [Dongfeng]",
        city="Lviv",
        region="Lvivska",
        source_type="discovered_search",
        discovery_query="public:AutoMoto:Dongfeng",
        discovery_provider="automoto_dongfeng",
    )
    result = process_seed(seed, BrandNoiseClient())

    assert result.row["brands"] == "Dongfeng"
    assert result.row["chinese_brand"] == "yes"
    assert result.row["score_total"] >= 30


def test_robots_parser_allows_clean_catalog_path_and_blocks_query() -> None:
    robots_text = """
    User-agent: *
    Allow: /
    Allow: /catalog-avto-china/
    Disallow: /catalog-avto-china*?
    Disallow: /api/
    """

    assert _robots_allowed_by_text(
        robots_text,
        "ua-dealer-intel/0.1",
        "https://westmotors.example/catalog-avto-china/dongfeng-forthing",
    )
    assert not _robots_allowed_by_text(
        robots_text,
        "ua-dealer-intel/0.1",
        "https://westmotors.example/catalog-avto-china/dongfeng-forthing?sort=price",
    )
    assert not _robots_allowed_by_text(
        robots_text,
        "ua-dealer-intel/0.1",
        "https://westmotors.example/api/search",
    )
