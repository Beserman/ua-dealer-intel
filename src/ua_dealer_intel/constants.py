"""Konstanty pre projekt."""

TARGET_COLUMNS = [
    "company_name",
    "city",
    "region",
    "country",
    "source_url",
    "final_url",
    "fetch_status",
    "data_quality",
    "brands",
    "brand_count",
    "chinese_brand",
    "site_count",
    "services",
    "website_languages",
    "emails",
    "phones",
    "social_links",
    "linkedin_url",
    "facebook_url",
    "instagram_url",
    "telegram_url",
    "viber_url",
    "whatsapp_url",
    "owner_name",
    "decision_power",
    "owner_linkedin_url",
    "linkedin_signal",
    "eu_footprint",
    "cross_border_evidence",
    "recent_expansion",
    "entry_channel",
    "entry_strength",
    "intro_contact",
    "score_auto",
    "score_manual",
    "score_total",
    "tier",
    "red_flags",
    "next_action",
    "last_touch",
    "status",
    "source_notes",
    "error",
]

EXCLUDED_REASON_COLUMN = "excluded_reason"

SCORING_RULES = [
    {
        "oblast": "znacky",
        "pravidlo": "viac ako jedna znacka",
        "body": 18,
        "poznamka": "silnejsi signal vacsieho dealera",
    },
    {
        "oblast": "znacky",
        "pravidlo": "cinska znacka",
        "body": 10,
        "poznamka": "signal otvorenosti na nove znacky",
    },
    {
        "oblast": "jazyky",
        "pravidlo": "EU jazyk na webe",
        "body": 10,
        "poznamka": "anglictina, polstina, slovencina, cestina, madarcina, nemcina, rumuncina",
    },
    {
        "oblast": "sluzby",
        "pravidlo": "siroke portfolio sluzieb",
        "body": 16,
        "poznamka": "az 2 body za kazdu sluzbu, maximum 16",
    },
    {
        "oblast": "digital",
        "pravidlo": "digitalna stopa",
        "body": 8,
        "poznamka": "kontakty a socialne odkazy",
    },
    {
        "oblast": "geografia",
        "pravidlo": "prioritny region",
        "body": 10,
        "poznamka": "zapadne regiony s vyssou prioritou",
    },
]

WESTERN_BRANDS = {
    "audi", "bmw", "citroen", "dacia", "fiat", "ford", "honda", "hyundai",
    "jaguar", "jeep", "kia", "land rover", "lexus", "mazda", "mercedes-benz",
    "mini", "mitsubishi", "nissan", "opel", "peugeot", "porsche", "renault",
    "seat", "skoda", "subaru", "suzuki", "tesla", "toyota", "volkswagen", "volvo",
}

CHINESE_BRANDS = {
    "byd", "chery", "exeed", "faw", "geely", "great wall", "gwm", "haval",
    "jac", "jetour", "mg", "omoda", "roewe", "saic", "seres", "zeekr",
}

SERVICE_KEYWORDS = {
    "sales": ["sales", "new cars", "avto v nayavnosti", "auto sale", "prodazh", "avtosalon"],
    "service": ["service", "repair", "maintenance", "sto", "servis"],
    "leasing": ["leasing", "lizynh", "leasingu"],
    "fleet": ["fleet", "b2b", "corporate", "korporatyv", "fleet service"],
    "import": ["import", "doviz", "pryviz", "postachannya"],
    "trade-in": ["trade-in", "trade in", "obmin", "vykup"],
    "parts": ["parts", "spare parts", "zapchast", "aksesuary"],
    "finance": ["finance", "credit", "kredyt", "finansuvannya"],
    "insurance": ["insurance", "strahuvannya", "osago", "kasko"],
}

EU_LANGUAGE_CODES = {"en", "pl", "sk", "cs", "de", "hu", "ro"}

PRIORITY_REGIONS = {
    "lvivska": "primary",
    "zakarpatska": "primary",
    "riven ska": "secondary",
    "rivnenska": "secondary",
    "volynska": "secondary",
    "ivano-frankivska": "secondary",
    "ternopilska": "secondary",
    "chernivetska": "secondary",
}

