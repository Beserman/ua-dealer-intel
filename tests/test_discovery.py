import json

from ua_dealer_intel import discovery as discovery_module
from ua_dealer_intel.discovery import (
    discover_from_official_sources,
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


def test_parse_ford_official_directory() -> None:
    html = """
    <html>
      <body>
        <div id="dealer-list">
          <div class="flex flex-row shadow-selectDealerCard my-2.5" id="dealer-1">
            <div class="text-darkBlue uppercase flex flex-row items-center">Автопалац Тернопіль</div>
            <div class="text-grayText">вул. Микулинецька, 25а Тернопіль 47222</div>
            <a href="tel:+38 (097) 559 33 33">+38 (097) 559 33 33</a>
            <a href="http://www.ford.te.ua">http://www.ford.te.ua</a>
          </div>
          <div class="flex flex-row shadow-selectDealerCard my-2.5" id="dealer-2">
            <div class="text-darkBlue uppercase flex flex-row items-center">Велет Авто</div>
            <div class="text-grayText">вул. Липинського, 50в Львів 79000</div>
            <a href="http://www.ford.lviv.ua">http://www.ford.lviv.ua</a>
          </div>
          <div class="flex flex-row shadow-selectDealerCard my-2.5" id="dealer-3">
            <div class="text-darkBlue uppercase flex flex-row items-center">Мустанг Моторс</div>
            <div class="text-grayText">вул. Грушевського, 37 Одеса 65000</div>
            <a href="http://www.ford-odessa.org">http://www.ford-odessa.org</a>
          </div>
        </div>
      </body>
    </html>
    """
    results = parse_official_directory(
        html=html,
        page_url="https://www.ford.ua/dealerships",
        provider_name="ford_ua",
        parser_name="ford_listing",
        brand="Ford",
    )
    assert len(results) == 2
    by_url = {item.source_url: item for item in results}
    assert by_url["http://www.ford.te.ua"].city == "Ternopil"
    assert by_url["http://www.ford.lviv.ua"].company_hint == "Велет Авто [Ford]"


def test_parse_mg_official_directory() -> None:
    html = """
    <html>
      <body>
        <table>
          <tr>
            <td><a title="Івано-Франківськ Альянс-А" href="../../../dealer/aliansa"><strong>Івано-Франківськ<br/>Альянс-А</strong></a></td>
            <td>Калуське шосе, 2К</td>
          </tr>
          <tr>
            <td><a title="Львів Велет Авто" href="../../../dealer/velet-avto"><strong>Львів<br/>Велет Авто</strong></a></td>
            <td>вулиця Липинського, 50в</td>
          </tr>
          <tr>
            <td><a title="Мукачево ТОВ " href="../../../dealer/motorcom">Мукачево ТОВ "Прем'єр Авто"</a></td>
            <td>с. Клячаново, вул.Автомобілістів, 28 А</td>
          </tr>
          <tr>
            <td><a title="Одеса Мустанг Моторс" href="../../../dealer/mustang-motors">Одеса Мустанг Моторс</a></td>
            <td>вулиця Грушевського, 37</td>
          </tr>
        </table>
      </body>
    </html>
    """
    results = parse_official_directory(
        html=html,
        page_url="https://mgmotor.com.ua/dealers",
        provider_name="mg_ua",
        parser_name="mg_table",
        brand="MG",
    )
    assert len(results) == 3
    by_url = {item.source_url: item for item in results}
    assert by_url["https://mgmotor.com.ua/dealer/aliansa"].city == "Ivano-Frankivsk"
    assert by_url["https://mgmotor.com.ua/dealer/velet-avto"].company_hint == "Велет Авто [MG]"
    assert by_url["https://mgmotor.com.ua/dealer/motorcom"].company_hint == 'ТОВ "Прем\'єр Авто" [MG]'


def test_parse_chery_official_directory_region_blocks() -> None:
    html = """
    <html>
      <body>
        <a href="/autosalon/lvivska-oblast.html">Львівська область</a>
        <a href="/autosalon/zakarpatska-oblast.html">Закарпатська область</a>
        <div class="l_d_m">
          <h3>Львівська область</h3>
          <div class="dealer">
            <div class="left_info"><h3>ТОВ «УКРАВТО ЛЬВІВ»</h3></div>
            <div class="right_info">
              <p>м. Львів, вул. Городоцька, 282</p>
              <a href="https://maps.app.goo.gl/test">подивитись на карті</a>
            </div>
          </div>
        </div>
        <div class="l_d_m">
          <h3>Закарпатська область</h3>
          <div class="dealer">
            <div class="left_info"><h3>ТОВ "УКРАВТО ЗАКАРПАТТЯ"</h3></div>
            <div class="right_info"><p>м. Ужгород, вул. Олександра Блеста, 20</p></div>
          </div>
        </div>
        <div class="l_d_m">
          <h3>Одеська область</h3>
          <div class="dealer">
            <div class="left_info"><h3>ТОВ «УКРАВТО ОДЕСА»</h3></div>
            <div class="right_info"><p>м. Одеса, вул. Київська, 19</p></div>
          </div>
        </div>
      </body>
    </html>
    """
    results = parse_official_directory(
        html=html,
        page_url="https://chery.ua/autosalon.html",
        provider_name="chery_ua",
        parser_name="chery_regions",
        brand="Chery",
    )
    assert len(results) == 2
    by_city = {item.city: item for item in results}
    assert by_city["Lviv"].source_url == "https://chery.ua/autosalon/lvivska-oblast.html"
    assert by_city["Uzhhorod"].company_hint == 'ТОВ "УКРАВТО ЗАКАРПАТТЯ" [Chery]'


def test_parse_haval_gwm_official_directory() -> None:
    html = """
    <html>
      <body>
        <div class="uk-card">
          <h4 class="uk-card-title">ТОВ Богдан-Авто Луцьк</h4>
          <div>43020, Україна, Волинська, Луцьк, вул. Рівненська, 100</div>
          <a href="https://www.haval-ukraine.com/partners/dylery/bohdan-avto-lutsk/" class="uk-button uk-button-default">Докладніше</a>
        </div>
        <div class="uk-card">
          <h4 class="uk-card-title">ТОВ Богдан-Авто Черкаси</h4>
          <div>Черкаси, вул. Смілянська, 153</div>
          <a href="https://www.haval-ukraine.com/partners/dylery/tov-bohdan-avto-cherkasy/" class="uk-button uk-button-default">Докладніше</a>
        </div>
      </body>
    </html>
    """
    results = parse_official_directory(
        html=html,
        page_url="https://www.haval-ukraine.com/partners/dylery/",
        provider_name="haval_gwm_ua",
        parser_name="haval_cards",
        brand="Haval",
    )
    assert len(results) == 1
    assert results[0].city == "Lutsk"
    assert results[0].company_hint == "ТОВ Богдан-Авто Луцьк [Haval]"


def test_discovery_nezahodi_detailove_stranky_z_rovnakej_oficialnej_domeny(monkeypatch) -> None:
    html = """
    <html>
      <body>
        <table>
          <tr>
            <td><a title="Івано-Франківськ Альянс-А" href="../../../dealer/aliansa">Івано-Франківськ Альянс-А</a></td>
          </tr>
          <tr>
            <td><a title="Львів Велет Авто" href="../../../dealer/velet-avto">Львів Велет Авто</a></td>
          </tr>
        </table>
      </body>
    </html>
    """

    class Fetcher:
        def fetch(self, url: str) -> tuple[str, str, str]:
            assert url == "https://mgmotor.com.ua/dealers"
            return html, url, "ok"

    monkeypatch.setattr(
        discovery_module,
        "DISCOVERY_OFFICIAL_SOURCES",
        [
            {
                "name": "mg_ua",
                "brand": "MG",
                "url": "https://mgmotor.com.ua/dealers",
                "parser": "mg_table",
            }
        ],
    )
    records, _ = discover_from_official_sources(Fetcher(), set())
    assert len(records) == 2
