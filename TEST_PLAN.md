# TEST_PLAN.md – Teststrategie

## Stand
- Es gibt **keine** automatisierten Tests im Repository (ein früherer Testordner wurde mit dem Research-Umbau zurückgenommen).
- Bisher geprüft wurde manuell bzw. in der Claude-Cloud-Umgebung mit Playwright (vorinstalliert dort, nicht im Repo)
  und nachgebildeten Datenquellen. Diese Ergebnisse sind nicht reproduzierbar abgelegt.
- In Phase 0/1 wurden **keine** Tests ausgeführt (nur Analyse und Dokumentation).
- 24.11.2026: MCP-Funktionstest (Playwright, Chrome DevTools) gegen die Live-Seite: keine JS-Fehler; Befunde in ROADMAP.md.
- 28.11.2026: `tests/test_depot_keys.py` (S1) – lokal: `python3 -m unittest discover -s tests`. Läuft noch nicht in Actions.

## Geplante Test-Ebenen
| Ebene | Werkzeug (Vorschlag) | Läuft wo | Status |
|---|---|---|---|
| Python-Berechnungen (Indikatoren, Backtest, Depot-Schlüssel) | `unittest` (Standardbibliothek, keine Installation) | GitHub Actions vor jedem Lauf | ausstehend |
| Seite lädt ohne JS-Fehler, alle Blöcke rendern | Playwright (Python oder Node) mit lokalen Beispieldaten | Actions / lokal | ausstehend |
| Globus: Drehen, Zoom, Klick auf Land/Flugzeug, Infofenster, Esc | Playwright | lokal / Actions | ausstehend |
| Kartenebenen ein/aus, Doomsday an/aus, Intro überspringbar | Playwright | lokal / Actions | ausstehend |
| Flugzeugauswahl + Flugroute (Phase 3) | Playwright mit festen Beispiel-Positionen inkl. 180°-Übergang | lokal / Actions | ausstehend |
| Datenaktualisierung (veraltete Daten werden markiert) | Playwright mit manipuliertem `generated` | lokal / Actions | ausstehend |
| Responsive (Handy 390 px, Tablet, Desktop): kein horizontales Scrollen | Playwright-Geräteprofile | lokal / Actions | ausstehend |
| Barrierefreiheit | axe-core über Playwright | lokal / Actions | ausstehend |
| Performance | Lighthouse (in Chrome DevTools eingebaut) | lokal | ausstehend |
| Sicherheit | Muster-Suche nach Schlüsseln, Prüfung `state/` auf Depot-Rückschlüsse, Abhängigkeits-Audit (`pip-audit`) | Actions | ausstehend |

## Ergebnisse P2 (28.11.2026, manuell mit Playwright-MCP und Chrome-DevTools-MCP, lokaler Server 127.0.0.1)
| Prüfung | Ergebnis |
|---|---|
| Konsole beim Laden | nur bekannte Fehler (favicon 404, adsb.lol CORS) – keine neuen |
| LAGEBILD ohne Zustimmung | 0 iframes, keine Verbindungen zu Kamera-Hosts (nur bestehende Wikimedia-Porträts) |
| Nach „LAGEBILD LADEN“ (Testeinträge auf 127.0.0.1:1) | iframes mit `sandbox`, `referrerpolicy=no-referrer` |
| Reiter DETAILS / Fenster schließen | Einbettungen entfernt (0 iframes); Rückkehr lädt nach Sitzungs-Zustimmung erneut |
| Raster 2×2, Status-Pillen | 2 Spalten, Fenster verbreitert; STAND UNBEKANNT / DELAYED / LIVE / OFFLINE korrekt |
| Konfliktgebiet (UKR) | Panorama ausgefiltert, nur zugelassener Nachrichten-Eintrag |
| Land ohne Quelle | UNAVAILABLE mit Grund |
| Befehlsliste | ⌘K/Strg+K öffnet, Suche „lagebild schweiz“ → Enter öffnet Land + Reiter, Esc schließt |
| Bestehende Funktionen | Doomsday an (echter Klick), Hotspots + neuer Verweis, Aktiensuche, Depot-Block, Charts |
| Handy 390 px (App-Ansicht) | kein Querscrollen, ALFRED volle Breite |
| Leistung (DevTools) | Bildrate 145 → 143 fps mit ALFRED + LAGEBILD offen; neue Dateien ≈ 25 KB |
Nicht geprüft: echte Streams (Katalog leer), Vollbild im echten Gerät, Screenreader.

