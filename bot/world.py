"""Weltwirtschaft für das Dashboard: IMF-Daten (Ist + Prognose bis ~2030), Eskalationsstufen je Land.

Quelle 1: IMF DataMapper (World Economic Outlook, ohne Schlüssel).
Quelle 2 (Ausweichlösung): Weltbank-API (nur Ist-Werte).
Die Szenarien bis 2050 rechnet das Dashboard selbst aus diesen Werten (siehe docs/index.html).
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import requests
from urllib.parse import quote

OUT = Path(__file__).resolve().parent.parent / "docs" / "world.js"
YEARS = list(range(2000, 2031))
UA = {"User-Agent": "Mozilla/5.0 (TradeBot dashboard)"}

# Die wichtigsten Volkswirtschaften (Balkendiagramm neben der Karte)
KEY = ["USA", "CHN", "DEU", "JPN", "IND", "GBR", "FRA", "ITA", "BRA", "CAN", "RUS", "KOR"]

INDICATORS = {  # IMF-Code -> (Weltbank-Code, Faktor)
    "NGDP_RPCH": ("NY.GDP.MKTP.KD.ZG", 1),    # reales BIP-Wachstum %
    "PCPIPCH": ("FP.CPI.TOTL.ZG", 1),         # Inflation %
    "LUR": ("SL.UEM.TOTL.ZS", 1),             # Arbeitslosenquote %
    "GGXWDG_NGDP": ("GC.DOD.TOTL.GD.ZS", 1),  # Staatsschulden % BIP
    "PPPPC": ("NY.GDP.PCAP.PP.CD", 1),        # BIP pro Kopf, Kaufkraftparität (int. $)
    "NGDPD": ("NY.GDP.MKTP.CD", 1e-9),        # BIP in Mrd. USD
}

# Ländernamen in Schlagzeilen (de/en) -> ISO3, für die Eskalations-Ausweichlösung
COUNTRY_WORDS = {
    "USA": ("usa", "u.s.", "united states", "vereinigte staaten", "washington", "pentagon"),
    "CHN": ("china", "beijing", "peking", "chinese", "chinesisch"),
    "RUS": ("russia", "russland", "moscow", "moskau", "kremlin", "kreml", "putin"),
    "UKR": ("ukraine", "kyiv", "kiew", "selenskyj", "zelensky"),
    "IRN": ("iran", "tehran", "teheran"),
    "ISR": ("israel", "gaza", "netanyahu", "netanjahu"),
    "PSE": ("gaza", "palestin", "palästin", "westjordanland", "west bank"),
    "LBN": ("lebanon", "libanon", "hezbollah", "hisbollah"),
    "SYR": ("syria", "syrien"),
    "YEM": ("yemen", "jemen", "houthi", "huthi"),
    "TWN": ("taiwan", "taipei"),
    "PRK": ("north korea", "nordkorea", "pyongyang"),
    "KOR": ("south korea", "südkorea", "seoul"),
    "IND": ("india", "indien", "new delhi", "neu-delhi"),
    "PAK": ("pakistan",),
    "VEN": ("venezuela",),
    "SAU": ("saudi",),
    "TUR": ("turkey", "türkei", "erdogan"),
    "DEU": ("germany", "deutschland", "berlin", "bundesregierung"),
    "FRA": ("france", "frankreich", "paris", "macron"),
    "GBR": ("britain", "großbritannien", "london", "uk "),
    "JPN": ("japan", "tokyo", "tokio"),
    "SDN": ("sudan",),
    "IRQ": ("iraq", "irak"),
    "EGY": ("egypt", "ägypten", "suez"),
    "MEX": ("mexico", "mexiko"),
    "BRA": ("brazil", "brasilien"),
}
CONFLICT_WORDS = (
    "war", "krieg", "attack", "angriff", "missile", "rakete", "strike", "sanction", "sanktion", "military",
    "militär", "conflict", "konflikt", "invasion", "blockade", "terror", "coup", "putsch", "unrest", "unruhen",
    "nuclear", "atom", "drone", "drohne", "eskalation", "escalat", "troops", "truppen", "bomb", "tariff", "zoll",
)


# Gold: amtliche Reserven der Zentralbanken in Tonnen (World Gold Council, gerundet, Stand ca. Mitte 2025)
# und Minenförderung in Tonnen pro Jahr (USGS Mineral Commodity Summaries 2025, Werte für 2024, gerundet).
# Es gibt dafür keine freie Echtzeit-API; die Werte ändern sich nur langsam und werden hier gepflegt.
GOLD_SOURCE = {"reserven": "World Gold Council, Zentralbank-Bestände, ca. Mitte 2025 (gerundet)",
               "foerderung": "USGS Mineral Commodity Summaries 2025, Förderung 2024 (gerundet)"}
GOLD_RESERVES = {
    "USA": 8133, "DEU": 3350, "ITA": 2452, "FRA": 2437, "RUS": 2330, "CHN": 2299, "CHE": 1040, "IND": 880,
    "JPN": 846, "NLD": 612, "TUR": 600, "POL": 515, "PRT": 383, "UZB": 380, "SAU": 323, "GBR": 310,
    "KAZ": 300, "LBN": 287, "ESP": 282, "AUT": 280, "THA": 235, "BEL": 227, "SGP": 220, "IRQ": 160,
    "PHL": 160, "BRA": 130, "EGY": 127, "SWE": 126, "ZAF": 125, "MEX": 120, "LBY": 117, "GRC": 114,
    "KOR": 104, "ROU": 104, "QAT": 110, "AUS": 80, "KWT": 79, "IDN": 79, "DNK": 67, "PAK": 65, "ARG": 62,
}
GOLD_PRODUCTION = {
    "CHN": 380, "RUS": 310, "AUS": 290, "CAN": 200, "USA": 160, "MEX": 140, "GHA": 140, "KAZ": 130,
    "UZB": 120, "PER": 100, "IDN": 100, "ZAF": 100, "SDN": 80, "MLI": 70, "BRA": 70, "TZA": 60,
    "BFA": 60, "COL": 60, "GIN": 60, "PNG": 50, "ARG": 50, "CHL": 40, "KGZ": 30, "PHL": 30,
}


# Feste Wikidata-Kennungen der wichtigsten Länder – Ausweichweg, falls dort der ISO-Code fehlt
COUNTRY_QIDS = {"USA": "Q30", "MEX": "Q96", "CHN": "Q148", "DEU": "Q183", "JPN": "Q17", "IND": "Q668", "GBR": "Q145",
                "FRA": "Q142", "ITA": "Q38", "BRA": "Q155", "CAN": "Q16", "RUS": "Q159", "KOR": "Q884", "UKR": "Q212",
                "ISR": "Q801", "IRN": "Q794", "TUR": "Q43", "SAU": "Q851", "AUS": "Q408", "ZAF": "Q258"}


def fetch_leaders() -> dict[str, list[dict]]:
    """Aktuelles Staatsoberhaupt und Regierungschef je Land (Wikidata, mit Foto von Wikimedia Commons)."""
    out = _leaders_query("""
  VALUES ?type { wd:Q3624078 wd:Q6256 }
  ?c wdt:P31 ?type; wdt:P298 ?iso.""")
    missing = {iso: q for iso, q in COUNTRY_QIDS.items() if iso not in out}
    if missing:
        values = " ".join(f'(wd:{q} "{iso}")' for iso, q in missing.items())
        out.update(_leaders_query(f"\n  VALUES (?c ?iso) {{ {values} }}"))
    missing = {iso: q for iso, q in COUNTRY_QIDS.items() if iso not in out}
    if missing:  # Amtsinhaber ohne Amtsende mit dem jüngsten Amtsantritt
        values = " ".join(f'(wd:{q} "{iso}")' for iso, q in missing.items())
        out.update(_leaders_query(f"\n  VALUES (?c ?iso) {{ {values} }}", by_statement=True))
    for iso, people in FIXED_LEADERS.items():  # nur falls Wikidata für dieses Land gar nichts liefert
        if iso not in out:
            out[iso] = [{"role": role, "name": name, **_person_image(name)} for name, role in people]
    return out


# Fester Ersatz für Länder, deren Wikidata-Einträge die Abfragen nicht treffen (Amtszeiten bis 2029/2030).
FIXED_LEADERS = {
    "USA": [("Donald Trump", "Staatsoberhaupt & Regierungschef")],
    "MEX": [("Claudia Sheinbaum", "Staatsoberhaupt & Regierungschef")],
}


def _person_image(name: str) -> dict:
    """Foto einer Person über die Wikidata-Suche (P18 → Wikimedia Commons)."""
    try:
        hdr = {"User-Agent": "TradeBot-Dashboard/1.0 (GitHub Actions)"}
        hit = requests.get("https://www.wikidata.org/w/api.php", headers=hdr, timeout=20, params={
            "action": "wbsearchentities", "search": name, "language": "de", "format": "json", "limit": 1}).json()["search"][0]
        ent = requests.get(f"https://www.wikidata.org/wiki/Special:EntityData/{hit['id']}.json", headers=hdr, timeout=20).json()
        claims = ent["entities"][hit["id"]]["claims"].get("P18", [])
        file = claims[0]["mainsnak"]["datavalue"]["value"] if claims else ""
        img = f"https://commons.wikimedia.org/wiki/Special:FilePath/{quote(file.replace(' ', '_'))}?width=320" if file else ""
        return {"img": img, "wiki": f"https://www.wikidata.org/wiki/{hit['id']}"}
    except Exception:
        return {"img": "", "wiki": ""}


def _leaders_query(country_filter: str, by_statement: bool = False) -> dict[str, list[dict]]:
    if by_statement:
        office = """
  { ?c p:P35 ?st. ?st ps:P35 ?person. BIND("Staatsoberhaupt" AS ?role) } UNION { ?c p:P6 ?st. ?st ps:P6 ?person. BIND("Regierungschef" AS ?role) }
  ?st pq:P580 ?start. FILTER NOT EXISTS { ?st pq:P582 ?end. }"""
    else:
        office = """
  { ?c wdt:P35 ?person. BIND("Staatsoberhaupt" AS ?role) } UNION { ?c wdt:P6 ?person. BIND("Regierungschef" AS ?role) }"""
    query = """
