"""Regelbasierte Marktregime-Erkennung aus messbaren Indikatoren.

Bewusst KEINE Wahrscheinlichkeiten: Jeder Indikator stimmt nach einer festen, sichtbaren Regel ab
(+1 / 0 / −1). Ergebnis = Abstimmung je Achse (Wachstum, Inflation, Risikoappetit); die Unsicherheit
ist die Uneinigkeit der Indikatoren. Die Zyklusphase ist der Kriterienkatalog mit den meisten
erfüllten Bedingungen. Schwerpunkt USA, weil dort die Datenlage am vollständigsten ist.
Hinweis: FRED liefert den heutigen Datenstand (inkl. späterer Revisionen), keine Echtzeit-Vintages.
"""

import pandas as pd


def _upto(s: pd.Series | None, asof: pd.Timestamp, lag_days: int = 0) -> pd.Series | None:
    if s is None:
        return None
    s = s[s.index <= asof - pd.Timedelta(days=lag_days)]
    return s if len(s) else None


def _yoy(s: pd.Series) -> float | None:
    m = s.resample("ME").last().dropna()
    return float(m.iat[-1] / m.iat[-13] * 100 - 100) if len(m) > 13 else None


def _ann3m(s: pd.Series) -> float | None:
    m = s.resample("ME").last().dropna()
    return float(((m.iat[-1] / m.iat[-4]) ** 4 - 1) * 100) if len(m) > 4 else None


