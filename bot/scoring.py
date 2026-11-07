"""Kennzahlen, Faktor-Scores, Red Flags und Bewertungs-Eingaben für Branchen und Aktien.

Grundsätze: Werte werden nur aus vorhandenen Daten berechnet; fehlt etwas, bleibt es None.
Vergleichbarkeit über Z-Scores (winsorisiert bei ±2,5) im Querschnitt. Die Gewichtung der Faktoren
erfolgt im Browser (konfigurierbar); hier entstehen nur die Faktor-Z-Werte und Rohkennzahlen.
"""

import math

import numpy as np
import pandas as pd

# key, Name, GICS-Bezug, Proxy (ETF-Symbol oder Korb), Finanzbranche?
SECTORS = [
    ("it", "Informationstechnologie", "GICS 45 Information Technology", "XLK", False),
    ("semis", "Halbleiter", "GICS 453010 Semiconductors", "SMH", False),
    ("ai_infra", "KI-Infrastruktur", "eigener Korb (Chips, Netzwerk, Server, Strom)", ["NVDA", "AVGO", "AMD", "TSM", "ANET", "VRT", "MU", "DELL", "ETN", "CEG"], False),
    ("software", "Software", "GICS 451030 Software", "IGV", False),
    ("comm", "Kommunikationsdienste", "GICS 50 Communication Services", "XLC", False),
    ("health", "Gesundheit", "GICS 35 Health Care", "XLV", False),
    ("biotech", "Biotechnologie", "GICS 352010 Biotechnology", "XBI", False),
    ("pharma", "Pharma", "GICS 352020 Pharmaceuticals", "PPH", False),
    ("fin", "Finanzdienstleister", "GICS 40 Financials", "XLF", True),
    ("banks", "Banken", "GICS 4010 Banks", "KBE", True),
    ("insurance", "Versicherungen", "GICS 4030 Insurance", "KIE", True),
    ("industrials", "Industrie", "GICS 20 Industrials", "XLI", False),
    ("defense", "Luftfahrt & Verteidigung", "GICS 201010 Aerospace & Defense", "ITA", False),
    ("energy", "Energie (Öl & Gas)", "GICS 10 Energy", "XLE", False),
    ("renewables", "Erneuerbare Energien", "thematisch (Clean Energy)", "ICLN", False),
    ("utilities", "Versorger", "GICS 55 Utilities", "XLU", False),
    ("staples", "Basiskonsum", "GICS 30 Consumer Staples", "XLP", False),
    ("discretionary", "Zyklischer Konsum", "GICS 25 Consumer Discretionary", "XLY", False),
    ("realestate", "Immobilien", "GICS 60 Real Estate", "XLRE", False),
    ("materials", "Grundstoffe", "GICS 15 Materials", "XLB", False),
    ("mining", "Bergbau & Metalle", "GICS 151040 Metals & Mining", "XME", False),
    ("auto", "Automobil & E-Mobilität", "GICS 2510 Automobiles & Components (thematisch)", "CARZ", False),
    ("luxury", "Luxusgüter", "eigener Korb (GICS 252030 Textiles, Apparel & Luxury)", ["MC.PA", "RMS.PA", "CFR.SW", "KER.PA", "RACE.MI", "BRBY.L", "MONC.MI", "1913.HK"], False),
    ("infra", "Infrastruktur", "thematisch (US-Infrastruktur)", "PAVE", False),
    ("cyber", "Cybersecurity", "thematisch (Cybersecurity)", "CIBR", False),
]
BENCH = "SPY"

