# CHANGELOG

## [alfred-dev] – 28.11.2026 – Stream-Prüfung für die Camera Wall
- Befund: Bei mehreren Sendern (Bloomberg, Sky News, ABC News) zeigt der Kanal-Embed `live_stream?channel=` „Video nicht verfügbar“,
  obwohl der Sender live und einbettbar ist; per Video-ID eingebettet läuft der Stream (im Browser geprüft).
- Neu `bot/streamcheck.py`: prüft alle freigegebenen Quellen. YouTube über die offizielle **YouTube Data API v3** (Secret `YT_API_KEY`,
  Entscheidung des Eigentümers): laufender, einbettbarer Livestream + Video-ID; sonst OFFLINE mit Grund; ohne Schlüssel „unbekannt“.
  Keine YouTube-Webseiten-Abrufe (Nutzungsbedingungen). Bildquellen: HTTP-Abruf (erreichbar + Bildformat). Schreibt `docs/streamstatus.js`.
- Neu `.github/workflows/streamcheck.yml`: alle 8 Stunden + manuell; Actions per SHA, `requests==2.34.2`; gleiche Concurrency-Gruppe wie die Bots.
- `camwall.js`: nutzt Prüfergebnisse ≤ 24 h: LIVE mit geprüfter Video-ID (Einbettung per Video), OFFLINE ohne Player-Laden, sonst wie bisher.
- Tests: `tests/test_streamcheck.py` (8 Prüfungen, nachgebildete Antworten, Schlüssel erscheint nie in Fehlertexten). Playwright mit nachgebildetem Prüfergebnis.

## [master] – 28.11.2026 – Redesign „Noir“ live
- Fast-Forward `70d507b..c32bd96` auf master mit Freigabe; Sicherung `backup/master-vor-noir` (`70d507b`); kein Force-Push.
- Vorher: 32 Tests grün, Datendateien unverändert, keine Geheimnisse. Pages gebaut 14:00 UTC.
- Live-Prüfung (Playwright, echte Adresse): alle 7 Module geladen; DOOMSDAY → Kartenlage an + CHRONOS; Jahr 2035 „kein Datensatz“;
  Esc schließt CHRONOS, Kartenlage bleibt; Lagezentrale Japan: 0 Einbettungen vor Zustimmung, Esc schließt. Nur bekannte Konsolenfehler.
- Rückweg: die vier Commits `70d507b..c32bd96` per `git revert` zurücknehmen (kein Force-Push); Sicherung `backup/master-vor-noir`.

## [alfred-dev] – 28.11.2026 – Redesign Variante A „Noir“: Lagezentrale + PROJECT CHRONOS
- Auswahl des Eigentümers aus drei Prototypen (`docs/proto/alfred-design.html`): Variante A „Noir“.
- Neu `docs/globe3d.js` (`window.TB_globe`): Globus-Renderer mit d3-geo auf Canvas (keine neue Bibliothek) – Sternenhimmel,
  Atmosphärenleuchten, leuchtende Grenzen, Koordinatennetz, Kamerafahrten, Ziehen zum Drehen, Länderauswahl; zeichnet nur bei Bedarf,
  Eigendrehung nur ohne reduzierte Bewegung und bei sichtbarem Tab.
- Camera Wall: Noir-Kacheln (goldene/grüne Eckrahmen), neue bildschirmfüllende **Lagezentrale „GLOBAL INTELLIGENCE NETWORK“**
  (Knopf „⛶ LAGEZENTRALE“ im Reiter LAGEBILD): Land oder Weltübersicht, große Kacheln, Mini-Globus mit Quellen, ALFRED-Lage, Regeln,
  Vollbild für Wand und Einzelquelle. Gleiche Regeln: Laden nur nach Zustimmung, Konfliktfilter, Aufräumen beim Schließen (Esc).
- **PROJECT CHRONOS** (`docs/chronos.js`) ersetzt die frühere Doomsday-Cartoon-Animation: DOOMSDAY schaltet die Kartenlage wie bisher ein
  und öffnet CHRONOS. Zeitachse 2026–2050 mit Abspielen/Pause/Neustart/1×–4×, Reiter Geopolitik/Wirtschaft/Klima, ALFRED-Analysefenster.
  Nur belegte Daten: IMF WEO bis zum letzten Datenjahr (2030), danach ausdrücklich keine Werte; Geopolitik nur heutiger Stand;
  Klima „nicht konfiguriert“. IMF-Ländergruppen werden nicht als Länder gezählt. Das frühere Szenariomodell wird in CHRONOS nicht verwendet.
- Tests: `tests/chronos.test.js` (6 Prüfungen). Playwright: CHRONOS (Bedienung, Regler, Jahr ohne Daten, Länderklick, Esc),
  Lagezentrale (Land/Welt, Zustimmung, Aufräumen), Handy 390 px; keine neuen Konsolenfehler.
  Bei der Prüfung behoben: Ländergruppen in der Statistik, Jahresregler setzte zurück, Indikator-Auswahl in Geopolitik sichtbar, Handy-Layout.

