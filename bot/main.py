"""Signal-Bot: scannt die Watchlist, prüft Signale per Backtest und meldet sie per Telegram.

Aufruf:
    python -m bot.main            # Scan + offene Signale auswerten
    python -m bot.main --report   # zusätzlich Tagesbericht senden
    python -m bot.main --test     # nur Testnachricht senden
    python -m bot.main --dry-run  # nichts senden, Ausgabe in der Konsole
"""

import argparse
import html
import json
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

from .strategies import STRATEGIES, add_indicators, backtest, simulate_trade
from .watchlist import MACRO, UNIVERSE

STATE_FILE = Path(__file__).resolve().parent.parent / "state" / "signals.json"

BUDGET_EUR = float(os.getenv("BUDGET_EUR", "100"))
FEE_PER_ORDER_EUR = float(os.getenv("FEE_PER_ORDER_EUR", "1"))
FEE_PCT = 2 * FEE_PER_ORDER_EUR / BUDGET_EUR  # Kauf + Verkauf
MIN_HIT_RATE = float(os.getenv("MIN_HIT_RATE", "0.70"))
MIN_TRADES = int(os.getenv("MIN_TRADES", "12"))
MAX_SIGNALS_PER_RUN = int(os.getenv("MAX_SIGNALS_PER_RUN", "3"))
HISTORY = os.getenv("HISTORY", "6y")

# Ungefährer Handelsschluss (Stunde UTC) je Börsensuffix; bis dahin ist die heutige Tageskerze unfertig.
CLOSE_HOUR_UTC = {
    ".DE": 16.75, ".PA": 16.75, ".AS": 16.75, ".MI": 16.75, ".SW": 16.75,
    ".CO": 16.0, ".L": 16.5, ".T": 6.5, ".HK": 8.25,
}


def close_hour(ticker: str) -> float:
    if ticker.endswith("-USD"):
        return 24.0  # Krypto: Tageskerze (UTC) erst um Mitternacht fertig
    for suffix, hour in CLOSE_HOUR_UTC.items():
        if ticker.endswith(suffix):
            return hour
    return 21.0  # USA


def esc(text) -> str:
    return html.escape(str(text), quote=False)


# ---------------------------------------------------------------- Daten


def download(tickers: list[str]) -> dict[str, pd.DataFrame]:
    raw = yf.download(
        tickers, period=HISTORY, interval="1d", group_by="ticker",
        auto_adjust=True, threads=True, progress=False,
    )
    now = datetime.now(timezone.utc)
    hour_now = now.hour + now.minute / 60
    out = {}
    for t in tickers:
        try:
            df = raw[t] if isinstance(raw.columns, pd.MultiIndex) else raw
        except KeyError:
            continue
        df = df.dropna(subset=["Open", "High", "Low", "Close"]).copy()
        if df.empty:
            continue
        df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
        if df.index[-1].date() >= now.date() and hour_now < close_hour(t):
            df = df.iloc[:-1]
        df["Volume"] = df["Volume"].fillna(0)
        out[t] = df
    return out


def fundamentals(ticker: str) -> dict:
    try:
        info = yf.Ticker(ticker).info or {}
    except Exception:
        return {}
    return info


def fundamental_check(info: dict) -> tuple[bool, list[str]]:
    """Nur für Einzelaktien: grobe Qualitätsprüfung. ETFs/Krypto werden durchgelassen."""
    if info.get("quoteType") != "EQUITY":
        return True, []
    lines, ok = [], True
    pe, fpe = info.get("trailingPE"), info.get("forwardPE")
    margin = info.get("profitMargins")
    growth = info.get("revenueGrowth")
    debt = info.get("debtToEquity")
    if pe:
        lines.append(f"KGV {pe:.1f}" + (f" (erwartet {fpe:.1f})" if fpe else ""))
    if margin is not None:
        lines.append(f"Gewinnmarge {margin * 100:.1f}%")
        ok &= margin > 0
    if growth is not None:
        lines.append(f"Umsatzwachstum {growth * 100:+.1f}%")
        ok &= growth > -0.10
    if debt is not None:
        lines.append(f"Verschuldung/EK {debt:.0f}%")
        ok &= debt < 300
    rec = info.get("recommendationKey")
    target = info.get("targetMeanPrice")
    if rec and rec != "none":
        lines.append(f"Analysten: {rec}" + (f", Ø Kursziel {target:.2f}" if target else ""))
    return ok, lines


