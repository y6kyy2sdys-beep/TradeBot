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
- **Global Risk Layer** mit einheitlicher Anbieter-Schnittstelle (Phase 4):
  `{ id, name, source, license, needsKey, refreshSec, fetch(), toEvents() }` →
  Ereignis `{ id, type, lat, lon, time, severity 0–4, title, source, url, fetchedAt, confidence: fact|possible|forecast }`.
- **Camera Wall** (Phase 4): nur offiziell einbettbare Quellen, Laden erst beim Öffnen, Kennzeichnung Live/Standbild/Zeitraffer,
  keine Gesichtserkennung, keine Personenverfolgung.
- **Portfolio Risk Center** (Phase 4): Konzentration, Branchen/Länder/Währungen, Volatilität, Max Drawdown,
  Korrelationen, Sharpe, Benchmark, Verknüpfung mit Lage-Ereignissen – nur aus vorhandenen Kursdaten.