# Faktor -> [(Kennzahl, Richtung +1 höher = besser / −1 niedriger = besser, Beschreibung)]
SECTOR_FACTORS = {
    "valuation": [("ey", 1, "Gewinnrendite des ETF-Portfolios (1/KGV)"), ("fwd_ey", 1, "Erwartete Gewinnrendite der Top-Positionen (1/Forward-KGV)"),
                  ("by", 1, "Buchwertrendite (1/KBV)"), ("sy", 1, "Umsatzrendite (1/KUV)"), ("cfy", 1, "Cashflow-Rendite (1/KCV)"),
                  ("ev_ebitda_y", 1, "EBITDA/EV der Top-Positionen"), ("fcf_y", 1, "Free-Cashflow-Rendite der Top-Positionen")],
    "fundamental": [("rev_g", 1, "Umsatzwachstum (Quartal ggü. Vorjahr)"), ("eps_g", 1, "Gewinnwachstum (Quartal ggü. Vorjahr)"),
                    ("op_m", 1, "Operative Marge"), ("roe", 1, "Eigenkapitalrendite"), ("fcf_m", 1, "Free-Cashflow-Marge")],
    "momentum": [("eps_rev_1y", 1, "EPS-Schätzung nächstes GJ: Änderung 90 Tage"), ("eps_rev_0y", 1, "EPS-Schätzung laufendes GJ: Änderung 90 Tage"),
                 ("breadth", 1, "Revisionsbreite (Anhebungen − Senkungen) / alle, 30 Tage"), ("surprise", 1, "Ø Earnings Surprise (4 Quartale)")],
    "strength": [("rs3", 1, "Überrendite ggü. S&P 500, 3 Monate"), ("rs6", 1, "Überrendite, 6 Monate"), ("rs12", 1, "Überrendite, 12 Monate ohne letzten Monat"),
                 ("trend", 1, "Abstand zur 200-Tage-Linie"), ("hold_breadth", 1, "Anteil Top-Positionen über 200-Tage-Linie"), ("volume", 1, "Handelsvolumen 20 T ggü. 120 T")],
    "macro": [("tailwind", 1, "Makro-Rückenwind: Sensitivität × Faktorbewegung der letzten 13 Wochen"),
              ("regime_fit", 1, "Ø Monats-Überrendite in früheren Phasen desselben Regimes")],
    "risk": [("vol", -1, "Volatilität 1 Jahr"), ("mdd", -1, "Maximaler Drawdown 1 Jahr (Betrag)"), ("beta", -1, "Beta ggü. S&P 500 (2 J, wöchentlich)"),
             ("cvar", -1, "Tail Risk: Ø der schlechtesten 5 % Tage"), ("lev", -1, "Verschuldung der Top-Positionen (Debt/Equity)")],
}
FIN_EXCLUDE = {"sy", "cfy", "ev_ebitda_y", "fcf_y", "fcf_m", "lev"}

STOCK_FACTORS = {
    "quality": [("roic", 1, "ROIC (EBIT nach Steuern / investiertes Kapital)"), ("roe", 1, "Eigenkapitalrendite"), ("op_m", 1, "Operative Marge"),
                ("fcf_m", 1, "Free-Cashflow-Marge"), ("cash_conv", 1, "Cash Conversion (FCF / Nettogewinn)"), ("int_cov", 1, "Zinsdeckung (EBIT / Zinsaufwand)")],
    "valuation": [("fwd_ey", 1, "Erwartete Gewinnrendite (1/Forward-KGV)"), ("ev_ebitda_y", 1, "EBITDA/EV"), ("fcf_y", 1, "Free-Cashflow-Rendite"),
                  ("sales_y", 1, "Umsatz/EV"), ("book_y", 1, "Buchwertrendite (1/KBV)")],
    "growth": [("rev_g", 1, "Umsatzwachstum (letztes Quartal ggü. Vorjahr)"), ("rev_cagr3", 1, "Umsatzwachstum p. a. (3 Geschäftsjahre)"),
               ("rev_g_next", 1, "Konsens-Umsatzwachstum nächstes GJ"), ("eps_g_next", 1, "Konsens-Gewinnwachstum nächstes GJ")],
    "momentum": [("eps_rev_1y", 1, "EPS-Schätzung nächstes GJ: Änderung 90 Tage"), ("eps_rev_0y", 1, "EPS-Schätzung laufendes GJ: Änderung 90 Tage"),
                 ("breadth", 1, "Revisionsbreite 30 Tage"), ("surprise", 1, "Ø Earnings Surprise (4 Quartale)")],
    "strength": [("r12_1", 1, "Rendite 12 Monate ohne letzten Monat"), ("r6", 1, "Rendite 6 Monate"), ("trend", 1, "Abstand zur 200-Tage-Linie")],
    "risk": [("vol", -1, "Volatilität 1 Jahr"), ("mdd", -1, "Maximaler Drawdown 1 Jahr (Betrag)"), ("beta", -1, "Beta (Yahoo, 5 J monatlich)"),
             ("nd_ebitda", -1, "Nettoverschuldung / EBITDA")],
}
STOCK_FIN_EXCLUDE = {"roic", "fcf_m", "cash_conv", "int_cov", "ev_ebitda_y", "fcf_y", "sales_y", "nd_ebitda"}
MINOR = {"GBp": ("GBP", 100), "GBX": ("GBP", 100), "ZAc": ("ZAR", 100), "ILA": ("ILS", 100)}