def ticker_news(ticker: str, limit: int = 2) -> list[str]:
    try:
        items = yf.Ticker(ticker).news or []
    except Exception:
        return []
    titles = []
    for item in items:
        content = item.get("content", item)
        title = content.get("title")
        if title:
            titles.append(title)
        if len(titles) >= limit:
            break
    return titles


def world_headlines(limit: int = 4) -> list[str]:
    url = (
        "https://news.google.com/rss/search?q=B%C3%B6rse+OR+Weltwirtschaft+OR+Zinsen"
        "+OR+Z%C3%B6lle+OR+Geopolitik+when:1d&hl=de&gl=DE&ceid=DE:de"
    )
    try:
        root = ET.fromstring(requests.get(url, timeout=15).content)
    except Exception:
        return []
    return [el.findtext("title") for el in root.iter("item")][:limit]


# ---------------------------------------------------------------- Marktumfeld


def market_context(data: dict[str, pd.DataFrame]) -> dict:
    ctx = {"lines": [], "risk_off": False}
    for sym, label in MACRO.items():
        df = data.get(sym)
        if df is None or len(df) < 2:
            continue
        last, prev = df["Close"].iat[-1], df["Close"].iat[-2]
        chg = (last / prev - 1) * 100
        ctx["lines"].append(f"{label}: {last:,.2f} ({chg:+.1f}%)")
    vix = data.get("^VIX")
    spx = data.get("^GSPC")
    if vix is not None and not vix.empty and vix["Close"].iat[-1] > 30:
        ctx["risk_off"] = True
    if spx is not None and len(spx) > 200 and spx["Close"].iat[-1] < spx["Close"].rolling(200).mean().iat[-1]:
        ctx["risk_off"] = True
    ctx["regime"] = "⚠️ Risk-off (Stress am Markt) – strengere Filter aktiv" if ctx["risk_off"] else "✅ Risk-on (Markt im Aufwärtstrend)"
    return ctx


# ---------------------------------------------------------------- Telegram


def send(text: str, dry_run: bool) -> None:
    if dry_run:
        print("----- TELEGRAM -----\n" + text + "\n")
        return
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
        timeout=20,
    )
    if not r.ok:
        print("Telegram-Fehler:", r.status_code, r.text, file=sys.stderr)


# ---------------------------------------------------------------- Zustand


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"open": [], "closed": []}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")


def track_record(state: dict) -> str:
    closed = state["closed"]
    if not closed:
        return "Bisher keine abgeschlossenen Signale."
    wins = sum(s["net_pct"] > 0 for s in closed)
    avg = sum(s["net_pct"] for s in closed) / len(closed)
    return f"Echte Bilanz: {wins}/{len(closed)} Treffer ({wins / len(closed):.0%}), Ø {avg:+.1f}% netto je Signal"


# ---------------------------------------------------------------- Logik