## Ergebnisse P4 Camera Wall (28.11.2026, Playwright, echte Quellen)
| Prüfung | Ergebnis |
|---|---|
| `tests/test_camera_catalog.py` (Pflichtfelder, HTTPS, nocookie, Konfliktgebiete, Auflagen, = freigegebener Katalog) | 7/7 bestanden |
| Vor „LAGEBILD LADEN“ | 0 Verbindungen zu Kamera-/Stream-Hosts |
| Alle 30 Bildquellen (inkl. GIBS-Vortag, JMA `{HHMM}`) | 30/30 abrufbar |
| Deutschland 2×2 | DW live, phoenix nur angekündigter Stream (Status STAND UNBEKANNT), EUMETSAT DELAYED, Skyline-Vorschau |
| Ukraine (Konfliktgebiet) | nur TSN + 2 Satellitenbilder mit Quellenangabe; TSN zeigt „Video nicht verfügbar“ (kein Livestream) |
| Reiterwechsel / Schließen | 3 → 0 Einbettungen |
| Schweiz | 2 Skyline-Vorschauen, Link unverändert auf Kameraseite |
Nicht prüfbar im Browser: YouTube-Livestatus (fremder Player) → Vorschlag Bot-Prüfung (ROADMAP 17e).

## Ergebnisse P4 Global Risk Layer (28.11.2026)
| Prüfung | Ergebnis |
|---|---|
| `tests/risklayer.test.js` (USGS/EONET-Umwandlung, Schwere-Stufen, Schnittstelle, leere Antworten) | 5/5 bestanden |
| Ebene aus | 0 Abrufe bei USGS/NASA |
| Ebene an (Live) | beide Quellen LIVE, 85 Ereignisse (76 Erdbeben, 9 Waldbrände), alle Marker gezeichnet |
| Globus | nur Ereignisse der sichtbaren Halbkugel (29 von 85), drehen mit |
| Infofenster | Schwere, bestätigt/vorläufig, Magnitude, Tiefe, PAGER, Tsunami-Hinweis, Quelle |
| Zusammen mit Doomsday | Flugzeuge, Hotspots und Risk Layer gleichzeitig; keine neuen Konsolenfehler |
| Ausschalten | Marker und Leiste weg, Wahl gemerkt |

## Ergebnisse P4 Portfolio Risk Center (28.11.2026)
| Prüfung | Ergebnis |
|---|---|
| `tests/risk.test.js` (Drawdown, Kursreihe, Gewichte/Wechselkurs, Korrelation ±, Beta = 1, fehlende Daten, Lage, Rückrechnung von Hand) | 9/9 bestanden |
| Playwright mit Testdepot (8 Werte + 1 unbekanntes Symbol, nur im isolierten Testprofil) | Kennzahlen plausibel, unbekanntes Symbol ausgewiesen, keine Konsolenfehler |
| ALFRED DEPOT + Sprung zum Risk Center | funktioniert |
| Handy 390 px (App-Ansicht) | kein Querscrollen, Tabellen scrollen in ihrem Rahmen |
Ausführen: `node --test tests/` und `python3 -m unittest discover -s tests`.

## Country Intelligence & Camera Wall (verbindlich, P2/P4)
| Prüfung | Werkzeug | Phase | Status |
|---|---|---|---|
| Kein Netzwerkabruf zu Kamera-/Stream-Hosts, solange Länderfenster bzw. Reiter LAGEBILD geschlossen ist | Playwright (Netzwerk-Mitschnitt) | P2 + P4 | ausstehend |
| Beim Schließen, Reiter- oder Länderwechsel werden alle Einbettungen entfernt | Playwright | P2 + P4 | ausstehend |
| Leerzustand: Land ohne Quelle zeigt UNAVAILABLE mit Grund; bestehende Reiter ÜBERBLICK/DETAILS unverändert | Playwright | P2 | ausstehend |
| Raster 1/2/2×2, Handy einspaltig, Vollbild + Esc | Playwright (Geräteprofile) | P2 | ausstehend |
| Statuslogik LIVE/DELAYED/OFFLINE/UNAVAILABLE + „Stand unbekannt“ aus Beispieldaten | Playwright mit festen Beispiel-Einträgen | P4 | ausstehend |
| Katalog-Regelprüfung: Pflichtfelder, Einbett-Beleg, `geprueft_am`, Konfliktzonen nur Art „Nachrichten“/zeitversetzt, keine privaten Hosts | `unittest` auf `docs/cameras.js` | P4 | ausstehend |
| Einbettung: `sandbox`, `referrerpolicy=no-referrer`, Ton aus, kein Autoplay vor dem Öffnen | Playwright (DOM-Prüfung) | P4 | ausstehend |
| Bestehende Funktionen (Globus, Länderklick, Flugzeuge, Doomsday, Depot) unverändert | Playwright-Basistest | P2 + P4 | ausstehend |

## Grundsatz
Testergebnisse werden nur berichtet, wenn sie tatsächlich ausgeführt wurden; Fehlschläge werden mit Ausgabe dokumentiert.
Externe Dienste werden in Tests durch gespeicherte Beispielantworten ersetzt (keine Live-Abrufe, keine Kosten).
