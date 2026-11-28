"""Klimaprojektionen für PROJECT CHRONOS (Reiter KLIMA) – einmaliger Abruf, Ergebnis docs/climate.js.

Quelle: World Bank Climate Change Knowledge Portal (CCKP), CMIP6, auf Länder umgerechnet (0,25°, bias-korrigiert).
Lizenz: CC BY 4.0 (World Bank Open Data, Nutzungsbedingungen des CCKP). Kein Schlüssel, keine Kosten.
Größe: Anomalie der Jahresmitteltemperatur (tas) gegenüber 1995–2014, 20-Jahres-Mittel 2020–2039 und 2040–2059,
Ensemble-Median sowie 10./90. Perzentil, Szenarien SSP1-2.6, SSP2-4.5, SSP5-8.5.
Es sind Projektionen Dritter für angenommene Emissionspfade – keine Vorhersagen, keine Eintrittswahrscheinlichkeiten.

Die Daten ändern sich nicht laufend; das Skript wird nur bei Bedarf von Hand ausgeführt:  python3 -m bot.climate
Nur Standardbibliothek (urllib), damit es ohne zusätzliche Pakete läuft.
"""
from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "docs" / "climate.js"
API = "https://cckpapi.worldbank.org/cckp/v1/cmip6-x0.25_climatology_tas_anomaly_annual_{period}_{stat}_{ssp}_ensemble_all_mean/all_countries?_format=json"
SSPS = {"ssp126": "SSP1-2.6 · starker Klimaschutz", "ssp245": "SSP2-4.5 · mittlerer Pfad", "ssp585": "SSP5-8.5 · sehr hohe Emissionen"}
PERIODS = ["2020-2039", "2040-2059"]
STATS = ["median", "p10", "p90"]
UA = {"User-Agent": "Mozilla/5.0 (TradeBot dashboard; Klimadaten)"}


def fetch(url: str, opener=urllib.request.urlopen) -> dict:
    with opener(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def values(payload: dict) -> dict[str, float]:
    """{'DEU': {'2040-07': 1.34}, …} → {'DEU': 1.34}; leere/kaputte Einträge fallen weg (nichts wird geschätzt)."""
    data = (payload or {}).get("data") or {}
    if not isinstance(data, dict):
        return {}
    out = {}
    for iso, v in data.items():
        if isinstance(v, dict) and v:
            x = next(iter(v.values()))
            if isinstance(x, (int, float)):
                out[iso] = round(float(x), 2)
    return out


def build(get=fetch) -> dict:
    data: dict = {}
    for ssp in SSPS:
        for period in PERIODS:
            per = {s: values(get(API.format(period=period, stat=s, ssp=ssp))) for s in STATS}
            isos = sorted(set(per["median"]))   # nur Länder mit Median; Spannweite falls vorhanden
            data.setdefault(ssp, {})[period] = {i: [per["median"][i], per["p10"].get(i), per["p90"].get(i)] for i in isos}
    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "quelle": "World Bank Climate Change Knowledge Portal (CCKP), CMIP6-Ensemble, 0,25° bias-korrigiert",
        "lizenz": "CC BY 4.0 – The World Bank",
        "lizenz_url": "https://www.worldbank.org/en/about/legal/terms-of-use-for-datasets",
        "quelle_url": "https://climateknowledgeportal.worldbank.org/",
        "groesse": "Anomalie der Jahresmitteltemperatur in °C gegenüber 1995–2014",
        "bezug": "1995-2014", "werte": "[Median, 10. Perzentil, 90. Perzentil]",
        "szenarien": SSPS, "perioden": PERIODS, "daten": data,
    }


def main() -> None:
    d = build()
    OUT.write_text("/* Klimaprojektionen (CMIP6, World Bank CCKP, CC BY 4.0) – ERZEUGT von bot/climate.py. Nicht von Hand ändern. */\n"
                   "window.CLIMATE = " + json.dumps(d, ensure_ascii=False, separators=(",", ":")) + ";\n")
    n = {s: {p: len(v) for p, v in d["daten"][s].items()} for s in d["daten"]}
    print("Klimadaten geschrieben:", n)


if __name__ == "__main__":
    main()
