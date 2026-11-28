# PROJECT A.L.F.R.E.D.
**Advanced Logistics, Financial Research & Event Detection** – TradeBot · Wayne Intelligence Command Center

## Vision
Eine glaubwürdige persönliche Intelligence-Kommandozentrale: das bestehende Matrix-Dashboard, behutsam
ergänzt um einen Assistenten (ALFRED), präzisere Lagebilder und Risiko-Module. Keine Comic-Fanseite,
kein Neubau. Gewichtung im Design: 80 % Matrix · 15 % Batcomputer · 5 % Wayne-Eleganz (siehe DESIGN_SYSTEM.md).

## ALFRED – Zielbild der Schnittstelle (Phase 1: nur Konzept, noch kein Code)
ALFRED spricht den Nutzer mit „Master Wayne“ an und arbeitet zunächst **ohne kostenpflichtige KI**
ausschließlich mit Daten, die das Dashboard bereits geladen hat.

| Funktion | Datenbasis heute | Status nach erster Umsetzung |
|---|---|---|
| Persönliche Begrüßung | Uhrzeit, Datenstand (`DASH.generated`) | umsetzbar |
| Marktbericht | `DASH.series` (Indizes, Rohstoffe), `DASH.regime`, Hot-Picks | umsetzbar |
| Globale Lage | `WORLD.escalation`, `DOOM.hotspots`, KI-`lagebild` (falls vorhanden) | umsetzbar |
| Portfolio-Risikobericht | Browser-Depot + `PROFILES` (Kurse 2 J., Volatilität, Branche, Land) | umsetzbar (Grundkennzahlen) |
| Systemstatus | Alter jeder Datendatei, Live-Status Flugzeuge/onvista, Token konfiguriert? | umsetzbar |
| Benachrichtigungszentrale | `DASH.alerts` (Alarm-Protokoll) | umsetzbar (nur Anzeige) |
| Command Palette | Tastenkürzel (z. B. ⌘K/Strg+K): Wert öffnen, Bereich springen, Doomsday, Aktualisieren | umsetzbar |
| Sprachausgabe | Web Speech API (`speechSynthesis`, im Browser, kostenlos) | vorbereitet, Standard **aus** |
| Spracheingabe | Web Speech API (`SpeechRecognition`) – in Safari/Chrome unterschiedlich, Mikrofon-Freigabe | **nicht konfiguriert** |
| KI-Dialog | würde API-Schlüssel + Server benötigen (Pages kann keine Schlüssel schützen) | **nicht konfiguriert** |

Regeln: Nicht verfügbare Funktionen erscheinen sichtbar als „nicht konfiguriert“. ALFRED erfindet keine
Zahlen, zitiert Quelle und Stand jedes Werts und unterscheidet Fakten, Zusammenhänge, Prognosen und Unsicherheit.

### Architektur-Vorschlag (minimalinvasiv)
Ein zusätzliches Modul `(function alfred() { … })()` am Ende der bestehenden IIFE in `docs/index.html`
(oder als `docs/alfred.js`, das auf eine kleine öffentliche Schnittstelle `window.TB` zugreift):

```
ALFRED
 ├─ reports: { greeting(), market(), world(), portfolio(), system() }   // reine Funktionen über vorhandene Daten
 ├─ notify:  Liste aus DASH.alerts + Browser-Ereignissen (Depot-Warnungen)
 ├─ palette: Befehlsliste [{ id, label, run() }], Tastenkürzel
 ├─ voice:   { speak(text) – optional, aus; listen() – nicht konfiguriert }
 └─ ui:      kompaktes Terminal-Fenster im Matrix-Stil, einklappbar
```

## Weitere Module (nur Planung, siehe ROADMAP.md)
- **Flugroute** auf dem bestehenden Globus (Phase 3).
- **Global Risk Layer** – umgesetzt auf `alfred-dev` (28.11.2026, `docs/risklayer.js`): USGS-Erdbeben + NASA EONET, Schalter „◎ RISK LAYER“,
  lädt erst beim Einschalten; Schwere 0–4 nach festen, im Code dokumentierten Regeln (keine amtliche Warnstufe). Schnittstelle (Phase 4):
  `{ id, name, source, license, needsKey, refreshSec, fetch(), toEvents() }` →
  Ereignis `{ id, type, lat, lon, time, severity 0–4, title, source, url, fetchedAt, confidence: fact|possible|forecast }`.
