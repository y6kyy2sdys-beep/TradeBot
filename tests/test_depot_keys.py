"""S1: Depot-Sperrschlüssel dürfen nicht per Wörterbuch auflösbar sein.

Läuft ohne Netzwerk und ohne Telegram: python3 -m unittest discover -s tests
pandas/yfinance werden nur durch Platzhalter ersetzt, falls sie lokal nicht installiert sind.
"""
import hashlib
import os
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
for _m in ("pandas", "yfinance"):
    try:
        __import__(_m)
    except ImportError:
        sys.modules[_m] = types.ModuleType(_m)

from bot import depot  # noqa: E402


class DepotKeyTest(unittest.TestCase):
    def test_format_und_geheimnis(self):
        a = depot._key("SAP.DE", "loss10", b"A")
        self.assertTrue(a.startswith(depot.KEY_PREFIX))
        self.assertEqual(len(a), len(depot.KEY_PREFIX) + depot.KEY_HEX)
        self.assertNotEqual(a, depot._key("SAP.DE", "loss10", b"B"))
        self.assertEqual(a, depot._key("SAP.DE", "loss10", b"A"))  # Sperrfrist bleibt wirksam

    def test_nicht_wie_alter_ungesalzener_hash(self):
        old = hashlib.sha1(b"SAP.DE:loss10").hexdigest()[:10]
        self.assertNotIn(old, depot._key("SAP.DE", "loss10", b"A"))

    def test_geheimnis_quelle(self):
        with mock.patch.dict(os.environ, {"DEPOT": "X:1:1", "DEPOT_SALT": ""}):
            self.assertEqual(depot._secret(), b"X:1:1")
        with mock.patch.dict(os.environ, {"DEPOT": "X:1:1", "DEPOT_SALT": "salz"}):
            self.assertEqual(depot._secret(), b"salz")

    def test_alte_schluessel_werden_entfernt(self):
        new = depot._key("SAP.DE", "drop", b"A")
        state = {"alerts": {"depot:0123456789": "t", new: "t", "move:SPY": "t"}}
        self.assertEqual(depot.purge_legacy_keys(state), 1)
        self.assertEqual(set(state["alerts"]), {new, "move:SPY"})
        self.assertEqual(depot.purge_legacy_keys(state), 0)

    def test_ohne_depot_wird_nichts_gesendet(self):
        sent = []
        state = {"alerts": {"depot:0123456789": "t"}}
        with mock.patch.dict(os.environ, {"DEPOT": ""}):
            depot.watch(state, lambda *a: sent.append(a), str, lambda *a: True, True)
        self.assertEqual(sent, [])
        self.assertEqual(state["alerts"], {})


if __name__ == "__main__":
    unittest.main()
