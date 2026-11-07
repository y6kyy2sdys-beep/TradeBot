"""Prüft die Kernberechnungen mit bekannten Ergebnissen (python -m unittest discover tests)."""
import unittest

import numpy as np
import pandas as pd

from bot import backtest_sectors as B
from bot import regime
from bot import scoring as S


def stm(rev=(100, 90, 80, 70), ebit=(20, 18, 16, 14), debt=(50, 40), cash=(10, 10), eq=(100, 95), shares=(10, 10), fcf=(15, 12), ni=(15, 13), intexp=(2, 2), ebitda=(30, 27)):
    n = len(rev)
    pad = lambda t: list(t) + [None] * (n - len(t))
    return {"is": {"periods": [f"{2025 - i}-12-31" for i in range(n)], "Total Revenue": list(rev), "Operating Income": list(ebit), "EBITDA": pad(ebitda),
                   "Net Income": pad(ni), "Interest Expense": pad(intexp), "Tax Rate For Calcs": [0.2] * n},
            "bs": {"Total Debt": pad(debt), "Cash And Cash Equivalents": pad(cash), "Stockholders Equity": pad(eq), "Ordinary Shares Number": pad(shares)},
            "cf": {"Free Cash Flow": pad(fcf), "Capital Expenditure": [-5] * n}}


class Statements(unittest.TestCase):
    def test_ratios(self):
        m = S.statements_metrics(stm())
        self.assertAlmostEqual(m["roic"], 20 * 0.8 / (50 + 100 - 10))          # EBIT·(1−t) / (Schulden + EK − Cash)
        self.assertAlmostEqual(m["nd_ebitda"], (50 - 10) / 30)
        self.assertAlmostEqual(m["int_cov"], 10)
        self.assertAlmostEqual(m["rev_cagr3"], (100 / 70) ** (1 / 3) - 1)
        self.assertAlmostEqual(m["rev_yoy_fy"], 100 / 90 - 1)
        self.assertAlmostEqual(m["cash_conv"], 1.0)
        self.assertAlmostEqual(m["dilution"], 0.0)

    def test_flags(self):
        sm = S.statements_metrics(stm(rev=(80, 100), ebit=(4, 15), debt=(200, 100), ebitda=(20, 25), intexp=(3, 2), fcf=(-5, 3), shares=(11, 10)))
        texts = {f["text"] for f in S.red_flags({}, sm, {}, {}, {}, False, None, 100)}
        for t in ("Hohe Nettoverschuldung", "Schwache Zinsdeckung", "Negativer Free Cashflow", "Umsatzrückgang", "Operative Marge sinkt",
                  "Verwässerung durch neue Aktien", "Schulden steigen deutlich schneller als das EBITDA"):
            self.assertIn(t, texts)
        clean = S.red_flags({}, S.statements_metrics(stm()), {"numberOfAnalystOpinions": 10}, {}, {}, False, None, 100)
        self.assertEqual([f for f in clean if f["level"] == "confirmed"], [])

    def test_missing_stays_missing(self):
        self.assertEqual(S.statements_metrics(None), {})
        m = S.holding_metrics({"forwardPE": None}, None, None)
        self.assertIsNone(m["fwd_ey"])
        self.assertIsNone(m["fcf_y"])


class Scores(unittest.TestCase):
    def test_zscores(self):
        z = S.zscores({c: float(i) for i, c in enumerate("abcdef")}, 1)
        self.assertAlmostEqual(sum(z.values()), 0, places=6)
        self.assertGreater(z["f"], z["a"])
        self.assertEqual(S.zscores({"a": 1, "b": 2}, 1), {})                  # zu wenige Werte → kein Score
        zn = S.zscores({c: float(i) for i, c in enumerate("abcdef")}, -1)
        self.assertLess(zn["f"], zn["a"])

    def test_shrinkage(self):
        metrics = {c: {"rs3": float(i), "rs6": float(i), "rs12": None, "trend": None, "hold_breadth": None, "volume": None} for i, c in enumerate("abcdefg")}
        ft = S.factor_table(metrics, {"strength": S.SECTOR_FACTORS["strength"]}, {})
        full = S.zscores({c: m["rs3"] for c, m in metrics.items()}, 1)
        self.assertAlmostEqual(ft["g"]["z"]["strength"], full["g"] * 2 / 6, places=2)   # 2 von 6 Kennzahlen → Faktor × 2/6
        one = {c: {**m, "rs6": None} for c, m in metrics.items()}
        self.assertNotIn("strength", S.factor_table(one, {"strength": S.SECTOR_FACTORS["strength"]}, {})["g"]["z"])   # 1 von 6 reicht nicht


class Backtest(unittest.TestCase):
    def test_stats_constant(self):
        idx = pd.period_range("2010-01", periods=60, freq="M").to_timestamp("M")
        r = pd.Series(0.01, index=idx) + np.random.default_rng(1).normal(0, 1e-6, 60)
        st = B.stats(r, r, pd.Series(0.0, index=idx))
        self.assertAlmostEqual(st["cagr"], 1.01 ** 12 - 1, places=4)
        self.assertAlmostEqual(st["mdd"], 0.0, places=4)
        self.assertAlmostEqual(st["beta"], 1.0, places=3)

    def test_no_lookahead(self):
        # Ein ETF, der erst NACH dem Signaltag stark steigt, darf am Signaltag keinen Vorteil haben
        days = pd.bdate_range("2005-01-03", "2012-12-31")
        g = np.random.default_rng(3)
        P = pd.DataFrame({f"E{i}": 100 * np.exp(np.cumsum(g.normal(0, 0.01, len(days)))) for i in range(9)}, index=days)
        P["SPY"] = 100 * np.exp(np.cumsum(g.normal(0, 0.01, len(days))))
        sc1 = B.monthly_scores(P, "SPY")
        P2 = P.copy()
        cut = pd.Timestamp("2010-06-30")
        P2.loc[P2.index > cut, "E0"] *= 3
        sc2 = B.monthly_scores(P2, "SPY")
        pd.testing.assert_series_equal(sc1[cut].sort_index(), sc2[cut].sort_index())


class Regime(unittest.TestCase):
    def test_axis(self):
        ind = {"a": {"axis": "growth", "vote": 1}, "b": {"axis": "growth", "vote": 1}, "c": {"axis": "growth", "vote": -1}, "d": {"axis": "growth", "vote": None}}
        a = regime._axis(ind, "growth")
        self.assertAlmostEqual(a["score"], 1 / 3, places=2)
        self.assertEqual((a["n"], a["of"], a["pro"], a["contra"]), (3, 4, 2, 1))


if __name__ == "__main__":
    unittest.main()