- **Country Intelligence & Camera Wall** (UI-Gerüst P2, Integration P4) – verbindliche Anforderungen im eigenen Abschnitt unten.
- **Portfolio Risk Center** (Phase 4): Konzentration, Branchen/Länder/Währungen, Volatilität, Max Drawdown,
  Korrelationen, Sharpe, Benchmark, Verknüpfung mit Lage-Ereignissen – nur aus vorhandenen Kursdaten.

## Country Intelligence & Camera Wall (verbindlich, Vorgabe vom 28.11.2026)
Die Kameras sind **kein separates Modul**, sondern Teil des bestehenden Globus und der WarMap.

### Einbindung
- **Länderfenster** `showCard(iso)` (`docs/index.html`, Reiter ÜBERBLICK · DETAILS) erhält einen dritten Reiter **LAGEBILD**.
  Das Hotspot-Fenster `showHotspot(h)` verweist auf den LAGEBILD-Reiter des betroffenen Landes. Alle bestehenden Inhalte bleiben unverändert.
- **Laden nur bei Bedarf:** Solange das Länderfenster geschlossen oder der Reiter LAGEBILD nicht aktiv ist, wird **nichts** geladen
  (kein iframe, kein Bild, keine Statusabfrage). Im Reiter erscheint zuerst der Datenschutz-Hinweis mit Knopf „LAGEBILD LADEN“;
  erst danach wird geladen (die Wahl kann für die Sitzung gemerkt werden). Beim Schließen, Reiter- oder Länderwechsel werden
  alle Einbettungen entfernt (Stream stoppt).
- **Kachel-Raster:** 1, 2 oder 2×2 Quellen nebeneinander (Auswahl durch den Nutzer, Standard 1), auf dem Handy untereinander.
- **Vollbild** für eine einzelne Kachel (Fullscreen API), Esc beendet.
- **Kachelkopf:** Betreiber/Quelle, Art (Nachrichten-Livestream · Panorama · Wetter · zivile Übersicht), Aktualität
  („Stand 14:05“ bzw. „Stand unbekannt“), Status-Pille, Link zur Originalquelle, Lizenz-/Nutzungshinweis.

### Status (feste Bedeutung)
| Status | Bedeutung |
|---|---|
| **LIVE** | Quelle sendet laut eigener Angabe (z. B. Player-Status) jetzt, ohne erklärte Verzögerung |
| **DELAYED** | Quelle sendet mit erklärter Verzögerung oder liefert Standbilder/Zeitraffer; Alter wird angezeigt |
| **OFFLINE** | Quelle ist eingetragen, sendet aber gerade nicht oder der Abruf schlägt fehl |
| **UNAVAILABLE** | Für das Land keine geprüfte Quelle, Einbettung nicht erlaubt, oder aus Sicherheitsgründen bewusst nicht angeboten |

Lässt sich der Status nicht ehrlich feststellen, wird „Stand unbekannt“ angezeigt – **nie** ein geratenes LIVE.
Ohne geeignete Quelle erscheint transparent: „Keine geprüfte öffentliche Quelle für {Land}“ mit Grund und Verweis auf die Nachrichtenlage.

### Quellenkatalog
- Statische, von Hand gepflegte Datei `docs/cameras.js` (`window.CAMS`), **keine automatische Suche, kein Scraping**.
- Pflichtfelder je Eintrag: `id, iso, ort (Stadt/Region), art, betreiber, embed {typ, url}, quelle_url, lizenz_url,
  einbettung_erlaubt (Beleg), verzoegerung_min, geprueft_am, konfliktzone_zulaessig`.
- Jeder neue Eintrag bzw. jede Katalog-Erweiterung braucht die **Freigabe des Eigentümers** (Liste mit Betreiber, Lizenz, Begründung).
- Optional (P4, Vorschlag): täglicher Bot-Lauf prüft Einträge über kostenlose, schlüsselfreie Wege (z. B. oEmbed, HTTP-Status)
  und schreibt Ergebnis + Zeitstempel in den Katalog. Keine kostenpflichtigen APIs (z. B. YouTube Data API) ohne Freigabe.

