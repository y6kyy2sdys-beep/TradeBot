"""Backtest der Branchenrotation mit dem kursbasierten Teil des Branchen-Scores.

Nur relative Stärke und Risiko sind historisch point-in-time verfügbar (aus Kursen). Bewertung,
Fundamentaldaten und Gewinnrevisionen gibt es kostenlos nicht als Zeitreihe → sie werden NICHT
rückgetestet. Ablauf: Monatsende t → Score aus Kursen bis t → Top-N gleichgewichtet von t bis t+1.
Kosten: Provision + Slippage auf den gehandelten Anteil. Total Return (dividendenbereinigt).
Universum: heute existierende ETFs, aufgenommen erst ab ihrer Auflage (Rest-Survivorship-Bias:
Auswahl der Branchen erfolgte heute). Eigene Körbe (KI, Luxus) sind ausgeschlossen.
"""

import numpy as np
import pandas as pd

COST = 0.0010      # 0,10 % je gehandeltem Betrag (Provision/Spread)
SLIP = 0.0005      # 0,05 % Slippage


def _z(s: pd.Series) -> pd.Series:
    s = s.dropna()
    if len(s) < 3 or s.std() == 0:
        return s * 0
    return ((s - s.mean()) / s.std()).clip(-2.5, 2.5)


def monthly_scores(P: pd.DataFrame, bench: str) -> dict:
    """Je Monatsende: Score = 15/25 × relative Stärke + 10/25 × (−Risiko) aus Tageskursen bis zu diesem Tag."""
    me = P.resample("ME").last().index
    out = {}
    for t in me:
        d = P[P.index <= t]
        if len(d) < 260:
            continue
        b = d[bench]
        rs, rk = {}, {}
        for c in d.columns:
            if c == bench:
                continue
            s = d[c].dropna()
            if len(s) < 260 or s.index[-1] < t - pd.Timedelta(days=7):
                continue
            r = lambda x, n, sk=0: x.iat[-1 - sk] / x.iat[-1 - n] - 1
            bb = b.reindex(s.index).ffill()
            rs[c] = np.mean([r(s, 63) - r(bb, 63), r(s, 126) - r(bb, 126), r(s, 252, 21) - r(bb, 252, 21), s.iat[-1] / s.iloc[-200:].mean() - 1])
            dr = s.pct_change().iloc[-252:]
            y = s.iloc[-252:]
            rk[c] = np.mean([dr.std() * np.sqrt(252), -(y / y.cummax() - 1).min()])
        if len(rs) >= 8:
            sc = 0.6 * _z(pd.Series(rs)) + 0.4 * _z(-pd.Series(rk))
            out[t] = sc.sort_values(ascending=False)
    return out


def stats(r: pd.Series, b: pd.Series, rf: pd.Series) -> dict:
    r, b, rf = r.dropna(), b.reindex(r.index), rf.reindex(r.index).fillna(0)
    n = len(r)
    if n < 24:
        return {}
    eq = (1 + r).cumprod()
    cagr = eq.iat[-1] ** (12 / n) - 1
    ex = r - rf
    vol = r.std() * np.sqrt(12)
    dd = (eq / eq.cummax() - 1).min()
    down = ex[ex < 0]
    beta = np.cov(r, b)[0, 1] / b.var()
    alpha = ((r - rf) - beta * (b - rf)).mean() * 12
    act = r - b
    gains, losses = r[r > 0].sum(), -r[r < 0].sum()
    return {"months": n, "cagr": cagr, "vol": vol, "sharpe": ex.mean() / r.std() * np.sqrt(12) if r.std() else None,
            "sortino": ex.mean() * 12 / (np.sqrt((down ** 2).mean()) * np.sqrt(12)) if len(down) else None,
            "mdd": dd, "beta": beta, "alpha": alpha, "ir": act.mean() / act.std() * np.sqrt(12) if act.std() else None,
            "win": (r > 0).mean(), "beat": (act > 0).mean(), "pf": gains / losses if losses else None}


