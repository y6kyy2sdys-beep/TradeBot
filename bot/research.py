"""Research-Lauf: Makro & Regime, Sector Intelligence, Aktien-Scanner, Red Flags, Bewertungs-Eingaben,
Katalysatoren und Backtest → docs/research.js (window.RESEARCH). Läuft täglich in .github/workflows/research.yml.
"""

import json
import math
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from . import backtest_sectors, fred, regime
from . import scoring as S
from .fundamentals import NOW, Store
from .watchlist import PROFILE_EXTRA, STOCKS_ASIA, STOCKS_EU, STOCKS_US
from .wkn import wkn

OUT = Path(__file__).resolve().parent.parent / "docs" / "research.js"
STOCKS = [t for t in dict.fromkeys(STOCKS_US + STOCKS_EU + STOCKS_ASIA + PROFILE_EXTRA) if t not in ("GDX",)]
MACRO_PANEL = ["DGS3MO", "DGS2", "DGS10", "T10Y3M", "IRLTLT01DEM156N", "DFF", "ECBDFR", "BAMLH0A0HYM2", "BAMLC0A0CM", "VIXCLS",
               "NFCI", "T10YIE", "UNRATE", "ICSA", "UMCSENT", "DCOILWTICO", "DTWEXBGS", "WALCL"]
YOY_PANEL = {"CPIAUCSL": "US-Inflation (CPI, ggü. Vorjahr)", "CPILFESL": "US-Kerninflation (Core CPI, ggü. Vorjahr)",
             "PCEPILFE": "US-Kern-PCE (ggü. Vorjahr)", "CP0000EZ19M086NEST": "Eurozone-Inflation (HVPI, ggü. Vorjahr)",
             "CES0500000003": "US-Lohnwachstum (ggü. Vorjahr)", "INDPRO": "US-Industrieproduktion (ggü. Vorjahr)"}


def r(v, d=4):
    return S.rnd(v, d)


def download(tickers, period, min_len=30):
    if not tickers:
        return pd.DataFrame(), pd.DataFrame()
    raw = yf.download(sorted(set(tickers)), period=period, interval="1d", group_by="ticker", auto_adjust=True, threads=True, progress=False)
    C, V = {}, {}
    for t in set(tickers):
        try:
            df = raw[t] if isinstance(raw.columns, pd.MultiIndex) else raw
            c = df["Close"].dropna()
        except KeyError:
            continue
        if len(c) >= min_len:
            idx = pd.to_datetime(c.index).tz_localize(None).normalize()
            C[t] = pd.Series(c.to_numpy(), index=idx)
            V[t] = pd.Series(df["Volume"].reindex(c.index).to_numpy(), index=idx)
    C = pd.DataFrame(C).sort_index()
    V = pd.DataFrame(V).sort_index()
    return C[~C.index.duplicated()], V[~V.index.duplicated()]


def fx_table(currencies: set[str]) -> dict[str, float]:
    cur = sorted(c for c in currencies if c and c != "USD")
    out = {"USD": 1.0}
    if not cur:
        return out
    C, _ = download([f"{c}USD=X" for c in cur], "10d", min_len=1)
    for c in cur:
        s = C.get(f"{c}USD=X")
        if s is not None and s.dropna().size:
            out[c] = float(s.dropna().iat[-1])
    print(f"Wechselkurse: {len(out)} Währungen")
    return out


def major(cur: str | None):
    if cur in S.MINOR:
        return S.MINOR[cur]
    return (cur, 1)


def fx_rate(fx: dict, a: str | None, b: str | None):
    if not a or not b:
        return None
    if a == b:
        return 1.0
    return fx[a] / fx[b] if a in fx and b in fx else None


