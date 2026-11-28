# ROADMAP.md – PROJECT A.L.F.R.E.D. (Stand 28.11.2026)

Jede Phase startet nur nach ausdrücklicher Freigabe des Eigentümers. Entwicklung auf `alfred-dev`,
`master` ist produktiv (GitHub Pages + Bot) – Änderungen dort, Live-Veröffentlichung und Force-Push nur mit Freigabe.

Legende: ✔ abgeschlossen · ◐ teilweise · ☐ geplant (dokumentiert) · – nicht begonnen

## Gesamtstatus
| Bereich | Status | Stand |
|---|---|---|
| Phase 0/1 – Analyse, Dokumentation, Konzept | ✔ | 24.11.2026 |
| MCP-Werkzeuge (Playwright, Chrome DevTools, Context7) | ✔ | getestet 24.11.2026, isolierte Profile |
| S1 – Depot-Rückschluss | ◐ | Code fertig + getestet; Branch `release/s1-master` (lokal) wartet auf Freigabe für master |
| S1 – alte Einträge in der Git-Historie | – | eigene Entscheidung (Umschreiben = Force-Push) |
| S2 Token · S3 Lieferkette · S4 Schrift/Datenschutz | ☐ | siehe SECURITY.md |
| Matrix-Design | ✔ | live; Fehler: Hintergrund-Regen nur 300×150 px |
| Batcomputer-/Wayne-Ergänzungen | ☐ | DESIGN_SYSTEM.md, kein Code |
| ALFRED-Assistent | ☐ | PROJECT_ALFRED.md, kein Code |
| Globus, Militärflugzeuge, Frontlinien, Hotspots | ✔ | live (Live-Abruf adsb.lol im Browser per CORS blockiert → Bot-Stand) |
| Flugrouten beim Anklicken | ☐ | Plan unten, kein Code |
| Global Risk Layer | ☐ | Schnittstelle in PROJECT_ALFRED.md |
| Portfolio Risk Center | ☐ | Kennzahlen festgelegt, kein Code |
| Camera Wall (öffentliche Live-Kameras) | ☐ | nur Regeln, keine Quellenliste |
| Automatische Tests | ◐ | `tests/test_depot_keys.py` (S1); Rest TEST_PLAN.md ausstehend |

## Priorisierte Reihenfolge

### P0 – Sicherheit abschließen
1. ✔ `alfred-dev` auf GitHub (43db660) · ✔ Secret `DEPOT_SALT` hinterlegt · ✔ GitHub CLI mit `workflow`-Recht.
2. ◐ S1 auf master: `release/s1-master` = aktueller master + nur `bot/depot.py` und Workflow (Projektdokumente bleiben auf `alfred-dev`).
   Ablauf nach Freigabe: Branch auf neuesten master setzen → Tests → Fast-Forward-Push auf master → nächsten Bot-Lauf prüfen
   (`state/signals.json` ohne 10-stellige `depot:`-Einträge). Rücknahme: `git revert` des einen Commits.
3. – Entscheidung Git-Historie.

### P1 – Kleine Korrekturen und Grundlagen (`alfred-dev`)
4. Matrix-Regen bildschirmfüllend (CSS `#rain`: Breite/Höhe ergänzen).
5. `.playwright-mcp/` ignorieren ✔ · MCP-Vorlage um Context7 ergänzen.
6. S3: Python-Abhängigkeiten und Actions-Versionen pinnen.
7. Playwright-Basistest: Seite ohne JS-Fehler, Globus, Infofenster, Esc.

### P2 – Phase 2 Design + ALFRED-Kern
8. Design-Tokens und Status-Pillen (LIVE · BOT-STAND · VERALTET · NICHT KONFIGURIERT), Gold-Akzent max. 1–2 Stellen,
   taktische Eckrahmen, Kopfzeile „WAYNE INTELLIGENCE · A.L.F.R.E.D.“ (klein, `--muted`). Keine Logos, kein Comic.
9. ALFRED-Modul `docs/alfred.js` über kleine Schnittstelle `window.TB`: Begrüßung, Systemstatus (Alter je Datendatei),
   Markt- und Lagebericht, Benachrichtigungen aus `DASH.alerts`; nur vorhandene Daten, Quelle + Stand je Wert.
10. Befehlsliste ⌘K / Strg+K. Sprachausgabe vorbereitet, Standard aus; Spracheingabe und KI-Dialog „nicht konfiguriert“.

### P3 – Flugrouten (Phase 3)
11. Recherche adsb.lol (Positionshistorie, Routen, CORS, Lizenz) – ohne Code.
12. Selbst aufgezeichnete Spur je ICAO-Adresse (Ringpuffer ~120 Punkte, nur Arbeitsspeicher) als grüne Großkreis-Linie (`d3.geoPath`).
13. Weiterführung nur gestrichelt „geschätzt (Kurs × Tempo)“; Ziel/ETA nur bei bekannter Quelle, sonst „nicht verfügbar“.
14. Schalter Folgen/Zentrieren/Route/Esc + Playwright-Test inkl. 180°-Übergang.
    Hinweis: Da der Browser-Live-Abruf per CORS blockiert ist, entsteht eine Spur zunächst nur aus den 30-Minuten-Ständen des Bots.

### P4 – Risk Center und Lage-Ebenen (Phase 4)
15. Portfolio Risk Center: Konzentration, Branche/Land/Währung, Volatilität, Max Drawdown, Korrelation, Sharpe – nur aus vorhandenen Kursen.
16. Global Risk Layer: 1–2 frei nutzbare Quellen nach Lizenz- und CORS-Prüfung, einheitliches Ereignisformat.
17. Camera Wall: erst Quellen- und Lizenzliste (nur offiziell einbettbare Kameras), Laden erst beim Öffnen,
    Kennzeichnung Live/Standbild/Zeitraffer, keine Gesichtserkennung, keine Personenverfolgung.

### P5 – Feinschliff
18. Performance: Flugzeug-Marker auf Canvas, Pfad-Neuberechnung beim Ziehen drosseln, große Dateien bei Bedarf laden.
19. S4: Schrift lokal, Favicon, Formularfelder benennen · S2: Token-Hinweis · Barrierefreiheit + Lighthouse.
