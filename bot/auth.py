"""Passwortsperre für das Dashboard (docs/auth.js).

Das Passwort steht nur im GitHub-Secret DASH_PIN (5 Ziffern). Ins Repo kommt lediglich ein PBKDF2-Hash
mit Salz und vielen Runden – das bremst Durchprobieren, ist aber keine echte Zugriffssperre, weil die
Seite und ihre Datendateien öffentlich abrufbar bleiben.
"""

import hashlib
import json
import os
import secrets
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "docs" / "auth.js"
ITER = 200_000


def _hash(pin: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(salt), ITER).hex()


def normalize(raw: str) -> str:
    """Nur Ziffern behalten; Sonderziffern (z. B. ２ oder ٢ von Handy-Tastaturen) in 0-9 umwandeln."""
    return "".join(str(unicodedata.digit(ch)) for ch in raw if unicodedata.digit(ch, None) is not None)


def export() -> None:
    pin = normalize(os.getenv("DASH_PIN") or "")
    if not pin:  # kein Secret (mehr) gesetzt -> Sperre aus; so kommt man bei vergessenem Code wieder rein
        if not OUT.exists() or "null" not in OUT.read_text():
            OUT.write_text("window.AUTH = null;\n")
            print("Passwortsperre aus (kein DASH_PIN)")
        return
    if not (len(pin) == 5 and pin.isdigit()):
        print("DASH_PIN muss genau 5 Ziffern haben – Sperre unverändert")
        return
    try:  # Salz behalten, solange das Passwort gleich bleibt (keine unnötigen Commits)
        old = json.loads(OUT.read_text()[len("window.AUTH = "):-2])
        if old and old.get("updated") and _hash(pin, old["salt"]) == old["hash"]:
            return
    except Exception:
        pass
    salt = secrets.token_hex(16)
    stamp = datetime.now(timezone.utc).isoformat(timespec="minutes")
    OUT.write_text("window.AUTH = " + json.dumps({"salt": salt, "iter": ITER, "hash": _hash(pin, salt), "updated": stamp}) + ";\n")
    print(f"Passwortsperre aktualisiert (Code-Stand {stamp})")
