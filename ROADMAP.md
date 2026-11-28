# ROADMAP.md – PROJECT A.L.F.R.E.D. (Stand 28.11.2026)

Jede Phase startet nur nach ausdrücklicher Freigabe des Eigentümers. Entwicklung auf `alfred-dev`,
`master` ist produktiv (GitHub Pages + Bot) – Änderungen dort, Live-Veröffentlichung und Force-Push nur mit Freigabe.

Legende: ✔ abgeschlossen · ◐ teilweise · ☐ geplant (dokumentiert) · – nicht begonnen

## Gesamtstatus
| Bereich | Status | Stand |
|---|---|---|
| Phase 0/1 – Analyse, Dokumentation, Konzept | ✔ | 24.11.2026 |
| MCP-Werkzeuge (Playwright, Chrome DevTools, Context7) | ✔ | getestet 24.11.2026, isolierte Profile |
| S1 – Depot-Rückschluss | ✔ | live seit 28.11.2026 (`a47bb68`); alte Einträge im Bot-Lauf 46148816499 entfernt (bestätigt) |
| S1 – alte Einträge in der Git-Historie | – | eigene Entscheidung (Umschreiben = Force-Push) |
| S2 Token · S3 Lieferkette · S4 Schrift/Datenschutz | ☐ | siehe SECURITY.md |
| Matrix-Design | ✔ | live, Regen bildschirmfüllend |
| Batcomputer-/Wayne-Ergänzungen | ✔ | live seit 28.11.2026 (Merge `70d6711`) |
| ALFRED-Assistent | ✔ | live seit 28.11.2026: Lage, Markt, Depot, System, Meldungen, ⌘K; Spracheingabe/KI-Dialog bewusst „nicht konfiguriert“ |
| Globus, Militärflugzeuge, Frontlinien, Hotspots | ✔ | live (Live-Abruf adsb.lol im Browser per CORS blockiert → Bot-Stand) |
| Flugrouten beim Anklicken | ☐ | Plan unten, kein Code |
| Global Risk Layer | ✔ | live seit 28.11.2026 (USGS + NASA EONET); weitere Quellen nur nach Prüfung |
| Portfolio Risk Center | ✔ | live seit 28.11.2026 |
| Country Intelligence & Camera Wall (im Länderfenster) | ◐ | live seit 28.11.2026 (58 freigegebene Quellen); offen: tägliche Bot-Statusprüfung der Streams |
| Automatische Tests | ◐ | `tests/test_depot_keys.py` (S1); Rest TEST_PLAN.md ausstehend |

## Live-Übernahme 28.11.2026
Merge `alfred-dev` → master mit Freigabe des Eigentümers: Commit `70d6711` (Fast-Forward-freier Merge, kein Force-Push),
Sicherung `backup/master-vor-alfred` = `5ce4046`. Pages gebaut 13:16 UTC, Live-Prüfung mit Playwright bestanden,
Bot-Lauf 46148816499 (manuell, scan) erfolgreich. Rückweg: `git revert -m 1 70d6711`.

## Redesign Variante A „Noir“ – live seit 28.11.2026 (`c32bd96`)
Lagezentrale „GLOBAL INTELLIGENCE NETWORK“ und PROJECT CHRONOS; Sicherung `backup/master-vor-noir`.
Offen: Entscheidung über das alte Szenariomodell der Weltkarte (Basis/Stagnation/Dystopie bis 2050).

## Nächste Schritte (je mit Freigabe)
1. Tägliche Bot-Statusprüfung der YouTube-Streams (OFFLINE statt „Video nicht verfügbar“).
2. P3 Flugrouten.
3. Entscheidung Git-Historie (alte S1-Einträge in früheren Commits).
4. Automatische Tests in GitHub Actions (`node --test`, `unittest`), S4 (Schrift lokal, Favicon), S2-Hinweis.
5. Weitere Risk-Layer-Quelle (z. B. GDACS) nach Prüfung der Bedingungen.

## Priorisierte Reihenfolge

### P0 – Sicherheit abschließen
1. ✔ `alfred-dev` auf GitHub (43db660) · ✔ Secret `DEPOT_SALT` hinterlegt · ✔ GitHub CLI mit `workflow`-Recht.
2. ✔ S1 auf master (Freigabe 28.11.2026): nur `bot/depot.py` und Workflow, Fast-Forward-Push `76304aa..a47bb68`, kein Force-Push.
   Projektdokumente bleiben auf `alfred-dev`. Rücknahme: `git revert a47bb68`.
3. – Entscheidung Git-Historie.

### P1 – Kleine Korrekturen und Grundlagen (`alfred-dev`)
4. ✔ Matrix-Regen bildschirmfüllend (auf `alfred-dev`, noch nicht live).
5. ✔ `.playwright-mcp/` ignorieren · ✔ MCP-Vorlage um Context7 ergänzt.
6. ✔ S3: Python-Abhängigkeiten und Actions-Versionen gepinnt – live, im Bot-Lauf 46148816499 bestätigt.
7. ◐ Playwright-Basistest manuell durchgeführt (TEST_PLAN.md); als automatischer Test in Actions noch offen.