PRIMARY_CITIES = {"lviv", "uzhhorod", "mukachevo", "chop", "berehove"}
SECONDARY_CITIES = {"rivne", "lutsk", "ivano-frankivsk", "ternopil", "chernivtsi"}

SOCIAL_HOSTS = {
    "linkedin.com": "linkedin_url",
    "facebook.com": "facebook_url",
    "instagram.com": "instagram_url",
    "t.me": "telegram_url",
    "telegram.me": "telegram_url",
    "viber.com": "viber_url",
    "wa.me": "whatsapp_url",
    "whatsapp.com": "whatsapp_url",
}

ALLOWED_LANGUAGE_CODES = EU_LANGUAGE_CODES | {"uk", "ru"}

DISCOVERY_LOCATIONS = [
    {"city": "Lviv", "region": "Lvivska", "queries": ["avtosalon lviv", "car dealer lviv", "avtodiler lviv"]},
    {"city": "Uzhhorod", "region": "Zakarpatska", "queries": ["avtosalon uzhhorod", "car dealer uzhhorod"]},
    {"city": "Mukachevo", "region": "Zakarpatska", "queries": ["avtosalon mukachevo", "car dealer mukachevo"]},
    {"city": "Chop", "region": "Zakarpatska", "queries": ["avtosalon chop ukraine"]},
    {"city": "Berehove", "region": "Zakarpatska", "queries": ["avtosalon berehove ukraine"]},
    {"city": "Rivne", "region": "Rivnenska", "queries": ["avtosalon rivne", "car dealer rivne"]},
    {"city": "Lutsk", "region": "Volynska", "queries": ["avtosalon lutsk", "car dealer lutsk"]},
    {"city": "Ivano-Frankivsk", "region": "Ivano-Frankivska", "queries": ["avtosalon ivano frankivsk", "car dealer ivano frankivsk"]},
    {"city": "Ternopil", "region": "Ternopilska", "queries": ["avtosalon ternopil", "car dealer ternopil"]},
    {"city": "Chernivtsi", "region": "Chernivetska", "queries": ["avtosalon chernivtsi", "car dealer chernivtsi"]},
]

DISCOVERY_PROVIDERS = [
    {
        "name": "duckduckgo_html",
        "url_template": "https://html.duckduckgo.com/html/?q={query}",
    },
    {
        "name": "bing",
        "url_template": "https://www.bing.com/search?q={query}",
    },
]

DISCOVERY_BLOCKLIST_HOSTS = {
    "duckduckgo.com",
    "html.duckduckgo.com",
    "bing.com",
    "google.com",
    "maps.google.com",
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "youtube.com",
    "t.me",
}

DISCOVERY_CITY_VARIANTS = {
    "Lviv": ["lviv", "львів"],
    "Uzhhorod": ["uzhhorod", "ужгород"],
    "Mukachevo": ["mukachevo", "мукачево"],
    "Chop": ["chop", "чоп"],
    "Berehove": ["berehove", "берегове", "beregove"],
    "Rivne": ["rivne", "рівне", "рiвне", "ровно"],
    "Lutsk": ["lutsk", "луцьк"],
    "Ivano-Frankivsk": ["ivano-frankivsk", "ivano frankivsk", "івано-франківськ"],
    "Ternopil": ["ternopil", "тернопіль"],
    "Chernivtsi": ["chernivtsi", "чернівці", "chernovtsy"],
}

DISCOVERY_OFFICIAL_SOURCES = [
    {
        "name": "toyota_ua",
        "brand": "Toyota",
        "url": "https://www.toyota.ua/contact/toyota-dealers",
        "parser": "toyota_listing",
    },
    {
        "name": "renault_ua",
        "brand": "Renault",
        "url": "https://www.renault.ua/find-a-dealer/find-a-dealer-listing.html",
        "parser": "renault_listing",
    },
    {
        "name": "opel_ua",
        "brand": "Opel",
        "url": "https://www.opel.ua/tools/opel-locate-dealer.html",
        "parser": "opel_listing",
    },
]
