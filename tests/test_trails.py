"""P3 Flugspuren (bot/trails.py): eigene Aufzeichnung aus Bot-Abrufen – ohne Netzwerk.

Ausführen: python3 -m unittest discover -s tests
"""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bot import trails  # noqa: E402

T0 = datetime(2026, 11, 28, 12, 0, tzinfo=timezone.utc)
ac = lambda h, lat, lon, **k: {"hex": h, "lat": lat, "lon": lon, **k}


class TrailTest(unittest.TestCase):
    def test_punkte_werden_angehaengt(self):
        tr = trails.update({}, [ac("a1", 50, 10, alt=30000, trk=90)], T0)
        tr = trails.update(tr, [ac("a1", 50, 11)], T0 + timedelta(minutes=30))
        self.assertEqual([p[1:3] for p in tr["a1"]], [[50, 10], [50, 11]])
        self.assertEqual(tr["a1"][0][3:], [30000, 90])

    def test_zeitfenster_sechs_stunden(self):
        tr = trails.update({}, [ac("a1", 1, 1), ac("b2", 2, 2)], T0)
        tr = trails.update(tr, [ac("a1", 1, 2)], T0 + timedelta(hours=6, minutes=1))
        self.assertEqual(len(tr["a1"]), 1)          # alter Punkt außerhalb des Fensters
        self.assertNotIn("b2", tr)                   # nicht mehr gesehen → entfernt

    def test_hoechstens_max_punkte(self):
        tr = {}
        for i in range(30):
            tr = trails.update(tr, [ac("a1", 0, i)], T0 + timedelta(minutes=10 * i))
        self.assertEqual(len(tr["a1"]), trails.MAX_POINTS)
        self.assertEqual(tr["a1"][-1][2], 29)

    def test_doppelter_abruf_und_stillstand(self):
        tr = trails.update({}, [ac("a1", 5, 5)], T0)
        tr = trails.update(tr, [ac("a1", 5, 6)], T0)                              # gleicher Abruf → ersetzt
        self.assertEqual([p[1:3] for p in tr["a1"]], [[5, 6]])
        tr = trails.update(tr, [ac("a1", 5, 6)], T0 + timedelta(minutes=10))      # unverändert, < 30 Min. → nicht doppelt
        self.assertEqual(len(tr["a1"]), 1)

    def test_datumsgrenze_bleibt_rohdaten(self):
        tr = trails.update({}, [ac("a1", 10, 179.5)], T0)
        tr = trails.update(tr, [ac("a1", 10, -179.6)], T0 + timedelta(minutes=30))
        self.assertEqual([p[2] for p in tr["a1"]], [179.5, -179.6])   # keine Umrechnung – die Karte (d3) zeichnet den Großkreis

    def test_unvollstaendige_eintraege_ignoriert(self):
        self.assertEqual(trails.update({}, [{"hex": "x", "lat": None, "lon": 1}, {"lat": 1, "lon": 1}], T0), {})
        self.assertEqual(trails.update({"a": "kaputt"}, [], T0), {})


if __name__ == "__main__":
    unittest.main()
