"""Schneller Flugzeug-Abruf (alle 30 Minuten per eigenem Workflow): docs/aircraft.js.

Aufruf: python -m bot.aircraft
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from .doomsday import military_aircraft

OUT = Path(__file__).resolve().parent.parent / "docs" / "aircraft.js"


def main() -> None:
    ac = military_aircraft()
    if not ac["ok"]:
        print("Kein neuer Flugzeug-Stand – alte Datei bleibt")
        return
    payload = {"generated": datetime.now(timezone.utc).isoformat(timespec="minutes"), **ac}
    OUT.write_text("window.AIRCRAFT = " + json.dumps(payload, separators=(",", ":")) + ";\n")
    print(f"Militärflugzeuge: {len(ac['items'])}")


if __name__ == "__main__":
    main()
