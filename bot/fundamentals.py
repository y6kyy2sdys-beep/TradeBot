"""Abruf und Zwischenspeicherung von Unternehmensdaten über yfinance (Yahoo Finance, inoffiziell).

Cache in state/research_cache.json, je Datensatz mit Abrufzeit. Abruf priorisiert die ältesten Einträge und
ist zeitlich begrenzt, damit der Lauf stabil bleibt; fehlende Daten bleiben fehlend (nie geschätzt).
"""

import json
import math
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "state" / "research_cache.json"
NOW = datetime.now(timezone.utc)

INFO_KEYS = (
    "shortName", "longName", "quoteType", "sector", "industry", "country", "currency", "financialCurrency", "exchange",
    "marketCap", "enterpriseValue", "currentPrice", "regularMarketPrice", "previousClose", "sharesOutstanding",
    "trailingPE", "forwardPE", "priceToBook", "priceToSalesTrailing12Months", "enterpriseToEbitda", "enterpriseToRevenue",
    "trailingPegRatio", "dividendYield", "payoutRatio", "beta", "totalRevenue", "ebitda", "freeCashflow", "operatingCashflow",
    "totalDebt", "totalCash", "grossMargins", "operatingMargins", "ebitdaMargins", "profitMargins", "returnOnEquity",
    "returnOnAssets", "revenueGrowth", "earningsGrowth", "debtToEquity", "currentRatio", "bookValue", "trailingEps", "forwardEps",
    "targetMeanPrice", "targetMedianPrice", "targetHighPrice", "targetLowPrice", "numberOfAnalystOpinions",
    "recommendationMean", "recommendationKey", "shortPercentOfFloat", "heldPercentInsiders", "lastFiscalYearEnd",
    "mostRecentQuarter", "fullTimeEmployees", "website",
)
IS_ROWS = ("Total Revenue", "Gross Profit", "Operating Income", "EBIT", "EBITDA", "Net Income", "Diluted EPS",
           "Interest Expense", "Tax Rate For Calcs", "Reconciled Depreciation", "Diluted Average Shares", "Pretax Income", "Tax Provision")
BS_ROWS = ("Total Debt", "Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments", "Stockholders Equity",
           "Ordinary Shares Number", "Working Capital", "Invested Capital", "Total Assets", "Current Assets", "Current Liabilities",
           "Goodwill And Other Intangible Assets")
CF_ROWS = ("Free Cash Flow", "Operating Cash Flow", "Capital Expenditure", "Repurchase Of Capital Stock", "Cash Dividends Paid",
           "Change In Working Capital", "Stock Based Compensation")
QIS_ROWS = ("Total Revenue", "Operating Income", "Net Income", "Diluted EPS")
QCF_ROWS = ("Free Cash Flow", "Operating Cash Flow")


def _num(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) or math.isinf(v) else float(f"{v:.6g}")


def _stmt(df: pd.DataFrame | None, rows, n: int) -> dict | None:
    if df is None or df.empty:
        return None
    cols = sorted(df.columns, reverse=True)[:n]
    out = {"periods": [pd.Timestamp(c).strftime("%Y-%m-%d") for c in cols]}
    for r in rows:
        if r in df.index:
            vals = [_num(df.at[r, c]) for c in cols]
            if any(v is not None for v in vals):
                out[r] = vals
    return out if len(out) > 1 else None


def _frame(df: pd.DataFrame | None, cols=None) -> dict | None:
    if df is None or getattr(df, "empty", True):
        return None
    df = df[[c for c in (cols or df.columns) if c in df.columns]]
    return {str(i): {c: (_num(v) if not isinstance(v, str) else v) for c, v in row.items()} for i, row in df.iterrows()}


# ---------------------------------------------------------------- Abrufer je Datentyp
def get_info(t):
    info = yf.Ticker(t).info or {}
    d = {k: info.get(k) for k in INFO_KEYS if info.get(k) is not None}
    if "longBusinessSummary" in info:
        d["summary"] = info["longBusinessSummary"][:700]
    return d if d.get("quoteType") else None


def get_estimates(t):
    T = yf.Ticker(t)
    d = {}
    for key, fn in (("eps_trend", lambda: _frame(T.eps_trend, ["current", "7daysAgo", "30daysAgo", "60daysAgo", "90daysAgo"])),
                    ("eps_rev", lambda: _frame(T.eps_revisions, ["upLast7days", "upLast30days", "downLast30days", "downLast7Days"])),
                    ("eps_est", lambda: _frame(T.earnings_estimate, ["avg", "low", "high", "yearAgoEps", "numberOfAnalysts", "growth"])),
                    ("rev_est", lambda: _frame(T.revenue_estimate, ["avg", "low", "high", "numberOfAnalysts", "yearAgoRevenue", "growth"])),
                    ("surprise", lambda: _frame(T.earnings_history, ["epsActual", "epsEstimate", "surprisePercent"]))):
        try:
            d[key] = fn()
        except Exception:
            d[key] = None
    return d if any(d.values()) else None


