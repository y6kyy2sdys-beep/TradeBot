"""Frühwarnsystem für das Dashboard (docs/doomsday.js).

Nur öffentlich verfügbare Daten:
- Militärflugzeuge mit eingeschaltetem Transponder (ADS-B, api.adsb.lol – ODbL), Momentaufnahme je Lauf.
- Konflikt-Brennpunkte aus der aktuellen Nachrichtenlage (Google News), je Meldung nach Art eingeordnet
  (Luft, Marine, U-Boot, Boden, Raketen, Nuklear). Das sind Meldungen, keine Positionen von Truppen oder Schiffen.
"""

import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote

import requests

OUT = Path(__file__).resolve().parent.parent / "docs" / "doomsday.js"
UA = {"User-Agent": "TradeBot-Dashboard/1.0 (GitHub Actions)"}

# key, Name, Breite, Länge, Suchanfrage
HOTSPOTS = [
    ("ukr_front", "Ukraine · Ostfront (Donbas)", 48.3, 37.8, "Ukraine front OR Pokrovsk OR Donbas OR Kharkiv attack"),
    ("blacksea", "Schwarzes Meer · Krim", 44.6, 33.5, "Black Sea navy OR Crimea strike OR Sevastopol drone"),
    ("sudan_darfur", "Sudan · Darfur / El Fasher (RSF)", 13.6, 25.3, "\"Rapid Support Forces\" OR RSF Sudan OR El Fasher OR Darfur"),
    ("sudan_khartoum", "Sudan · Khartum / Kordofan", 14.5, 31.0, "Khartoum OR Kordofan OR \"Sudanese army\" OR Omdurman"),
    ("gaza", "Gaza · Israel", 31.4, 34.4, "Gaza strike OR IDF OR Hamas"),
    ("lebanon", "Libanon · Hisbollah", 33.4, 35.6, "Lebanon Hezbollah strike OR Israel Lebanon"),
    ("syria", "Syrien", 35.0, 38.5, "Syria clashes OR Syria airstrike"),
    ("hormuz", "Iran · Straße von Hormus", 26.8, 56.3, "Iran strike OR \"Strait of Hormuz\" OR IRGC navy"),
    ("redsea", "Rotes Meer · Jemen (Huthi)", 14.8, 42.2, "Houthi OR \"Red Sea\" attack ship OR Yemen strike"),
    ("taiwan", "Taiwanstraße", 24.4, 119.6, "\"Taiwan Strait\" OR PLA drills Taiwan OR Taiwan military"),
    ("scs", "Südchinesisches Meer", 11.5, 115.0, "\"South China Sea\" OR Philippines China coast guard"),
    ("korea", "Koreanische Halbinsel", 38.4, 127.2, "\"North Korea\" missile OR DMZ OR Pyongyang military"),
    ("kashmir", "Kaschmir · Indien/Pakistan", 34.1, 74.8, "Kashmir military OR India Pakistan border firing"),
    ("sahel", "Sahel · Mali / Burkina Faso / Niger", 14.5, -1.5, "Mali OR \"Burkina Faso\" OR Niger jihadist attack"),
    ("congo", "Ost-Kongo · M23", -1.6, 29.2, "M23 OR \"eastern Congo\" fighting OR Goma"),
    ("myanmar", "Myanmar", 21.0, 96.0, "Myanmar junta OR Myanmar resistance fighting"),
    ("caribbean", "Venezuela · Karibik", 11.5, -66.5, "Venezuela military OR Caribbean \"US Navy\" OR Venezuela strike"),
    ("baltic", "Ostsee · Baltikum", 57.5, 19.5, "\"Baltic Sea\" NATO OR Russian navy Baltic OR Kaliningrad"),
    ("arctic", "Nordatlantik · Arktis", 70.0, 15.0, "submarine Atlantic OR Arctic navy OR GIUK"),
]