def evaluate_open(state: dict, data: dict[str, pd.DataFrame], dry_run: bool) -> None:
    still_open = []
    for s in state["open"]:
        df = data.get(s["ticker"])
        if df is None:
            still_open.append(s)
            continue
        after = df.index > pd.Timestamp(s["signal_date"])
        if not after.any():
            still_open.append(s)
            continue
        entry_idx = int(after.argmax())
        entry = df["Open"].iat[entry_idx]
        if entry > s["ref_close"] * 1.01:
            send(
                f"⏭ <b>{esc(s['name'])} ({esc(s['ticker'])})</b>: Eröffnung {entry:.2f} lag über dem "
                f"Kauflimit {s['ref_close'] * 1.01:.2f} – Signal nicht ausgeführt, nicht hinterherkaufen.",
                dry_run,
            )
            continue
        res = simulate_trade(df, entry_idx, s["target"], s["stop"], s["max_days"])
        if res is None:
            still_open.append(s)
            continue
        exit_price, exit_idx, reason = res
        net = (exit_price / entry - 1 - FEE_PCT) * 100
        s.update(entry=round(float(entry), 4), exit=round(float(exit_price), 4), reason=reason,
                 exit_date=str(df.index[exit_idx].date()), net_pct=round(float(net), 2))
        state["closed"].append(s)
        icon = {"target": "🎯 Kursziel erreicht", "stop": "🛑 Stop-Loss ausgelöst", "time": "⏱ Haltedauer abgelaufen"}[reason]
        send(
            f"<b>{icon}: {esc(s['name'])} ({esc(s['ticker'])})</b>\n"
            f"Einstieg {entry:.2f} → Ausstieg {exit_price:.2f} {esc(s['currency'])}\n"
            f"Ergebnis netto (inkl. Gebühren): <b>{net:+.1f}%</b>\n"
            + ("👉 Jetzt verkaufen, falls noch nicht automatisch geschehen.\n" if reason == "time" else "")
            + f"\n{track_record(state)}",
            dry_run,
        )
    state["open"] = still_open


def find_signals(data: dict[str, pd.DataFrame], state: dict, min_hit: float) -> list[dict]:
    recent = {s["ticker"] for s in state["open"]}
    cutoff = (datetime.now(timezone.utc) - timedelta(days=5)).date().isoformat()
    recent |= {s["ticker"] for s in state["closed"] if s["signal_date"] >= cutoff}
    found = []
    for t in UNIVERSE:
        df = data.get(t)
        if df is None or len(df) < 300 or t in recent:
            continue
        df = add_indicators(df)
        for strat in STRATEGIES:
            if not strat.signals(df).iat[-1]:
                continue
            bt = backtest(df.iloc[:-1], strat, FEE_PCT)
            if bt.trades < MIN_TRADES or bt.hit_rate < min_hit or bt.avg_net <= 0:
                print(f"{t} {strat.key}: verworfen (n={bt.trades}, Treffer={bt.hit_rate:.0%}, Ø={bt.avg_net:+.2%})")
                continue
            last = df.iloc[-1]
            found.append({
                "ticker": t, "strat": strat, "bt": bt, "close": float(last["Close"]),
                "target": float(last["Close"] + strat.target_atr * last["atr"]),
                "stop": float(last["Close"] - strat.stop_atr * last["atr"]),
                "date": str(df.index[-1].date()), "rsi14": float(last["rsi14"]),
                "score": bt.wilson_low * bt.avg_net,
            })
    found.sort(key=lambda f: f["score"], reverse=True)
    return found


