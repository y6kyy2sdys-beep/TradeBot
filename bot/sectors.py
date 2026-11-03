"""Branchen für das Dashboard: Kennzahlen des Branchen-ETFs und die neuesten Meldungen je Branche."""

import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import timezone
from urllib.parse import quote

import requests

# key, Name, US-Branchen-ETF (nur als Messlatte), Symbol für das Matrix-Bild, Suchanfrage
SECTORS = [
    ("gesundheit", "Gesundheit & Pharma", "XLV", "dna", "Pharma OR Biotech OR Medizintechnik Aktie"),
    ("it", "IT & Software", "XLK", "code", "Software OR Cloud OR \"künstliche Intelligenz\" Aktie"),
    ("halbleiter", "Halbleiter", "SMH", "chip", "Halbleiter OR Chiphersteller OR Nvidia OR TSMC"),
    ("finanzen", "Banken & Finanzen", "XLF", "bank", "Banken OR Versicherer OR Finanzbranche Aktie"),
    ("energie", "Energie & Öl", "XLE", "drop", "Ölkonzerne OR Energiekonzerne OR Erdgas Aktie"),
    ("industrie", "Industrie & Maschinenbau", "XLI", "gear", "Maschinenbau OR Industrie Aktie Aufträge"),
    ("ruestung", "Rüstung & Luftfahrt", "ITA", "shield", "Rüstung OR Rheinmetall OR Airbus OR Verteidigung Aktie"),
    ("konsum", "Konsum & Handel", "XLY", "cart", "Einzelhandel OR Konsum OR Luxus Aktie"),
    ("versorger", "Versorger & Strom", "XLU", "bolt", "Versorger OR Strompreis OR Energiewende Aktie"),
    ("immobilien", "Immobilien", "XLRE", "building", "Immobilien OR Wohnimmobilien OR Vonovia Aktie"),
    ("rohstoffe", "Rohstoffe & Chemie", "XLB", "cube", "Chemie OR BASF OR Rohstoffe OR Bergbau Aktie"),
    ("kommunikation", "Telekom & Medien", "XLC", "antenna", "Telekom OR Medien OR Streaming Aktie"),
]
KEYS = [s[0] for s in SECTORS]


def sector_news(query: str, limit: int = 4) -> list[dict]:
    url = f"https://news.google.com/rss/search?q={quote(query + ' when:3d')}&hl=de&gl=DE&ceid=DE:de"
    try:
        root = ET.fromstring(requests.get(url, timeout=15).content)
    except Exception:
        return []
    out = []
    for item in root.iter("item"):
        try:
            ts = parsedate_to_datetime(item.findtext("pubDate") or "").astimezone(timezone.utc).isoformat(timespec="minutes")
        except Exception:
            ts = ""
        out.append({"title": item.findtext("title") or "", "link": item.findtext("link") or "",
                    "source": item.findtext("source") or "", "time": ts})
    out.sort(key=lambda n: n["time"], reverse=True)
    return out[:limit]
