"""Unternehmens-News je Aktie mit einfacher Tonalität (docs/news.js).

Die Tonalität ist eine Stichwort-Auswertung der Schlagzeile (deutsch/englisch): grob, aber nachvollziehbar.
"""

import json
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote

import requests

OUT = Path(__file__).resolve().parent.parent / "docs" / "news.js"
POS = ("beat", "beats", "surge", "soar", "jump", "jumps", "rise", "rises", "rally", "upgrade", "upgraded", "raises", "record",
       "strong", "growth", "profit", "outperform", "wins", "win", "contract", "deal", "approval", "approved", "bullish", "buyback",
       "dividend", "partnership", "expands", "gewinn", "steigt", "steigen", "hebt", "rekord", "kaufempfehlung", "übertrifft",
       "stark", "auftrag", "zulassung", "kursziel erhöht", "hochgestuft", "plus", "wachstum", "rückkauf", "erhöht",
       "legt zu", "gewinnt", "klettert", "springt", "zieht an", "erholt", "aufwärts", "rally", "kaufen")
NEG = ("miss", "misses", "falls", "fall", "drop", "drops", "plunge", "plunges", "slump", "downgrade", "downgraded", "cuts", "cut",
       "lawsuit", "probe", "investigation", "recall", "loss", "losses", "weak", "warning", "warns", "layoffs", "bearish", "fine",
       "fined", "strike", "tariff", "verlust", "fällt", "fallen", "senkt", "warnung", "warnt", "klage", "abgestuft", "abstufung",
       "stellenabbau", "einbruch", "bricht ein", "schwach", "minus", "kursziel gesenkt", "ermittlung", "rückruf", "streik", "zölle",
       "verliert", "verlieren", "gibt nach", "sinkt", "sinken", "rutscht", "absturz", "abwärts", "verkaufen", "crash", "verluste")


def tone(title: str) -> int:
    low = " " + re.sub(r"[^\w\s%-]", " ", title.lower()) + " "
    return sum(f" {w} " in low for w in POS) - sum(f" {w} " in low for w in NEG)


def _fetch(item):
    ticker, name = item
    q = f'"{name}" Aktie OR "{name}" stock when:7d'
    url = f"https://news.google.com/rss/search?q={quote(q)}&hl=de&gl=DE&ceid=DE:de"
    try:
        root = ET.fromstring(requests.get(url, timeout=15).content)
    except Exception:
        return ticker, []
    out = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        try:
            ts = parsedate_to_datetime(it.findtext("pubDate") or "").astimezone(timezone.utc).isoformat(timespec="minutes")
        except Exception:
            ts = ""
        out.append({"title": title, "link": it.findtext("link") or "", "source": it.findtext("source") or "", "time": ts, "s": tone(title)})
    out.sort(key=lambda n: n["time"], reverse=True)
    return ticker, out[:5]


def export(stocks: list[tuple[str, str]]) -> None:
    with ThreadPoolExecutor(max_workers=10) as pool:
        news = dict(pool.map(_fetch, stocks))
    news = {t: v for t, v in news.items() if v}
    payload = {"generated": datetime.now(timezone.utc).isoformat(timespec="minutes"), "news": news}
    OUT.write_text("window.NEWS = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print(f"Unternehmens-News: {len(news)} Aktien")