## [master] – 28.11.2026 – PROJECT A.L.F.R.E.D. live
- Merge `alfred-dev` → master (`70d6711`) mit Freigabe; Sicherung `backup/master-vor-alfred` (`5ce4046`); kein Force-Push.
- Vor dem Push: 26 Tests grün, keine Konflikte, keine Datendateien verändert, keine Geheimnisse gefunden.
- GitHub Pages gebaut 13:16 UTC. Live-Prüfung (Playwright, echte Adresse): alle Module, ⌘K, ALFRED, LAGEBILD (lädt nichts ohne Zustimmung),
  Risk Layer (USGS + NASA LIVE, 86 Ereignisse), nur bekannter Favicon-Fehler.
- Bot-Lauf 46148816499 (manuell, scan): erfolgreich; Actions per SHA, Pakete exakt gepinnt (yfinance 1.7.0, pandas 3.1.1, numpy 2.5.5,
  requests 2.34.2, anthropic 2.4.0); **S1-Bereinigung bestätigt** – keine `depot:`-Einträge mehr in `state/signals.json`.
  Bekannter, älterer Fehler unverändert: Wikidata-Ausweichabfrage gelegentlich 504 (abgefangen).
- Beobachtung: GitHub löst die geplanten Läufe am 28.11. sehr unregelmäßig aus (unabhängig von dieser Übernahme).

## [alfred-dev] – 28.11.2026 – P4: Global Risk Layer
- Neu `docs/risklayer.js` (`window.TB_risklayer`): einheitliche Anbieter-Schnittstelle und Ereignisformat laut PROJECT_ALFRED.md.
  Quellen nach Lizenz-/CORS-Prüfung: USGS Erdbeben M4.5+ (7 Tage, gemeinfrei) und NASA EONET v3 (offene Naturereignisse). Kein Schlüssel, keine Kosten.
- Weltkarte/Globus: Schalter „◎ RISK LAYER“ (Standard aus, Wahl wird gemerkt; vorher kein Abruf), Marker mit Form + Farbe je Typ
  (Farben validiert), Größe = Schwere 0–4, Tooltip, Infofenster mit Quelle/Status, Legende mit Quellen-Status LIVE/OFFLINE, Ereignisliste.
  Abruf alle 10/30 Min. nur bei sichtbarem Tab.
- `index.html`: allgemeine Schnittstelle für Zusatzebenen (`TB_map.overlay/redraw/info/showTip`); bestehende Ebenen unverändert.
- ALFRED LAGE: stärkste Naturereignisse, wenn die Ebene an ist.
- Tests: `tests/risklayer.test.js` (5 Prüfungen mit Beispielantworten im Originalformat). Playwright mit Live-Daten: 76 Erdbeben + 9 Waldbrände,
  Karte und Globus, gemeinsam mit Doomsday; dabei Startreihenfolge-Fehler gefunden und behoben.

## [alfred-dev] – 28.11.2026 – P4: Portfolio Risk Center
- Neu `docs/risk.js` (`window.TB_risk`): Risiko-Auswertung des Browser-Depots aus vorhandenen Daten (profiles.js, data.js, world.js).
  Kennzahlen 12 Monate: Volatilität, Max. Drawdown, Rendite, Sharpe (ohne risikofreien Zins), Value at Risk 95 % (historisch, 1 Tag),
  Beta/Korrelation zu DAX und S&P 500, Konzentration (größte Position, Top 3, effektive Anzahl), Struktur nach Branche/Land/Währung,
  Einzelwerte, Korrelations-Heatmap, Faustregel-Hinweise mit festen Schwellen, Lage-Verknüpfung (Sitzland auf Konfliktliste).
- Methode sichtbar gekennzeichnet: Rückrechnung mit heutigen Stückzahlen × damaligem Kurs × heutigem Wechselkurs;
  fehlende Kurs-/Wechselkursdaten werden ausgewiesen, nie geschätzt. Alles nur im Browser.
- Depot-Block: einklappbares „// Portfolio Risk Center“ (rechnet erst beim Öffnen, aktualisiert bei Depot-Änderung).
- ALFRED: neuer Reiter DEPOT (Kurzfassung) und Befehl „Portfolio Risk Center öffnen“.
- Tests: `tests/risk.test.js` (9 Prüfungen mit festen Beispieldaten, `node --test tests/`). Playwright mit Testdepot, Handy ohne Querscrollen.

## [alfred-dev] – 28.11.2026 – P4: Camera Wall eingebunden
- `docs/cameras.js` wird aus dem freigegebenen Katalog erzeugt (`catalog/build_cameras.py`): 58 Quellen, 28 Länder,
  Kennzeichnung staatsnaher Sender, Quellenangaben (NASA, EUMETSAT, NOAA, JMA, HKO), SkylineWebcams als Vorschau mit Link.