def indicators(F: dict, spy: pd.Series | None, sector_closes: pd.DataFrame | None, asof: pd.Timestamp) -> dict:
    """Berechnet alle Indikatoren zum Stichtag (Monatsdaten mit 35 Tagen Veröffentlichungsverzug)."""
    g = lambda k, lag=0: _upto(F.get(k), asof, lag)
    out = {}

    def add(key, name, value, unit, vote, axis, rule, src, date=None):
        out[key] = {"key": key, "name": name, "value": None if value is None else round(float(value), 3), "unit": unit,
                    "vote": vote if value is not None else None, "axis": axis, "rule": rule, "source": src,
                    "asof": date.strftime("%Y-%m-%d") if date is not None else None}

    # --- Wachstum
    u = g("UNRATE", 35)
    if u is not None and len(u) > 15:
        a3 = u.rolling(3).mean()
        sahm = float(a3.iat[-1] - a3.iloc[-13:-1].min())
        add("sahm", "Sahm-Regel (Arbeitslosigkeit)", sahm, "pp", 1 if sahm < 0.3 else -1 if sahm >= 0.5 else 0, "growth",
            "< 0,3 Expansion · ≥ 0,5 historisches Rezessionssignal", "BLS/FRED UNRATE", u.index[-1])
    else:
        add("sahm", "Sahm-Regel (Arbeitslosigkeit)", None, "pp", None, "growth", "", "BLS/FRED UNRATE")
    p = g("PAYEMS", 35)
    v = float(p.diff().iloc[-3:].mean()) if p is not None and len(p) > 4 else None
    add("payrolls", "Stellenaufbau (Ø 3 Monate)", v, "Tsd./Monat", None if v is None else 1 if v > 100 else -1 if v < 0 else 0, "growth",
        "> 100 Tsd. robust · < 0 Stellenabbau", "BLS/FRED PAYEMS", p.index[-1] if p is not None else None)
    ip = g("INDPRO", 35)
    v = _yoy(ip) if ip is not None else None
    add("indpro", "Industrieproduktion (ggü. Vorjahr)", v, "%", None if v is None else 1 if v > 1 else -1 if v < -1 else 0, "growth",
        "> +1 % Expansion · < −1 % Kontraktion", "Fed/FRED INDPRO", ip.index[-1] if ip is not None else None)
    c = g("ICSA", 7)
    if c is not None and len(c) > 60:
        r = float(c.rolling(4).mean().iat[-1] / c.rolling(4).mean().iloc[-52:].min() - 1) * 100
        add("claims", "Erstanträge ggü. 52-Wochen-Tief", r, "%", 1 if r < 15 else -1 if r > 30 else 0, "growth",
            "< +15 % unauffällig · > +30 % deutliche Verschlechterung", "DOL/FRED ICSA", c.index[-1])
    else:
        add("claims", "Erstanträge ggü. 52-Wochen-Tief", None, "%", None, "growth", "", "DOL/FRED ICSA")
    yc = g("T10Y3M")
    v = float(yc.iat[-1]) if yc is not None else None
    add("curve", "Zinskurve 10J − 3M", v, "pp", None if v is None else 1 if v > 0.5 else -1 if v < 0 else 0, "growth",
        "> 0,5 normal · < 0 invertiert (Frühindikator Rezession)", "FRED T10Y3M", yc.index[-1] if yc is not None else None)

    # --- Inflation
    cc = g("CPILFESL", 35)
    yo = _yoy(cc) if cc is not None else None
    add("core_cpi", "Kerninflation CPI (ggü. Vorjahr)", yo, "%", None if yo is None else 1 if yo > 3 else -1 if yo < 2.5 else 0, "inflation",
        "> 3 % erhöht · < 2,5 % nahe Ziel", "BLS/FRED CPILFESL", cc.index[-1] if cc is not None else None)
    a3 = _ann3m(cc) if cc is not None else None
    d = None if a3 is None or yo is None else a3 - yo
    add("core_cpi_mom", "Kerninflation 3M annualisiert − Vorjahresrate", d, "pp", None if d is None else 1 if d > 0.3 else -1 if d < -0.3 else 0,
        "inflation", "> +0,3 beschleunigt · < −0,3 verlangsamt", "BLS/FRED CPILFESL", cc.index[-1] if cc is not None else None)
    pc = g("PCEPILFE", 35)
    v = _yoy(pc) if pc is not None else None
    add("core_pce", "Kern-PCE (Fed-Zielgröße)", v, "%", None if v is None else 1 if v > 2.7 else -1 if v < 2.3 else 0, "inflation",
        "> 2,7 % über Ziel · < 2,3 % nahe Ziel (2 %)", "BEA/FRED PCEPILFE", pc.index[-1] if pc is not None else None)
    be = g("T10YIE")
    v = float(be.iat[-1]) if be is not None else None
    add("breakeven", "Inflationserwartung 10J", v, "%", None if v is None else 1 if v > 2.5 else -1 if v < 2.1 else 0, "inflation",
        "> 2,5 % erhöht · < 2,1 % verankert", "FRED T10YIE", be.index[-1] if be is not None else None)

    # --- Risikoappetit
    if spy is not None:
        s = spy[spy.index <= asof]
        if len(s) > 200:
            v = float(s.iat[-1] / s.rolling(200).mean().iat[-1] - 1) * 100
            add("trend", "S&P 500 ggü. 200-Tage-Linie", v, "%", 1 if v > 0 else -1, "risk", "über Linie = Aufwärtstrend", "Yahoo Finance SPY (Tagesschluss)", s.index[-1])
    vx = g("VIXCLS")
    v = float(vx.iat[-1]) if vx is not None else None
    add("vix", "VIX", v, "Punkte", None if v is None else 1 if v < 18 else -1 if v > 25 else 0, "risk", "< 18 ruhig · > 25 Stress", "Cboe/FRED VIXCLS",
        vx.index[-1] if vx is not None else None)
    hy = g("BAMLH0A0HYM2")
    if hy is not None and len(hy) > 70:
        lvl, ch = float(hy.iat[-1]), float(hy.iat[-1] - hy.iat[-64])
        add("hy", "High-Yield-Spread (Δ 3 Monate)", lvl, "pp", 1 if lvl < 4 and ch < 0.5 else -1 if lvl > 5 or ch > 1 else 0, "risk",
            f"< 4 und stabil = entspannt · > 5 oder +1 pp in 3 M = Stress (Δ {ch:+.2f})", "ICE BofA/FRED BAMLH0A0HYM2", hy.index[-1])
    if sector_closes is not None and len(sector_closes) > 200:
        sc = sector_closes[sector_closes.index <= asof]
        above = [(sc[c].dropna().iat[-1] > sc[c].dropna().rolling(200).mean().iat[-1]) for c in sc if sc[c].dropna().size > 200]
        if len(above) >= 10:
            v = 100 * sum(above) / len(above)
            add("breadth", "Marktbreite: Branchen über 200-Tage-Linie", v, "%", 1 if v > 60 else -1 if v < 40 else 0, "risk",
                "> 60 % breit getragen · < 40 % schmal", "Yahoo Finance Branchen-ETFs", sc.index[-1])
    nf = g("NFCI", 7)
    v = float(nf.iat[-1]) if nf is not None else None
    add("nfci", "Finanzierungsbedingungen (NFCI)", v, "Index", None if v is None else 1 if v < -0.2 else -1 if v > 0 else 0, "risk",
        "< −0,2 locker · > 0 straffer als im Schnitt", "Chicago Fed/FRED NFCI", nf.index[-1] if nf is not None else None)

    # --- Geldpolitik/Liquidität (Information, fließt in Zyklusregeln ein)
    ff = g("DFF")
    if ff is not None and len(ff) > 260:
        ch = float(ff.iat[-1] - ff.iloc[-260])
        add("fed12m", "Fed Funds: Veränderung 12 Monate", ch, "pp", None, "policy", "< 0 Zinssenkungen · > 0 Zinserhöhungen", "Fed/FRED DFF", ff.index[-1])
        if "core_pce" in out and out["core_pce"]["value"] is not None:
            add("realrate", "Realzins (Fed Funds − Kern-PCE)", float(ff.iat[-1]) - out["core_pce"]["value"], "pp", None, "policy",
                "> 1,5 restriktiv · < 0 expansiv", "Fed/BEA via FRED", ff.index[-1])
    wl = g("WALCL", 7)
    if wl is not None and len(wl) > 14:
        add("fedbs", "Fed-Bilanz: Veränderung 13 Wochen", float(wl.iat[-1] / wl.iat[-14] - 1) * 100, "%", None, "policy",
            "< 0 Liquiditätsentzug (QT) · > 0 Ausweitung", "Fed/FRED WALCL", wl.index[-1])
    return out


