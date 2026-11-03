"""Signal-Bot: scannt die Watchlist, prüft Signale per Backtest und meldet sie per Telegram.

Aufruf:
    python -m bot.main            # Scan + offene Signale auswerten
    python -m bot.main --report   # zusätzlich Tagesbericht senden
    python -m bot.main --analysis # zusätzlich KI-Lageanalyse (Claude) mit Kaufideen
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

from . import analyst, auth, dashboard, depot, doomsday, macro, profiles, world
from .wkn import search_url, wkn
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
MIN_IDEA_TARGET_PCT = float(os.getenv("MIN_IDEA_TARGET_PCT", "8"))  # Kaufideen: Mindest-Kursziel in %
MAX_IDEAS_PER_RUN = int(os.getenv("MAX_IDEAS_PER_RUN", "2"))
MIN_IDEA_EV_PCT = float(os.getenv("MIN_IDEA_EV_PCT", "5"))  # Erwartungswert der Szenarien nach Gebühren
MAX_EXPLAIN_PER_RUN = int(os.getenv("MAX_EXPLAIN_PER_RUN", "3"))  # KI-Erklärungen für Marktbewegungen
ALERT_COOLDOWN_DAYS = {"move": 2, "scenario": 3, "warn": 5, "ki": 1, "depot": 3}

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


SEND_FAILURES = []


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
        SEND_FAILURES.append(r.status_code)


# ---------------------------------------------------------------- Zustand


def load_state() -> dict:
    state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    for k, default in (("open", []), ("closed", []), ("alerts", {})):
        state.setdefault(k, default)
    return state


def alert_due(state: dict, key: str) -> bool:
    """Duplikat-Schutz: dieselbe Meldung erst nach Ablauf der Sperrfrist erneut senden."""
    last = state["alerts"].get(key)
    if not last:
        return True
    days = ALERT_COOLDOWN_DAYS.get(key.split(":")[0], 3)
    return datetime.now(timezone.utc) - datetime.fromisoformat(last) >= timedelta(days=days)


def mark_alert(state: dict, key: str, kind: str, title: str) -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="minutes")
    state["alerts"][key] = now
    state.setdefault("alert_log", []).append({"time": now, "kind": kind, "title": title})
    state["alert_log"] = state["alert_log"][-100:]


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
        f"🟢 <b>KAUFSIGNAL (Swing, Tage): {esc(name)} ({esc(f['ticker'])})</b>",
        f"Strategie: {esc(strat.name)}",
        wkn_line(f["ticker"], name),
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


# ---------------------------------------------------------------- Makro, Warnungen, KI


def wkn_line(ticker: str, name: str, ki_wkn: str = "") -> str:
    w = wkn(ticker) or ki_wkn
    if w:
        return f"WKN: <b>{esc(w)}</b>" + ("" if wkn(ticker) else " (KI-Angabe, bitte prüfen)")
    return f'WKN: <a href="{esc(search_url(name))}">bei finanzen.net suchen</a>'


def bullets(title: str, items) -> list[str]:
    items = [i for i in items if i]
    return [f"<b>{title}</b>"] + [f"• {esc(i)}" for i in items] if items else []


def alert_message(a: "macro.Alert") -> str:
    if a.kind == "warning":
        parts = [f"⚠️ <b>MARKTWARNUNG: {esc(a.title)}</b>", ""] + [esc(f) for f in a.facts]
        parts += [""] + bullets("Bedeutung:", a.chain)
        parts += ["", "<i>Keine Panik-Verkäufe – aber Stop-Loss prüfen und neue Käufe klein halten.</i>"]
        return "\n".join(parts)
    parts = [f"🌍 <b>MAKRO-SIGNAL: {esc(a.title)}</b>", ""] + [esc(f) for f in a.facts]
    if a.reasons:
        parts += [""] + bullets("🔎 Warum? (KI-recherchiert)" if a.explained else "🔎 Mögliche Gründe (aktuelle Schlagzeilen):", a.reasons)
    if a.chain:
        parts += ["", "<b>Wirkungskette:</b>", esc(" → ".join(a.chain))]
    parts += [""] + bullets("📈 Mögliche Gewinner:", a.winners)
    parts += [""] + bullets("📉 Mögliche Verlierer:", a.losers)
    parts += [""] + bullets("🇩🇪 Folgen für Deutschland:", a.germany)
    if a.horizon:
        parts += ["", f"⏱ <b>Zeitperspektive:</b> {esc(a.horizon)}"]
    parts += ["", "<i>Einordnung, kein Kaufsignal.</i>"]
    return "\n".join(parts)


def ki_macro_message(m: dict) -> str:
    parts = [f"🌍 <b>MAKRO-ANALYSE: {esc(m['titel'])}</b>", f"Eintrittswahrscheinlichkeit: {esc(m['wahrscheinlichkeit'])}", "",
             esc(m["ausloeser"]), "", "<b>Wirkungskette:</b>", esc(" → ".join(m["wirkungskette"])), ""]
    parts += bullets("📈 Mögliche Gewinner:", m["gewinner"]) + [""]
    parts += bullets("📉 Mögliche Verlierer:", m["verlierer"])
    if m.get("auswirkung_deutschland"):
        parts += ["", f"🇩🇪 <b>Folgen für Deutschland:</b> {esc(m['auswirkung_deutschland'])}"]
    parts += ["", f"⏱ <b>Zeitperspektive:</b> {esc(m['zeithorizont'])}", "", "<i>KI-Einordnung, kein Kaufsignal.</i>"]
    return "\n".join(parts)


def ki_warning_message(w: dict) -> str:
    icon = {"hinweis": "ℹ️", "warnung": "⚠️", "alarm": "🚨"}.get(w["schwere"], "⚠️")
    return "\n".join([
        f"{icon} <b>MARKTWARNUNG ({esc(w['schwere'])}): {esc(w['titel'])}</b>", "",
        esc(w["begruendung"]), "", f"<b>Was tun?</b> {esc(w['was_tun'])}",
    ])


def validate_idea(idea: dict, mv: dict, state: dict) -> str | None:
    """Gibt einen Ablehnungsgrund zurück oder None, wenn die Idee realistisch lohnt."""
    t = idea["ticker"]
    if t not in UNIVERSE or t not in mv:
        return "Symbol nicht in der Werteliste"
    if t in {s["ticker"] for s in state["open"]}:
        return "bereits offen"
    up, down = idea["kursziel_prozent"], idea["stop_prozent"]
    if up < MIN_IDEA_TARGET_PCT:
        return f"Kursziel {up:.1f}% unter Mindestziel {MIN_IDEA_TARGET_PCT:.0f}%"
    if not 2 <= down <= 25:
        return f"Stop-Abstand {down:.1f}% unplausibel"
    if (up - FEE_PCT * 100) / (down + FEE_PCT * 100) < 1.5:
        return "Chance/Risiko nach Gebühren unter 1,5"
    if not 5 <= idea["haltedauer_handelstage"] <= 180:
        return "Haltedauer unplausibel"
    if idea["ueberzeugung"] != "hoch":
        return "Überzeugung nicht hoch"
    sc = idea["szenarien"]
    probs = sum(sc[k]["wahrscheinlichkeit_prozent"] for k in ("bull", "basis", "bear"))
    if not 95 <= probs <= 105:
        return f"Szenario-Wahrscheinlichkeiten ergeben {probs:.0f} % statt 100 %"
    ev = expected_value(idea)
    if ev < MIN_IDEA_EV_PCT:
        return f"Erwartungswert {ev:+.1f} % nach Gebühren unter {MIN_IDEA_EV_PCT:.0f} %"
    return None


def expected_value(idea: dict) -> float:
    """Wahrscheinlichkeitsgewichtete Rendite der drei Szenarien nach Gebühren, in %."""
    sc = idea["szenarien"]
    total = sum(sc[k]["wahrscheinlichkeit_prozent"] for k in ("bull", "basis", "bear")) or 1
    return sum(sc[k]["kursziel_prozent"] * sc[k]["wahrscheinlichkeit_prozent"] for k in ("bull", "basis", "bear")) / total - FEE_PCT * 100


def idea_message(idea: dict, m: dict) -> str:
    close = m["last"]
    up, down = idea["kursziel_prozent"] / 100, idea["stop_prozent"] / 100
    gain = BUDGET_EUR * up - 2 * FEE_PER_ORDER_EUR
    loss = BUDGET_EUR * down + 2 * FEE_PER_ORDER_EUR
    sc = idea["szenarien"]
    parts = [
        f"🟢 <b>CALL: {esc(idea['name'])} ({esc(idea['ticker'])})</b>",
        wkn_line(idea["ticker"], idea["name"], idea.get("wkn", "")),
        f"Branche: {esc(idea['branche'])} · Überzeugung: <b>{esc(idea['ueberzeugung'])}</b> · Zeithorizont: <b>{esc(idea['zeithorizont'])}</b>",
        "",
        f"Schlusskurs {m['date']}: <b>{close:.2f}</b> · Kauf bis max. {close * 1.01:.2f}",
        f"🎯 Kursziel (Basis): {close * (1 + up):.2f} (+{up:.0%})",
        f"🛑 Stop-Loss: {close * (1 - down):.2f} (−{down:.0%})",
        f"💶 Bei {BUDGET_EUR:.0f} €: +{gain:.2f} € Chance / −{loss:.2f} € Risiko (inkl. Gebühren)",
        "",
        "<b>📊 Prognose (Szenarien):</b>",
        f"• Bull: {sc['bull']['kursziel_prozent']:+.0f} % (Wahrscheinlichkeit {sc['bull']['wahrscheinlichkeit_prozent']:.0f} %)",
        f"• Basis: {sc['basis']['kursziel_prozent']:+.0f} % ({sc['basis']['wahrscheinlichkeit_prozent']:.0f} %)",
        f"• Bear: {sc['bear']['kursziel_prozent']:+.0f} % ({sc['bear']['wahrscheinlichkeit_prozent']:.0f} %)",
        f"→ Erwartungswert nach Gebühren: <b>{expected_value(idea):+.1f} %</b>",
        "",
        f"<b>💡 These:</b> {esc(idea['these'])}",
        "",
        f"<b>📐 Bewertung:</b> {esc(idea['bewertung'])}",
        "",
        f"<b>📈 Technik:</b> {esc(idea['technik'])}",
        "",
        f"<b>⏰ Warum jetzt?</b> {esc(idea['warum_jetzt'])}",
        "",
    ]
    parts += bullets("Auslöser:", idea["katalysatoren"]) + [""]
    parts += bullets("Risiken:", idea["risiken"])
    parts += ["", "<i>KI-Einschätzung, kein Backtest und keine Garantie. Keine Anlageberatung. Stop-Loss immer setzen.</i>"]
    return "\n".join(parts)


def idea_candidates(data: dict, mv: dict) -> list[dict]:
    """Vorfilter für die KI: 20 stärkste Trendwerte + 10 größte Rücksetzer profitabler Firmen, mit Fundamentaldaten."""
    from .watchlist import STOCKS_ASIA, STOCKS_EU, STOCKS_US
    stocks = [t for t in STOCKS_US + STOCKS_EU + STOCKS_ASIA if t in data]
    scored = [(t, dashboard.momentum(data[t]["Close"])) for t in stocks]
    trend = [t for t, m in sorted((x for x in scored if x[1] and x[1]["score"] is not None), key=lambda x: -x[1]["score"])][:20]
    dips = sorted((t for t in stocks if t in mv and t not in trend), key=lambda t: mv[t]["m1"])[:10]
    out = []
    for t in trend + dips:
        info = fundamentals(t)
        if not info:
            continue
        price, target = info.get("currentPrice") or mv.get(t, {}).get("last"), info.get("targetMeanPrice")
        pct = lambda v: None if v is None else f"{v * 100:.1f}%"
        out.append({
            "ticker": t, "name": info.get("shortName", t), "wkn": wkn(t), "sector": info.get("sector"),
            "kgv": info.get("trailingPE") and round(info["trailingPE"], 1),
            "kgv_erwartet": info.get("forwardPE") and round(info["forwardPE"], 1),
            "marge": pct(info.get("profitMargins")), "umsatzwachstum": pct(info.get("revenueGrowth")),
            "verschuldung_ek": info.get("debtToEquity") and round(info["debtToEquity"]),
            "analysten_ziel_abstand": f"{target / price - 1:+.0%}" if target and price else None,
            "empfehlung": info.get("recommendationKey"),
        })
    return out


def explain_alerts(alerts: list, state: dict) -> None:
    """Starke Bewegungen von der KI begründen lassen (Ursachen + Folgen für Deutschland)."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        return
    n = 0
    for a in alerts:
        if a.kind != "macro" or not alert_due(state, a.key) or n >= MAX_EXPLAIN_PER_RUN:
            continue
        n += 1
        try:
            res = analyst.explain_move(a.title, a.facts, a.reasons)
        except Exception as e:
            print("KI-Erklärung fehlgeschlagen:", repr(e), file=sys.stderr)
            continue
        if res:
            a.reasons = res["gruende"] + ([f"Einordnung: {res['einordnung']}"] if res.get("einordnung") else [])
            a.germany = res["auswirkung_deutschland"] or a.germany
            a.explained = True