def signal_message(f: dict, info: dict, fund_lines: list[str], news: list[str], ctx: dict) -> str:
    strat, bt = f["strat"], f["bt"]
    name = info.get("shortName") or info.get("longName") or f["ticker"]
    cur = info.get("currency", "")
    up = f["target"] / f["close"] - 1
    down = 1 - f["stop"] / f["close"]
    gain_eur = BUDGET_EUR * up - 2 * FEE_PER_ORDER_EUR
    loss_eur = BUDGET_EUR * down + 2 * FEE_PER_ORDER_EUR
    parts = [
        f"🟢 <b>KAUFSIGNAL: {esc(name)} ({esc(f['ticker'])})</b>",
        f"Strategie: {esc(strat.name)}",
        "",
        f"Schlusskurs {f['date']}: <b>{f['close']:.2f} {esc(cur)}</b>",
        f"Kauf: morgen zur Eröffnung, max. {f['close'] * 1.01:.2f}",
        f"🎯 Kursziel: {f['target']:.2f} ({up:+.1%})",
        f"🛑 Stop-Loss: {f['stop']:.2f} ({-down:.1%})",
        f"⏱ Max. Haltedauer: {strat.max_days} Handelstage",
        "",
        f"📈 Geschätzte Rendite: <b>{up - FEE_PCT:+.1%} netto</b> bei Erfolg",
        f"   Bei {BUDGET_EUR:.0f} €: +{gain_eur:.2f} € Chance / −{loss_eur:.2f} € Risiko",
        f"📊 Backtest ({HISTORY}): <b>{bt.hit_rate:.0%} Treffer</b> in {bt.trades} Trades, "
        f"Ø {bt.avg_net:+.1%} netto/Trade (konservativ ≥{bt.wilson_low:.0%})",
        "",
        f"<b>Warum?</b> {esc(strat.why)}",
    ]
    if fund_lines:
        parts += ["", "<b>Fundamentaldaten:</b> " + esc(" · ".join(fund_lines))]
    if news:
        parts += ["", "<b>Aktuelle Meldungen:</b>"] + [f"• {esc(n)}" for n in news]
    parts += ["", f"<b>Marktumfeld:</b> {ctx['regime']}"]
    parts += ["", "<i>Keine Anlageberatung. Backtest-Quoten sind Vergangenheit, keine Garantie. Stop-Loss immer setzen.</i>"]
    return "\n".join(parts)


def daily_report(state: dict, ctx: dict, n_signals: int, dry_run: bool) -> None:
    parts = ["📰 <b>Tagesbericht</b>", "", f"<b>Marktumfeld:</b> {ctx['regime']}"]
    parts += [esc(line) for line in ctx["lines"]]
    headlines = world_headlines()
    if headlines:
        parts += ["", "<b>Weltlage (Schlagzeilen):</b>"] + [f"• {esc(h)}" for h in headlines]
    parts += ["", f"Neue Signale heute: {n_signals}"]
    if state["open"]:
        parts += ["<b>Offene Signale:</b>"] + [
            f"• {esc(s['name'])}: Ziel {s['target']:.2f} / Stop {s['stop']:.2f}" for s in state["open"]
        ]
    parts += ["", track_record(state)]
    send("\n".join(parts), dry_run)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--test", action="store_true")
    args = ap.parse_args()

    if args.test:
        send("✅ Signal-Bot ist verbunden. Kaufsignale kommen ab jetzt hierher.", args.dry_run)
        return

    state = load_state()
    data = download(UNIVERSE + list(MACRO))
    print(f"Daten geladen: {len(data)} Werte")
    ctx = market_context(data)

    evaluate_open(state, data, args.dry_run)

    min_hit = MIN_HIT_RATE + (0.05 if ctx["risk_off"] else 0)
    candidates = find_signals(data, state, min_hit)
    sent = 0
    for f in candidates:
        if sent >= MAX_SIGNALS_PER_RUN:
            break
        info = fundamentals(f["ticker"])
        ok, fund_lines = fundamental_check(info)
        if not ok:
            print(f"{f['ticker']}: fundamental verworfen ({fund_lines})")
            continue
        send(signal_message(f, info, fund_lines, ticker_news(f["ticker"]), ctx), args.dry_run)
        state["open"].append({
            "ticker": f["ticker"], "name": info.get("shortName") or f["ticker"],
            "currency": info.get("currency", ""), "strategy": f["strat"].key,
            "signal_date": f["date"], "ref_close": round(f["close"], 4),
            "target": round(f["target"], 4), "stop": round(f["stop"], 4),
            "max_days": f["strat"].max_days,
            "backtest_hit": round(f["bt"].hit_rate, 3), "backtest_trades": f["bt"].trades,
        })
        sent += 1

    if args.report:
        daily_report(state, ctx, sent, args.dry_run)
    save_state(state)
    print(f"Fertig: {sent} neue Signale, {len(state['open'])} offen")


if __name__ == "__main__":
    main()
