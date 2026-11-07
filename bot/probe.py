"""Diagnose: zeigt die Struktur der freien Datenquellen (nur Log-Ausgabe, schreibt nichts)."""
import io

import pandas as pd
import requests
import yfinance as yf

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 12)


def show(label, fn):
    try:
        v = fn()
        print(f"\n### {label} -> {type(v).__name__}")
        if isinstance(v, pd.DataFrame):
            print(v.iloc[:40, :6].to_string())
        else:
            print(repr(v)[:1500])
    except Exception as e:
        print(f"\n### {label} -> FEHLER {type(e).__name__}: {e}")


for t in ["AAPL", "SAP.DE", "JPM", "TSM"]:
    T = yf.Ticker(t)
    print(f"\n================ {t}")
    show("info-keys", lambda: sorted(k for k in (T.info or {}) if any(s in k.lower() for s in ("currency", "ebitda", "margin", "debt", "cash", "shares", "enterprise", "growth", "return", "beta", "target", "eps", "fiscal", "recommend"))))
    show("financialCurrency", lambda: (T.info.get("financialCurrency"), T.info.get("currency")))
    show("income_stmt", lambda: T.income_stmt)
    show("balance_sheet", lambda: T.balance_sheet)
    show("cashflow", lambda: T.cashflow)
    show("quarterly_income_stmt", lambda: T.quarterly_income_stmt.iloc[:12])
    show("eps_trend", lambda: T.eps_trend)
    show("eps_revisions", lambda: T.eps_revisions)
    show("revenue_estimate", lambda: T.revenue_estimate)
    show("earnings_estimate", lambda: T.earnings_estimate)
    show("growth_estimates", lambda: T.growth_estimates)
    show("earnings_history", lambda: T.earnings_history)
    show("upgrades_downgrades", lambda: T.upgrades_downgrades.head(8))
    show("calendar", lambda: T.calendar)
    show("analyst_price_targets", lambda: T.analyst_price_targets)

for t in ["XLK", "KBE", "IGV"]:
    T = yf.Ticker(t)
    print(f"\n================ ETF {t}")
    show("equity_holdings", lambda: T.funds_data.equity_holdings)
    show("top_holdings", lambda: T.funds_data.top_holdings)
    show("sector_weightings", lambda: T.funds_data.sector_weightings)

for sid in ["DGS10", "BAMLH0A0HYM2", "CPILFESL", "IRLTLT01DEM156N", "ECBDFR", "NFCI"]:
    try:
        r = requests.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", timeout=30,
                         headers={"User-Agent": "TradeBot research"})
        df = pd.read_csv(io.StringIO(r.text))
        print(f"\nFRED {sid}: HTTP {r.status_code}, {len(df)} Zeilen, Spalten {list(df.columns)}, letzte: {df.tail(2).values.tolist()}")
    except Exception as e:
        print(f"\nFRED {sid}: FEHLER {e}")
