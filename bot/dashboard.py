"""Exportiert die Daten für das Matrix-Dashboard (docs/data.js, gelesen von docs/index.html)."""

import json
import math
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import pandas as pd
import yfinance as yf

from . import depot as depot_mod
from . import sectors as sector_mod
from .macro import SCENARIOS
from .strategies import rsi
from .watchlist import STOCKS_ASIA, STOCKS_EU, STOCKS_US
from .wkn import name as display_name, search_url, wkn

OUT = Path(__file__).resolve().parent.parent / "docs" / "data.js"
HISTORY = "10y"

# Reihenfolge = feste Farbreihenfolge im Hauptchart (max. 8 Serien)
INDICES = {
    "^GSPC": "S&P 500", "^NDX": "Nasdaq 100", "^STOXX50E": "Euro Stoxx 50", "^GDAXI": "DAX",
    "^FTSE": "FTSE 100", "^N225": "Nikkei 225", "000001.SS": "Shanghai Composite", "^HSI": "Hang Seng",
}
INDICES_EXTRA = {"URTH": "MSCI World (ETF)", "EEM": "MSCI Emerging Markets (ETF)", "^STOXX": "STOXX Europe 600", "^RUT": "Russell 2000",
                 "^DJI": "Dow Jones", "^FCHI": "CAC 40", "^BSESN": "Sensex (Indien)", "^KS11": "KOSPI (Korea)", "BTC-USD": "Bitcoin"}
COMMODITY_GROUPS = {
    "Energie": {"BZ=F": "Brent-Öl", "CL=F": "WTI-Öl", "NG=F": "Erdgas USA", "TTF=F": "Erdgas Europa (TTF)",
                "HO=F": "Heizöl", "RB=F": "Benzin"},
    "Edelmetalle": {"GC=F": "Gold", "SI=F": "Silber", "PL=F": "Platin", "PA=F": "Palladium"},
    "Industriemetalle": {"HG=F": "Kupfer", "ALI=F": "Aluminium", "LIT": "Lithium (ETF)", "URA": "Uran (ETF)"},
    "Agrar": {"ZW=F": "Weizen", "ZC=F": "Mais", "ZS=F": "Sojabohnen", "KC=F": "Kaffee", "CC=F": "Kakao",
              "SB=F": "Zucker", "CT=F": "Baumwolle", "OJ=F": "Orangensaft"},
    "Vieh": {"LE=F": "Lebendrind", "HE=F": "Mastschwein", "GF=F": "Mastrind"},
    "Währungen": {"EURUSD=X": "EUR/USD", "DX-Y.NYB": "US-Dollar-Index", "USDJPY=X": "USD/JPY", "^VIX": "VIX (Angstindex)"},
}
SECTORS = {
    "XLK": "Technologie", "SMH": "Halbleiter", "XLF": "Finanzen", "KRE": "Regionalbanken", "XLE": "Energie",
    "XOP": "Öl-Förderer", "XLV": "Gesundheit", "XLI": "Industrie", "ITA": "Rüstung & Luftfahrt",
    "XLY": "Zyklischer Konsum", "XLP": "Basiskonsum", "XLU": "Versorger", "XLB": "Grundstoffe",
    "XLRE": "Immobilien", "XLC": "Kommunikation", "URA": "Uran", "JETS": "Airlines",
}

IMPACT_WORDS = (
    "crash", "plunge", "tumble", "surge", "soar", "record", "sanction", "attack", "war", "strike", "missile",
    "default", "recession", "inflation", "rate cut", "rate hike", "tariff", "embargo", "blockade", "emergency",
    "einbruch", "absturz", "rekord", "krieg", "angriff", "sanktion", "zinsen", "inflation", "rezession",
    "zoll", "zölle", "notenbank", "eskalation", "pleite", "insolvenz",
)


def _round(v: float):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return float(f"{v:.5g}")


