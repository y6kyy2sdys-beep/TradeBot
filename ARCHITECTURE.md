# ARCHITECTURE.md – Tatsächliche Architektur (Stand Phase 0, 24.11.2026)

Dokumentiert, was **heute** im Repository steht – nicht eine Zielarchitektur.

## Überblick

```
GitHub Actions (Cron)                     GitHub Pages (master:/docs, öffentlich)
┌──────────────────────────────┐          ┌──────────────────────────────────────────┐
│ signals.yml  → python -m bot.main │ ──► │ docs/index.html  (UI, ~2 800 Zeilen)       │
│ aircraft.yml → python -m bot.aircraft│ ──►│ docs/data.js, world.js, profiles.js,    │
│   schreibt docs/*.js + state/*.json │    │ doomsday.js, news.js, aircraft.js        │
│   commit & push auf master          │    │ docs/vendor/ (uPlot, d3, topojson, Atlas)│
└──────────────────────────────┘          └──────────────────────────────────────────┘
        │ Telegram Bot API (Meldungen)              │ Browser-Direktabrufe:
        │ Anthropic API (KI-Lageanalyse, optional)  │ adsb.lol, onvista, Coinbase,
        ▼                                           │ planespotters, flagcdn, Wikimedia-Bilder,
   Telegram-Chat des Nutzers                        │ GitHub API (Aktualisieren-Knopf)
```

Kein eigener Server. Kein Build-Schritt. Keine Paketverwaltung im Frontend.

## Backend: Python-Bot (`bot/`, ~2 900 Zeilen)
| Modul | Aufgabe |
|---|---|
| `main.py` | Orchestrierung: Kurse laden, Swing-Signale, offene Signale nachverfolgen, Makro-Alarme, KI-Analyse, Exporte, Telegram |
| `strategies.py` | Indikatoren (RSI, ATR, MACD …), 3 Swing-Strategien, Backtest je Wert |
| `macro.py` | Makro-Bewegungen, Szenarien („Angriff auf Iran → …“), Warnungen, Google-News-Schlagzeilen |
| `analyst.py` | Claude-Lageanalyse mit Websuche, strukturierte Ausgabe (JSON-Schema), Bewegungs-Erklärungen |
| `dashboard.py` | Export `docs/data.js`: Indizes, Rohstoffe, News-Scoring, Hot-Picks, Branchen |
| `world.py` | Export `docs/world.js`: IMF-Indikatoren, Staatsführung (Wikidata), Gold, Eskalation |
| `doomsday.py` | Export `docs/doomsday.js`: Brennpunkte, Militärflugzeuge, Konfliktbilder, Frontlinien (DeepStateMap) |
| `aircraft.py` | Export `docs/aircraft.js` (alle 30 min, eigener Workflow) |
| `profiles.py` / `stocknews.py` | Steckbriefe (`profiles.js`, 2 Jahre Kurse je Wert) und Unternehmens-News (`news.js`) |
| `depot.py` | Depot-Wächter aus Secret `DEPOT`, Wechselkurse |
| `sectors.py`, `watchlist.py`, `wkn.py` | Branchen, Universen (~240 Werte), WKN-Tabelle |

Abhängigkeiten (`requirements.txt`): yfinance 1.7.0, anthropic 2.4.0 (fest); pandas ≥2.2, numpy ≥1.26, requests ≥2.31 (nicht fest).

Zustand: `state/signals.json` (offene/geschlossene Signale, Alarm-Sperren, Protokoll), `state/fundamentals.json` (Cache).
Beides liegt **öffentlich** im Repository.

## Workflows
| Datei | Takt | Rechte | Secrets |
|---|---|---|---|
| `signals.yml` | werktags stündlich 6–22 Uhr UTC + Sonderläufe, Wochenende alle 3 h, `workflow_dispatch` (mode) | `contents: write` | TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, ANTHROPIC_API_KEY, DEPOT |
| `aircraft.yml` | alle 30 min | `contents: write` | keine |

Beide nutzen `concurrency: signals`, Actions `actions/checkout@v4`, `actions/setup-python@v5` (Tag, nicht SHA-gepinnt).

## Frontend (`docs/index.html`)
**Ergänzt in P2 (28.11.2026, `alfred-dev`):** `docs/cameras.js` (Quellenkatalog `window.CAMS`, leer bis Freigabe) und
`docs/camwall.js` (`window.TB_camwall`, Reiter LAGEBILD) werden vor dem Haupt-Skript geladen, `docs/alfred.js`
(`window.TB_alfred`, ALFRED + Befehlsliste) danach. `index.html` stellt dafür `window.TB_map` bereit (Land öffnen, Namen, Eskalation).

Eine Datei, CSS inline, JavaScript in einer IIFE, Module als benannte Funktionen:

| Modul | Inhalt |
|---|---|
| Intro / Matrix-Regen | Canvas-Animation, Schalter RAIN AN/AUS, `prefers-reduced-motion` wird beachtet |
| Kopf, Ticker | Uhr UTC/Berlin, Datenstand, Regime-Anzeige, A−/A+, Aktualisieren, Layout, App-Modus |
| `news` | „Kritische Lage“: gewichtete Schlagzeilen |
| Chart-Fabrik + Zeitraum-Steuerung | uPlot-Charts für Indizes und Rohstoffe, Zeitraum-Presets, Koppeln |
| `picks` | Hot-Picks (Momentum) + KI-Calls mit Szenarien |
| `worldMap` | d3-Karte (NaturalEarth) **und Globus (d3 orthographic, SVG)**, Modi Eskalation/Wirtschaft/Inflation/Gold, Szenarien bis 2050 inkl. Dystopie, Länderkarte mit Staatsführung, Doomsday-Modus (Brennpunkte, Militärflugzeuge live, Frontlinien), Cartoon-Intro |
| `sectors` | Branchen-Kacheln mit News und KI-Ausblick |
| `log` | Signal-Protokoll |
| `search` | Suche + Steckbrief (Kennzahlen, News, Favoriten) |
| `myDepot` | Depot im Browser (localStorage + IndexedDB), Prognose-Fächer, Grafik mit Live-Kurs (onvista), Backup/Link |
| `refresher` | Bot-Lauf per GitHub-API starten (Token im Browser) |
| `layout`, `appMode` | Blöcke verschieben/einklappen, Handy-Ansicht |

### Globus / Karte im Detail
- Rendering: **SVG** über d3 (`geoNaturalEarth1` flach, `geoOrthographic` als Globus), `d3.zoom`/`d3.drag`.
- Ländergrenzen: world-atlas 110m (sofort), 50m wird beim Hineinzoomen nachgeladen (`world-geo-50m.js`).
- Ebenen: Länderfärbung, Brennpunkte, Militärflugzeuge (bis 800 Marker), Frontlinien-Polygone.
- Flugzeuge: Bot-Stand alle 30 min (`aircraft.js`) + Browser-Livestand von `api.adsb.lol/v2/mil` (einstellbar, Standard 60 s).
- Klick auf Flugzeug: Infofenster (Kennung, Typ, Höhe, Tempo, Kurs, Land über ICAO-Adressblock, Foto von planespotters, Links zu Flightradar24/ADS-B Exchange).
- **Hinweis:** Es gibt keine eingebettete Flightradar24-Karte; „Flightradar“ ist ein Link. Die „WarMap“ sind DeepStateMap-Polygone (Ukraine) plus Link zu liveuamap.

## Browser-Speicher (nur auf dem Gerät des Nutzers)
`depot`, `favs`, `ghToken`, `ovmap`, `pcharts`, Layout-/Anzeige-Einstellungen; IndexedDB-Spiegel des Depots.
