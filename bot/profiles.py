"""Aktien-Steckbriefe für die Suche im Dashboard (docs/profiles.js).

Je Wert: Stammdaten, Kursverlauf (2 Jahre), Technik, Fundamentaldaten und eine regelbasierte
Einschätzung für kurzfristig (Wochen) und mittelfristig (Monate) mit Begründungen.
Fundamentaldaten werden ~1x täglich aktualisiert und in state/fundamentals.json zwischengespeichert.
"""

import json
import math
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from .strategies import rsi
from .watchlist import CRYPTO, ETFS, PROFILE_EXTRA, STOCKS_ASIA, STOCKS_EU, STOCKS_US
from .wkn import NAMES, search_url, wkn

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "profiles.js"
CACHE = ROOT / "state" / "fundamentals.json"
TICKERS = list(dict.fromkeys(STOCKS_US + STOCKS_EU + STOCKS_ASIA + PROFILE_EXTRA + ETFS + CRYPTO))
KEEP = ("shortName", "longName", "quoteType", "sector", "industry", "country", "currency", "exchange", "marketCap",
        "trailingPE", "forwardPE", "trailingPegRatio", "priceToSalesTrailing12Months", "priceToBook",
        "trailingAnnualDividendYield", "profitMargins", "revenueGrowth", "earningsGrowth", "returnOnEquity",
        "debtToEquity", "freeCashflow", "beta", "recommendationKey", "targetMeanPrice", "numberOfAnalystOpinions",
        "longBusinessSummary", "fullTimeEmployees", "website")
REFRESH = timedelta(hours=20)


def _r(v, d=4):
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return None
    return float(f"{v:.{d}g}") if isinstance(v, (int, float)) else v


def load_fundamentals(tickers: list[str]) -> dict:
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    now = datetime.now(timezone.utc)
    stale = [t for t in tickers if t not in cache or now - datetime.fromisoformat(cache[t]["t"]) > REFRESH]

    def fetch(t):
        try:
            info = yf.Ticker(t).info or {}
            return t, {k: info.get(k) for k in KEEP if info.get(k) is not None}
        except Exception:
            return t, None

    with ThreadPoolExecutor(max_workers=8) as pool:
        for t, info in pool.map(fetch, stale):
            if info:
                if info.get("longBusinessSummary"):
                    info["longBusinessSummary"] = info["longBusinessSummary"][:600]
                cache[t] = {"t": now.isoformat(timespec="minutes"), "info": info}
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, separators=(",", ":")))
    print(f"Fundamentaldaten: {len(stale)} aktualisiert, {len(cache)} im Speicher")
    return {t: v["info"] for t, v in cache.items()}