def _closes(raw: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    cols = {}
    for t in tickers:
        try:
            c = raw[t]["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw["Close"]
        except KeyError:
            continue
        c = c.dropna()
        if len(c) > 20:
            c.index = pd.to_datetime(c.index).tz_localize(None).normalize()
            cols[t] = c[~c.index.duplicated()]
    return pd.DataFrame(cols).sort_index()


def score_news(items: list[dict]) -> list[dict]:
    out = []
    for it in items:
        low = it["title"].lower()
        score, tag = 0, ""
        for sc in SCENARIOS:
            if any(k in low for k in sc.keywords):
                score += 3
                tag = tag or sc.title
        score += 2 * sum(w in low for w in IMPACT_WORDS)
        if score < 3:
            continue
        try:
            ts = parsedate_to_datetime(it["time"]).astimezone(timezone.utc).isoformat(timespec="minutes")
        except Exception:
            ts = ""
        out.append({**it, "time": ts, "score": score, "tag": tag or "Marktbewegend"})
    out.sort(key=lambda n: (n["score"], n["time"]), reverse=True)
    return out[:12]


def momentum(c: pd.Series) -> dict | None:
    c = c.dropna()
    if len(c) < 210:
        return None
    last = c.iat[-1]
    sma50, sma200 = c.rolling(50).mean().iat[-1], c.rolling(200).mean().iat[-1]
    m1, m3, m6 = last / c.iat[-22] - 1, last / c.iat[-64] - 1, last / c.iat[-127] - 1
    r = rsi(c, 14).iat[-1]
    trend = last > sma200 and sma50 > sma200
    return {
        "m1": _round(m1), "m3": _round(m3), "m6": _round(m6), "rsi": _round(r), "trend": bool(trend),
        "score": _round(0.2 * m1 + 0.5 * m3 + 0.3 * m6) if trend and r < 75 and m3 > 0 and m6 > 0 else None,
        "dist200": _round(last / sma200 - 1),
    }


def _reason(m: dict) -> str:
    return (f"Aufwärtstrend (über 200-Tage-Linie, {m['dist200']:+.0%}), "
            f"3 Monate {m['m3']:+.0%}, 6 Monate {m['m6']:+.0%}, RSI {m['rsi']:.0f} (nicht überkauft)")


def hot_picks(sector_closes: pd.DataFrame, stock_data: dict[str, pd.DataFrame]) -> dict:
    sectors = []
    for t, name in SECTORS.items():
        if t in sector_closes and (m := momentum(sector_closes[t])) and m["score"] is not None:
            sectors.append({"ticker": t, "name": name, **m, "reason": _reason(m), "wkn": "",
                            "search": search_url(f"{name} ETF UCITS")})
    stocks = []
    for t in STOCKS_US + STOCKS_EU + STOCKS_ASIA:
        df = stock_data.get(t)
        if df is not None and (m := momentum(df["Close"])) and m["score"] is not None:
            nm = display_name(t)
            stocks.append({"ticker": t, "name": nm, **m, "reason": _reason(m), "wkn": wkn(t), "search": search_url(nm)})
    sectors.sort(key=lambda x: x["score"], reverse=True)
    stocks.sort(key=lambda x: x["score"], reverse=True)
    return {"sectors": sectors[:6], "stocks": stocks[:8]}


def sector_cards(closes: pd.DataFrame, analysis: dict | None) -> list[dict]:
    outlook = {b["branche"]: b for b in (analysis or {}).get("branchen_ausblick", [])}
    out = []
    for key, name, etf, icon, query in sector_mod.SECTORS:
        m = momentum(closes[etf]) if etf in closes else None
        c = closes[etf].dropna() if etf in closes else None
        out.append({
            "key": key, "name": name, "etf": etf, "icon": icon,
            "d1": _round(c.iat[-1] / c.iat[-2] - 1) if c is not None and len(c) > 2 else None,
            "m1": m and m["m1"], "m3": m and m["m3"], "m6": m and m["m6"], "trend": bool(m and m["trend"]),
            "news": sector_mod.sector_news(query),
            "ki": outlook.get(key),
        })
    return out


def export(stock_data: dict[str, pd.DataFrame], news_items: list[dict], state: dict, regime: str) -> None:
    groups = {"Indizes": INDICES, "Weitere Indizes": INDICES_EXTRA, **COMMODITY_GROUPS}
    names = {t: n for g in groups.values() for t, n in g.items()}
    tickers = list(names) + list(SECTORS)
    raw = yf.download(tickers, period=HISTORY, interval="1d", group_by="ticker",
                      auto_adjust=True, threads=True, progress=False)
    closes = _closes(raw, tickers)
    hist = closes[[t for t in names if t in closes]]
    hist = hist[hist.notna().sum(axis=1) >= 3]  # Tage, an denen fast nichts gehandelt wurde, raus
    epoch = pd.Timestamp("1970-01-01")
    dates = [int((d - epoch).days) for d in hist.index]
    series = {
        t: {"name": names[t], "v": [_round(v) for v in hist[t].tolist()]}
        for t in hist.columns
    }
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "regime": regime,
        "groups": {g: [t for t in m if t in series] for g, m in groups.items()},
        "dates": dates,
        "series": series,
        "news": score_news(news_items),
        "ki": state.get("last_analysis"),
        "picks": {
            **hot_picks(closes, stock_data),
            "positions": [
                {**{k: s.get(k) for k in ("ticker", "name", "strategy", "signal_date", "ref_close", "target", "stop",
                                          "horizon", "branche", "these", "warum_jetzt", "szenarien", "ev_pct", "risiken")},
                 "wkn": s.get("wkn") or wkn(s["ticker"]), "search": search_url(s.get("name") or s["ticker"])}
                for s in state["open"]
            ],
        },
        "sectors": sector_cards(closes, state.get("last_analysis")),
        "alerts": state.get("alert_log", [])[-30:][::-1],
        "fx": depot_mod.fx_rates(),
        "record": {
            "closed": len(state["closed"]),
            "wins": sum(s["net_pct"] > 0 for s in state["closed"]),
        },
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("window.DASH = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print(f"Dashboard-Daten: {len(dates)} Tage, {len(series)} Reihen, {OUT.stat().st_size // 1024} KB")
