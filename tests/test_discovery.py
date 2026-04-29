import json

from ua_dealer_intel.discovery import (
    parse_discovery_results,
    parse_hyundai_directory_detailed,
    parse_official_directory,
)


def test_parse_duckduckgo_results_filters_blocked_hosts() -> None:
    html = """
    <html>
      <body>
        <a class="result__a" href="https://dealer.example.ua/contact">Dealer Example | Official site</a>
        <a class="result__a" href="https://www.facebook.com/dealer.example">Facebook</a>
      </body>
    </html>
    """
    results = parse_discovery_results(
        html=html,
        provider_name="duckduckgo_html",
        city="Lviv",
        region="Lvivska",
        query="avtosalon lviv",
    )
    assert len(results) == 1
    assert results[0].source_url == "https://dealer.example.ua/contact"
    assert results[0].company_hint == "Dealer Example"
    assert results[0].source_type == "discovered_search"


def test_parse_bing_results_returns_seed_record() -> None:
    html = """
    <html>
      <body>
        <li class="b_algo">
          <h2><a href="https://autosalon.example.ua/">Auto Salon Rivne - Main</a></h2>
        </li>
      </body>
    </html>
    """
    results = parse_discovery_results(
        html=html,
        provider_name="bing",
        city="Rivne",
        region="Rivnenska",
        query="avtosalon rivne",
    )
    assert len(results) == 1
    assert results[0].city == "Rivne"
    assert results[0].region == "Rivnenska"
    assert results[0].source_url == "https://autosalon.example.ua"


def test_parse_toyota_official_directory() -> None:
    html = """
    <html>
      <body>
        <h2>Тойота Центр Львів "Діамант"</h2>
        <ul>
          <li>Кульпарківська, 226 - Львів</li>
          <li>Телефон +380 67 383 8378</li>
        </ul>
        <a href="https://toyota.lviv.ua">Перейти на сайт</a>
      </body>
    </html>
    """
    results = parse_official_directory(
        html=html,
        page_url="https://www.toyota.ua/contact/toyota-dealers",
        provider_name="toyota_ua",
        parser_name="toyota_listing",
        brand="Toyota",
    )
    assert len(results) == 1
    assert results[0].city == "Lviv"
    assert results[0].source_url == "https://toyota.lviv.ua"


def test_parse_renault_official_directory() -> None:
    html = """
    <html>
      <body>
        <a href="https://lviv-renault.com.ua">Галич-Моторс</a>
        <p>м. Львів вул. Зелена, буд. 407</p>
        <p>79066</p>
        <p>0322 703 066</p>
        <p>веб-сайт</p>
        <a href="https://renault.dp.ua">Сінгл-Мотор</a>
        <p>Дніпро Запорізьке шосе, 25А</p>
      </body>
    </html>
    """
    results = parse_official_directory(
        html=html,
        page_url="https://www.renault.ua/find-a-dealer/find-a-dealer-listing.html",
        provider_name="renault_ua",
        parser_name="renault_listing",
        brand="Renault",
    )
    assert len(results) == 1
    assert results[0].city == "Lviv"
    assert results[0].source_url == "https://lviv-renault.com.ua"


def test_parse_opel_official_directory() -> None:
    html = """
    <html>
      <body>
        <h3>Тернопіль</h3>
        <table>
          <tr>
            <td>Автопалац Тернопіль</td>
            <td>вул. Микулинецька, буд. 29а м. Тернопіль <a href="https://autopalace.example.ua">www.autopalace.example.ua</a></td>
            <td>(098) 559-33-33</td>
          </tr>
        </table>
      </body>
    </html>
    """
    results = parse_official_directory(
        html=html,
        page_url="https://www.opel.ua/tools/opel-locate-dealer.html",
        provider_name="opel_ua",
        parser_name="opel_listing",
        brand="Opel",
    )
    assert len(results) == 1
    assert results[0].city == "Ternopil"
    assert results[0].source_url == "https://autopalace.example.ua"


