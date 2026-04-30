# Ukrajinsky skraper a obohatenie pre automobilovych dealerov

Tento projekt sluzi na vyhladavanie, extrakciu a bodove hodnotenie ukrajinskych automobilovych dealerov ako potencialnych akvizicnych alebo partnerskych cielov.

Kod je navrhnuty tak, aby bol spustitelny lokalne aj v cloude, najma cez GitHub Actions alebo Codex cloud, bez potreby rucnej instalacie mimo standardneho Python workflow.

## Hlavne vlastnosti

- nacitanie vstupov zo suborov `seed_urls.csv` a `seed_companies.csv`
- autonomne objavovanie kandidatov z verejnych zdrojov bez nutnosti zadavat URL po jednej
- obmedzene a slusne prechadzanie webov s respektovanim `robots.txt`
- extrakcia kontaktov, jazykov, znaciek, sluzieb a socialnych odkazov
- geograficke filtrovanie na zapadne regiony Ukrajiny
- automaticke skore a zaradenie do tierov
- export do viaclistoveho Excel suboru a do CSV
- volitelna synchronizacia do Google Sheets
- testy pre klucove casti logiky

## Struktura projektu

```text
ua-dealer-intel/
  README.md
  requirements.txt
  src/
    ua_dealer_intel/
  data/
  outputs/
  tests/
  .github/
    workflows/
```

## Instalacia

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Spustenie

Zakladne spustenie so seed URL:

```bash
python -m ua_dealer_intel.cli --seeds data/seed_urls.csv
```

Spustenie so seed URL aj zoznamom spolocnosti:

```bash
python -m ua_dealer_intel.cli --seeds data/seed_urls.csv --companies data/seed_companies.csv
```

Autonomne objavovanie kandidatov bez manualnych URL:

```bash
python -m ua_dealer_intel.cli --discover --discover-limit 100
```

Kombinacia manualnych seedov a autonomneho objavovania:

```bash
python -m ua_dealer_intel.cli \
  --seeds data/seed_urls.csv \
  --companies data/seed_companies.csv \
  --discover \
  --discover-limit 100
```

Volitelne nahratie vystupu do Google Sheets:

```bash
python -m ua_dealer_intel.cli \
  --seeds data/seed_urls.csv \
  --google-sheet-id VASE_ID \
  --google-credentials data/google_service_account.json
```

## Vstupne subory

### `data/seed_urls.csv`

```csv
source_url,company_hint,city,region,source_type
https://example.ua,Example Dealer,Lviv,Lvivska,website
```

Ak chcete ist cisto autonomne, subor moze obsahovat len hlavicku a discovery rezim doplni kandidatov sam.

### `data/seed_companies.csv`

```csv
company_name,city,region,notes
Example Dealer,Lviv,Lvivska,
```

## Vystupy

- `outputs/ua_dealer_targets.xlsx`
- `outputs/ua_dealer_targets.csv`
- `outputs/run_log.txt`

Excel obsahuje listy:

1. `targets`
2. `excluded`
3. `sources`
4. `scoring_rules`
5. `run_log`
6. `manual_enrichment_queue`

## Google Sheets integracia

Google Sheets integracia je volitelna. Ak zadate `--google-sheet-id` a cestu cez `--google-credentials`, program skusi nahrat jednotlivy obsah listov do zodpovedajucich tabov.

Poznamky:

- odporucany je service account JSON
- service account musi mat pristup na dany Sheet
- ak integracia nie je dostupna alebo zlyha, lokalny Excel a CSV sa stale vytvoria

## Pravne a eticke hranice

Projekt umyselne:

- nespracovava LinkedIn obsah ako zdroj na scraping
- nespracovava Google Maps
- neobchadza CAPTCHA, prihlasenie ani anti-bot ochrany
- respektuje `robots.txt` pri prechadzani webu
- pouziva konzervativne casovanie poziadaviek

## Ako funguje autonomne objavovanie

Discovery rezim:

- cita verejne oficialne zoznamy dealerov vybranych znaciek, aktualne Toyota, Renault, Kia, Hyundai, Peugeot, Citroen, Mitsubishi, Ford, Chery, MG a Haval/GWM
- zvysuje prioritu klientskych znaciek Dongfeng, Voyah, Forthing a Ford bez zmeny struktury vystupneho sheetu
- pouziva predajcov cinskych znaciek ako signal vhodnosti pre oslovenie s Dongfeng, Voyah a Forthing
- sklada vyhladavacie dotazy pre cielove mesta a regiony
- skusa verejne HTML vysledky vyhladavania iba z povolenych zdrojov
- odfiltruje socialne siete, Google Maps a LinkedIn
- deduplikuje domeny a pri oficialnych detailoch dealerov aj konkretne URL adresy
- nalezene kandidaty posle do standardnej scraping a scoring pipeline

Limit `--discover-limit` znamena maximalny pocet novych kandidatov, ktory sa program pokusi spracovat v jednom behu. Ak verejne zdroje najdu menej kvalitnych kandidatov v povolenych regionoch, vystup bude mensi ako limit.

Ak discovery zdroj nevrati vysledok alebo nepovoli pristup, program ho preskoci a pokracuje dalej bez obchadzania ochrany.

## Zname obmedzenia

- niektore weby mozu byt velmi dynamicke a bez JavaScript renderu neposkytnu uplne data
- autonomne objavovanie zavisi od dostupnosti verejnych HTML vysledkov a moze sa menit podla zdroja
- detekcia znaciek a sluzieb je heuristicka
- bez externych platenych zdrojov sa vlastnici a rozhodovacie osoby casto nedaju spolahlivo potvrdit
- pri vstupoch bez URL sa spolocnost zaradi do manualnej fronty na doplnenie

## Dalsie zlepsenia

- doplnenie volitelneho API obohatenia
- presnejsia normalizacia telefonov a znaciek
- inteligentnejsie hladanie vstupnej URL pre firmy bez webu
- delta rezim pre opakovane behy a porovnanie zmien