def macro_panel(F: dict) -> list[dict]:
    rows = []
    for sid in MACRO_PANEL:
        s = F.get(sid)
        if s is None:
            rows.append({**fred.meta(sid, None), "value": None})
            continue
        m = s.resample("ME").last().dropna()
        last = float(s.iat[-1])
        ch = lambda n: float(last - m.iat[-1 - n]) if len(m) > n else None
        rows.append({**fred.meta(sid, s), "value": r(last), "d3m": r(ch(3)), "d12m": r(ch(12)), "kind": "level",
                     "hist": [[d.strftime("%Y-%m"), r(v)] for d, v in m.iloc[-120:].items()]})
    for sid, label in YOY_PANEL.items():
        s = F.get(sid)
        if s is None:
            rows.append({**fred.meta(sid, None), "label": label, "value": None})
            continue
        m = s.resample("ME").last().dropna()
        y = (m.pct_change(12) * 100).dropna()
        rows.append({**fred.meta(sid, s), "label": label, "unit": "%", "value": r(y.iat[-1]), "d3m": r(y.iat[-1] - y.iat[-4]) if len(y) > 4 else None,
                     "d12m": r(y.iat[-1] - y.iat[-13]) if len(y) > 13 else None, "kind": "yoy",
                     "hist": [[d.strftime("%Y-%m"), r(v)] for d, v in y.iloc[-120:].items()]})
    return rows


def historical_regimes(F: dict) -> pd.Series | None:
    try:
        idx = pd.date_range("2004-01-31", pd.Timestamp.now(), freq="ME")
        q = {t: regime.classify(F, None, None, t)["quadrant"] for t in idx}
        s = pd.Series(q).dropna()
        print(f"Historische Regime: {len(s)} Monate")
        return s
    except Exception as e:
        print("Regime-Historie:", e)
        return None