def _closes(tickers: list[str]) -> dict[str, pd.Series]:
    raw = yf.download(tickers, period="2y", interval="1d", group_by="ticker", auto_adjust=True, threads=True, progress=False)
    out = {}
    for t in tickers:
        try:
            c = (raw[t]["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw["Close"]).dropna()
        except KeyError:
            continue
        if len(c) > 60:
            c.index = pd.to_datetime(c.index).tz_localize(None).normalize()
            out[t] = c
    return out


def technicals(c: pd.Series) -> dict:
    last = c.iat[-1]
    ret = lambda n: last / c.iat[-n - 1] - 1 if len(c) > n else None
    year = c[c.index >= pd.Timestamp(c.index[-1].year, 1, 1)]
    r = c.pct_change().dropna()
    one_y = c.iloc[-252:]
    return {
        "last": last, "d1": ret(1), "w1": ret(5), "m1": ret(21), "m3": ret(63), "m6": ret(126), "y1": ret(252),
        "ytd": last / year.iat[0] - 1 if len(year) > 1 else None,
        "high52": one_y.max(), "low52": one_y.min(),
        "sma20": c.rolling(20).mean().iat[-1], "sma50": c.rolling(50).mean().iat[-1],
        "sma200": c.rolling(200).mean().iat[-1] if len(c) >= 200 else None,
        "rsi": rsi(c, 14).iat[-1],
        "vol": r.iloc[-252:].std() * np.sqrt(252),
        "maxdd": (one_y / one_y.cummax() - 1).min(),
    }


def verdict(tech: dict, info: dict, fee_pct: float) -> dict:
    """Regelbasierte Einschätzung mit Begründungen. Kein Ersatz für eigene Prüfung."""
    def score(points: list[tuple[int, str]]):
        s = 50 + sum(p for p, _ in points)
        s = max(0, min(100, s))
        label = "interessant" if s >= 65 else "neutral – abwarten" if s >= 40 else "eher meiden"
        return {"score": s, "label": label, "pro": [t for p, t in points if p > 0], "contra": [t for p, t in points if p < 0]}

    last, s20, s50, s200, r = tech["last"], tech["sma20"], tech["sma50"], tech["sma200"], tech["rsi"]
    short = []
    short.append((15, "Kurs über der 50-Tage-Linie (kurzfristiger Aufwärtstrend)") if last > s50 else (-15, "Kurs unter der 50-Tage-Linie (kurzfristiger Abwärtstrend)"))
    short.append((10, "20-Tage-Linie über der 50-Tage-Linie (Momentum dreht nach oben)") if s20 > s50 else (-10, "20-Tage-Linie unter der 50-Tage-Linie (Momentum schwach)"))
    if r < 30 and s200 and last > s200:
        short.append((15, f"Überverkauft (RSI {r:.0f}) im langfristigen Aufwärtstrend – Rebound-Chance"))
    elif r < 30:
        short.append((-5, f"Überverkauft (RSI {r:.0f}), aber ohne intakten Langfristtrend – fallendes Messer"))
    elif r > 75:
        short.append((-15, f"Überkauft (RSI {r:.0f}) – Rücksetzer wahrscheinlich"))
    elif 45 <= r <= 65:
        short.append((5, f"RSI {r:.0f} im gesunden Bereich"))
    if tech["m1"] is not None:
        if tech["m1"] > 0.05:
            short.append((10, f"Starker Monat ({tech['m1']:+.0%})"))
        elif tech["m1"] < -0.10:
            short.append((-10, f"Schwacher Monat ({tech['m1']:+.0%})"))
    if tech["vol"] > 0.6:
        short.append((-10, f"Sehr schwankungsanfällig ({tech['vol']:.0%} Volatilität p. a.) – Stop-Loss nötig"))
    if last >= tech["high52"] * 0.97 and last > s50:
        short.append((5, "Nahe am 52-Wochen-Hoch – Ausbruch möglich"))
    daily_move = tech["vol"] / np.sqrt(252)
    if daily_move * np.sqrt(10) < fee_pct * 2:
        short.append((-10, f"Typische 2-Wochen-Bewegung (≈{daily_move * np.sqrt(10):.1%}) zu klein für {fee_pct:.0%} Gebühren"))

    mid = []
    if s200:
        mid.append((15, f"Über der 200-Tage-Linie ({last / s200 - 1:+.0%}) – langfristiger Aufwärtstrend") if last > s200
                   else (-15, f"Unter der 200-Tage-Linie ({last / s200 - 1:+.0%}) – langfristiger Abwärtstrend"))
    if tech["m6"] is not None:
        if tech["m6"] > 0.10:
            mid.append((10, f"6 Monate {tech['m6']:+.0%}"))
        elif tech["m6"] < -0.15:
            mid.append((-10, f"6 Monate {tech['m6']:+.0%}"))
    if info.get("quoteType") == "EQUITY":
        fpe, peg = info.get("forwardPE"), info.get("trailingPegRatio")
        if fpe is not None and fpe > 0:
            if fpe < 15:
                mid.append((10, f"Günstig bewertet (erwartetes KGV {fpe:.1f})"))
            elif fpe > 40:
                mid.append((-10, f"Hoch bewertet (erwartetes KGV {fpe:.0f})"))
        if peg is not None and 0 < peg < 1.5:
            mid.append((5, f"Wachstum im Verhältnis zur Bewertung günstig (PEG {peg:.1f})"))
        m = info.get("profitMargins")
        if m is not None:
            if m < 0:
                mid.append((-15, f"Schreibt Verluste (Marge {m:.0%})"))
            elif m > 0.2:
                mid.append((5, f"Hohe Gewinnmarge ({m:.0%})"))
        g = info.get("revenueGrowth")
        if g is not None:
            if g > 0.10:
                mid.append((10, f"Umsatz wächst stark ({g:+.0%})"))
            elif g < 0:
                mid.append((-10, f"Umsatz schrumpft ({g:+.0%})"))
        d = info.get("debtToEquity")
        if d is not None and d > 200:
            mid.append((-10, f"Hohe Verschuldung ({d:.0f} % des Eigenkapitals)"))
        tgt = info.get("targetMeanPrice")
        if tgt:
            up = tgt / last - 1
            if up > 0.15:
                mid.append((10, f"Analysten sehen {up:+.0%} Potenzial (Ø Kursziel {tgt:.2f})"))
            elif up < 0:
                mid.append((-10, f"Kurs über dem Ø Analystenziel ({up:+.0%})"))
        rec = info.get("recommendationKey")
        if rec in ("buy", "strong_buy"):
            mid.append((5, "Analysten-Konsens: Kaufen"))
        elif rec in ("sell", "strong_sell", "underperform"):
            mid.append((-10, "Analysten-Konsens: Verkaufen"))
    return {"kurz": score(short), "mittel": score(mid)}


def clean_name(raw: str) -> str:
    """Yahoo-Namen lesbar machen: Gattungskürzel (N, I, V, NA O.N. ...) weg, GROSSBUCHSTABEN normalisieren."""
    name = re.sub(r"(\s+(N|I|V|A|NA|ON|O\.N\.|INH|VZO|VZ|ST|NAM|EO|-,?\d+))+\.?$", "", " ".join(str(raw).split()))
    if name.isupper() and len(name) > 4:
        keep = {"SE", "AG", "CO.", "N.V.", "+", "&"}
        name = " ".join("KGaA" if w == "KGAA" else w if w in keep or len(w) <= 2 else w.capitalize() for w in name.split())
    return name.replace("Aktiengesellschaft", "AG")


def export(fee_pct: float, calls: dict[str, dict]) -> None:
    infos = load_fundamentals([t for t in TICKERS if t not in CRYPTO])
    closes = _closes(TICKERS)
    epoch = pd.Timestamp("1970-01-01")
    profiles = []
    for t in TICKERS:
        c = closes.get(t)
        if c is None:
            continue
        info = infos.get(t, {})
        tech = technicals(c)
        kind = "Krypto" if t in CRYPTO else "ETF" if t in ETFS or info.get("quoteType") == "ETF" else "Aktie"
        name = clean_name(NAMES.get(t) or info.get("longName") or info.get("shortName") or t)
        tgt = info.get("targetMeanPrice")
        profiles.append({
            "t": t, "n": name, "k": kind, "w": wkn(t), "s": search_url(name),
            "sec": info.get("sector"), "ind": info.get("industry"), "land": info.get("country"),
            "cur": info.get("currency"), "ex": info.get("exchange"), "mcap": _r(info.get("marketCap")),
            "desc": info.get("longBusinessSummary"), "web": info.get("website"), "emp": info.get("fullTimeEmployees"),
            "tech": {k: _r(v) for k, v in tech.items()},
            "fund": {k: _r(info.get(k)) for k in ("trailingPE", "forwardPE", "trailingPegRatio", "priceToSalesTrailing12Months",
                                                  "priceToBook", "trailingAnnualDividendYield", "profitMargins", "revenueGrowth",
                                                  "earningsGrowth", "returnOnEquity", "debtToEquity", "freeCashflow", "beta",
                                                  "numberOfAnalystOpinions")},
            "an": {"rec": info.get("recommendationKey"), "tgt": _r(tgt), "up": _r(tgt / tech["last"] - 1) if tgt else None},
            "v": verdict(tech, info, fee_pct),
            "call": calls.get(t),
            "d0": int((c.index[0] - epoch).days),
            # Tagesabstände als Ziffernfolge (spart Platz), Kurse auf 4 Stellen
            "g": "".join(str(min(9, int(x))) for x in np.diff((c.index - epoch).days)),
            "px": [_r(x, 4) for x in c.tolist()],
        })
    OUT.write_text("window.PROFILES = " + json.dumps(profiles, ensure_ascii=False, separators=(",", ":")) + ";\n")
    try:
        from . import stocknews
        stocknews.export([(x["t"], x["n"]) for x in profiles if x["k"] == "Aktie"])
    except Exception as e:
        print("Unternehmens-News fehlgeschlagen:", repr(e))
    print(f"Steckbriefe: {len(profiles)} Werte, {OUT.stat().st_size // 1024} KB")
