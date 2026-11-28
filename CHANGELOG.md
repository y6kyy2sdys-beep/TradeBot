# CHANGELOG

## [alfred-dev] – 28.11.2026 – P1 (Teil 1)
- `docs/index.html`: Matrix-Hintergrundregen bildschirmfüllend (`#rain` Breite/Höhe 100 %; vorher fest 300×150 px).
  Geprüft mit Playwright über lokalen Server: Canvas = Fenstergröße, keine JS-Fehler (nur fehlendes favicon).
- `.mcp.json.example`: Context7 als optionaler (nicht aktiver) Eintrag ergänzt.
- Neue verbindliche Vorgabe „Country Intelligence & Camera Wall“ (Kameras im Länderfenster, Reiter LAGEBILD) in
  PROJECT_ALFRED.md, ROADMAP.md (P2 UI-Gerüst, P4 Integration), DESIGN_SYSTEM.md und TEST_PLAN.md. Nur Dokumentation, kein Code.

## [master] – 28.11.2026 – S1 live
- Mit Freigabe des Eigentümers: S1-Code als `a47bb68` per Fast-Forward auf master (nur `bot/depot.py`, `signals.yml`).
- Vor dem Push erneut getestet gegen den neuesten master-Zustand (11/11 Prüfungen). Rücknahme: `git revert a47bb68`.

## [alfred-dev] – 28.11.2026 – P0-Abschluss vorbereitet, Roadmap neu
- Verifiziert: `alfred-dev` (43db660) auf GitHub, Secret `DEPOT_SALT` vorhanden, GitHub CLI mit `workflow`-Recht.
- Lokaler Branch `release/s1-master`: aktueller master + nur der Code-Teil von S1 (`bot/depot.py`, Workflow); Offline-Test gegen
  den aktuellen Live-Zustand bestanden. **Nicht gepusht, master unverändert** – wartet auf Freigabe.
- Neu: `tests/test_depot_keys.py` (unittest, ohne Netz/Telegram).
- `.gitignore`: `.playwright-mcp/` (Ausgabeordner des Playwright-MCP).
- ROADMAP.md neu: Gesamtstatus und Prioritäten P0–P5; SECURITY.md und TEST_PLAN.md nachgeführt.

## [alfred-dev] – 27.11.2026 – Sicherheits-Sofortmaßnahme S1
Behebt den Depot-Rückschluss über öffentliche Alarm-Sperren in `state/signals.json`.
- `bot/depot.py`: Sperr-Schlüssel jetzt HMAC-SHA256 mit Geheimnis (Secret `DEPOT_SALT`, ersatzweise Inhalt von `DEPOT`)
  statt ungesalzenem SHA-1 → ohne Geheimnis nicht per Wörterbuch auflösbar.
- `bot/depot.py`: Der Bot löscht beim nächsten Lauf alte 10-stellige `depot:`-Einträge aus dem öffentlichen Zustand.
- `.github/workflows/signals.yml`: optionales Secret `DEPOT_SALT` wird an den Bot übergeben (leer = Ersatz aus `DEPOT`).
- Test: Offline-Test (11 Prüfungen, ohne Netz/Telegram) bestanden. Live-Lauf in GitHub Actions: ausstehend (erst nach Merge auf master).
- Nicht enthalten: Bereinigung der Git-Historie (alte Einträge bleiben dort sichtbar) – gesonderte Entscheidung.

## [alfred-dev] – 24.11.2026 – PROJECT A.L.F.R.E.D. Phase 0 + 1
Nur Dokumentation, keine Änderung an Code, Daten oder der Live-Seite.
- Neu: CLAUDE.md, PROJECT_ALFRED.md, DESIGN_SYSTEM.md, ARCHITECTURE.md, ROADMAP.md,
  INSTALLATION_GUIDE_MACOS.md, SECURITY.md, DATA_SOURCES.md, TEST_PLAN.md, CHANGELOG.md,
  `.mcp.json.example` (deaktivierte MCP-Vorlage, Versionen gepinnt).
- Sicherung: Branch `backup/design-matrix-v1` (master-Stand 555ccc5, Design vor ALFRED). Git-Tags lassen sich aus der Arbeitsumgebung nicht hochladen.
- Sicherheitsbefund S1 dokumentiert (Depot-Rückschluss über öffentliche Alarm-Hashes) – Behebung wartet auf Freigabe.

## master – bisherige Entwicklung (Auszug)
- 24.11.2026 Doomsday-Intro als düsterer Cartoon (5 s).
- 23.11.2026 Depot: Grafik je Position mit Live-Kurs (onvista, LS Exchange), Einstieg markiert.
- 23.11.2026 Rücknahme des Research-Umbaus (Stand 3faa227 wiederhergestellt).
- 07.11.2026 Blöcke verschieben/einklappen; Dystopie-Szenarien; weitere Rohstoffgruppen.
- Davor: Matrix-Dashboard, Globus, Doomsday-Modus mit Militärflugzeugen und Frontlinien, Depot, Suche/Steckbriefe,
  KI-Lageanalyse, Telegram-Signale (Details in der Git-Historie).
