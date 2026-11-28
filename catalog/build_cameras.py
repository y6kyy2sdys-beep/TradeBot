"""Erzeugt docs/cameras.js aus dem freigegebenen Quellenkatalog (catalog/kamera_katalog_2026-11-28.json).

Nur freigegebene Einträge, Feldformat für docs/camwall.js, Auflagen der Freigabe vom 28.11.2026:
Kennzeichnung staatsnaher Sender, Quellenangaben der Behörden, SkylineWebcams nur als unverändertes Vorschaubild mit Link.
Aufruf: python3 catalog/build_cameras.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "catalog" / "kamera_katalog_2026-11-28.json"
OUT = ROOT / "docs" / "cameras.js"
FREIGABE = "2026-11-28"
KONFLIKTZONEN = ["UKR", "RUS", "ISR", "PSE", "LBN", "SYR", "YEM", "SDN", "IRN", "SAU", "ARE"]

KENNZEICHNUNG = {
    "chn-cgtn": "Staatssender (China)",
    "tur-trt-world": "Staatssender (Türkei)",
    "qat-aljazeera-en": "staatlich finanziert (Katar)",
    "qat-aljazeera-ar": "staatlich finanziert (Katar)",
    "sau-al-arabiya": "staatsnah (Saudi-Arabien)",
    "are-sky-news-arabia": "staatsnah (VAE)",
    "irn-iran-international": "Exilsender (London)",
}


def credit(e: dict) -> str | None:
    b = e["betreiber"]
    if b.startswith("NASA"):
        return "Imagery: NASA EOSDIS GIBS (VIIRS NOAA-20)"
    if b.startswith("EUMETSAT"):
        return "© EUMETSAT 2026"
    if b.startswith("NOAA"):
        return "NOAA/NESDIS STAR – GOES-19"
    if b.startswith("Japan Meteorological"):
        return "Source: Japan Meteorological Agency website"
    if b.startswith("Hong Kong Observatory"):
        return "Quelle: Hong Kong Observatory – nicht-kommerzielle Nutzung, Hinweis und Bedingungen des HKO gelten"
    if b.startswith("SkylineWebcams"):
        return "SkylineWebcams – Vorschau, kein Live-Player"
    return None


def convert(e: dict) -> dict:
    typ = e["embed_typ"]
    if e["betreiber"].startswith("SkylineWebcams"):
        typ = "skyline"  # unveränderter Original-Embed: Vorschaubild, verlinkt auf die Kameraseite
    out = {
        "id": e["id"], "iso": e["iso"], "ort": e["ort"], "art": e["art"], "betreiber": e["betreiber"],
        "embed": {"typ": typ, "url": e["embed_url"]},
        "quelle_url": e["quelle_url"], "lizenz_url": e["lizenz_url"],
        "verzoegerung_min": e["verzoegerung_min"], "konfliktzone_zulaessig": bool(e["konfliktzone_zulaessig"]),
        "sprache": e.get("sprache"), "vertrauen": e["vertrauen"], "geprueft_am": e["geprueft_am"],
        "freigegeben": True, "freigabe_am": FREIGABE,
    }
    if e["id"] in KENNZEICHNUNG:
        out["kennzeichnung"] = KENNZEICHNUNG[e["id"]]
    c = credit(e)
    if c:
        out["credit"] = c
    return out


def main() -> None:
    src = json.loads(SRC.read_text())
    items = [convert(e) for e in src]
    data = {"stand": FREIGABE, "hinweis": f"Freigegebener Quellenkatalog vom {FREIGABE} ({len(items)} Einträge).",
            "konfliktzonen": KONFLIKTZONEN, "items": items}
    OUT.write_text(
        "/* PROJECT A.L.F.R.E.D. – Quellenkatalog Country Intelligence / Camera Wall.\n"
        "   ERZEUGT von catalog/build_cameras.py aus catalog/kamera_katalog_2026-11-28.json – nicht von Hand ändern.\n"
        "   Nur vom Eigentümer freigegebene Quellen; neue Quellen brauchen eine neue Freigabe. Keine automatische Suche. */\n"
        "window.CAMS = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n")
    print(f"{len(items)} Einträge → {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
