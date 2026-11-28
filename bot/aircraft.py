"""Schneller Flugzeug-Abruf (alle 30 Minuten per eigenem Workflow): docs/aircraft.js.

Aufruf: python -m bot.aircraft
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from . import trails
from .doomsday import military_aircraft

OUT = Path(__file__).resolve().parent.parent / "docs" / "aircraft.js"


def previous_trails(path: Path = OUT) -> dict:
    """Spuren aus der bisherigen Datei lesen (fehlt/kaputt → leer)."""
    try:
        text = path.read_text()
        return json.loads(text[text.index("=") + 1:].strip().rstrip(";")).get("trails") or {}
    except Exception:
        return {}


def main() -> None:
    ac = military_aircraft()
    if not ac["ok"]:
        print("Kein neuer Flugzeug-Stand – alte Datei bleibt")
        return
    now = datetime.now(timezone.utc)
    tr = trails.update(previous_trails(), ac["items"], now)
    payload = {"generated": now.isoformat(timespec="minutes"), **ac,
               "trails": tr, "trailInfo": {"hours": trails.HOURS, "maxPoints": trails.MAX_POINTS,
                                           "quelle": "eigene Aufzeichnung aus den Bot-Abrufen (adsb.lol, ca. alle 30 Min.)"}}
    OUT.write_text("window.AIRCRAFT = " + json.dumps(payload, separators=(",", ":")) + ";\n")
    print(f"Militärflugzeuge: {len(ac['items'])} · Spuren: {len(tr)}")


if __name__ == "__main__":
    main()
