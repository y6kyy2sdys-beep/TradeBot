"""Weltwirtschaft für das Dashboard: IMF-Daten (Ist + Prognose bis ~2030), Eskalationsstufen je Land.

Quelle 1: IMF DataMapper (World Economic Outlook, ohne Schlüssel).
Quelle 2 (Ausweichlösung): Weltbank-API (nur Ist-Werte).
Die Szenarien bis 2050 rechnet das Dashboard selbst aus diesen Werten (siehe docs/index.html).
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import requests

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
        "analysis_time": (analysis or {}).get("time"),
    }
    OUT.write_text("window.WORLD = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print(f"Welt-Daten: {len(indicators)} Kennzahlen, {len(escalation)} Länder mit Eskalation, {OUT.stat().st_size // 1024} KB")
