from ua_dealer_intel.discovery import parse_discovery_results, parse_official_directory


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