def num(v):
    if v is None:
        return None
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) or math.isinf(v) else v


def rnd(v, d=4):
    v = num(v)
    return None if v is None else float(f"{v:.{d}g}")


def clip(v, lo, hi):
    return None if v is None else max(lo, min(hi, v))


# ---------------------------------------------------------------- Kurs-Kennzahlen
def ret(s: pd.Series, n: int, skip: int = 0):
    s = s.dropna()
    return float(s.iat[-1 - skip] / s.iat[-1 - n] - 1) if len(s) > n else None


def price_stats(s: pd.Series, bench: pd.Series | None) -> dict:
    s = s.dropna()
    if len(s) < 130:
        return {}
    r = s.pct_change().dropna()
    y = s.iloc[-252:]
    out = {"vol": float(r.iloc[-252:].std() * np.sqrt(252)), "mdd": float(-(y / y.cummax() - 1).min()),
           "cvar": float(-np.sort(r.iloc[-252:].to_numpy())[: max(1, int(0.05 * min(252, len(r))))].mean()),
           "trend": float(s.iat[-1] / s.rolling(200).mean().iat[-1] - 1) if len(s) >= 200 else None,
           "r1": ret(s, 21), "r3": ret(s, 63), "r6": ret(s, 126), "r12": ret(s, 252), "r12_1": ret(s, 252, 21), "d1": ret(s, 1)}
    if bench is not None:
        b = bench.dropna()
        for k, n, skip in (("rs3", 63, 0), ("rs6", 126, 0), ("rs12", 252, 21)):
            a, c = ret(s, n, skip), ret(b, n, skip)
            out[k] = None if a is None or c is None else a - c
        w = pd.concat([s.resample("W-FRI").last(), b.resample("W-FRI").last()], axis=1).dropna().pct_change().dropna().iloc[-104:]
        if len(w) > 40:
            out["beta"] = float(np.cov(w.iloc[:, 0], w.iloc[:, 1])[0, 1] / w.iloc[:, 1].var())
    return out


def zscores(values: dict, sign: int) -> dict:
    v = {k: x for k, x in values.items() if x is not None}
    if len(v) < 5:
        return {}
    a = np.array(list(v.values()), dtype=float)
    lo, hi = np.percentile(a, [2.5, 97.5])
    a = np.clip(a, lo, hi)
    sd = a.std()
    if sd == 0:
        return {k: 0.0 for k in v}
    return {k: float(np.clip(sign * (x - a.mean()) / sd, -2.5, 2.5)) for k, x in zip(v, a)}


