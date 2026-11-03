"""Depot-Wächter: überwacht die eigenen Positionen und meldet Auffälligkeiten per Telegram.

Die Positionen kommen ausschließlich aus dem GitHub-Secret DEPOT (nie aus dem Repo), Format:
    SAP.DE:10:180.50;NVDA:3:120
    = Symbol : Stückzahl : Kaufkurs in Euro, mehrere Positionen mit ; getrennt.
Damit nichts Persönliches im öffentlichen Repo landet, werden Duplikat-Schlüssel gehasht und
Depot-Meldungen nicht ins öffentliche Signal-Protokoll geschrieben.
"""

import hashlib
import json
import os
from pathlib import Path

import pandas as pd
import yfinance as yf

from .wkn import name as display_name

FX_CURRENCIES = ["USD", "GBP", "CHF", "DKK", "SEK", "NOK", "JPY", "HKD", "KRW", "AUD", "CNY"]
CACHE = Path(__file__).resolve().parent.parent / "state" / "fundamentals.json"


def parse(raw: str) -> list[dict]:
    out = []
    for part in (raw or "").replace("\n", ";").split(";"):
        bits = [b.strip() for b in part.split(":")]
        if len(bits) < 3 or not bits[0]:
            continue
        try:
            out.append({"t": bits[0].upper(), "qty": float(bits[1].replace(",", ".")), "buy": float(bits[2].replace(",", "."))})
        except ValueError:
            continue
    return out


def fx_rates() -> dict[str, float]:
    """Wechselkurs Landeswährung -> EUR (GBp = Pence)."""
    tickers = [f"{c}EUR=X" for c in FX_CURRENCIES]
    try:
        raw = yf.download(tickers, period="5d", interval="1d", group_by="ticker", progress=False, auto_adjust=True)
    except Exception:
        return {"EUR": 1.0}
    rates = {"EUR": 1.0}
    for c, t in zip(FX_CURRENCIES, tickers):
        try:
            v = raw[t]["Close"].dropna()
            if len(v):
                rates[c] = float(v.iat[-1])
        except KeyError:
            continue
    if "GBP" in rates:
        rates["GBp"] = rates["GBP"] / 100
    return rates


def currency_of(ticker: str) -> str:
    if ticker.endswith(".DE") or ticker.endswith(".PA") or ticker.endswith(".AS") or ticker.endswith(".MI"):
        return "EUR"
    try:
        cache = json.loads(CACHE.read_text())
        return cache.get(ticker, {}).get("info", {}).get("currency") or "USD"
    except Exception:
        return "USD"


def _key(ticker: str, kind: str) -> str:
    return "depot:" + hashlib.sha1(f"{ticker}:{kind}".encode()).hexdigest()[:10]


def watch(state: dict, send, esc, alert_due, dry_run: bool) -> None:
    positions = parse(os.getenv("DEPOT", ""))
    if not positions:
        return
    tickers = [p["t"] for p in positions]
    raw = yf.download(tickers, period="1y", interval="1d", group_by="ticker", progress=False, auto_adjust=True)
    fx = fx_rates()
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat(timespec="minutes")
    for p in positions:
        try:
            c = (raw[p["t"]]["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw["Close"]).dropna()
        except KeyError:
            continue
        if len(c) < 30:
            continue
        rate = fx.get(currency_of(p["t"]))
        if not rate:
            continue
        last, prev = c.iat[-1], c.iat[-2]
        eur = last * rate
        pnl = eur / p["buy"] - 1
        d1 = last / prev - 1
        sma200 = c.rolling(200).mean()
        name = display_name(p["t"])
        value = eur * p["qty"]
        head = f"<b>{esc(name)} ({esc(p['t'])})</b> · {p['qty']:g} Stück · Kurs {eur:.2f} € · Wert {value:.2f} € · G/V <b>{pnl:+.1%}</b>"
        checks = []
        if d1 <= -0.04:
            checks.append(("drop", f"📉 <b>DEPOT: Starker Tagesverlust</b>\n{head}\nHeute {d1:+.1%}. Ruhe bewahren – prüfe, ob es eine Nachricht zum Unternehmen gibt (Steckbrief im Dashboard)."))
        if len(c) > 200 and c.iat[-2] >= sma200.iat[-2] and last < sma200.iat[-1]:
            checks.append(("sma200", f"⚠️ <b>DEPOT: Unter die 200-Tage-Linie gerutscht</b>\n{head}\nDer langfristige Aufwärtstrend ist gebrochen. Viele Anleger ziehen hier ihren Stop-Loss nach oder reduzieren."))
        if pnl <= -0.10:
            checks.append(("loss10", f"🛑 <b>DEPOT: Verlust über 10 %</b>\n{head}\nZeit, die Kaufgründe zu überprüfen: Gelten sie noch? Wenn nicht, Verluste begrenzen statt hoffen."))
        if pnl >= 0.20:
            checks.append(("gain20", f"🎯 <b>DEPOT: Gewinn über 20 %</b>\n{head}\nÜberlege, einen Teil zu verkaufen oder einen Stop-Loss knapp unter dem aktuellen Kurs zu setzen, um den Gewinn zu sichern."))
        for kind, text in checks:
            key = _key(p["t"], kind)
            if alert_due(state, key):
                send(text + "\n\n<i>Keine Anlageberatung.</i>", dry_run)
                state["alerts"][key] = now  # bewusst nicht ins öffentliche Protokoll
    print("Depot-Wächter: geprüft")