def sector_block(store, P, V, F, reg, hist_reg, fx, sector_hist) -> dict:
    spy = P[S.BENCH].dropna() if S.BENCH in P else None
    MF = S.macro_frame(F)
    metrics, info_out = {}, {}
    prev_metrics = {}
    for key, name, gics, proxy, is_fin in S.SECTORS:
        basket = isinstance(proxy, list)
        if basket:
            members = [t for t in proxy if t in P]
            if len(members) < 4:
                continue
            idx = P[members].pct_change().mean(axis=1, skipna=True).fillna(0)
            s = (1 + idx).cumprod()
            s = s[s.index >= P[members].dropna(how="all").index[0]]
            hold = [(t, 1 / len(proxy)) for t in proxy]
            fy = None
        else:
            if proxy not in P:
                continue
            s = P[proxy].dropna()
            fund = store.get("fund", proxy) or {}
            hold = [(h["t"], h["w"] or 0) for h in fund.get("top") or [] if h.get("t")]
            fy = fund.get("yields") or {}
        hm = {}
        for t, w in hold:
            inf = store.get("info", t)
            if not inf:
                continue
            est = store.get("est", t) or store.get("lest", t)
            q, _ = major(inf.get("currency"))
            hm[t] = S.holding_metrics(inf, est, fx_rate(fx, inf.get("financialCurrency") or q, q))
        m = {}
        agg_cov = {}
        for k in ("fwd_ey", "ev_ebitda_y", "fcf_y", "rev_g", "eps_g", "op_m", "roe", "fcf_m", "lev", "eps_rev_1y", "eps_rev_0y", "breadth", "surprise"):
            v, cov = S.wavg([(w, hm.get(t, {}).get(k)) for t, w in hold])
            m[k], agg_cov[k] = v, round(cov, 2)
        if fy:
            pos = lambda x: x if x and x > 0 else None
            m["ey"], m["by"], m["sy"], m["cfy"] = (pos(fy.get("Price/Earnings")), pos(fy.get("Price/Book")), pos(fy.get("Price/Sales")), pos(fy.get("Price/Cashflow")))
        else:
            def inv(field):
                return S.wavg([(w, (1 / S.num((store.get("info", t) or {}).get(field))) if S.num((store.get("info", t) or {}).get(field)) else None) for t, w in hold])[0]
            m["ey"], m["by"], m["sy"], m["cfy"] = inv("trailingPE"), inv("priceToBook"), inv("priceToSalesTrailing12Months"), None
        ps = S.price_stats(s, spy)
        m.update({k: ps.get(k) for k in ("rs3", "rs6", "rs12", "trend", "vol", "mdd", "beta", "cvar", "r1", "r3", "r6", "r12", "d1")})
        above = []
        for t, w in hold:
            c = P.get(t)
            if c is not None and c.dropna().size > 200:
                c = c.dropna()
                above.append((w, 1.0 if c.iat[-1] > c.rolling(200).mean().iat[-1] else 0.0))
        m["hold_breadth"] = S.wavg(above)[0] if above else None
        if not basket and proxy in V and V[proxy].dropna().size > 130:
            vv = V[proxy].dropna()
            m["volume"] = float(vv.iloc[-20:].mean() / vv.iloc[-120:].mean() - 1) if vv.iloc[-120:].mean() else None
        sens = S.macro_sensitivity(s, spy, MF) if spy is not None else {}
        m["tailwind"] = sens.get("tailwind")
        rf_, n_reg = S.regime_fit(s, spy, hist_reg, reg.get("quadrant")) if spy is not None else (None, 0)
        m["regime_fit"] = rf_
        lag = S.price_stats(s.iloc[:-21], spy.iloc[:-21]) if spy is not None and len(s) > 300 else {}
        prev_metrics[key] = {k: lag.get(k) for k in ("rs3", "rs6", "rs12", "trend")}
        metrics[key] = m
        info_out[key] = {"key": key, "name": name, "gics": gics, "proxy": proxy if not basket else "Korb", "members": proxy if basket else None,
                         "is_fin": is_fin, "holdings": [{"t": t, "w": r(w, 3), "n": (store.get("info", t) or {}).get("shortName")} for t, w in hold],
                         "hold_cov": agg_cov, "sens": sens, "regime_n": n_reg, "since": s.index[0].strftime("%Y-%m-%d"),
                         "series": [[d.strftime("%Y-%m-%d"), r(v)] for d, v in s.iloc[-260::5].items()]}
    excl = {k: (S.FIN_EXCLUDE if any(k == x[0] and x[4] for x in S.SECTORS) else set()) for k in metrics}
    ft = S.factor_table(metrics, S.SECTOR_FACTORS, excl)
    prev = S.factor_table(prev_metrics, {"strength": S.SECTOR_FACTORS["strength"][:4]}, {})
    today = NOW.strftime("%Y-%m-%d")
    sector_hist[today] = {k: v["z"] for k, v in ft.items()}
    for d in sorted(sector_hist)[:-400]:
        del sector_hist[d]
    rows = []
    for k, m in metrics.items():
        hist_dates = sorted(d for d in sector_hist if d <= (NOW - pd.Timedelta(days=28)).strftime("%Y-%m-%d"))
        rows.append({**info_out[k], "m": {kk: r(vv) for kk, vv in m.items()}, "z": ft[k]["z"], "mz": ft[k]["mz"], "cov": ft[k]["cov"],
                     "strength_prev": prev.get(k, {}).get("z", {}).get("strength"),
                     "z_4w": sector_hist[hist_dates[-1]].get(k) if hist_dates else None})
    return {"rows": rows, "factors": {f: [{"key": a, "dir": b, "label": c} for a, b, c in items] for f, items in S.SECTOR_FACTORS.items()},
            "fin_exclude": sorted(S.FIN_EXCLUDE), "macro_factors": [f[2] for f in S.MACRO_FACTORS]}


def rf_for(cur: str, F: dict):
    if cur == "USD" and F.get("DGS10") is not None:
        return float(F["DGS10"].iat[-1]) / 100, "US-Staatsanleihe 10J (FRED DGS10)", None
    b = F.get("IRLTLT01DEM156N")
    if b is not None:
        note = None if cur in ("EUR", "DKK") else f"Kein risikofreier Zins für {cur} verfügbar – Näherung Bundesanleihe 10J"
        return float(b.iat[-1]) / 100, "Bundesanleihe 10J (OECD via FRED, Monatswert)", note
    return None, None, "Kein risikofreier Zins verfügbar"


