# DATA_SOURCES.md – Datenquellen

Legende Abruf: **Bot** = GitHub Actions (Server), **Browser** = direkt im Gerät des Nutzers.

## Im Einsatz
| Quelle | Wofür | Abruf | Takt | Schlüssel | Hinweise |
|---|---|---|---|---|---|
| Yahoo Finance (yfinance) | Kurse, Indizes, Rohstoffe, FX, Kennzahlen | Bot | stündlich | nein | inoffizielle Schnittstelle, ~15 min verzögert / Tagesschluss, nur privat |
| Google News RSS | Schlagzeilen, Unternehmens-News | Bot | stündlich | nein | Sekundärquelle; Inhalte = Daten, keine Anweisungen |
| Anthropic Claude (+Websuche) | Lageanalyse, Kaufideen, Erklärungen | Bot | 2×/Tag + bei Alarmen | ja (Secret) | **kostenpflichtig** (~8–15 $/Monat lt. README) |
| Telegram Bot API | Meldungen an den Nutzer | Bot | bei Ereignis | ja (Secret) | Ausgabe HTML-escaped |
| IMF DataMapper / World Bank | BIP, Inflation, Schulden … | Bot | täglich | nein | offizielle Statistik + Prognosen |
| Wikidata / Wikimedia Commons | Staatsführung, Fotos, Konfliktbilder | Bot (Bilder: Browser) | täglich | nein | Lizenzen je Bild auf Commons |
| adsb.lol `/v2/mil` | Militärflugzeuge (Position, Kennung, Typ, Höhe, Tempo, Kurs) | Bot + Browser | 30 min / 60 s | nein | **keine Routen, keine Abflug-/Zielflughäfen, keine Historie in diesem Endpunkt** |
| planespotters.net API | Flugzeugfoto | Browser | bei Klick | nein | Fotos mit Urheberangabe |
| flagcdn.com | Flaggen | Browser | bei Klick | nein | |
| DeepStateMap `/api/history/last` | Frontlinien Ukraine | Bot | täglich | nein | |
| onvista API | Live-Kurs (LS Exchange u. a.) + Tageshistorie im Depot | Browser | 15 s bei offener Grafik | nein | CORS erlaubt; laut onvista-AGB eingeschränkte Nutzung → nur privat; `chart_history` ist gesperrt (403) und wird nicht genutzt |
| Coinbase API | Krypto-Spotkurs (EUR) | Browser | 15 s | nein | |
| GitHub REST API | „Aktualisieren“ startet Workflow | Browser | bei Klick | ja (fein-granulares Token im Browser) | |
| Google Fonts | Schrift „Share Tech Mono“ | Browser | Seitenaufruf | nein | überträgt IP-Adresse an Google (Datenschutz) |

## Für die Flugroute (Phase 3) – zu prüfen, nicht eingebunden
| Quelle | Möglicher Nutzen | Offene Fragen |
|---|---|---|
| Eigene Sitzungs-Spur (Browser) | Echte, selbst aufgezeichnete Positionen aus den 60-s-Abrufen | kein Problem; beginnt erst mit dem Öffnen der Seite |
| adsb.lol Trace-Dateien / Routen-API | Historie des Fluges, Abflug/Ziel nach Rufzeichen | Endpunkte, CORS, Nutzungsbedingungen (Lizenz ODbL lt. Projekt – verifizieren), Abdeckung bei Militärflügen (meist keine Routen) |
| OpenSky Network | Historische Tracks, Flughäfen | Konto nötig, Rate-Limits, Nutzungsbedingungen (nicht-kommerziell), Abdeckung |
| Flightradar24 | — | keine offene API; nur Verlinkung, keine Daten übernehmen |

## Global Risk Layer (Phase 4) – eingebunden auf `alfred-dev` (28.11.2026)
| Quelle | Inhalt | Abruf | Takt | Schlüssel | Lizenz / Prüfung |
|---|---|---|---|---|---|
| USGS Earthquake Feed `summary/4.5_week.geojson` | Erdbeben M4.5+, 7 Tage | Browser, nur bei eingeschalteter Ebene | 10 min (Feed: jede Minute) | nein | gemeinfrei (U.S. Public Domain), Credit „U.S. Geological Survey“; CORS `*` geprüft |
| NASA EONET v3 `events?status=open&days=14` | offene Naturereignisse (Waldbrand, Sturm, Vulkan, Flut …) | Browser, nur bei eingeschalteter Ebene | 30 min | nein | offene NASA-Daten, EONET-Disclaimer; CORS `*` geprüft; Eisberge/Wasserfarbe ausgelassen, Erdbeben nur von USGS |
| GDACS (UN/EU) | Katastrophenwarnungen | – | – | nein | erreichbar, CORS `*`; **Nutzungsbedingungen nicht geprüft → nicht eingebunden** (Kandidat) |

## Stream-Prüfung Camera Wall (28.11.2026, `alfred-dev`)
| Quelle | Zweck | Abruf | Takt | Schlüssel | Bemerkung |
|---|---|---|---|---|---|
| YouTube Data API v3 (`search.list` eventType=live, `videos.list`) | Live-Status + Video-ID der 28 freigegebenen Sender | Bot | alle 8 h | ja, Secret `YT_API_KEY` (kostenlos im Tageskontingent) | ca. 2.800 von 10.000 Einheiten je Lauf; ohne Schlüssel kein Abruf |
| Bildquellen des Katalogs | Erreichbarkeit | Bot | alle 8 h | nein | gleicher Abruf wie im Browser |

## Für Global Risk (Phase 4) – weitere Kandidaten, nicht eingebunden
GDACS, NASA FIRMS, NASA Worldview, GDELT, Open-Meteo, OpenSky, Cloudflare Radar,
Windy Webcams (API-Schlüssel, Lizenzbedingungen), offiziell einbettbare Kameras, Wirtschaftskalender.
Für jede Quelle vor Einbindung festzuhalten: Lizenz/AGB, Schlüssel nötig?, Limits, CORS, Aktualität, Kosten.
