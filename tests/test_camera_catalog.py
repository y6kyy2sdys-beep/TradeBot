"""Regelprüfung des Quellenkatalogs docs/cameras.js (Country Intelligence / Camera Wall).

Offline, ohne Netzwerk: python3 -m unittest discover -s tests
Prüft die verbindlichen Vorgaben aus PROJECT_ALFRED.md und die Auflagen der Freigabe vom 28.11.2026.
"""
import importlib.util
import json
import re
import unittest
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
CAMS_JS = ROOT / "docs" / "cameras.js"
REQUIRED = ["id", "iso", "ort", "art", "betreiber", "embed", "quelle_url", "lizenz_url",
            "verzoegerung_min", "konfliktzone_zulaessig", "geprueft_am", "freigegeben", "freigabe_am"]
ARTEN = {"nachrichten", "panorama", "wetter", "zeitversetzt"}
EMBED_TYPEN = {"youtube", "bild", "skyline", "iframe"}
STAATSNAH = {"chn-cgtn", "tur-trt-world", "qat-aljazeera-en", "qat-aljazeera-ar", "sau-al-arabiya",
             "are-sky-news-arabia", "irn-iran-international"}
PRIVATE_HOST = re.compile(r"^(localhost|127\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|\[?::1)")


def load_cams() -> dict:
    text = CAMS_JS.read_text()
    body = text[text.index("window.CAMS =") + len("window.CAMS ="):].strip().rstrip(";")
    return json.loads(body)


class CameraCatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cams = load_cams()
        cls.items = cls.cams["items"]

    def test_pflichtfelder_und_freigabe(self):
        for c in self.items:
            with self.subTest(c.get("id")):
                self.assertFalse([k for k in REQUIRED if k not in c], "Pflichtfeld fehlt")
                self.assertIs(c["freigegeben"], True)
                self.assertIn(c["art"], ARTEN)
                self.assertIn(c["embed"]["typ"], EMBED_TYPEN)

    def test_ids_eindeutig(self):
        ids = [c["id"] for c in self.items]
        self.assertEqual(len(ids), len(set(ids)))

    def test_nur_https_und_keine_privaten_hosts(self):
        for c in self.items:
            for key in ("quelle_url", "lizenz_url"):
                self.assertTrue(c[key].startswith("https://"), f"{c['id']} {key}")
            u = urlparse(c["embed"]["url"])
            self.assertEqual(u.scheme, "https", c["id"])
            self.assertFalse(PRIVATE_HOST.match(u.hostname or ""), f"{c['id']}: privater Host")

    def test_youtube_datensparsam(self):
        for c in self.items:
            if c["embed"]["typ"] == "youtube":
                self.assertTrue(c["embed"]["url"].startswith("https://www.youtube-nocookie.com/embed/"), c["id"])

    def test_konfliktgebiete_nur_nachrichten_und_zeitversetzt(self):
        zonen = set(self.cams["konfliktzonen"])
        self.assertTrue({"UKR", "RUS", "ISR", "PSE", "LBN", "YEM", "SDN", "IRN", "SAU", "ARE"} <= zonen)
        for c in self.items:
            if c["iso"] in zonen:
                with self.subTest(c["id"]):
                    self.assertIn(c["art"], {"nachrichten", "zeitversetzt"})
                    self.assertIs(c["konfliktzone_zulaessig"], True)

    def test_auflagen_der_freigabe(self):
        for c in self.items:
            if c["id"] in STAATSNAH:
                self.assertTrue(c.get("kennzeichnung"), f"{c['id']}: Kennzeichnung fehlt")
            if c["betreiber"].startswith("SkylineWebcams"):
                self.assertEqual(c["embed"]["typ"], "skyline")
                self.assertIn("Vorschau", c.get("credit", ""))
            if c["betreiber"].startswith(("NASA", "EUMETSAT", "NOAA", "Japan Meteorological", "Hong Kong Observatory")):
                self.assertTrue(c.get("credit"), f"{c['id']}: Quellenangabe fehlt")

    def test_entspricht_freigegebenem_katalog(self):
        """cameras.js darf nicht von Hand vom freigegebenen Katalog abweichen."""
        spec = importlib.util.spec_from_file_location("build_cameras", ROOT / "catalog" / "build_cameras.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        src = json.loads(mod.SRC.read_text())
        self.assertEqual([mod.convert(e) for e in src], self.items)


if __name__ == "__main__":
    unittest.main()