SELECT ?iso ?role ?person ?personLabel ?img ?start WHERE {""" + country_filter + office + """
  OPTIONAL { ?person wdt:P18 ?img. }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "de,en". }
}"""
    r = requests.get("https://query.wikidata.org/sparql", params={"query": query, "format": "json"},
                     headers={"User-Agent": "TradeBot-Dashboard/1.0 (GitHub Actions)", "Accept": "application/sparql-results+json"}, timeout=60)
    r.raise_for_status()
    out: dict[str, list[dict]] = {}
    rows = r.json()["results"]["bindings"]
    if by_statement:  # je Land und Amt nur den jüngsten Amtsantritt behalten
        latest = {}
        for b in rows:
            k = (b["iso"]["value"], b["role"]["value"])
            if k not in latest or b.get("start", {}).get("value", "") > latest[k].get("start", {}).get("value", ""):
                latest[k] = b
        rows = list(latest.values())
    for b in rows:
        iso, name = b["iso"]["value"], b["personLabel"]["value"]
        if name.startswith("Q") and name[1:].isdigit():
            continue
        lst = out.setdefault(iso, [])
        if any(x["name"] == name for x in lst):
            for x in lst:
                if x["name"] == name and b["role"]["value"] not in x["role"]:
                    x["role"] += " & " + b["role"]["value"]
            continue
        img = b.get("img", {}).get("value", "")
        if img.startswith("http://"):
            img = "https://" + img[len("http://"):]
        lst.append({"role": b["role"]["value"], "name": name, "img": img + "?width=320" if img else "",
                    "wiki": b["person"]["value"]})
    return out


def _imf(code: str) -> dict[str, list]:
    r = requests.get(f"https://www.imf.org/external/datamapper/api/v1/{code}", headers=UA, timeout=40)
    r.raise_for_status()
    vals = r.json()["values"][code]
    return {iso: [v.get(str(y)) for y in YEARS] for iso, v in vals.items() if len(iso) == 3}


def _worldbank(code: str, factor: float) -> dict[str, list]:
    url = f"https://api.worldbank.org/v2/country/all/indicator/{code}?format=json&date={YEARS[0]}:{YEARS[-1]}&per_page=20000"
    rows = requests.get(url, headers=UA, timeout=60).json()[1] or []
    out: dict[str, list] = {}
    for row in rows:
        iso, year, v = row.get("countryiso3code"), int(row["date"]), row.get("value")
        if not iso or v is None:
            continue
        out.setdefault(iso, [None] * len(YEARS))[YEARS.index(year)] = v * factor
    return out


def fetch_indicators() -> tuple[dict, dict]:
    data, source = {}, {}
    for imf, (wb, factor) in INDICATORS.items():
        try:
            data[imf], source[imf] = _imf(imf), "IMF World Economic Outlook"
        except Exception as e:
            print(f"IMF {imf} fehlgeschlagen ({e!r}), nutze Weltbank")
            try:
                data[imf], source[imf] = _worldbank(wb, factor), "Weltbank"
            except Exception as e2:
                print(f"Weltbank {wb} fehlgeschlagen ({e2!r})")
        if imf in data:  # auf 3 signifikante Stellen runden spart Platz
            data[imf] = {iso: [None if v is None else float(f"{v:.4g}") for v in vals] for iso, vals in data[imf].items()}
    return data, source


def escalation_from_news(titles: list[str]) -> dict[str, dict]:
    """Ausweichlösung ohne KI: Konflikt-Schlagzeilen je Land zählen."""
    hits: dict[str, list[str]] = {}
    for t in titles:
        low = t.lower()
        if not any(w in low for w in CONFLICT_WORDS):
            continue
        for iso, words in COUNTRY_WORDS.items():
            if any(w in low for w in words):
                hits.setdefault(iso, []).append(t)
    out = {}
    for iso, hs in hits.items():
        level = 1 if len(hs) == 1 else 2 if len(hs) <= 3 else 3
        out[iso] = {"stufe": level, "grund": f"{len(hs)} Konflikt-Schlagzeile(n), z. B.: {hs[0]}", "quelle": "Nachrichten-Zählung"}
    return out


def export(titles: list[str], analysis: dict | None) -> None:
    previous = {}
    if OUT.exists():  # bei Ausfall der Datenquellen alte Werte behalten
        try:
            previous = json.loads(OUT.read_text()[len("window.WORLD = "):-2])
        except Exception:
            previous = {}
    indicators, source = fetch_indicators()
    for code in INDICATORS:
        if code not in indicators and code in previous.get("indicators", {}):
            indicators[code] = previous["indicators"][code]
            source[code] = previous.get("source", {}).get(code, "") + " (älterer Stand)"

    try:
        leaders = fetch_leaders()
        print(f"Staatsführung: {len(leaders)} Länder")
    except Exception as e:
        print("Wikidata fehlgeschlagen:", repr(e))
        leaders = previous.get("leaders", {})
    escalation = escalation_from_news(titles)
    inflation_now = {}
    if analysis:
        for c in analysis.get("laender_risiko", []):
            escalation[c["iso3"]] = {"stufe": c["stufe"], "grund": c["grund"], "quelle": "KI-Analyse"}
            if c.get("inflation_aktuell"):
                inflation_now[c["iso3"]] = c["inflation_aktuell"]

    payload = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "years": YEARS,
        "key": KEY,
        "indicators": indicators,
        "source": source,
        "escalation": escalation,
        "inflation_now": inflation_now,
        "ausblick_2050": (analysis or {}).get("ausblick_2050"),
        "gold": {"reserven": GOLD_RESERVES, "foerderung": GOLD_PRODUCTION, "source": GOLD_SOURCE},
        "leaders": leaders,
        "analysis_time": (analysis or {}).get("time"),
    }
    OUT.write_text("window.WORLD = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print(f"Welt-Daten: {len(indicators)} Kennzahlen, {len(escalation)} Länder mit Eskalation, {OUT.stat().st_size // 1024} KB")
