"""Stream-Prüfung (bot/streamcheck.py) mit nachgebildeten Antworten – ohne Netzwerk, ohne API-Schlüssel.

Ausführen: python3 -m unittest discover -s tests
"""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    import requests  # noqa: F401
except ImportError:   # lokal ohne Paket: Tests nutzen ohnehin nur nachgebildete Antworten
    import types
    sys.modules["requests"] = types.SimpleNamespace(get=None)
from bot import streamcheck as S  # noqa: E402

KEY = "AIzaTESTKEY0000000000000000000000000000"


class Resp:
    def __init__(self, code=200, data=None, headers=None):
        self.status_code, self._d, self.headers = code, data, headers or {}
    def json(self):
        return self._d
    def close(self):
        pass


def fake_get(routes):
    """routes: Liste von (Teilstring der URL, Antwort). Merkt sich Aufrufe."""
    calls = []
    def get(url, params=None, **kw):
        calls.append((url, params))
        for frag, resp in routes:
            if frag in url:
                return resp(params) if callable(resp) else resp
        raise ConnectionError("unerwartete URL " + url)
    get.calls = calls
    return get


class YouTubeTest(unittest.TestCase):
    def test_ohne_schluessel_kein_abruf(self):
        g = fake_get([])
        self.assertEqual(S.check_youtube("UC" + "x" * 22, None, g)["status"], "unknown")
        self.assertEqual(g.calls, [])

    def test_live_einbettbar_liefert_video_id(self):
        g = fake_get([("/search", Resp(200, {"items": [{"id": {"videoId": "abcdefghijk"}}]})),
                      ("/videos", Resp(200, {"items": [{"id": "abcdefghijk", "snippet": {"liveBroadcastContent": "live", "title": "Live"},
                                                        "status": {"embeddable": True}, "liveStreamingDetails": {"actualStartTime": "2026-11-28T10:00:00Z"}}]}))])
        r = S.check_youtube("UC" + "x" * 22, KEY, g)
        self.assertEqual((r["status"], r["videoId"]), ("live", "abcdefghijk"))

    def test_live_aber_nicht_einbettbar(self):
        g = fake_get([("/search", Resp(200, {"items": [{"id": {"videoId": "abcdefghijk"}}]})),
                      ("/videos", Resp(200, {"items": [{"id": "abcdefghijk", "snippet": {"liveBroadcastContent": "live"}, "status": {"embeddable": False}}]}))])
        r = S.check_youtube("UC" + "x" * 22, KEY, g)
        self.assertEqual(r["status"], "offline"); self.assertIn("Einbettung", r["note"])

    def test_kein_livestream(self):
        g = fake_get([("/search", Resp(200, {"items": []}))])
        self.assertEqual(S.check_youtube("UC" + "x" * 22, KEY, g)["status"], "offline")

    def test_api_fehler_wird_nicht_geraten_und_schluessel_nie_ausgegeben(self):
        g = fake_get([("/search", Resp(403, {}))])
        self.assertEqual(S.check_youtube("UC" + "x" * 22, KEY, g)["status"], "unknown")
        def boom(url, params=None, **kw):
            raise ConnectionError(f"fehler bei {url}?key={KEY}")
        r = S.check_youtube("UC" + "x" * 22, KEY, boom)
        self.assertEqual(r["status"], "unknown"); self.assertNotIn(KEY, r["note"])


class BildTest(unittest.TestCase):
    def test_bild_ok_offline(self):
        ok = fake_get([("x", Resp(200, None, {"Content-Type": "image/jpeg", "Last-Modified": "Sat, 28 Nov 2026 10:00:00 GMT"}))])
        self.assertEqual(S.check_image("https://x/a.jpg", ok)["status"], "ok")
        self.assertEqual(S.check_image("https://x/a.jpg", fake_get([("x", Resp(404, None, {"Content-Type": "text/html"}))]))["status"], "offline")
        self.assertEqual(S.check_image("https://x/a.jpg", fake_get([("x", Resp(200, None, {"Content-Type": "text/html"}))]))["status"], "offline")

    def test_vorlagen_wie_im_browser(self):
        now = datetime(2026, 11, 28, 14, 7, tzinfo=timezone.utc)
        self.assertEqual(S.resolve_template("u?TIME={YYYY-MM-DD}", now), "u?TIME=2026-11-27")
        self.assertEqual(S.resolve_template("jpn_{HHMM}.jpg", now), "jpn_1330.jpg")


class GesamtTest(unittest.TestCase):
    def test_echter_katalog_ohne_schluessel(self):
        cams = S.load_cams()
        g = fake_get([("", Resp(200, None, {"Content-Type": "image/png"}))])
        data = S.run(cams, None, datetime(2026, 11, 28, 12, tzinfo=timezone.utc), g)
        self.assertEqual(len(data["items"]), len(cams["items"]))
        self.assertFalse(data["youtubeApi"])
        yt = [c["id"] for c in cams["items"] if c["embed"]["typ"] == "youtube"]
        self.assertTrue(all(data["items"][i]["status"] == "unknown" for i in yt))
        self.assertFalse(any("googleapis" in u for u, _ in g.calls))   # ohne Schlüssel keine API-Aufrufe
        self.assertTrue(all(S.channel_id(c["embed"]["url"]) for c in cams["items"] if c["embed"]["typ"] == "youtube"))


if __name__ == "__main__":
    unittest.main()
