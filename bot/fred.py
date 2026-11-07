"""Makro-Zeitreihen der Federal Reserve Bank of St. Louis (FRED), CSV-Abruf ohne API-Schlüssel.

Jede Reihe trägt Metadaten (Quelle, Einheit, Frequenz, Art), damit das Dashboard Stand und Herkunft zeigt.
"""

import io
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests

URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}&cosd={}"
SOURCE_URL = "https://fred.stlouisfed.org/series/{}"

# id: (Bezeichnung, Einheit, Frequenz, Ursprungsquelle)
SERIES = {
    "DGS3MO": ("US-Staatsanleihe 3 Monate", "%", "täglich", "U.S. Treasury via FRED"),
    "DGS2": ("US-Staatsanleihe 2 Jahre", "%", "täglich", "U.S. Treasury via FRED"),
    "DGS10": ("US-Staatsanleihe 10 Jahre", "%", "täglich", "U.S. Treasury via FRED"),
    "T10Y3M": ("Zinskurve 10J − 3M (USA)", "Prozentpunkte", "täglich", "FRED"),
    "T10Y2Y": ("Zinskurve 10J − 2J (USA)", "Prozentpunkte", "täglich", "FRED"),
    "T10YIE": ("Inflationserwartung 10J (Breakeven)", "%", "täglich", "FRED"),
    "DFF": ("Fed Funds Rate", "%", "täglich", "Federal Reserve via FRED"),
    "ECBDFR": ("EZB-Einlagensatz", "%", "täglich", "EZB via FRED"),
    "IRLTLT01DEM156N": ("Bundesanleihe 10 Jahre", "%", "monatlich", "OECD via FRED"),
    "BAMLH0A0HYM2": ("Kreditspread High Yield (OAS)", "Prozentpunkte", "täglich", "ICE BofA via FRED"),
    "BAMLC0A0CM": ("Kreditspread Investment Grade (OAS)", "Prozentpunkte", "täglich", "ICE BofA via FRED"),
    "VIXCLS": ("VIX (implizite Volatilität S&P 500)", "Punkte", "täglich", "Cboe via FRED"),
    "NFCI": ("Finanzierungsbedingungen (Chicago Fed NFCI)", "Index (0 = Durchschnitt, >0 = straffer)", "wöchentlich", "Chicago Fed via FRED"),
    "WALCL": ("Fed-Bilanzsumme", "Mio. USD", "wöchentlich", "Federal Reserve via FRED"),
    "CPIAUCSL": ("US-Verbraucherpreise (CPI)", "Index", "monatlich", "BLS via FRED"),
    "CPILFESL": ("US-Kerninflation (Core CPI)", "Index", "monatlich", "BLS via FRED"),
    "PCEPILFE": ("US-Kern-PCE-Preisindex", "Index", "monatlich", "BEA via FRED"),
    "CP0000EZ19M086NEST": ("Eurozone Verbraucherpreise (HVPI)", "Index", "monatlich", "Eurostat via FRED"),
    "UNRATE": ("US-Arbeitslosenquote", "%", "monatlich", "BLS via FRED"),
    "PAYEMS": ("US-Beschäftigte außerhalb der Landwirtschaft", "Tsd.", "monatlich", "BLS via FRED"),
    "ICSA": ("US-Erstanträge Arbeitslosenhilfe", "Anzahl", "wöchentlich", "U.S. DOL via FRED"),
    "INDPRO": ("US-Industrieproduktion", "Index", "monatlich", "Federal Reserve via FRED"),
    "UMCSENT": ("US-Verbrauchervertrauen (Univ. Michigan)", "Index", "monatlich", "Univ. of Michigan via FRED"),
    "CES0500000003": ("US-Stundenlöhne (Privatsektor)", "USD", "monatlich", "BLS via FRED"),
    "DCOILWTICO": ("WTI-Rohöl (Spot)", "USD/Barrel", "täglich", "EIA via FRED"),
    "DTWEXBGS": ("US-Dollar (handelsgewichtet, breit)", "Index", "täglich", "Federal Reserve via FRED"),
}


def fetch(sid: str, start: str = "1995-01-01") -> pd.Series | None:
    try:
        r = requests.get(URL.format(sid, start), timeout=40, headers={"User-Agent": "TradeBot research (private use)"})
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        s = pd.to_numeric(df.iloc[:, 1], errors="coerce")
        s.index = pd.to_datetime(df.iloc[:, 0])
        s = s.dropna()
        return s if len(s) else None
    except Exception as e:  # Netzwerk/Format – fehlende Reihe wird im UI als „keine Daten“ gezeigt
        print(f"FRED {sid}: {type(e).__name__}: {e}")
        return None


def load_all() -> dict[str, pd.Series]:
    with ThreadPoolExecutor(max_workers=6) as pool:
        res = dict(zip(SERIES, pool.map(fetch, SERIES)))
    ok = {k: v for k, v in res.items() if v is not None}
    print(f"FRED: {len(ok)}/{len(SERIES)} Reihen geladen")
    return ok


def meta(sid: str, s: pd.Series | None) -> dict:
    label, unit, freq, origin = SERIES[sid]
    return {"id": sid, "label": label, "unit": unit, "freq": freq, "source": origin, "url": SOURCE_URL.format(sid),
            "asof": s.index[-1].strftime("%Y-%m-%d") if s is not None and len(s) else None, "type": "Ist-Wert (amtliche Statistik/Marktdaten)"}