def get_light_estimates(t):   # für ETF-Top-Positionen außerhalb des Universums
    T = yf.Ticker(t)
    d = {}
    for key, fn in (("eps_trend", lambda: _frame(T.eps_trend, ["current", "90daysAgo"])),
                    ("eps_rev", lambda: _frame(T.eps_revisions, ["upLast30days", "downLast30days"]))):
        try:
            d[key] = fn()
        except Exception:
            d[key] = None
    return d if any(d.values()) else None


def get_events(t):
    T = yf.Ticker(t)
    d = {}
    try:
        cal = T.calendar or {}
        d["calendar"] = {k: (v[0].isoformat() if isinstance(v, list) and v else v.isoformat() if hasattr(v, "isoformat") else _num(v))
                         for k, v in cal.items() if k in ("Earnings Date", "Ex-Dividend Date", "Dividend Date", "Earnings Average", "Revenue Average")}
    except Exception:
        d["calendar"] = None
    try:
        ud = T.upgrades_downgrades
        if ud is not None and not ud.empty:
            ud = ud[ud.index >= pd.Timestamp.now() - pd.Timedelta(days=90)].head(15)
            d["actions"] = [{"date": pd.Timestamp(i).strftime("%Y-%m-%d"), "firm": r.get("Firm"), "to": r.get("ToGrade"), "from": r.get("FromGrade"),
                             "action": r.get("Action"), "pt_action": r.get("priceTargetAction"), "pt": _num(r.get("currentPriceTarget"))}
                            for i, r in ud.iterrows()]
    except Exception:
        d["actions"] = None
    return d


def get_statements(t):
    T = yf.Ticker(t)
    d = {}
    for key, fn in (("is", lambda: _stmt(T.income_stmt, IS_ROWS, 5)), ("bs", lambda: _stmt(T.balance_sheet, BS_ROWS, 5)),
                    ("cf", lambda: _stmt(T.cashflow, CF_ROWS, 5)), ("qis", lambda: _stmt(T.quarterly_income_stmt, QIS_ROWS, 5)),
                    ("qcf", lambda: _stmt(T.quarterly_cashflow, QCF_ROWS, 5))):
        try:
            d[key] = fn()
        except Exception:
            d[key] = None
    return d if d.get("is") else None


def get_fund(t):
    fd = yf.Ticker(t).funds_data
    d = {}
    try:
        eh = fd.equity_holdings
        col = eh.columns[0]
        # Yahoo liefert hier Kehrwerte (z. B. Price/Earnings 0,0316 ≙ KGV 31,6) – als Renditen gespeichert
        d["yields"] = {k: _num(eh.at[k, col]) for k in ("Price/Earnings", "Price/Book", "Price/Sales", "Price/Cashflow") if k in eh.index}
    except Exception:
        d["yields"] = None
    try:
        th = fd.top_holdings
        d["top"] = [{"t": str(i), "n": r.get("Name"), "w": _num(r.get("Holding Percent"))} for i, r in th.iterrows()]
    except Exception:
        d["top"] = None
    return d if d.get("top") or d.get("yields") else None


FETCHERS = {"info": (get_info, timedelta(hours=20)), "est": (get_estimates, timedelta(hours=44)),
            "lest": (get_light_estimates, timedelta(hours=44)), "events": (get_events, timedelta(hours=20)),
            "stm": (get_statements, timedelta(days=6)), "fund": (get_fund, timedelta(days=6))}


class Store:
    def __init__(self):
        self.c = json.loads(CACHE.read_text()) if CACHE.exists() else {}
        self.deadline = time.time() + 26 * 60
        self.stats = {}

    def get(self, kind, t):
        e = self.c.get(kind, {}).get(t)
        return e["d"] if e else None

    def age(self, kind, t):
        e = self.c.get(kind, {}).get(t)
        return e and e["ts"]

    def refresh(self, kind: str, tickers: list[str], limit: int, workers: int = 6):
        fn, ttl = FETCHERS[kind]
        box = self.c.setdefault(kind, {})
        due = [t for t in tickers if t not in box or NOW - datetime.fromisoformat(box[t]["ts"]) > ttl]
        due.sort(key=lambda t: box[t]["ts"] if t in box else "")
        due = due[:limit]
        ok = 0

        def run(t):
            if time.time() > self.deadline:
                return t, None, "zeit"
            for attempt in range(2):
                try:
                    return t, fn(t), None
                except Exception as e:
                    err = f"{type(e).__name__}"
                    time.sleep(2 + 3 * attempt)
            return t, None, err

        with ThreadPoolExecutor(max_workers=workers) as pool:
            for t, d, err in pool.map(run, due):
                if d:
                    box[t] = {"ts": NOW.isoformat(timespec="minutes"), "d": d}
                    ok += 1
        self.stats[kind] = {"due": len(due), "ok": ok, "cached": len(box), "requested": len(tickers)}
        print(f"Daten {kind}: {ok}/{len(due)} aktualisiert, {sum(1 for t in tickers if t in box)}/{len(tickers)} vorhanden")

    def save(self):
        CACHE.parent.mkdir(exist_ok=True)
        CACHE.write_text(json.dumps(self.c, ensure_ascii=False, separators=(",", ":")))
