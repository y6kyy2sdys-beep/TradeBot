"""Makro-Signale: auffällige Marktbewegungen, Risiko-Warnungen und Szenario-Ketten aus Nachrichten.

Läuft regelbasiert und kostenlos bei jedem Lauf. Die KI-Lageanalyse (analyst.py) baut darauf auf.
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from urllib.parse import quote

import numpy as np
import pandas as pd
import requests

from .strategies import rsi
from .watchlist import MACRO


@dataclass
class Alert:
    key: str  # für Duplikat-Schutz
    kind: str  # "macro" oder "warning"
    title: str
    facts: list[str]
    chain: list[str] = field(default_factory=list)  # Wirkungskette
    winners: list[str] = field(default_factory=list)
    losers: list[str] = field(default_factory=list)
    horizon: str = ""


# ---------------------------------------------------------------- Kennzahlen


def moves(data: dict[str, pd.DataFrame]) -> dict[str, dict]:
    """Tages-, Wochen- und Monatsveränderung sowie Stärke der Tagesbewegung (in Standardabweichungen)."""
    out = {}
    for sym in list(MACRO) + [t for t in data if t not in MACRO]:
        df = data.get(sym)
        if df is None or len(df) < 60:
            continue
        c = df["Close"]
        r = c.pct_change()
        vol = r.iloc[-61:-1].std()
        out[sym] = {
            "last": float(c.iat[-1]),
            "d1": float(r.iat[-1]),
            "w1": float(c.iat[-1] / c.iat[-6] - 1),
            "m1": float(c.iat[-1] / c.iat[-22] - 1),
            "m3": float(c.iat[-1] / c.iat[-64] - 1) if len(c) > 64 else np.nan,
            "z": float(r.iat[-1] / vol) if vol else 0.0,
            "sma200": float(c.rolling(200).mean().iat[-1]) if len(c) >= 200 else np.nan,
            "high52": float(c.iloc[-252:].max()),
            "rsi14": float(rsi(c, 14).iat[-1]),
            "date": str(df.index[-1].date()),
        }
    return out


def macro_table(mv: dict[str, dict]) -> str:
    lines = ["Instrument | Kurs | 1T | 1W | 1M | 3M | Abstand 200T-Linie"]
    for sym, label in MACRO.items():
        m = mv.get(sym)
        if not m:
            continue
        dist = m["last"] / m["sma200"] - 1 if m["sma200"] == m["sma200"] else np.nan
        lines.append(
            f"{label} ({sym}) | {m['last']:.2f} | {m['d1']:+.1%} | {m['w1']:+.1%} | {m['m1']:+.1%} | "
            f"{m['m3']:+.1%} | {dist:+.1%}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------- Wirkungsketten bei starken Bewegungen

# Symbol -> (Schwelle Tagesbewegung, Text steigt, Text fällt)
MOVE_PLAYBOOK = {
    "BZ=F": (0.04, {
        "chain": ["Ölpreis steigt kräftig", "Energie- und Transportkosten steigen", "Inflationserwartung ↑, Zinssenkungen unwahrscheinlicher", "Konsum und Margen von Energieverbrauchern unter Druck"],
        "winners": ["Ölkonzerne (Shell, TotalEnergies, Exxon, Chevron)", "Öl-Förderer-ETF XOP", "Tanker/Öl-Dienstleister"],
        "losers": ["Airlines (Lufthansa, JETS)", "Chemie (BASF)", "Autobauer", "Konsumwerte"],
    }, {
        "chain": ["Ölpreis fällt kräftig", "Entlastung bei Inflation und Transportkosten", "Mehr Spielraum für Zinssenkungen", "Signal für schwächere Nachfrage oder mehr Angebot (OPEC)"],
        "winners": ["Airlines", "Chemie", "Konsum/Einzelhandel", "Logistik"],
        "losers": ["Ölkonzerne", "Öl-Förderer", "Rohstoffwährungen (NOK, CAD)"],
    }),
    "TTF=F": (0.08, {
        "chain": ["Europäischer Gaspreis springt", "Strom- und Heizkosten in Europa steigen", "Energieintensive Industrie verliert Wettbewerbsfähigkeit", "Belastung für Euro und DAX-Industrie"],
        "winners": ["LNG-Exporteure (US-Gasförderer)", "Erneuerbare Energien", "Versorger mit eigener Erzeugung"],
        "losers": ["Chemie (BASF)", "Stahl, Glas, Papier", "Euro", "Europäische Industrie"],
    }, {
        "chain": ["Europäischer Gaspreis fällt stark", "Entlastung für Industrie und Haushalte", "Positiv für Konjunktur in Europa"],
        "winners": ["Chemie (BASF)", "Europäische Industrie", "Euro"],
        "losers": ["Gasförderer", "LNG-Exporteure"],
    }),
    "NG=F": (0.07, {
        "chain": ["US-Erdgas steigt stark", "Höhere Strompreise in den USA", "Mehr Exportanreize für LNG"],
        "winners": ["US-Gasförderer", "LNG-Exporteure"],
        "losers": ["Versorger mit Gaskraftwerken", "Düngemittel/Chemie"],
    }, None),
    "^TNX": (0.04, {
        "chain": ["US-Zinsen steigen deutlich", "Anleihen werden attraktiver als Aktien", "Hoch bewertete Wachstumswerte verlieren an Wert", "Kredite teurer, Immobilien unter Druck"],
        "winners": ["Banken (Zinsmarge)", "Versicherer", "US-Dollar"],
        "losers": ["Tech-/Wachstumswerte (Nasdaq)", "Immobilien", "Versorger", "Gold", "Langlaufende Anleihen (TLT)"],
    }, {
        "chain": ["US-Zinsen fallen deutlich", "Markt erwartet Zinssenkungen oder flüchtet in Sicherheit", "Wachstumswerte und Immobilien profitieren"],
        "winners": ["Tech/Wachstum", "Immobilien", "Gold", "Anleihen (TLT)"],
        "losers": ["Banken", "US-Dollar"],
    }),
    "DX-Y.NYB": (0.01, {
        "chain": ["US-Dollar wertet kräftig auf", "US-Anlagen verlieren für Euro-Anleger weniger, Exporte der USA teurer", "Druck auf Schwellenländer mit Dollar-Schulden", "Rohstoffe in Dollar werden teurer für den Rest der Welt"],
        "winners": ["Europäische Exporteure (relativ)", "Euro-Anleger in US-Aktien (Währungsgewinn)"],
        "losers": ["Schwellenländer (EEM)", "Gold", "Rohstoffe", "US-Multis mit Auslandsumsatz"],
    }, {
        "chain": ["US-Dollar fällt kräftig", "US-Aktien bringen Euro-Anlegern Währungsverlust", "Entlastung für Schwellenländer und Rohstoffe"],
        "winners": ["Schwellenländer", "Gold", "Rohstoffe"],
        "losers": ["Euro-Anleger in US-Werten (Währungsverlust)", "Europäische Exporteure"],
    }),
    "USDJPY=X": (0.015, None, {
        "chain": ["Yen wertet stark auf", "Auflösung von 'Carry Trades' (billiger Yen-Kredit für Aktienkäufe) möglich", "Kann weltweite Verkaufswellen auslösen (wie Aug. 2024)"],
        "winners": ["Yen", "Sichere Häfen"],
        "losers": ["Japanische Exporteure (Toyota, Sony)", "Hoch bewertete Tech-Werte weltweit"],
    }),
    "GC=F": (0.03, {
        "chain": ["Gold springt", "Anleger suchen Sicherheit (Krise, Inflation, Zinssenkungsfantasie)", "Oft Vorbote erhöhter Unsicherheit"],
        "winners": ["Gold (GLD)", "Goldminen", "Silber (SLV)"],
        "losers": ["Risikoanlagen bei Krisenmotiv"],
    }, None),
    "HG=F": (0.04, {
        "chain": ["Kupfer steigt stark", "Gilt als Konjunkturbarometer: Industrie-/Chinanachfrage zieht an"],
        "winners": ["Minenwerte", "Industrie", "Schwellenländer"],
        "losers": [],
    }, {
        "chain": ["Kupfer fällt stark", "Warnsignal für Weltkonjunktur / China"],
        "winners": ["Anleihen"],
        "losers": ["Minen", "Industrie", "China-Werte (FXI)"],
    }),
    "ZW=F": (0.05, {
        "chain": ["Weizen springt", "Lebensmittelinflation, oft durch Krieg/Wetter (Schwarzmeer-Region)"],
        "winners": ["Agrarproduzenten", "Düngemittel"],
        "losers": ["Lebensmittelhersteller", "Importabhängige Schwellenländer"],
    }, None),
}


def move_alerts(mv: dict[str, dict]) -> list[Alert]:
    alerts = []
    for sym, (threshold, up, down) in MOVE_PLAYBOOK.items():
        m = mv.get(sym)
        if not m:
            continue
        d1 = m["d1"]
        big = abs(d1) >= threshold or abs(m["z"]) >= 3
        book = up if d1 > 0 else down
        if not big or book is None:
            continue
        label = MACRO.get(sym, sym)
        alerts.append(Alert(
            key=f"move:{sym}:{'up' if d1 > 0 else 'down'}",
            kind="macro",
            title=f"{label} {'+' if d1 > 0 else ''}{d1:.1%} an einem Tag",
            facts=[
                f"Stand {m['last']:.2f} ({m['date']}), Woche {m['w1']:+.1%}, Monat {m['m1']:+.1%}",
                f"Bewegung ≈ {abs(m['z']):.1f}-fache normale Tagesschwankung",
            ],
            chain=book["chain"], winners=book["winners"], losers=book["losers"],
            horizon="Tage bis Wochen – bestätigt sich der Trend, wirken die Folgen länger.",
        ))
    return alerts


# ---------------------------------------------------------------- Risiko-Warnungen


def risk_warnings(mv: dict[str, dict]) -> list[Alert]:
    w = []
    vix, spx, hyg = mv.get("^VIX"), mv.get("^GSPC"), mv.get("HYG")
    tnx, irx = mv.get("^TNX"), mv.get("^IRX")
    if vix and vix["last"] > 25:
        level = "sehr hoch" if vix["last"] > 35 else "erhöht"
        w.append(Alert("warn:vix", "warning", f"Angstindex VIX {level}: {vix['last']:.1f}",
                       [f"Woche {vix['w1']:+.0%}. Über 25 = nervöser Markt, über 35 = Panik."],
                       ["Hohe Schwankungen", "Stop-Loss werden häufiger ausgelöst", "Neue Käufe nur klein und gestaffelt"]))
    if spx:
        dd = spx["last"] / spx["high52"] - 1
        if dd < -0.10:
            w.append(Alert("warn:spx_dd", "warning", f"S&P 500 {dd:.0%} unter Jahreshoch – Korrektur",
                           [f"Stand {spx['last']:.0f}, Hoch {spx['high52']:.0f}"],
                           ["Ab −10 % Korrektur, ab −20 % Bärenmarkt", "Breite Verkäufe treffen auch gute Firmen"]))
        if spx["sma200"] == spx["sma200"] and spx["last"] < spx["sma200"]:
            w.append(Alert("warn:spx_trend", "warning", "S&P 500 unter seiner 200-Tage-Linie",
                           ["Langfristiger Aufwärtstrend gebrochen"],
                           ["Historisch schwächere Renditen und mehr Rückschläge in dieser Phase"]))
    if hyg and hyg["m1"] < -0.03:
        w.append(Alert("warn:credit", "warning", f"Stress am Kreditmarkt: Hochzinsanleihen {hyg['m1']:+.1%} im Monat",
                       ["Anleger verlangen mehr Risikoaufschlag von schwachen Firmen"],
                       ["Kreditmarkt reagiert oft vor dem Aktienmarkt", "Gefahr für hoch verschuldete Unternehmen"]))
    if tnx and irx and tnx["last"] < irx["last"]:
        w.append(Alert("warn:curve", "warning", "US-Zinskurve invers (10J unter 3M)",
                       [f"10J {tnx['last']:.2f}% vs. 3M {irx['last']:.2f}%"],
                       ["Klassischer Rezessions-Vorbote mit 6–18 Monaten Vorlauf"]))
    return w


# ---------------------------------------------------------------- Nachrichten & Szenarien

FEEDS = [
    ("Börse OR Weltwirtschaft OR Notenbank OR Zölle when:1d", "de", "DE"),
    ("geopolitics OR oil OR Fed OR tariffs OR sanctions when:1d", "en", "US"),
    ("Iran OR Israel OR Taiwan OR Ukraine OR OPEC when:1d", "en", "US"),
]


def headlines(limit: int = 40) -> list[str]:
    seen, out = set(), []
    for q, hl, gl in FEEDS:
        url = f"https://news.google.com/rss/search?q={quote(q)}&hl={hl}&gl={gl}&ceid={gl}:{hl}"
        try:
            root = ET.fromstring(requests.get(url, timeout=15).content)
        except Exception:
            continue
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            if title and title not in seen:
                seen.add(title)
                out.append(title)
    return out[:limit]


@dataclass(frozen=True)
class Scenario:
    key: str
    title: str
    keywords: tuple[str, ...]
    confirm: tuple[str, float] | None  # (Symbol, Mindestbewegung) als Marktbestätigung
    chain: tuple[str, ...]
    winners: tuple[str, ...]
    losers: tuple[str, ...]
    horizon: str


SCENARIOS = [
    Scenario("iran", "Eskalation Nahost / Iran",
             ("iran", "hormuz", "tehran", "teheran", "israel strike", "angriff auf iran"),
             ("BZ=F", 0.02),
             ("Konflikt mit Iran", "Risiko für die Straße von Hormus (≈20 % des Welt-Öls)", "Ölpreis steigt, Risikoprämie", "Inflation ↑ → Notenbanken zögern mit Zinssenkungen", "Sichere Häfen gefragt"),
             ("Ölkonzerne (Shell, TotalEnergies, Exxon)", "Rüstung (Rheinmetall, Lockheed, RTX, ITA)", "Gold", "Tanker"),
             ("Airlines (Lufthansa, JETS)", "Reise/Tourismus", "Chemie", "Schwellenländer-Importeure (Indien)"),
             "Akut Tage–Wochen; bei Blockade von Hormus Monate."),
    Scenario("taiwan", "Spannungen China / Taiwan",
             ("taiwan", "south china sea", "südchinesisch"),
             ("TSM", -0.02),
             ("Militärische Spannung um Taiwan", "TSMC fertigt >90 % der Spitzen-Chips", "Lieferkettenrisiko für die gesamte Tech-Branche", "Mögliche Sanktionen gegen China"),
             ("Rüstung", "Chipfertigung außerhalb Taiwans (Intel, Samsung)", "Gold"),
             ("TSMC, Nvidia, Apple, AMD, ASML", "China-Werte (Alibaba, Tencent)", "Halbleiter-ETF SMH"),
             "Wochen bis Monate, extrem schwer vorhersehbar."),
    Scenario("russia", "Russland / Ukraine / NATO",
             ("russia", "russland", "ukraine", "nato", "putin"),
             ("TTF=F", 0.04),
             ("Eskalation oder Verhandlungen im Ukrainekrieg", "Gas, Weizen, Rüstungsausgaben reagieren", "Europa am stärksten betroffen"),
             ("Rüstung (Rheinmetall, Airbus Defence)", "Bei Frieden: Wiederaufbau, Chemie, DAX-Zykliker"),
             ("Bei Eskalation: Chemie, europ. Industrie, Euro", "Bei Frieden: Rüstung, Gas"),
             "Wochen bis Monate."),
    Scenario("tariffs", "Handelskonflikt / Zölle",
             ("tariff", "zoll", "zölle", "trade war", "handelskrieg"),
             ("^GSPC", -0.01),
             ("Neue oder höhere Zölle", "Importe teurer → Inflation", "Gegenzölle und Lieferkettenumbau", "Exportlastige Branchen verlieren"),
             ("Heimische US-Produzenten", "Inländische Dienstleister", "Gold"),
             ("Autobauer (BMW, Mercedes, Toyota)", "Exportstarke Industrie (DAX)", "China-Werte", "Apple (Fertigung in Asien)"),
             "Wochen bis Monate; oft starke Gegenbewegung bei Einigung."),
    Scenario("opec", "OPEC-Förderentscheidung",
             ("opec",),
             ("BZ=F", 0.015),
             ("OPEC ändert Fördermenge", "Angebot bestimmt Ölpreis-Trend der nächsten Monate"),
             ("Bei Kürzung: Ölkonzerne", "Bei Erhöhung: Airlines, Chemie"),
             ("Bei Kürzung: Airlines, Konsum", "Bei Erhöhung: Öl-Förderer"),
             "Wochen bis Monate."),
    Scenario("fed", "Zinsentscheid / Notenbank",
             ("fed ", "federal reserve", "powell", "rate cut", "zinssenkung", "ezb", "ecb", "rate hike"),
             None,
             ("Notenbank verändert Zinspfad", "Zinsen bestimmen Bewertung aller Anlageklassen", "Überraschungen bewegen vor allem Tech, Banken, Gold, Dollar"),
             ("Bei Senkung: Tech, Immobilien, Gold, Small Caps (IWM)", "Bei Straffung: Banken, Dollar"),
             ("Bei Senkung: Banken-Marge, Dollar", "Bei Straffung: Wachstumswerte, Immobilien"),
             "Tage bis Monate."),
    Scenario("banks", "Bankenstress",
             ("bank run", "bank collapse", "bankenkrise", "regional bank", "liquidity crisis"),
             ("KRE", -0.03),
             ("Vertrauensverlust in Banken", "Kreditvergabe wird gebremst", "Flucht in Staatsanleihen und Gold", "Notenbank muss evtl. eingreifen"),
             ("Gold", "Staatsanleihen (TLT)", "Große, solide Banken (JPM)"),
             ("Regionalbanken (KRE)", "Immobilien", "Small Caps"),
             "Wochen; Notenbank-Eingriffe können schnell drehen."),
    Scenario("usfiscal", "US-Haushalt / Shutdown / Schuldenobergrenze",
             ("shutdown", "debt ceiling", "schuldenobergrenze", "downgrade", "herabstufung"),
             None,
             ("Streit um US-Haushalt", "Risiko für Zahlungsfähigkeit/Bonität der USA", "Dollar und Anleihen unter Druck"),
             ("Gold", "Bitcoin (als Alternative)", "Nicht-US-Märkte"),
             ("US-Staatsanleihen", "US-Dollar", "Rüstung/Behördendienstleister bei Shutdown"),
             "Tage bis Wochen; meist politische Einigung in letzter Minute."),
]


def scenario_alerts(heads: list[str], mv: dict[str, dict]) -> list[Alert]:
    low = [h.lower() for h in heads]
    out = []
    for sc in SCENARIOS:
        hits = [heads[i] for i, h in enumerate(low) if any(k in h for k in sc.keywords)]
        if len(hits) < 2:
            continue
        confirmed = False
        if sc.confirm:
            sym, thr = sc.confirm
            m = mv.get(sym)
            confirmed = bool(m) and (m["d1"] >= thr if thr > 0 else m["d1"] <= thr)
        if not confirmed and len(hits) < 4:
            continue
        facts = [f"{len(hits)} aktuelle Meldungen, z. B.: „{hits[0]}“"]
        if sc.confirm and confirmed:
            sym, _ = sc.confirm
            facts.append(f"Markt bestätigt: {MACRO.get(sym, sym)} {mv[sym]['d1']:+.1%} heute")
        out.append(Alert(f"scenario:{sc.key}", "macro", f"Szenario: {sc.title}", facts,
                         list(sc.chain), list(sc.winners), list(sc.losers), sc.horizon))
    return out