FIN_BALANCE = re.compile(r"Bank|Insurance|Asset Management|Capital Markets|Mortgage|Conglomerate|Shell|Credit Union", re.I)


def growth_inputs(est: dict, sm: dict):
    """Konsens-Wachstum mit Plausibilitätsprüfung gegen den letzten Jahresabschluss."""
    tab = est.get("rev_est") or {}
    g_y0, g_y1 = S.num((tab.get("0y") or {}).get("growth")), S.num((tab.get("+1y") or {}).get("growth"))
    avg0 = S.num((tab.get("0y") or {}).get("avg"))
    rev0 = S._v((sm.get("hist") or {}).get("rev"))
    own = avg0 / rev0 - 1 if avg0 and rev0 and rev0 > 0 else None
    note, g0 = None, g_y0
    if own is not None and abs(own) < 0.03 and g_y1 is not None:
        g0, g_y1 = g_y1, None          # „laufendes“ Konsensjahr ist bereits abgeschlossen → Jahr 1 = nächstes GJ
    elif g_y0 is not None and abs(g_y0) > 0.6:
        if own is not None and abs(own) <= 0.6:
            g0, note = own, f"Konsens-Wachstum laut Yahoo {g_y0:+.0%} unplausibel – ersetzt durch Konsensumsatz ÷ letzter Jahresumsatz ({own:+.0%})"
        elif own is None or abs(own) > 0.8:
            g0, note = None, f"Konsens-Wachstum {g_y0:+.0%} nicht plausibel prüfbar – nicht verwendet"
    if g_y1 is not None and abs(g_y1) > 0.8:
        g_y1 = None
    return g0, g_y1, note