def factor_table(metrics: dict[str, dict], factors: dict, exclude_for: dict[str, set], groups: dict[str, str] | None = None) -> dict:
    """metrics: id -> {kennzahl: wert}. Liefert id -> {faktor: z, ...} plus Abdeckung."""
    out = {i: {"z": {}, "mz": {}, "cov": {}} for i in metrics}
    for f, items in factors.items():
        for key, sign, _ in items:
            if groups:   # Vergleich innerhalb der Gruppe, sonst über alle
                vals_all = {i: m.get(key) for i, m in metrics.items() if key not in exclude_for.get(i, set())}
                res = {}
                for g in set(groups.values()):
                    members = {i: v for i, v in vals_all.items() if groups.get(i) == g}
                    zz = zscores(members, sign) if sum(v is not None for v in members.values()) >= 8 else {}
                    res.update(zz)
                rest = {i: v for i, v in vals_all.items() if i not in res}
                if rest:
                    zall = zscores(vals_all, sign)
                    res.update({i: zall[i] for i in rest if i in zall})
                z = res
            else:
                z = zscores({i: m.get(key) for i, m in metrics.items() if key not in exclude_for.get(i, set())}, sign)
            for i, v in z.items():
                out[i]["mz"][key] = round(v, 3)
        for i in metrics:
            vals = [out[i]["mz"][k] for k, _, _ in items if k in out[i]["mz"]]
            applicable = [k for k, _, _ in items if k not in exclude_for.get(i, set())]
            out[i]["cov"][f] = f"{len(vals)}/{len(applicable)}"
            if vals and len(vals) >= max(1, math.ceil(len(applicable) / 3)):
                out[i]["z"][f] = round(float(np.mean(vals)), 3)
    return out


# ---------------------------------------------------------------- Einzelwerte (für Top-Positionen und Aktien)
def holding_metrics(info: dict | None, est: dict | None, fx: float | None) -> dict:
    i, e = info or {}, est or {}
    m = {}
    fpe = num(i.get("forwardPE"))
    m["fwd_ey"] = 1 / fpe if fpe else None
    ee = num(i.get("enterpriseToEbitda"))
    m["ev_ebitda_y"] = 1 / ee if ee and ee > 0 else None
    er = num(i.get("enterpriseToRevenue"))
    m["sales_y"] = 1 / er if er and er > 0 else None
    pb = num(i.get("priceToBook"))
    m["book_y"] = 1 / pb if pb and pb > 0 else None
    fcf, mc, rev = num(i.get("freeCashflow")), num(i.get("marketCap")), num(i.get("totalRevenue"))
    m["fcf_y"] = fcf * fx / mc if fcf is not None and mc and fx else None
    m["fcf_m"] = fcf / rev if fcf is not None and rev else None
    m["rev_g"] = clip(num(i.get("revenueGrowth")), -1, 2)
    m["eps_g"] = clip(num(i.get("earningsGrowth")), -1, 2)
    m["op_m"] = clip(num(i.get("operatingMargins")), -1, 1)
    m["roe"] = clip(num(i.get("returnOnEquity")), -1, 1.5)
    de = num(i.get("debtToEquity"))
    m["lev"] = de / 100 if de is not None and de >= 0 else None
    tr = (e.get("eps_trend") or {})
    for per, k in (("+1y", "eps_rev_1y"), ("0y", "eps_rev_0y")):
        row = tr.get(per) or {}
        c, a = num(row.get("current")), num(row.get("90daysAgo"))
        m[k] = clip(c / a - 1, -0.5, 0.5) if c is not None and a and a > 0 else None
    rv = (e.get("eps_rev") or {}).get("+1y") or {}
    up, dn = num(rv.get("upLast30days")), num(rv.get("downLast30days"))
    m["breadth"] = None if up is None or dn is None else (up - dn) / (up + dn) if up + dn else 0.0
    sp = [num(r.get("surprisePercent")) for r in (e.get("surprise") or {}).values()]
    sp = [clip(x, -0.5, 0.5) for x in sp if x is not None][-4:]
    m["surprise"] = float(np.mean(sp)) if sp else None
    return m


def wavg(items: list[tuple[float, float | None]], min_cov: float = 0.5):
    tot = sum(w for w, _ in items)
    have = [(w, v) for w, v in items if v is not None]
    cw = sum(w for w, _ in have)
    if not tot or cw / tot < min_cov:
        return None, (cw / tot if tot else 0)
    return sum(w * v for w, v in have) / cw, cw / tot


def harmonic_yield(items):   # Renditen (1/Multiple) werden gewichtet gemittelt = harmonisches Mittel der Multiples
    return wavg(items)


