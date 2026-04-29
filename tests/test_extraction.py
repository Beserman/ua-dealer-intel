from bs4 import BeautifulSoup

from ua_dealer_intel.extraction import (
    extract_brands,
    extract_company_name,
    extract_emails,
    extract_languages,
    extract_phones,
    extract_services,
    extract_social_links,
)


def test_extract_company_name_prefers_hint() -> None:
    soup = BeautifulSoup("<html><head><title>Test</title></head></html>", "html.parser")
    assert extract_company_name(soup, "Hint Dealer", "https://example.ua") == "Hint Dealer"


def test_extract_brands_and_chinese_flag() -> None:
    brands, chinese = extract_brands("Dealer predava Skoda, Toyota a BYD")
    assert "Skoda" in brands
    assert "Toyota" in brands
    assert "Byd" in brands
    assert chinese is True


def test_extract_client_chinese_brands() -> None:
    brands, chinese = extract_brands("Dealer predava Dongfeng, Voyah, Forthing a Ford")
    assert "Dongfeng" in brands
    assert "Voyah" in brands
    assert "Forthing" in brands
    assert "Ford" in brands
    assert chinese is True


def test_extract_services() -> None:
    services = extract_services("Ponukame service, trade-in a finance pre firemnych klientov.")
    assert set(services) >= {"service", "trade-in", "finance"}


def test_extract_languages_emails_phones_and_socials() -> None:
    html = """
    <html lang="uk">
      <head><link rel="alternate" hreflang="en" href="/en/" /><link rel="alternate" hreflang="x-default" href="/" /></head>
      <body>
        Kontakt: info@example.ua, +380 67 123 45 67
        <a href="https://facebook.com/dealer">FB</a>
        <a href="https://instagram.com/dealer">IG</a>
      </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)

    assert extract_languages(soup, "https://example.ua/en/") == ["uk", "en"]
    assert extract_emails(text) == ["info@example.ua"]
    assert "+380 67 123 4567" in extract_phones(text)
    socials = extract_social_links(soup, "https://example.ua")
    assert socials["facebook_url"] == "https://facebook.com/dealer"
    assert socials["instagram_url"] == "https://instagram.com/dealer"


def test_extract_phones_filters_non_phone_values() -> None:
    text = "Tel: +38 (044) 237 02 88 Datum 30.09.2025-1 Hodnota 4 000 000"
    phones = extract_phones(text)
    assert phones == ["+380 44 237 0288"]