def run_analysis(state, data, mv, heads, rule_alerts, dry_run) -> None:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).date().isoformat()
    recent = [f"{s['ticker']} ({s['signal_date']})" for s in state["open"] + state["closed"]
              if s.get("strategy") == "ki" and s["signal_date"] >= cutoff]
    fee = FEE_PCT * 100
    rules = (
        f"- kursziel_prozent ≥ {MIN_IDEA_TARGET_PCT:.0f}\n"
        f"- (kursziel_prozent − {fee:.0f}) / (stop_prozent + {fee:.0f}) ≥ 1,5  (Gebühren {fee:.0f} % je Kauf+Verkauf)\n"
        "- stop_prozent zwischen 2 und 25, haltedauer_handelstage zwischen 5 und 180\n"
        f"- höchstens {MAX_IDEAS_PER_RUN} Ideen, keine Werte, die bereits offen sind"
    )
    cands = idea_candidates(data, mv)
    result = analyst.analyse(mv, heads, rule_alerts, state["open"], recent, rules, cands)
    if not result:
        return
    send("🧭 <b>KI-Lagebild</b>\n\n" + esc(result["lagebild"]), dry_run)
    state["last_analysis"] = {
        "time": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        **{k: result[k] for k in ("lagebild", "makro_signale", "warnungen", "laender_risiko", "branchen_ausblick", "ausblick_2050")},
    }
    for m in result["makro_signale"]:
        key = "ki:macro:" + m["titel"].lower()[:40]
        if alert_due(state, key):
            send(ki_macro_message(m), dry_run)
            mark_alert(state, key, "macro", m["titel"])
    for w in result["warnungen"]:
        key = "ki:warn:" + w["titel"].lower()[:40]
        if alert_due(state, key):
            send(ki_warning_message(w), dry_run)
            mark_alert(state, key, "warning", w["titel"])
    sent = 0
    for idea in result["kaufideen"]:
        reason = validate_idea(idea, mv, state)
        if reason:
            print(f"Kaufidee {idea['ticker']} verworfen: {reason}")
            continue
        if sent >= MAX_IDEAS_PER_RUN:
            break
        m = mv[idea["ticker"]]
        send(idea_message(idea, m), dry_run)
        mark_alert(state, "ki:idea:" + idea["ticker"], "idea", f"Kaufidee {idea['name']} ({idea['ticker']})")
        state["open"].append({
            "ticker": idea["ticker"], "name": idea["name"], "currency": "", "strategy": "ki",
            "signal_date": m["date"], "ref_close": round(m["last"], 4),
            "target": round(m["last"] * (1 + idea["kursziel_prozent"] / 100), 4),
            "stop": round(m["last"] * (1 - idea["stop_prozent"] / 100), 4),
            "max_days": int(idea["haltedauer_handelstage"]), "horizon": idea["zeithorizont"],
            "wkn": wkn(idea["ticker"]) or idea.get("wkn", ""), "branche": idea["branche"],
            "these": idea["these"], "warum_jetzt": idea["warum_jetzt"], "szenarien": idea["szenarien"],
            "ev_pct": round(expected_value(idea), 1), "risiken": idea["risiken"],
        })
        sent += 1


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
    ap.add_argument("--analysis", action="store_true")
    args = ap.parse_args()

    if args.test:
        send("✅ Signal-Bot ist verbunden. Kaufsignale kommen ab jetzt hierher.", args.dry_run)
        sys.exit(1 if SEND_FAILURES else 0)

    state = load_state()
    data = download(UNIVERSE + list(MACRO))
    print(f"Daten geladen: {len(data)} Werte")
    ctx = market_context(data)

    evaluate_open(state, data, args.dry_run)

    mv = macro.moves(data)
    news_items = macro.headline_items()
    heads = [h["title"] for h in news_items]
    rule_alerts = macro.risk_warnings(mv) + macro.move_alerts(mv, heads) + macro.scenario_alerts(heads, mv)
    explain_alerts(rule_alerts, state)
    try:
        depot.watch(state, send, esc, alert_due, args.dry_run)
    except Exception as e:
        print("Depot-Wächter fehlgeschlagen:", repr(e), file=sys.stderr)
    for a in rule_alerts:
        if alert_due(state, a.key):
            send(alert_message(a), args.dry_run)
            mark_alert(state, a.key, a.kind, a.title)
    if args.analysis:
        try:
            run_analysis(state, data, mv, heads, rule_alerts, args.dry_run)
        except Exception as e:  # KI-Ausfall darf den restlichen Lauf nicht stoppen
            print("KI-Analyse fehlgeschlagen:", repr(e), file=sys.stderr)
            SEND_FAILURES.append("ki")

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
        mark_alert(state, f"swing:{f['ticker']}", "signal", f"Swing-Signal {info.get('shortName') or f['ticker']} ({f['ticker']})")

    if args.report:
        daily_report(state, ctx, sent, args.dry_run)
    save_state(state)
    try:
        dashboard.export(data, news_items, state, ctx["regime"])
    except Exception as e:
        print("Dashboard-Export fehlgeschlagen:", repr(e), file=sys.stderr)
        SEND_FAILURES.append("dashboard")
    try:
        world.export(heads, state.get("last_analysis"))
    except Exception as e:
        print("Welt-Export fehlgeschlagen:", repr(e), file=sys.stderr)
        SEND_FAILURES.append("world")
    try:
        calls = {x["ticker"]: {k: x.get(k) for k in ("these", "horizon", "target", "stop", "ev_pct")}
                 for x in state["open"] if x.get("strategy") == "ki"}
        profiles.export(FEE_PCT, calls)
    except Exception as e:
        print("Steckbrief-Export fehlgeschlagen:", repr(e), file=sys.stderr)
        SEND_FAILURES.append("profiles")
    try:
        auth.export()
    except Exception as e:
        print("Passwort-Export fehlgeschlagen:", repr(e), file=sys.stderr)
    try:
        doomsday.export()
    except Exception as e:
        print("Frühwarn-Export fehlgeschlagen:", repr(e), file=sys.stderr)
    print(f"Fertig: {sent} neue Signale, {len(state['open'])} offen")
    if SEND_FAILURES:
        sys.exit(f"Fehler beim Senden/Analysieren: {SEND_FAILURES}")


if __name__ == "__main__":
    main()