# ---------------------------------------------------------------- Makro-Sensitivität
MACRO_FACTORS = [("DGS10", "diff", "Zins 10J (+1 pp)", 1.0), ("DCOILWTICO", "log", "Ölpreis (+10 %)", 0.1),
                 ("DTWEXBGS", "log", "US-Dollar (+10 %)", 0.1), ("BAMLH0A0HYM2", "diff", "Kreditspread HY (+1 pp)", 1.0)]


def macro_frame(F: dict) -> pd.DataFrame | None:
    cols = {}
    for sid, how, _, _ in MACRO_FACTORS:
        s = F.get(sid)
        if s is None:
            return None
        w = s.resample("W-FRI").last()
        cols[sid] = w.diff() if how == "diff" else np.log(w).diff()
    return pd.DataFrame(cols).dropna()


def macro_sensitivity(s: pd.Series, bench: pd.Series, MF: pd.DataFrame | None) -> dict:
    if MF is None:
        return {}
    ex = (np.log(s.resample("W-FRI").last()).diff() - np.log(bench.resample("W-FRI").last()).diff()).rename("y")
    d = pd.concat([ex, MF], axis=1).dropna().iloc[-156:]
    if len(d) < 80:
        return {}
    X = np.column_stack([np.ones(len(d)), d[MF.columns].to_numpy()])
    y = d["y"].to_numpy()
    b, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ b
    r2 = 1 - resid.var() / y.var() if y.var() else 0
    se = np.sqrt(np.diag(resid.var() * np.linalg.pinv(X.T @ X)))
    recent = MF.iloc[-13:].sum()
    tail = float(sum(b[j + 1] * recent[c] for j, c in enumerate(MF.columns)))
    betas = []
    for j, (sid, how, label, scale) in enumerate(MACRO_FACTORS):
        betas.append({"factor": label, "beta": round(float(b[j + 1] * scale), 4), "t": round(float(b[j + 1] / se[j + 1]), 2) if se[j + 1] else None,
                      "recent": round(float(recent[sid] / scale), 3)})
    return {"betas": betas, "r2": round(float(r2), 3), "tailwind": tail, "weeks": len(d)}


def regime_fit(s: pd.Series, bench: pd.Series, hist_regimes: pd.Series | None, current: str | None):
    if hist_regimes is None or not current:
        return None, 0
    m = (s.resample("ME").last().pct_change() - bench.resample("ME").last().pct_change()).dropna()
    reg = hist_regimes.reindex(m.index, method="ffill").shift(1)   # Regime zu Monatsbeginn bekannt → kein Look-Ahead
    x = m[reg == current]
    return (float(x.mean()), len(x)) if len(x) >= 12 else (None, len(x))


# ---------------------------------------------------------------- Aktien: Finanzberichte auswerten
def _row(st: dict | None, *names):
    if not st:
        return None
    for n in names:
        if n in st:
            return st[n]
    return None


def _v(arr, i=0):
    return num(arr[i]) if arr and len(arr) > i else None