def stock_block(store, P, F, fx) -> dict:
    spy = P.get(S.BENCH)
    metrics, rows, groups, excl = {}, {}, {}, {}
    for t in STOCKS:
        info = store.get("info", t)
        if not info or info.get("quoteType") != "EQUITY":
            continue
        est, ev, stm = store.get("est", t) or {}, store.get("events", t) or {}, store.get("stm", t)
        qcur_raw = info.get("currency")
        qcur, div = major(qcur_raw)
        fcur = info.get("financialCurrency") or qcur
        rate = fx_rate(fx, fcur, qcur)
        fx_note = f"Bericht in {fcur}, Kurs in {qcur_raw}; umgerechnet mit {rate:.4g}" if fcur != qcur and rate else (
            f"Bericht in {fcur}, Kurs in {qcur_raw}; kein Wechselkurs verfügbar" if fcur != qcur else None)
        sm = S.statements_metrics(stm)
        hm = S.holding_metrics(info, est, rate)
        c = P.get(t)
        ps = S.price_stats(c, None) if c is not None else {}
        nxt = lambda tab, per="+1y": S.clip(S.num(((est.get(tab) or {}).get(per) or {}).get("growth")), -0.8, 3)
        m = {**hm, "roic": sm.get("roic"), "cash_conv": sm.get("cash_conv"), "int_cov": sm.get("int_cov"), "nd_ebitda": sm.get("nd_ebitda"),
             "rev_cagr3": sm.get("rev_cagr3"), "rev_g_next": nxt("rev_est"), "eps_g_next": nxt("eps_est"),
             "r12_1": ps.get("r12_1"), "r6": ps.get("r6"), "trend": ps.get("trend"), "vol": ps.get("vol"), "mdd": ps.get("mdd"),
             "beta": S.num(info.get("beta"))}
        is_fin = info.get("sector") == "Financial Services" and bool(FIN_BALANCE.search(info.get("industry") or ""))
        metrics[t] = m
        groups[t] = info.get("sector") or "?"
        excl[t] = S.STOCK_FIN_EXCLUDE if is_fin else set()
        stm_ts = store.age("stm", t)
        fy = sm.get("fy_end")
        age = (NOW.replace(tzinfo=None) - pd.Timestamp(fy).to_pydatetime()).days if fy else None
        g0, g1, g_note = growth_inputs(est, sm)
        flags = S.red_flags(m, sm, info, est, ev, is_fin, fx_note, age)
        if g_note:
            flags.append({"level": "dq", "cat": "Daten", "text": "Konsensdaten unplausibel", "value": g_note, "rule": "Abgleich Konsens vs. Jahresabschluss", "src": "Yahoo Finance"})
        price = S.num(info.get("currentPrice") or info.get("regularMarketPrice"))
        last_close = float(c.dropna().iat[-1]) if c is not None and c.dropna().size else None
        last_date = c.dropna().index[-1].strftime("%Y-%m-%d") if c is not None and c.dropna().size else None
        px = (last_close or price)
        px_major = px / div if px else None
        mcap = S.num(info.get("marketCap"))
        so = S.num(info.get("sharesOutstanding"))
        shares, share_note = so, None
        if mcap and px_major:
            implied = mcap / px_major
            if so and 0.8 < so / implied < 1.25:
                shares = so
            elif so and 80 < implied / so < 125:
                shares, mcap = so, mcap / 100
            else:
                shares, share_note = implied, "Aktienzahl aus Marktkapitalisierung ÷ Kurs abgeleitet (ADR-Verhältnis/Aktiengattungen)"
        if not shares:
            bs_sh = S._v((sm.get("hist") or {}).get("shares"))
            if bs_sh:
                shares, share_note = bs_sh, "Aktienzahl aus der Bilanz (Yahoo liefert keine Marktkapitalisierung)"
                mcap = mcap or (bs_sh * px_major if px_major else None)
        rf, rf_src, rf_note = rf_for(qcur, F)
        conv = lambda v: v * rate if v is not None and rate else None
        hist = sm.get("hist") or {}
        val = {
            "cur": qcur, "px": r(px_major, 6), "shares": r(shares, 6), "share_note": share_note,
            "rev": r(conv(S._v(hist.get("rev"))), 6), "ebit": r(conv(S._v(hist.get("ebit"))), 6),
            "net_debt": r(conv((S._v(hist.get("debt")) or 0) - (S._v(hist.get("cash")) or 0)) if hist.get("debt") or hist.get("cash") else None, 6),
            "equity": r(conv(S._v(hist.get("eq"))), 6), "ni": r(conv(S._v(hist.get("ni"))), 6), "debt": r(conv(S._v(hist.get("debt"))), 6),
            "opm": r(sm.get("opm_avg3")), "opm_last": r(sm.get("op_m_fy")), "tax": r(sm.get("tax_rate")), "capex": r(sm.get("capex_pct")),
            "da": r(sm.get("da_pct")), "nwc": r(sm.get("nwc_pct")), "ri_capex": r(sm.get("reinv_capex")), "ri_nwc": r(sm.get("reinv_nwc")), "g_cagr3": r(sm.get("rev_cagr3")),
            "g0": r(S.clip(g0, -0.3, 0.6)), "g1": r(S.clip(g1, -0.3, 0.6)), "g_note": g_note,
            "roe": r(sm.get("roe_avg3")), "intrate": r(sm.get("intrate")),
            "beta": r(S.num(info.get("beta"))), "rf": r(rf), "rf_src": rf_src, "rf_note": rf_note,
            "tg": 0.025 if qcur == "USD" else 0.02, "erp": 0.045,
            "method": "residual_income" if is_fin else "dcf", "fx_note": fx_note, "fy": fy,
        }
        cons = {k: S.num(info.get(k)) for k in ("targetMeanPrice", "targetMedianPrice", "targetHighPrice", "targetLowPrice", "numberOfAnalystOpinions", "recommendationMean")}
        cons["key"] = info.get("recommendationKey")
        cons = {k: (r(v) if isinstance(v, float) else v) for k, v in cons.items()}
        if div != 1:
            for k in ("targetMeanPrice", "targetMedianPrice", "targetHighPrice", "targetLowPrice"):
                cons[k] = r(cons[k] / div) if cons.get(k) else None
        rows[t] = {
            "t": t, "n": info.get("shortName") or info.get("longName") or t, "w": wkn(t), "sec": info.get("sector"), "ind": info.get("industry"),
            "land": info.get("country"), "cur": qcur_raw, "fcur": fcur, "px": r(px, 6), "pxd": last_date, "d1": r(ps.get("d1")),
            "mcap": r(mcap, 5), "mcap_cur": qcur, "is_fin": is_fin, "summary": info.get("summary"), "web": info.get("website"),
            "m": {k: r(v) for k, v in m.items()},
            "x": {k: r(S.num(info.get(k))) for k in ("trailingPE", "forwardPE", "priceToBook", "enterpriseToEbitda", "enterpriseToRevenue",
                                                     "trailingPegRatio", "dividendYield", "payoutRatio", "grossMargins", "ebitdaMargins",
                                                     "profitMargins", "returnOnAssets", "currentRatio", "debtToEquity", "shortPercentOfFloat")},
            "hist": {**{k: v for k, v in hist.items()}, "opm": sm.get("opm_hist"), "roic": sm.get("roic_hist")},
            "q": sm.get("q"), "flags": flags, "val": val, "cons": cons,
            "est": compact_est(est),
            "ev": ev,
            "src": {"info": store.age("info", t), "est": store.age("est", t), "events": store.age("events", t), "stm": stm_ts, "px": last_date},
        }
    ft = S.factor_table(metrics, S.STOCK_FACTORS, excl, groups)
    for t in rows:
        rows[t].update({"z": ft[t]["z"], "mz": ft[t]["mz"], "cov": ft[t]["cov"]})
    print(f"Aktien ausgewertet: {len(rows)}")
    return {"rows": list(rows.values()), "factors": {f: [{"key": a, "dir": b, "label": c} for a, b, c in items] for f, items in S.STOCK_FACTORS.items()},
            "fin_exclude": sorted(S.STOCK_FIN_EXCLUDE)}


