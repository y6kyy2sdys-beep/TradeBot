"""Passwortsperre für das Dashboard (docs/auth.js).

Das Passwort steht nur im GitHub-Secret DASH_PIN (5 Ziffern). Ins Repo kommt lediglich ein PBKDF2-Hash
mit Salz und vielen Runden – das bremst Durchprobieren, ist aber keine echte Zugriffssperre, weil die
Seite und ihre Datendateien öffentlich abrufbar bleiben.
"""

import hashlib
import json
import os
import secrets
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "docs" / "auth.js"
ITER = 200_000


def _hash(pin: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(salt), ITER).hex()


def export() -> None:
    pin = (os.getenv("DASH_PIN") or "").strip()
    if not pin:
        if not OUT.exists():
            OUT.write_text("window.AUTH = null;\n")
        return
    if not (len(pin) == 5 and pin.isdigit()):
        print("DASH_PIN muss genau 5 Ziffern haben – Sperre unverändert")
        return
    try:  # Salz behalten, solange das Passwort gleich bleibt (keine unnötigen Commits)
        old = json.loads(OUT.read_text()[len("window.AUTH = "):-2])
        if old and _hash(pin, old["salt"]) == old["hash"]:
            return
    except Exception:
        pass
    salt = secrets.token_hex(16)
    OUT.write_text("window.AUTH = " + json.dumps({"salt": salt, "iter": ITER, "hash": _hash(pin, salt)}) + ";\n")
    print("Passwortsperre aktualisiert")
