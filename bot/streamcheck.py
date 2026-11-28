"""Stream-Prüfung für die Camera Wall (PROJECT A.L.F.R.E.D.).

Prüft die freigegebenen Quellen aus docs/cameras.js und schreibt docs/streamstatus.js (window.CAMSTATUS):
- YouTube-Sender: offizielle YouTube Data API v3 (Secret YT_API_KEY). Ermittelt den gerade laufenden, einbettbaren
  Livestream des Kanals und dessen Video-ID – die Einbettung per Video-ID funktioniert auch dort, wo der Kanal-Embed
  („live_stream?channel=“) „Video nicht verfügbar“ zeigt. Ohne Schlüssel: Status „unbekannt“ (nichts wird geraten).
  Kein Abruf der YouTube-Webseiten (Nutzungsbedingungen).
- Bild-Quellen (Satellit, Wetter, Panorama-Vorschau): einfacher HTTP-Abruf wie im Browser; erreichbar + Bildformat.

Kontingent: search.list (100 Einheiten) je Kanal + ein videos.list (1 Einheit) – bei 28 Kanälen ca. 2.800 von 10.000 Einheiten
pro Lauf. Der API-Schlüssel erscheint nie in Ausgabe, Datei oder Fehlermeldungen.
Aufruf: python -m bot.streamcheck
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CAMS = ROOT / "docs" / "cameras.js"
OUT = ROOT / "docs" / "streamstatus.js"
API = "https://www.googleapis.com/youtube/v3"
UA = {"User-Agent": "Mozilla/5.0 (TradeBot dashboard; Stream-Prüfung)"}
TIMEOUT = 20


def load_cams(path: Path = CAMS) -> dict:
    text = path.read_text()
    return json.loads(text[text.index("window.CAMS =") + len("window.CAMS ="):].strip().rstrip(";"))


def channel_id(url: str) -> str | None:
    m = re.search(r"[?&]channel=([\w-]{24})", url or "")
    return m.group(1) if m else None


def resolve_template(url: str, now: datetime) -> str:
    """Gleiche Vorlagen wie docs/camwall.js: {YYYY-MM-DD} = Vortag (UTC), {HHMM} = UTC −30 min, auf 10 min abgerundet."""
    if "{YYYY-MM-DD}" in url:
        url = url.replace("{YYYY-MM-DD}", (now - timedelta(days=1)).strftime("%Y-%m-%d"))
    if "{HHMM}" in url:
        t = now - timedelta(minutes=30)
        url = url.replace("{HHMM}", f"{t.hour:02d}{t.minute // 10 * 10:02d}")
    return url


def scrub(text: str, key: str | None) -> str:
    """Schlüssel aus Fehlermeldungen entfernen."""
    text = str(text)
    if key:
        text = text.replace(key, "***")
    return re.sub(r"key=[^&\s']+", "key=***", text)[:160]


# ---------------- YouTube (Data API v3) ----------------
def pick_live(videos: dict) -> dict:
    """Aus einer videos.list-Antwort den ersten laufenden, einbettbaren Livestream wählen."""
    items = (videos or {}).get("items") or []
    live = [v for v in items if (v.get("snippet") or {}).get("liveBroadcastContent") == "live"]
    for v in live:
        if (v.get("status") or {}).get("embeddable") is True:
            return {"status": "live", "videoId": v["id"], "title": (v.get("snippet") or {}).get("title", "")[:120],
                    "since": (v.get("liveStreamingDetails") or {}).get("actualStartTime")}
    if live:
        return {"status": "offline", "note": "Livestream läuft, Einbettung vom Sender nicht erlaubt"}
    return {"status": "offline", "note": "kein laufender Livestream"}


def check_youtube(cid: str, key: str | None, get=requests.get) -> dict:
    if not key:
        return {"status": "unknown", "note": "nicht geprüft (kein API-Schlüssel hinterlegt)"}
    try:
        r = get(f"{API}/search", params={"part": "id", "channelId": cid, "eventType": "live", "type": "video", "maxResults": 5, "key": key},
                headers=UA, timeout=TIMEOUT)
        if r.status_code != 200:
            return {"status": "unknown", "note": f"API-Fehler HTTP {r.status_code}"}
        ids = [i["id"]["videoId"] for i in (r.json().get("items") or []) if (i.get("id") or {}).get("videoId")]
        if not ids:
            return {"status": "offline", "note": "kein laufender Livestream"}
        r = get(f"{API}/videos", params={"part": "snippet,status,liveStreamingDetails", "id": ",".join(ids), "key": key},
                headers=UA, timeout=TIMEOUT)
        if r.status_code != 200:
            return {"status": "unknown", "note": f"API-Fehler HTTP {r.status_code}"}
        return pick_live(r.json())
    except Exception as e:  # Netzwerk, JSON – nie raten
        return {"status": "unknown", "note": "Abruf fehlgeschlagen: " + scrub(e, key)}


# ---------------- Bild-Quellen ----------------
def check_image(url: str, get=requests.get) -> dict:
    try:
        r = get(url, headers=UA, timeout=TIMEOUT, stream=True)
        ctype = (r.headers.get("Content-Type") or "").lower()
        out = {"http": r.status_code}
        if r.headers.get("Last-Modified"):
            out["lastModified"] = r.headers["Last-Modified"]
        r.close()
        if r.status_code == 200 and ctype.startswith("image/"):
            return {"status": "ok", **out}
        return {"status": "offline", "note": f"HTTP {r.status_code}" + ("" if ctype.startswith("image/") else f", kein Bild ({ctype[:30] or 'unbekannt'})"), **out}
    except Exception as e:
        return {"status": "offline", "note": "nicht erreichbar: " + scrub(e, None)}


def run(cams: dict, key: str | None, now: datetime, get=requests.get) -> dict:
    items = {}
    stamp = now.isoformat(timespec="minutes")
    for c in cams.get("items", []):
        if not c.get("freigegeben"):
            continue
        typ, url = c["embed"]["typ"], c["embed"]["url"]
        if typ == "youtube":
            cid = channel_id(url)
            res = check_youtube(cid, key, get) if cid else {"status": "unknown", "note": "keine Kanal-ID"}
        else:
            res = check_image(resolve_template(url, now), get)
        items[c["id"]] = {**res, "checked": stamp}
    return {"generated": stamp, "youtubeApi": bool(key), "items": items}


def write(data: dict, path: Path = OUT) -> None:
    path.write_text("/* Stream-Prüfung der Camera Wall – ERZEUGT von bot/streamcheck.py. Nicht von Hand ändern. */\n"
                    "window.CAMSTATUS = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n")


def main() -> None:
    key = os.getenv("YT_API_KEY") or None
    data = run(load_cams(), key, datetime.now(timezone.utc))
    write(data)
    counts: dict = {}
    for v in data["items"].values():
        counts[v["status"]] = counts.get(v["status"], 0) + 1
    print(f"Stream-Prüfung: {len(data['items'])} Quellen · {counts} · YouTube-API {'aktiv' if key else 'ohne Schlüssel'}")


if __name__ == "__main__":
    main()