def compact_est(est: dict) -> dict:
    pick = lambda tab, keys: {p: [r(((est.get(tab) or {}).get(p) or {}).get(k)) for k in keys] for p in ("0y", "+1y") if (est.get(tab) or {}).get(p)}
    return {"eps": pick("eps_est", ("avg", "low", "high", "numberOfAnalysts", "growth", "yearAgoEps")),
            "rev": pick("rev_est", ("avg", "low", "high", "numberOfAnalysts", "growth", "yearAgoRevenue")),
            "trend": pick("eps_trend", ("current", "7daysAgo", "30daysAgo", "60daysAgo", "90daysAgo")),
            "revs": pick("eps_rev", ("upLast30days", "downLast30days")),
            "surprise": [[q[:10], r(v.get("epsActual")), r(v.get("epsEstimate")), r(v.get("surprisePercent"))] for q, v in (est.get("surprise") or {}).items()][-4:]}


def catalysts(stocks: dict) -> dict:
    today = NOW.strftime("%Y-%m-%d")
    up, actions = [], []
    for s in stocks["rows"]:
        cal = (s.get("ev") or {}).get("calendar") or {}
        d = cal.get("Earnings Date")
        if isinstance(d, str) and today <= d[:10] <= (NOW + pd.Timedelta(days=45)).strftime("%Y-%m-%d"):
            up.append({"t": s["t"], "n": s["n"], "date": d[:10], "eps_avg": cal.get("Earnings Average"), "type": "Quartalszahlen"})
        for a in (s.get("ev") or {}).get("actions") or []:
            if a.get("date", "") >= (NOW - pd.Timedelta(days=21)).strftime("%Y-%m-%d") and a.get("action") in ("up", "down", "init"):
                actions.append({"t": s["t"], "n": s["n"], **a})
    up.sort(key=lambda x: x["date"])
    actions.sort(key=lambda x: x["date"], reverse=True)
    return {"earnings": up[:60], "actions": actions[:60]}


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if math.isnan(o) or math.isinf(o) else float(o)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return o