def _axis(ind: dict, axis: str) -> dict:
    votes = [i["vote"] for i in ind.values() if i["axis"] == axis and i["vote"] is not None]
    total = sum(1 for i in ind.values() if i["axis"] == axis)
    if not votes:
        return {"score": None, "n": 0, "of": total, "agree": None, "certainty": "keine Daten"}
    sc = sum(votes) / len(votes)
    sign = 1 if sc > 0 else -1 if sc < 0 else 0
    agree = sum(1 for v in votes if v == sign) / len(votes)
    cert = "hoch" if agree >= 0.75 and abs(sc) >= 0.5 else "mittel" if agree >= 0.5 else "niedrig"
    return {"score": round(sc, 2), "n": len(votes), "of": total, "agree": round(agree, 2), "certainty": cert,
            "pro": sum(v > 0 for v in votes), "contra": sum(v < 0 for v in votes), "neutral": sum(v == 0 for v in votes)}


def _unemp_stats(F: dict, asof: pd.Timestamp):
    u = _upto(F.get("UNRATE"), asof, 35)
    if u is None or len(u) < 30:
        return None
    return {"last": float(u.iat[-1]), "min24": float(u.iloc[-24:].min()), "trend6": float(u.rolling(3).mean().iat[-1] - u.rolling(3).mean().iat[-7])}


