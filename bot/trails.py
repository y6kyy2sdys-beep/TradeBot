"""Flugspuren aus eigenen Bot-Abrufen (PROJECT A.L.F.R.E.D. P3, Entscheidung 28.11.2026: eigene Aufzeichnung).

Bei jedem Abruf der Militärflugzeuge (ca. alle 30 Min.) wird je ICAO-Adresse ein Punkt gemerkt:
[Zeit (Unix-Minuten), Breite, Länge, Höhe ft | None, Kurs ° | None]. Gehalten werden die letzten HOURS Stunden, höchstens
MAX_POINTS Punkte je Flugzeug. Flugzeuge ohne Punkt im Zeitfenster fallen heraus. Keine fremden Verlaufsdaten.
"""
from __future__ import annotations

from datetime import datetime

HOURS = 6
MAX_POINTS = 16


def _minute(now: datetime) -> int:
    return int(now.timestamp() // 60)


def update(prev: dict | None, items: list[dict], now: datetime) -> dict:
    t = _minute(now)
    cutoff = t - HOURS * 60
    trails = {h: [p for p in pts if isinstance(p, list) and len(p) >= 3 and p[0] >= cutoff] for h, pts in (prev or {}).items()}
    for a in items or []:
        h, lat, lon = a.get("hex"), a.get("lat"), a.get("lon")
        if not h or lat is None or lon is None:
            continue
        pt = [t, round(float(lat), 3), round(float(lon), 3), a.get("alt"), a.get("trk")]
        pts = trails.setdefault(h, [])
        if pts and pts[-1][0] == t:          # gleicher Abruf doppelt → ersetzen
            pts[-1] = pt
        elif not pts or pts[-1][1:3] != pt[1:3] or t - pts[-1][0] >= 30:
            pts.append(pt)                    # unveränderte Position nur nach ≥ 30 Min. erneut speichern
        trails[h] = pts[-MAX_POINTS:]
    return {h: pts for h, pts in trails.items() if pts}