def statements_metrics(stm: dict | None) -> dict:
    """Kennzahlen aus den Jahresabschlüssen (Berichtswährung; Verhältnisse sind währungsfrei)."""
    if not stm or not stm.get("is"):
        return {}
    IS, BS, CF = stm.get("is"), stm.get("bs") or {}, stm.get("cf") or {}
    rev = _row(IS, "Total Revenue")
    ebit = _row(IS, "Operating Income", "EBIT")
    ebitda = _row(IS, "EBITDA")
    ni = _row(IS, "Net Income")
    intr = _row(IS, "Interest Expense")
    tax = _row(IS, "Tax Rate For Calcs")
    debt = _row(BS, "Total Debt")
    cash = _row(BS, "Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents")
    eq = _row(BS, "Stockholders Equity")
    sh = _row(BS, "Ordinary Shares Number")
    fcf = _row(CF, "Free Cash Flow")
    capex = _row(CF, "Capital Expenditure")
    n = len(IS.get("periods", []))
    hist = {"periods": IS.get("periods", [])}
    keys = {"rev": rev, "ebit": ebit, "ebitda": ebitda, "ni": ni, "fcf": fcf, "debt": debt, "cash": cash, "eq": eq, "shares": sh, "capex": capex,
            "eps": _row(IS, "Diluted EPS"), "buyback": _row(CF, "Repurchase Of Capital Stock"), "div": _row(CF, "Cash Dividends Paid"),
            "da": _row(IS, "Reconciled Depreciation"), "intexp": intr, "tax": tax, "cwc": _row(CF, "Change In Working Capital"),
            "sbc": _row(CF, "Stock Based Compensation")}
    for k, arr in keys.items():
        hist[k] = [rnd(_v(arr, i), 6) for i in range(n)] if arr else None
    m = {"hist": hist}

    def at(arr, i):
        return _v(arr, i)

    def ratio(a, b, i):
        x, y = at(a, i), at(b, i)
        return x / y if x is not None and y not in (None, 0) else None

    m["opm_hist"] = [rnd(ratio(ebit, rev, i)) for i in range(n)]
    m["op_m_fy"] = ratio(ebit, rev, 0)
    t0 = clip(at(tax, 0) if at(tax, 0) is not None else 0.25, 0.0, 0.4)

    def roic(i):
        e, d, c, q = at(ebit, i), at(debt, i), at(cash, i), at(eq, i)
        if e is None or q is None:
            return None
        ic = (d or 0) + q - (c or 0)
        tx = clip(at(tax, i) if at(tax, i) is not None else 0.25, 0.0, 0.4)
        return e * (1 - tx) / ic if ic > 0 else None

    m["roic"] = clip(roic(0), -1, 2)
    m["roic_prev"] = clip(roic(1), -1, 2)
    m["roic_hist"] = [rnd(clip(roic(i), -1, 2)) for i in range(n)]
    e0, i0 = at(ebit, 0), at(intr, 0)
    m["int_cov"] = clip(e0 / i0, -50, 100) if e0 is not None and i0 and i0 > 0 else None
    eb0, d0, c0 = at(ebitda, 0), at(debt, 0), at(cash, 0)
    m["nd_ebitda"] = clip(((d0 or 0) - (c0 or 0)) / eb0, -10, 30) if eb0 and eb0 > 0 and d0 is not None else None
    m["nd_ebitda_neg_ebitda"] = bool(eb0 is not None and eb0 <= 0)
    f0, n0 = at(fcf, 0), at(ni, 0)
    m["cash_conv"] = clip(f0 / n0, -3, 3) if f0 is not None and n0 and n0 > 0 else None
    r0, r3 = at(rev, 0), at(rev, 3)
    m["rev_cagr3"] = clip((r0 / r3) ** (1 / 3) - 1, -0.5, 1.5) if r0 and r3 and r0 > 0 and r3 > 0 else None
    m["rev_yoy_fy"] = at(rev, 0) / at(rev, 1) - 1 if at(rev, 0) is not None and at(rev, 1) and at(rev, 1) > 0 else None
    m["opm_change"] = (m["opm_hist"][0] - m["opm_hist"][1]) if n > 1 and m["opm_hist"][0] is not None and m["opm_hist"][1] is not None else None
    s0, s1 = at(sh, 0), at(sh, 1)
    m["dilution"] = s0 / s1 - 1 if s0 and s1 else None
    d1 = at(debt, 1)
    eb1 = at(ebitda, 1)
    m["debt_growth"] = d0 / d1 - 1 if d0 is not None and d1 else None
    m["ebitda_growth"] = eb0 / eb1 - 1 if eb0 is not None and eb1 and eb1 > 0 else None
    m["fcf_fy"] = f0
    m["tax_rate"] = t0
    m["fy_end"] = IS.get("periods", [None])[0]
    # TTM aus Quartalen
    q = stm.get("qcf") or {}
    qf = q.get("Free Cash Flow")
    m["fcf_ttm"] = sum(qf[:4]) if qf and len(qf) >= 4 and all(x is not None for x in qf[:4]) else None
    qi = stm.get("qis") or {}
    m["q"] = {"periods": qi.get("periods"), "rev": qi.get("Total Revenue"), "ebit": qi.get("Operating Income"), "ni": qi.get("Net Income"),
              "eps": qi.get("Diluted EPS"), "fcf": qf}

    def avg(fn, k=3):
        vals = [fn(i) for i in range(min(k, n))]
        vals = [x for x in vals if x is not None]
        return float(np.mean(vals)) if vals else None

    m["opm_avg3"] = avg(lambda i: ratio(ebit, rev, i))
    m["capex_pct"] = avg(lambda i: (abs(at(capex, i)) / at(rev, i)) if at(capex, i) is not None and at(rev, i) else None)
    m["da_pct"] = avg(lambda i: ratio(keys["da"], rev, i))
    m["nwc_pct"] = clip(avg(lambda i: (-at(keys["cwc"], i) / at(rev, i)) if at(keys["cwc"], i) is not None and at(rev, i) else None), -0.05, 0.1)
    m["roe_avg3"] = avg(lambda i: ratio(ni, eq, i))
    m["intrate"] = clip(i0 / d0, 0.0, 0.15) if i0 and d0 and d0 > 0 else None
    return m