def classify(F: dict, spy, sector_closes, asof: pd.Timestamp) -> dict:
    ind = indicators(F, spy, sector_closes, asof)
    G, I, R = _axis(ind, "growth"), _axis(ind, "inflation"), _axis(ind, "risk")
    gs, is_ = G["score"], I["score"]
    if gs is None or is_ is None:
        quad = None
    elif gs > 0.2:
        quad = "Inflationary Growth" if is_ > 0.2 else "Disinflationary Growth"
    elif gs < -0.2:
        quad = "Stagflation" if is_ > 0.2 else ("Recession" if gs <= -0.5 else "Slowdown")
    else:
        quad = "Stagflation-Risiko" if is_ > 0.5 else "Slowdown"
    risk = None if R["score"] is None else "Risk-On" if R["score"] > 0.2 else "Risk-Off" if R["score"] < -0.2 else "Neutral"

    v = lambda k: (ind.get(k) or {}).get("value")
    us = _unemp_stats(F, asof)
    crit = {
        "Recession": [("Sahm-Regel ≥ 0,5", v("sahm") is not None and v("sahm") >= 0.5),
                      ("Stellenabbau (Ø 3 M < 0)", v("payrolls") is not None and v("payrolls") < 0),
                      ("Industrieproduktion < −1 % ggü. Vorjahr", v("indpro") is not None and v("indpro") < -1),
                      ("Erstanträge > +30 % über Tief", v("claims") is not None and v("claims") > 30)],
        "Recovery": [("Arbeitslosigkeit ≥ 0,8 pp über 24-M-Tief", bool(us and us["last"] - us["min24"] >= 0.8)),
                     ("Arbeitslosigkeit sinkt wieder (6 M)", bool(us and us["trend6"] < 0)),
                     ("Steile Zinskurve (10J−3M > 0,5)", v("curve") is not None and v("curve") > 0.5),
                     ("Fed hat gesenkt (12 M)", v("fed12m") is not None and v("fed12m") < -0.25)],
        "Early Cycle": [("Wachstumsindikatoren überwiegend positiv", gs is not None and gs > 0),
                        ("Arbeitslosigkeit sinkt (6 M)", bool(us and us["trend6"] < 0)),
                        ("Steile Zinskurve (10J−3M > 0,5)", v("curve") is not None and v("curve") > 0.5),
                        ("Inflation nicht beschleunigend", v("core_cpi_mom") is not None and v("core_cpi_mom") <= 0.3)],
        "Mid Cycle": [("Wachstumsindikatoren überwiegend positiv", gs is not None and gs > 0),
                      ("Arbeitslosigkeit nahe Tief (≤ 0,5 pp)", bool(us and us["last"] - us["min24"] <= 0.5)),
                      ("Kerninflation 2–3,5 %", v("core_cpi") is not None and 2 <= v("core_cpi") <= 3.5),
                      ("Kreditspreads entspannt (HY < 4,5)", v("hy") is not None and v("hy") < 4.5)],
        "Late Cycle": [("Arbeitslosigkeit am Tief (≤ 0,3 pp)", bool(us and us["last"] - us["min24"] <= 0.3)),
                       ("Flache/inverse Zinskurve (< 0,25)", v("curve") is not None and v("curve") < 0.25),
                       ("Kerninflation > 3 % oder beschleunigend", (v("core_cpi") or 0) > 3 or (v("core_cpi_mom") or 0) > 0.3),
                       ("Restriktive Geldpolitik (Realzins > 1,5 oder Zinserhöhungen)", (v("realrate") or 0) > 1.5 or (v("fed12m") or 0) > 0.25)],
    }
    phases = []
    for name, cs in crit.items():
        met = sum(1 for _, ok in cs if ok)
        phases.append({"phase": name, "met": met, "of": len(cs), "criteria": [{"text": t, "ok": bool(ok)} for t, ok in cs]})
    order = ["Recession", "Late Cycle", "Mid Cycle", "Early Cycle", "Recovery"]
    best = max(phases, key=lambda p: (p["met"], -order.index(p["phase"])))
    return {"asof": asof.strftime("%Y-%m-%d"), "indicators": ind, "axes": {"growth": G, "inflation": I, "risk": R},
            "quadrant": quad, "risk": risk, "phase": best["phase"], "phase_met": best["met"], "phase_of": best["of"], "phases": phases}


def regime(F: dict, spy, sector_closes) -> dict:
    now = pd.Timestamp.now().normalize()
    cur = classify(F, spy, sector_closes, now)
    prev = classify(F, spy, sector_closes, now - pd.Timedelta(days=91))
    cur["previous"] = {k: prev[k] for k in ("asof", "quadrant", "risk", "phase", "phase_met", "phase_of")} | {"axes": prev["axes"]}
    cur["method"] = ("Regelbasierte Indikator-Abstimmung: jeder Indikator stimmt nach fester Schwelle mit +1/0/−1. "
                     "Achsenwert = Durchschnitt der Stimmen; Sicherheit = Anteil gleichgerichteter Stimmen. "
                     "Keine Wahrscheinlichkeiten, da kein statistisch validiertes Modell. Monatsdaten werden mit "
                     "35 Tagen Verzug berücksichtigt; FRED liefert revidierte Daten (keine Echtzeit-Vintages).")
    return cur