CATEGORIES = {
    "luft": ("airstrike", "air strike", "air raid", "fighter jet", "jets", "bomber", "drone", "drones", "helicopter",
             "luftangriff", "kampfjet", "drohne", "aircraft", "airspace"),
    "marine": ("navy", "naval", "warship", "destroyer", "frigate", "carrier", "fleet", "coast guard", "vessel", "ship",
               "tanker", "kriegsschiff", "marine", "flugzeugträger"),
    "uboot": ("submarine", "u-boot", "u-boat"),
    "boden": ("troops", "offensive", "tank", "tanks", "front", "advance", "militia", "rsf", "rapid support", "soldiers",
              "fighting", "clashes", "ground", "truppen", "panzer", "soldaten", "artillery", "shelling", "siege", "battle"),
    "rakete": ("missile", "missiles", "rocket", "rockets", "ballistic", "hypersonic", "rakete", "raketen", "icbm"),
    "nuklear": ("nuclear", "atom", "nuklear", "uranium", "enrichment"),
}


# Zusätzliche ADS-B-Felder für den Flugzeug-Steckbrief (sofern gesendet)
EXTRA_FIELDS = ("desc", "ownOp", "year", "squawk", "emergency", "category", "alt_geom", "baro_rate", "geom_rate",
                "ias", "tas", "mach", "nav_altitude_mcp", "nav_heading", "seen_pos", "rssi", "dbFlags")


def military_aircraft(limit: int = 800) -> dict:
    try:
        r = requests.get("https://api.adsb.lol/v2/mil", headers=UA, timeout=30)
        r.raise_for_status()
        ac = r.json().get("ac", [])
    except Exception as e:
        print("ADS-B fehlgeschlagen:", repr(e))
        return {"ok": False, "items": []}
    items = []
    for a in ac:
        lat, lon = a.get("lat"), a.get("lon")
        if lat is None or lon is None:
            continue
        alt = a.get("alt_baro")
        items.append({
            "lat": round(lat, 2), "lon": round(lon, 2), "trk": round(a.get("track") or 0),
            "cs": (a.get("flight") or "").strip(), "typ": a.get("t") or "", "reg": a.get("r") or "", "hex": a.get("hex") or "",
            "alt": alt if isinstance(alt, (int, float)) else (0 if alt == "ground" else None),
            "gs": round(a["gs"]) if isinstance(a.get("gs"), (int, float)) else None,
            **{k: a[k] for k in EXTRA_FIELDS if a.get(k) not in (None, "")},
        })
    return {"ok": True, "items": items[:limit], "total": len(items)}


def _news(query: str, limit: int = 12) -> list[dict]:
    url = f"https://news.google.com/rss/search?q={quote(query + ' when:2d')}&hl=en&gl=US&ceid=US:en"
    try:
        root = ET.fromstring(requests.get(url, timeout=15).content)
    except Exception:
        return []
    out = []
    for item in root.iter("item"):
        try:
            ts = parsedate_to_datetime(item.findtext("pubDate") or "").astimezone(timezone.utc).isoformat(timespec="minutes")
        except Exception:
            ts = ""
        out.append({"title": (item.findtext("title") or "").strip(), "link": item.findtext("link") or "",
                    "source": item.findtext("source") or "", "time": ts})
    out.sort(key=lambda n: n["time"], reverse=True)
    return out[:limit]