def red_flags(m: dict, sm: dict, info: dict, est: dict, events: dict, is_fin: bool, fx_note: str | None, stm_age_days: float | None) -> list[dict]:
    """Jede Flagge: Stufe, Kategorie, Text, Wert, Regel, Quelle."""
    F = []
    fy = sm.get("fy_end") or "?"
    src_fs = f"Jahresabschluss GJ {fy} (Yahoo Finance)"

    def add(level, cat, text, value, rule, src):
        F.append({"level": level, "cat": cat, "text": text, "value": value, "rule": rule, "src": src})

    if not is_fin:
        if sm.get("nd_ebitda") is not None and sm["nd_ebitda"] > 3.5:
            add("confirmed", "Bilanz", "Hohe Nettoverschuldung", f"{sm['nd_ebitda']:.1f}× EBITDA", "Nettoverschuldung/EBITDA > 3,5", src_fs)
        if sm.get("nd_ebitda_neg_ebitda"):
            add("confirmed", "Bilanz", "Negatives EBITDA", "EBITDA ≤ 0", "EBITDA ≤ 0", src_fs)
        if sm.get("int_cov") is not None and sm["int_cov"] < 3:
            add("confirmed", "Bilanz", "Schwache Zinsdeckung", f"{sm['int_cov']:.1f}×", "EBIT / Zinsaufwand < 3", src_fs)
        if sm.get("debt_growth") is not None and sm["debt_growth"] > 0.25 and (sm.get("ebitda_growth") is None or sm["ebitda_growth"] < sm["debt_growth"] / 2):
            add("confirmed", "Bilanz", "Schulden steigen deutlich schneller als das EBITDA", f"Schulden {sm['debt_growth']:+.0%}", "Schulden > +25 % ggü. Vorjahr", src_fs)
        f_ttm, f_fy = sm.get("fcf_ttm"), sm.get("fcf_fy")
        if f_fy is not None and f_fy < 0 and (f_ttm is None or f_ttm < 0):
            add("confirmed", "Fundamental", "Negativer Free Cashflow", "GJ" + (" und letzte 4 Quartale" if f_ttm is not None else ""), "FCF < 0", src_fs)
        if sm.get("roic") is not None and sm.get("roic_prev") is not None and sm["roic"] < sm["roic_prev"] - 0.05:
            add("confirmed", "Fundamental", "ROIC deutlich gesunken", f"{sm['roic_prev']:.0%} → {sm['roic']:.0%}", "Rückgang > 5 pp ggü. Vorjahr", src_fs)
    if sm.get("rev_yoy_fy") is not None and sm["rev_yoy_fy"] < -0.05:
        add("confirmed", "Fundamental", "Umsatzrückgang", f"{sm['rev_yoy_fy']:+.0%}", "Umsatz < −5 % ggü. Vorjahr", src_fs)
    if sm.get("opm_change") is not None and sm["opm_change"] < -0.03 and not is_fin:
        add("confirmed", "Fundamental", "Operative Marge sinkt", f"{sm['opm_change'] * 100:+.1f} pp", "Marge > 3 pp unter Vorjahr", src_fs)
    if sm.get("dilution") is not None and sm["dilution"] > 0.03:
        add("confirmed", "Fundamental", "Verwässerung durch neue Aktien", f"{sm['dilution']:+.1%}", "Aktienzahl > +3 % ggü. Vorjahr", src_fs)
    # Markt/Schätzungen
    if m.get("eps_rev_1y") is not None and m["eps_rev_1y"] < -0.03 and (m.get("breadth") or 0) < -0.3:
        add("potential", "Sentiment", "Negative Gewinnrevisionen", f"EPS-Schätzung {m['eps_rev_1y']:+.1%} in 90 T, Breite {m['breadth']:+.2f}",
            "Schätzung −3 % und überwiegend Senkungen", "Analystenschätzungen (Yahoo Finance)")
    fpe = num(info.get("forwardPE"))
    if fpe is not None and fpe > 60:
        add("potential", "Bewertung", "Sehr hohe Bewertung", f"Forward-KGV {fpe:.0f}", "Forward-KGV > 60", "Yahoo Finance, Kurs und Konsens-EPS")
    er = num(info.get("enterpriseToRevenue"))
    if er is not None and er > 15 and not is_fin:
        add("potential", "Bewertung", "Sehr hoher Umsatz-Multiplikator", f"EV/Umsatz {er:.0f}", "EV/Umsatz > 15", "Yahoo Finance")
    if m.get("vol") is not None and m["vol"] > 0.55:
        add("potential", "Markt", "Sehr hohe Volatilität", f"{m['vol']:.0%} p. a.", "Volatilität > 55 %", "Kursdaten Yahoo Finance (Tagesschluss)")
    if m.get("mdd") is not None and m["mdd"] > 0.4:
        add("potential", "Markt", "Starker Drawdown", f"−{m['mdd']:.0%} vom Hoch", "Drawdown 1 J > 40 %", "Kursdaten Yahoo Finance")
    if m.get("trend") is not None and m["trend"] < -0.15:
        add("potential", "Markt", "Deutlich unter 200-Tage-Linie", f"{m['trend']:+.0%}", "> 15 % unter 200-Tage-Linie", "Kursdaten Yahoo Finance")
    spf = num(info.get("shortPercentOfFloat"))
    if spf is not None and spf > 0.10:
        add("potential", "Sentiment", "Hohes Short Interest", f"{spf:.0%} des Streubesitzes", "> 10 % leerverkauft", "Yahoo Finance (FINRA-Meldungen, nur USA)")
    sp = [num(r.get("surprisePercent")) for r in ((est or {}).get("surprise") or {}).values()]
    sp = [x for x in sp if x is not None]
    if len(sp) >= 2 and sp[-1] < 0 and sp[-2] < 0:
        add("potential", "Fundamental", "Zwei Quartale in Folge unter Erwartung", f"{sp[-2]:+.0%}, {sp[-1]:+.0%}", "2× negative Earnings Surprise", "Yahoo Finance Earnings History")
    downs = [a for a in (events or {}).get("actions") or [] if a.get("action") == "down"]
    if len(downs) >= 2:
        add("potential", "Sentiment", "Mehrere Analysten-Herabstufungen", f"{len(downs)} in 90 Tagen", "≥ 2 Downgrades", "Yahoo Finance Up-/Downgrades")
    # Datenqualität
    if fx_note:
        add("dq", "Daten", "Berichtswährung ≠ Kurswährung", fx_note, "Umrechnung zum aktuellen Kurs", "Yahoo Finance")
    if stm_age_days is None:
        add("dq", "Daten", "Keine Jahresabschlüsse verfügbar", "–", "Finanzberichte fehlen", "Yahoo Finance")
    elif stm_age_days > 460:
        add("dq", "Daten", "Jahresabschluss veraltet", f"GJ-Ende {fy}", "> 15 Monate alt", "Yahoo Finance")
    na = num(info.get("numberOfAnalystOpinions"))
    if na is None or na < 3:
        add("dq", "Daten", "Kaum Analystenabdeckung", f"{int(na) if na else 0} Analysten", "< 3 Analysten", "Yahoo Finance")
    return F
