"""Technische Indikatoren, Swing-Strategien (Haltedauer: Tage) und Backtest."""

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd


def rsi(close: pd.Series, n: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(100)


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    prev_close = df["Close"].shift(1)
    tr = pd.concat(
        [
            df["High"] - df["Low"],
            (df["High"] - prev_close).abs(),
            (df["Low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    c = df["Close"]
    df["sma20"] = c.rolling(20).mean()
    df["sma50"] = c.rolling(50).mean()
    df["sma200"] = c.rolling(200).mean()
    df["rsi2"] = rsi(c, 2)
    df["rsi14"] = rsi(c, 14)
    df["atr"] = atr(df)
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_sig"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["high20"] = c.rolling(20).max().shift(1)
    df["vol20"] = df["Volume"].rolling(20).mean()
    return df


@dataclass(frozen=True)
class Strategy:
    key: str
    name: str
    why: str
    target_atr: float  # Kursziel in ATR über Einstieg
    stop_atr: float  # Stop-Loss in ATR unter Einstieg
    max_days: int  # maximale Haltedauer in Handelstagen

    def signals(self, df: pd.DataFrame) -> pd.Series:
        c = df["Close"]
        uptrend = (c > df["sma200"]) & (df["sma50"] > df["sma200"])
        if self.key == "pullback":
            sig = uptrend & (df["rsi2"] < 10)
        elif self.key == "breakout":
            has_volume = df["vol20"] > 0
            vol_ok = ~has_volume | (df["Volume"] > 1.5 * df["vol20"])
            sig = (c > df["high20"]) & vol_ok & (c > df["sma50"]) & (df["rsi14"] < 75)
        elif self.key == "macd":
            cross = (df["macd"] > df["macd_sig"]) & (df["macd"].shift(1) <= df["macd_sig"].shift(1))
            sig = cross & (df["macd"] < 0) & (c > df["sma200"])
        else:
            raise ValueError(self.key)
        return sig.fillna(False)


STRATEGIES = [
    Strategy(
        "pullback",
        "Rücksetzer im Aufwärtstrend",
        "Langfristiger Aufwärtstrend intakt (Kurs über 200-Tage-Linie, 50 > 200), "
        "kurzfristig stark überverkauft (RSI(2) < 10). Solche Dellen wurden "
        "historisch oft schnell zurückgekauft.",
        target_atr=1.5,
        stop_atr=2.5,
        max_days=7,
    ),
    Strategy(
        "breakout",
        "Ausbruch auf 20-Tage-Hoch",
        "Schlusskurs über dem 20-Tage-Hoch bei deutlich erhöhtem Volumen, "
        "Trend über der 50-Tage-Linie, noch nicht überkauft (RSI(14) < 75). "
        "Hinweis auf neue Nachfrage / Momentum.",
        target_atr=2.0,
        stop_atr=1.5,
        max_days=10,
    ),
    Strategy(
        "macd",
        "MACD-Wende im Aufwärtstrend",
        "MACD kreuzt seine Signallinie unterhalb der Nulllinie nach oben, während "
        "der Kurs über der 200-Tage-Linie liegt: Ende einer Korrektur im Trend.",
        target_atr=2.0,
        stop_atr=2.0,
        max_days=10,
    ),
]


def simulate_trade(df: pd.DataFrame, entry_idx: int, target: float, stop: float, max_days: int):
    """Simuliert einen Trade ab Eröffnung von Bar `entry_idx`.

    Gibt (Ausstiegskurs, Index der Ausstiegsbar, Grund) zurück oder None,
    wenn der Trade noch nicht abgeschlossen ist. Stop wird vor Ziel geprüft
    (konservativ), Kurslücken werden zum Eröffnungskurs ausgeführt.
    """
    last = entry_idx + max_days - 1
    for j in range(entry_idx, min(last + 1, len(df))):
        o, h, l = df["Open"].iat[j], df["High"].iat[j], df["Low"].iat[j]
        if j > entry_idx and o <= stop:
            return o, j, "stop"
        if l <= stop:
            return stop, j, "stop"
        if j > entry_idx and o >= target:
            return o, j, "target"
        if h >= target:
            return target, j, "target"
    if last < len(df):
        return df["Close"].iat[last], last, "time"
    return None


@dataclass
class BacktestResult:
    trades: int
    wins: int
    avg_net: float  # durchschnittliche Netto-Rendite je Trade (nach Gebühren)

    @property
    def hit_rate(self) -> float:
        return self.wins / self.trades if self.trades else 0.0

    @property
    def wilson_low(self) -> float:
        """Untere Grenze des 90%-Konfidenzintervalls der Trefferquote."""
        if not self.trades:
            return 0.0
        z, n, p = 1.645, self.trades, self.hit_rate
        denom = 1 + z * z / n
        centre = p + z * z / (2 * n)
        margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
        return (centre - margin) / denom


def backtest(df: pd.DataFrame, strat: Strategy, fee_pct: float) -> BacktestResult:
    """Alle historischen Signale handeln (ohne Überlappung) – Einstieg am nächsten Tag zur Eröffnung."""
    sig = strat.signals(df).to_numpy()
    rets = []
    i = 0
    while i < len(df) - 1:
        if not sig[i] or np.isnan(df["atr"].iat[i]):
            i += 1
            continue
        entry = df["Open"].iat[i + 1]
        a = df["atr"].iat[i]
        res = simulate_trade(df, i + 1, entry + strat.target_atr * a, entry - strat.stop_atr * a, strat.max_days)
        if res is None:
            break
        exit_price, exit_idx, _ = res
        rets.append(exit_price / entry - 1 - fee_pct)
        i = exit_idx + 1
    wins = sum(r > 0 for r in rets)
    return BacktestResult(len(rets), wins, float(np.mean(rets)) if rets else 0.0)