def hotspots() -> list[dict]:
    out = []
    for key, name, lat, lon, query in HOTSPOTS:
        news = _news(query)
        counts = {c: 0 for c in CATEGORIES}
        for n in news:
            low = " " + n["title"].lower() + " "
            for c, words in CATEGORIES.items():
                if any(w in low for w in words):
                    counts[c] += 1
        total = sum(counts.values())
        level = 0 if not news else min(5, 1 + total // 3)
        out.append({"key": key, "name": name, "lat": lat, "lon": lon, "level": level, "counts": counts,
                    "news": news[:5]})
    return out


# Konfliktbilder für den Zeitraffer: frei lizenzierte Fotos von Wikimedia Commons (Zerstörung, Militärtechnik,
# Rauch) – bewusst ohne Opfer-Bilder.
IMAGE_QUERIES = [
    "destroyed tank Ukraine 2022", "Russian invasion of Ukraine destroyed building", "artillery Ukraine 2023",
    "Sudan war 2023 Khartoum", "Gaza Strip destruction 2023", "Syrian civil war destroyed",
    "Yemen civil war destroyed", "Mariupol destroyed 2022", "Bakhmut 2023", "military convoy war",
]
IMAGE_EXCLUDE = ("dead", "body", "bodies", "corpse", "killed", "victim", "funeral", "grave", "blood", "wounded", "injured", "child")


def conflict_images(per_query: int = 5) -> list[dict]:
    out, seen = [], set()
    for q in IMAGE_QUERIES:
        try:
            r = requests.get("https://commons.wikimedia.org/w/api.php", headers=UA, timeout=25, params={
                "action": "query", "format": "json", "generator": "search", "gsrsearch": q, "gsrnamespace": 6, "gsrlimit": 15,
                "prop": "imageinfo", "iiprop": "url|mime|extmetadata|size", "iiurlwidth": 720})
            pages = (r.json().get("query") or {}).get("pages") or {}
        except Exception:
            continue
        n = 0
        for pg in sorted(pages.values(), key=lambda x: x.get("index", 0)):
            ii = (pg.get("imageinfo") or [{}])[0]
            title = pg.get("title", "")
            if ii.get("mime") != "image/jpeg" or ii.get("width", 0) < 600 or title in seen:
                continue
            meta = ii.get("extmetadata") or {}
            text = (title + " " + str((meta.get("ImageDescription") or {}).get("value", ""))).lower()
            if any(w in text for w in IMAGE_EXCLUDE):
                continue
            seen.add(title)
            out.append({"src": ii.get("thumburl") or ii.get("url"), "page": ii.get("descriptionurl", ""),
                        "title": title.replace("File:", "").rsplit(".", 1)[0][:80],
                        "license": (meta.get("LicenseShortName") or {}).get("value", "")})
            n += 1
            if n >= per_query:
                break
    return out


def frontlines() -> dict:
    """Frontverlauf Ukraine von DeepStateMap (öffentliches GeoJSON), vereinfacht auf ~1 km Genauigkeit."""
    try:
        r = requests.get("https://deepstatemap.live/api/history/last", headers=UA, timeout=40)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print("DeepStateMap fehlgeschlagen:", repr(e))
        return {"ok": False, "features": []}

    def find_fc(x):
        if isinstance(x, dict):
            if x.get("type") == "FeatureCollection":
                return x
            for v in x.values():
                fc = find_fc(v)
                if fc:
                    return fc
        elif isinstance(x, list):
            for v in x:
                fc = find_fc(v)
                if fc:
                    return fc
        return None

    def simplify(ring):
        pts, last = [], None
        for c in ring:
            q = (round(c[0], 2), round(c[1], 2))
            if q != last:
                pts.append(list(q))
                last = q
        return pts if len(pts) >= 4 else None

    fc = find_fc(data) or {"features": []}
    feats = []
    for f in fc.get("features", []):
        g = f.get("geometry") or {}
        if g.get("type") not in ("Polygon", "MultiPolygon"):
            continue
        props = f.get("properties") or {}
        label = " ".join(str(v) for v in props.values() if isinstance(v, str)).lower()
        kind = "occupied" if any(w in label for w in ("окуп", "occup", "оккуп", "росі", "russia", "ордло", "крим", "crimea")) else \
               "contested" if any(w in label for w in ("сір", "grey", "gray", "contested", "невідом")) else \
               "liberated" if any(w in label for w in ("звільн", "liberat")) else "other"
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for poly in polys:
            rings = [r for r in (simplify(ring) for ring in poly) if r]
            if rings:
                feats.append({"type": "Feature", "properties": {"k": kind},
                              "geometry": {"type": "Polygon", "coordinates": rings}})
    date = data.get("datetime") or data.get("createdAt") or data.get("updatedAt") if isinstance(data, dict) else None
    print(f"DeepStateMap: {len(feats)} Flächen")
    return {"ok": bool(feats), "date": date, "features": feats}


def export() -> None:
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "aircraft": military_aircraft(),
        "hotspots": hotspots(),
        "images": conflict_images(),
        "front": frontlines(),
        "sources": {
            "aircraft": "ADS-B Exchange-Community-Daten via api.adsb.lol (ODbL) – nur Maschinen mit eingeschaltetem Transponder",
            "hotspots": "Google News, letzte 48 Stunden – Meldungslage, keine Positionsdaten",
            "images": "Wikimedia Commons (freie Lizenzen, Urheber auf der jeweiligen Bildseite)",
            "front": "DeepStateMap (deepstatemap.live) – Frontverlauf Ukraine",
        },
    }
    OUT.write_text("window.DOOM = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print(f"Frühwarnsystem: {len(payload['aircraft']['items'])} Militärflugzeuge, {len(payload['hotspots'])} Brennpunkte")