def main():
    t0 = time.time()
    store = Store()
    F = fred.load_all()
    etfs = [p for _, _, _, p, _ in S.SECTORS if isinstance(p, str)]
    baskets = [t for _, _, _, p, _ in S.SECTORS if isinstance(p, list) for t in p]
    store.refresh("fund", etfs, 40, workers=4)
    holdings = sorted({h["t"] for e in etfs for h in ((store.get("fund", e) or {}).get("top") or []) if h.get("t")})
    extra = [t for t in dict.fromkeys(holdings + baskets) if t not in STOCKS]
    store.refresh("info", STOCKS + extra, 700)
    store.refresh("est", STOCKS, 280)
    store.refresh("lest", extra, 300)
    store.refresh("events", STOCKS, 280)
    store.refresh("stm", STOCKS, 240, workers=4)
    store.save()

    P_etf, V_etf = download(etfs + [S.BENCH], "max")
    P_stk, _ = download(STOCKS + extra, "3y")
    P = pd.concat([P_etf, P_stk[[c for c in P_stk if c not in P_etf]]], axis=1).sort_index()
    curs = set()
    for t in STOCKS + extra:
        i = store.get("info", t) or {}
        curs.add(major(i.get("currency"))[0])
        curs.add(i.get("financialCurrency"))
    fx = fx_table({c for c in curs if c})

    spy = P[S.BENCH].dropna() if S.BENCH in P else None
    reg = regime.regime(F, spy, P_etf[[e for e in etfs if e in P_etf]])
    hist_reg = historical_regimes(F)
    sector_hist = store.c.setdefault("sector_hist", {})
    sectors = sector_block(store, P, V_etf, F, reg, hist_reg, fx, sector_hist)
    stocks = stock_block(store, P, F, fx)
    try:
        bt = backtest_sectors.run(P_etf[[e for e in etfs if e in P_etf] + [S.BENCH]], S.BENCH, F.get("DGS3MO"), F.get("CPIAUCSL"))
    except Exception as e:
        print("Backtest:", type(e).__name__, e)
        bt = {"error": f"Backtest fehlgeschlagen: {type(e).__name__}"}
    store.save()
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "regime": reg, "macro": macro_panel(F), "sectors": sectors, "stocks": stocks, "catalysts": catalysts(stocks), "backtest": bt,
        "regime_history": [[d.strftime("%Y-%m"), q] for d, q in (hist_reg.items() if hist_reg is not None else [])][-120:],
        "sources": {
            "prices": "Yahoo Finance über yfinance – Tagesschlusskurse (dividendenbereinigt), inoffizielle Schnittstelle, keine Echtzeitdaten",
            "fundamentals": "Yahoo Finance – Jahres-/Quartalsabschlüsse, Kennzahlen (TTM) und Analystenschätzungen; Abrufzeit je Wert unter „Quellen“",
            "macro": "FRED (Federal Reserve Bank of St. Louis) mit den jeweiligen Ursprungsquellen",
            "etf": "Yahoo Finance Fondsdaten (Bewertungskennzahlen des ETF-Portfolios, Top-10-Positionen)",
            "not_used": "Keine Daten von Bloomberg, LSEG/Refinitiv, FactSet, S&P Capital IQ, Morningstar Direct oder ICE (keine Lizenz).",
        },
        "fetch_stats": store.stats,
        "runtime_s": round(time.time() - t0),
    }
    OUT.write_text("window.RESEARCH = " + json.dumps(clean(payload), ensure_ascii=False, separators=(",", ":")) + ";\n")
    print(f"Research: {len(stocks['rows'])} Aktien, {len(sectors['rows'])} Branchen, {OUT.stat().st_size // 1024} KB, {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
