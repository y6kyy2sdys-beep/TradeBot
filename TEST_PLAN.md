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
