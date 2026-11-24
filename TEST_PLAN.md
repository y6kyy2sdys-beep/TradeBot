# TEST_PLAN.md – Teststrategie

## Stand
- Es gibt **keine** automatisierten Tests im Repository (ein früherer Testordner wurde mit dem Research-Umbau zurückgenommen).
- Bisher geprüft wurde manuell bzw. in der Claude-Cloud-Umgebung mit Playwright (vorinstalliert dort, nicht im Repo)
  und nachgebildeten Datenquellen. Diese Ergebnisse sind nicht reproduzierbar abgelegt.
- In Phase 0/1 wurden **keine** Tests ausgeführt (nur Analyse und Dokumentation).

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

## Grundsatz
Testergebnisse werden nur berichtet, wenn sie tatsächlich ausgeführt wurden; Fehlschläge werden mit Ausgabe dokumentiert.
Externe Dienste werden in Tests durch gespeicherte Beispielantworten ersetzt (keine Live-Abrufe, keine Kosten).