### P2 – Phase 2 Design + ALFRED-Kern
✔ 8.–10a. live seit 28.11.2026.
8. Design-Tokens und Status-Pillen (LIVE · BOT-STAND · VERALTET · NICHT KONFIGURIERT), Gold-Akzent max. 1–2 Stellen,
   taktische Eckrahmen, Kopfzeile „WAYNE INTELLIGENCE · A.L.F.R.E.D.“ (klein, `--muted`). Keine Logos, kein Comic.
9. ALFRED-Modul `docs/alfred.js` über kleine Schnittstelle `window.TB`: Begrüßung, Systemstatus (Alter je Datendatei),
   Markt- und Lagebericht, Benachrichtigungen aus `DASH.alerts`; nur vorhandene Daten, Quelle + Stand je Wert.
10. Befehlsliste ⌘K / Strg+K. Sprachausgabe vorbereitet, Standard aus; Spracheingabe und KI-Dialog „nicht konfiguriert“.
10a. Country-Intelligence-UI ohne externe Inhalte: Reiter LAGEBILD in `showCard(iso)`, Kachel-Raster 1/2/2×2, Kachelkopf,
     Status-Pillen LIVE/DELAYED/OFFLINE/UNAVAILABLE, Vollbild-Knopf, UNAVAILABLE-Hinweis („Quellenkatalog noch nicht freigegeben“).

### P3 – Flugrouten (Phase 3)
11. Recherche adsb.lol (Positionshistorie, Routen, CORS, Lizenz) – ohne Code.
12. Selbst aufgezeichnete Spur je ICAO-Adresse (Ringpuffer ~120 Punkte, nur Arbeitsspeicher) als grüne Großkreis-Linie (`d3.geoPath`).
13. Weiterführung nur gestrichelt „geschätzt (Kurs × Tempo)“; Ziel/ETA nur bei bekannter Quelle, sonst „nicht verfügbar“.
14. Schalter Folgen/Zentrieren/Route/Esc + Playwright-Test inkl. 180°-Übergang.
    Hinweis: Da der Browser-Live-Abruf per CORS blockiert ist, entsteht eine Spur zunächst nur aus den 30-Minuten-Ständen des Bots.

### P4 – Risk Center und Lage-Ebenen (Phase 4)
15. ✔ (alfred-dev, 28.11.2026) Portfolio Risk Center: Konzentration, Branche/Land/Währung, Volatilität, Max Drawdown, Korrelation, Sharpe – nur aus vorhandenen Kursen.
16. ✔ (alfred-dev, 28.11.2026) Global Risk Layer: USGS-Erdbeben + NASA EONET nach Lizenz- und CORS-Prüfung, einheitliches Ereignisformat
    (`docs/risklayer.js`). Weitere Quelle (z. B. GDACS) nur nach Prüfung der Bedingungen.
17. Country Intelligence & Camera Wall (auf `alfred-dev`, Vorgaben PROJECT_ALFRED.md):
    a) ✔ Quellenrecherche + Freigabe (28.11.2026): 58 Einträge, alle vier Gruppen freigegeben, Auflagen in `catalog/kamera_katalog_2026-11-28.md`;
       Konfliktregel = feste Liste (inkl. VAE) + Hotspot ≥ 3 – bereits in `camwall.js` umgesetzt.
    ✔ b)–d) umgesetzt am 28.11.2026 auf `alfred-dev` (58 Quellen eingebunden, getestet). Offen: e) Bot-Prüfung (braucht Bot-Änderung,
       erst nach Freigabe für master sinnvoll) – würde YouTube-Status OFFLINE/LIVE täglich belegen (z. B. TSN derzeit „nicht verfügbar“).
    b) Katalog `docs/cameras.js` mit den freigegebenen Einträgen füllen (Feldformat anpassen, `freigegeben: true`).
       Technik: GIBS-Datum (Vortag, UTC) und JMA-Zeitvorlage `{HHMM}` zur Laufzeit einsetzen; Kennzeichnung „staatsnah“ und
       Skyline-„Vorschau, kein Live-Player“ in der Kachel.
    c) Einbettung im Reiter LAGEBILD, Laden nur bei aktivem Reiter, Entfernen beim Schließen; Vollbild.
    d) Statuslogik LIVE/DELAYED/OFFLINE/UNAVAILABLE, „Stand unbekannt“ statt Raten.
    e) Optional: tägliche, kostenlose Katalogprüfung durch den Bot. f) Tests laut TEST_PLAN.md.

### P5 – Feinschliff
18. Performance: Flugzeug-Marker auf Canvas, Pfad-Neuberechnung beim Ziehen drosseln, große Dateien bei Bedarf laden.
19. S4: Schrift lokal, Favicon, Formularfelder benennen · S2: Token-Hinweis · Barrierefreiheit + Lighthouse.