def test_parse_kia_official_api() -> None:
    payload = {
        "dataInfo": [
            {
                "dealerNm": "УКРАВТО ЗАКАРПАТТЯ",
                "city": "м.Ужгород",
                "addr": "вул. Олександра Блеста, 20",
                "url": "http://kia.uz.ua",
            },
            {
                "dealerNm": "УКРАВТО ВОЛИНЬ",
                "city": "м.Луцьк",
                "addr": "вул. Рівненська, 145",
                "url": "http://kia.lutsk.ua",
            },
            {
                "dealerNm": "УКРАВТО ОДЕСА",
                "city": "м.Одеса",
                "addr": "вул. Інглезі, 15",
                "url": "http://kia.od.ua",
            },
        ]
    }
    results = parse_official_directory(
        html=json.dumps(payload, ensure_ascii=False),
        page_url="https://www.kia.com/api/kia_ukraine/base/fd01/findDealer.selectFindDealerByServiceList",
        provider_name="kia_ua",
        parser_name="kia_api",
        brand="Kia",
    )
    assert len(results) == 2
    by_url = {item.source_url: item for item in results}
    assert by_url["http://kia.uz.ua"].city == "Uzhhorod"
    assert by_url["http://kia.lutsk.ua"].city == "Lutsk"


def test_parse_city_first_table_official_directory() -> None:
    html = """
    <html>
      <body>
        <table>
          <tr>
            <td>Львів</td>
            <td>Ілта Львів</td>
            <td>вул. Збиральна 2а</td>
            <td><a href="https://peugeot-lviv.example.ua/">https://peugeot-lviv.example.ua/</a></td>
          </tr>
          <tr>
            <td>Одеса</td>
            <td>Автогруп</td>
            <td><a href="https://peugeot-odesa.example.ua/">https://peugeot-odesa.example.ua/</a></td>
          </tr>
        </table>
      </body>
    </html>
    """
    results = parse_official_directory(
        html=html,
        page_url="https://www.peugeot.ua/links/dealership.html",
        provider_name="peugeot_ua",
        parser_name="city_first_table",
        brand="Peugeot",
    )
    assert len(results) == 1
    assert results[0].company_hint == "Ілта Львів [Peugeot]"
    assert results[0].source_url == "https://peugeot-lviv.example.ua"


def test_parse_hyundai_official_directory_with_detail_fetch() -> None:
    class Fetcher:
        def fetch(self, url: str) -> tuple[str, str, str]:
            assert url == "https://hyundai.com.ua/node/get/ajax/698"
            return '<a href="https://hyundai-lviv.example.ua/">Сайт дилера</a>', url, "ok"

    html = """
    <html>
      <body>
        <select>
          <option value="26">Львів</option>
          <option value="8">Одеса</option>
        </select>
        <script>
          Drupal.settings = {"hmuDealers":{"26":{"698":{"nid":"698","city":"26","title":"Авто Лідер Захід","location":{"lat":"49","lng":"24"}}}},"hmuCity":false};
        </script>
      </body>
    </html>
    """
    results, stats = parse_hyundai_directory_detailed(
        html=html,
        page_url="https://hyundai.com.ua/dealers",
        provider_name="hyundai_ua",
        brand="Hyundai",
        fetcher=Fetcher(),
    )
    assert stats["raw_candidates"] == 1
    assert len(results) == 1
    assert results[0].city == "Lviv"
    assert results[0].source_url == "https://hyundai-lviv.example.ua"


def test_parse_mitsubishi_official_directory() -> None:
    dealers_json = json.dumps(
        [
            {
                "title": "НІКО-ЗАХІД",
                "city_name": "Львів",
                "address": "вул. Липинського, 50Б",
                "website_link": "http://www.mitsubishi.lviv.example.ua/",
            },
            {
                "title": "АВТОГРАД ОДЕСА",
                "city_name": "Одеса",
                "address": "вул. Інглезі, 15Б",
                "website_link": "https://mitsubishi-odesa.example.ua/",
            },
        ],
        ensure_ascii=False,
    ).replace('"', r"\"")
    html = f"<block-dealers :dealers='{dealers_json}'></block-dealers>"
    results = parse_official_directory(
        html=html,
        page_url="https://mitsubishi-motors.com.ua/find-a-dealer",
        provider_name="mitsubishi_ua",
        parser_name="mitsubishi_listing",
        brand="Mitsubishi",
    )
    assert len(results) == 1
    assert results[0].company_hint == "НІКО-ЗАХІД [Mitsubishi]"
    assert results[0].source_url == "http://www.mitsubishi.lviv.example.ua"