- `camwall.js`: Vorlagen `{YYYY-MM-DD}` (NASA GIBS, Vortag UTC) und `{HHMM}` (JMA Himawari), Status ehrlich:
  Bilder mit berechnetem Zeitpunkt/Verzögerung = DELAYED, nicht abrufbar = OFFLINE, YouTube = STAND UNBEKANNT
  (Livestatus ohne Player-API nicht feststellbar). Sortierung Nachrichten → Wetter → Satellit → Panorama.
- YouTube-Einbettung mit `referrerpolicy="strict-origin"` (nur Herkunft, kein Pfad) – YouTube verweigert sonst die Wiedergabe;
  alle anderen Quellen weiter ohne Referrer.
- Neu: `tests/test_camera_catalog.py` (7 Regelprüfungen, offline). Prüfung mit Playwright: siehe TEST_PLAN.md.

## [alfred-dev] – 28.11.2026 – Quellenkatalog freigegeben, Konfliktregel
- Quellenrecherche Camera Wall: 58 Einträge aus 28 Ländern (27 Nachrichten, 14 zeitversetzt/Satellit, 10 Panorama, 7 Wetter),
  Ausschlussliste mit Gründen. Vom Eigentümer freigegeben (alle vier Gruppen, mit Auflagen) → `catalog/kamera_katalog_2026-11-28.{json,md}`.
- `camwall.js`: Konfliktgebiet = feste Liste `konfliktzonen` (`cameras.js`, inkl. VAE vorsorglich) oder WarMap-Hotspot ≥ 3;
  Schlagzeilen-Eskalationsstufe entscheidet nicht mehr (USA/China nicht mehr fälschlich als Konfliktgebiet). Mit Playwright geprüft.
- Katalog-Einträge selbst noch nicht in `docs/cameras.js` (folgt mit P4).

## [alfred-dev] – 28.11.2026 – P1 abgeschlossen, P2 umgesetzt
**P1**
- `requirements.txt`: exakt die heute laufenden Versionen gepinnt (yfinance 1.7.0, pandas 3.1.1, numpy 2.5.5, requests 2.34.2, anthropic 2.4.0).
- Workflows: `actions/checkout` und `actions/setup-python` auf Commit-SHA gepinnt (v4/v5, Kommentar mit Tag).
**P2 – Design**
- Taktische Eckmarken (oben rechts/unten links) an allen Blöcken, Hover-Rahmen, `tabular-nums` für Zahlen.
- Kopfzeile: „◆ WAYNE INTELLIGENCE · A.L.F.R.E.D.“ (klein, `--muted`) und goldener Knopf „◆ ALFRED ⌘K“.
- Status-Pillen (LIVE · BOT-STAND/DELAYED · VERALTET/OFFLINE · NICHT KONFIGURIERT/UNAVAILABLE), Radar-Strich (aus bei reduzierter Bewegung).
**P2 – ALFRED** (`docs/alfred.js`)
- Terminal-Fenster mit Begrüßung „Master Wayne“, Reitern LAGE · MARKT · SYSTEM · MELDUNGEN; nur vorhandene Daten mit Quelle und Stand.
- Systemstatus je Datendatei (BOT-STAND/VERALTET), Funktionen sichtbar als „nicht konfiguriert“ (Spracheingabe, KI-Dialog, Lagebild-Quellen).
- Sprachausgabe vorbereitet (Standard aus). Befehlsliste ⌘K/Strg+K: ALFRED, Bereiche, Doomsday, Suche, Ansicht, Länder, Lagebild je Land.
**P2 – Country Intelligence** (`docs/camwall.js`, `docs/cameras.js`)
- Reiter LAGEBILD im Länderfenster, Verweis aus dem WarMap-Hotspot-Fenster; Raster 1/2/2×2, Vollbild, Status-Pillen, Leerzustand UNAVAILABLE.
- Lädt nichts ohne Zustimmung; entfernt Einbettungen bei Schließen/Reiter-/Länderwechsel; Konfliktgebiete nur Nachrichten/zeitversetzt.
- Quellenkatalog leer (Freigabe in P4) → überall „UNAVAILABLE – Quellenkatalog noch nicht freigegeben“.
- `index.html`: kleine Schnittstelle `window.TB_map` (Land öffnen, Namen); bestehende Funktionen unverändert.
**Prüfung** (Playwright + Chrome DevTools, lokaler Server, siehe TEST_PLAN.md): keine neuen Konsolenfehler, Bildrate unverändert,
Lade-/Aufräumlogik mit Testeinträgen bestätigt, Doomsday/Hotspots/Suche/Depot/Charts funktionieren, Handy ohne Querscrollen.
Behoben während der Prüfung: Begrüßung nach Uhrzeit (Formatfehler), Raster 2×2 bei 3 Quellen, Fensterbreite für mehrere Kacheln.

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