def run(P: pd.DataFrame, bench: str, rf_daily: pd.Series | None, cpi: pd.Series | None, top_ns=(3, 5, 7)) -> dict:
    P = P.dropna(how="all")
    scores = monthly_scores(P, bench)
    if len(scores) < 36:
        return {"error": "Zu wenig Historie für einen belastbaren Backtest."}
    me = P.resample("ME").last()
    mret = me.pct_change()
    rf = (rf_daily.resample("ME").mean() / 100 / 12) if rf_daily is not None else pd.Series(0.0, index=me.index)
    dates = sorted(scores)
    res = {}
    for N in top_ns:
        w_prev, rets, turns = pd.Series(dtype=float), {}, []
        for t, t1 in zip(dates[:-1], dates[1:]):
            pick = scores[t].index[:N]
            w = pd.Series(1 / len(pick), index=pick)
            turn = (w.reindex(w.index.union(w_prev.index), fill_value=0) - w_prev.reindex(w.index.union(w_prev.index), fill_value=0)).abs().sum() / 2
            turns.append(turn)
            gross = float((mret.loc[t1, pick].fillna(0) * w).sum())
            rets[t1] = gross - turn * 2 * (COST + SLIP)
            w_prev = w * (1 + mret.loc[t1, pick].fillna(0))
            w_prev = w_prev / w_prev.sum()
        r = pd.Series(rets)
        b = mret[bench].reindex(r.index)
        st = stats(r, b, rf)
        st["turnover"] = float(np.mean(turns))
        eq = (1 + r).cumprod()
        res[N] = {"stats": st, "equity": [[t.strftime("%Y-%m"), round(float(v), 4)] for t, v in eq.items()], "returns": r}
    main_r = res[5]["returns"]
    b = mret[bench].reindex(main_r.index)
    bench_stats = stats(b, b, rf)
    beq = (1 + b).cumprod()
    # Regime-Aufteilung (zu Monatsbeginn bekannt)
    regimes = {}
    trend = (me[bench] > me[bench].rolling(10).mean()).shift(1).reindex(main_r.index)
    for name, mask in (("S&P 500 über 10-Monats-Linie (Aufwärtstrend)", trend == True), ("S&P 500 unter 10-Monats-Linie (Abwärtstrend)", trend == False)):
        regimes[name] = _split(main_r, b, rf, mask)
    if cpi is not None:
        yoy = (cpi.resample("ME").last().pct_change(12) * 100).shift(2).reindex(main_r.index)   # 2 Monate Veröffentlichungsverzug
        for name, mask in (("Inflation > 3 %", yoy > 3), ("Inflation ≤ 3 %", yoy <= 3)):
            regimes[name] = _split(main_r, b, rf, mask)
    half = main_r.index[len(main_r) // 2]
    periods = {f"{main_r.index[0]:%Y}–{half:%Y}": _split(main_r, b, rf, main_r.index <= half),
               f"{half:%Y}–{main_r.index[-1]:%Y}": _split(main_r, b, rf, main_r.index > half)}
    clean = lambda d: {k: (None if v is None or (isinstance(v, float) and np.isnan(v)) else round(float(v), 4)) for k, v in d.items()}
    return {
        "start": main_r.index[0].strftime("%Y-%m"), "end": main_r.index[-1].strftime("%Y-%m"),
        "variants": {str(N): {"stats": clean(v["stats"]), "equity": v["equity"]} for N, v in res.items()},
        "benchmark": {"name": "S&P 500 (SPY, Total Return)", "stats": clean(bench_stats),
                      "equity": [[t.strftime("%Y-%m"), round(float(v), 4)] for t, v in beq.items()]},
        "regimes": {k: clean(v) for k, v in regimes.items()},
        "periods": {k: clean(v) for k, v in periods.items()},
        "latest_pick": list(scores[dates[-1]].index[:5]),
        "universe": [c for c in P.columns if c != bench],
        "costs": {"commission": COST, "slippage": SLIP},
        "method": ("Monatliches Rebalancing zum Monatsende, Signal nur aus Kursen bis zum Signaltag, Ausführung zum selben "
                   "Schlusskurs (leicht optimistisch; durch Slippage teilweise abgedeckt). Kosten je gehandeltem Betrag "
                   f"{COST:.2%} + {SLIP:.2%} Slippage. Feste, vorab gewählte Parameter (keine Optimierung); "
                   "Varianten Top 3/5/7 zeigen die Robustheit. Ergebnis ist kein Beweis für künftige Wertentwicklung."),
    }


def _split(r, b, rf, mask):
    mask = pd.Series(mask, index=r.index).fillna(False).astype(bool)
    rr, bb = r[mask], b[mask]
    if len(rr) < 12:
        return {"months": len(rr)}
    return {"months": len(rr), "avg_month": rr.mean(), "bench_avg_month": bb.mean(), "beat": (rr > bb).mean(),
            "ann": (1 + rr).prod() ** (12 / len(rr)) - 1, "bench_ann": (1 + bb).prod() ** (12 / len(bb)) - 1}