### Sicherheit und Datenschutz (Vorrang vor Funktionen)
- Ausschließlich öffentlich freigegebene, rechtmäßig einbettbare Quellen (offizieller Einbett-Code bzw. ausdrückliche Erlaubnis des Betreibers).
- **Aktive Konfliktgebiete** (feste Liste `konfliktzonen` in `docs/cameras.js` – UKR, RUS, ISR, PSE, LBN, SYR, YEM, SDN, IRN, SAU,
  ARE vorsorglich – oder WarMap-Hotspot ab Stufe 3; Entscheidung 28.11.2026, die Schlagzeilen-Zählung entscheidet nicht):
  nur redaktionelle Lagebilder etablierter Nachrichtenanbieter und
  **zeitversetzte** zivile Übersichtsaufnahmen. Behördliche Abschalt- oder Sendeverbote für Kameras werden respektiert.
- **Verboten:** Kameras auf militärische Stellungen, Truppenbewegungen, Schutzräume, Grenzübergänge oder andere sensible Einrichtungen;
  private Kameras; Gesichtserkennung, Kennzeichenerkennung, Personenverfolgung; Umgehung von Zugriffsbeschränkungen (Geoblocking,
  Anmeldung, Paywall, Hotlink-Schutz); Aufzeichnung oder Speicherung von Streams.
- Datenschutz: datensparsame Einbettung (z. B. `youtube-nocookie.com`), `referrerpolicy="no-referrer"` (Ausnahme YouTube:
  `strict-origin` – nur die Herkunft, weil YouTube sonst nicht abspielt), `sandbox` so eng wie möglich,
  Ton standardmäßig aus, kein Autoplay vor dem Öffnen des Reiters. Hinweis im Reiter, dass beim Öffnen Daten an den Betreiber gehen.
- Keine kostenpflichtigen Schnittstellen ohne Freigabe.

### Umsetzungsstufen
- **P2 (UI-Gerüst, ohne externe Inhalte):** Reiter LAGEBILD, Kachel-Raster, Kachelkopf, Status-Pillen, Vollbild-Knopf,
  UNAVAILABLE-Anzeige. Katalog leer → jedes Land zeigt UNAVAILABLE „Quellenkatalog noch nicht freigegeben“. Es wird nichts Externes geladen.
- **P4 (Integration auf `alfred-dev`):** Quellenrecherche und Freigabeliste, Katalog, Einbettung, Statuslogik, optionale Bot-Prüfung, Tests.
- **Stand 28.11.2026:** UI-Gerüst umgesetzt (P2). Quellenkatalog recherchiert und **freigegeben** (58 Einträge, 28 Länder,
  `catalog/kamera_katalog_2026-11-28.md` mit Auflagen je Gruppe). Übernahme in `docs/cameras.js` folgt mit P4.

## PROJECT CHRONOS (umgesetzt 28.11.2026, `alfred-dev`)
Ersetzt die frühere Doomsday-Animation. Verbindlich: keine erfundenen Daten, Prognosen oder Eintrittswahrscheinlichkeiten.
- Wirtschaft: IMF World Economic Outlook (Ist + IMF-Prognose) bis zum letzten Datenjahr – danach keine Werte, sichtbar gekennzeichnet.
- Geopolitik: nur heutiger Stand (Schlagzeilen-Zählung, Krisenregionen 48 h), keine Fortschreibung.
- Klima: nicht konfiguriert; mögliche Quellen (IPCC AR6, World Bank CCKP) erst nach Lizenz-/Abrufprüfung, dann als Projektion Dritter gekennzeichnet.
- Das Szenariomodell der Weltkarte ist seit 28.11.2026 als „⚠ SZENARIO-SPIEL (FIKTION)“ abgetrennt (Standard aus, Warnbanner, beginnt erst
  nach den IMF-Daten, keine Abschläge auf IMF-Jahre) und wird von CHRONOS und ALFRED nicht verwendet.
