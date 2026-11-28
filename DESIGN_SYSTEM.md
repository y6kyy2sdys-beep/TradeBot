# DESIGN_SYSTEM.md – Matrix × Batcomputer

**Gewichtung:** 80 % bestehendes Matrix-Design · 15 % Batcomputer · 5 % Wayne-Eleganz.
Sicherung des heutigen Designs: Branch `backup/design-matrix-v1` (Stand vor allen ALFRED-Änderungen).

## Bestand (bleibt unverändert)
| Token | Wert | Verwendung |
|---|---|---|
| `--bg` | `#000300` | Hintergrund |
| `--panel` | `rgba(3,14,7,.86)` | Blöcke |
| `--matrix` | `#00ff41` | Akzent, Überschriften, aktive Elemente |
| `--text` / `--muted` | `#c9f7d3` / `#6fa77b` | Text |
| `--up` / `--down` / `--warn` | `#2bd45a` / `#ff5c5c` / `#fab219` | Bewegung, Warnung |
| `--s1 … --s8` | validierte Kategorien-Palette | Chartserien (feste Reihenfolge) |
| Schrift | Share Tech Mono | überall |
| Rahmen | 1 px `--line`, Eck-Winkel oben links/unten rechts | Blöcke |
| Bewegung | Matrix-Regen (abschaltbar), Intro, Ticker | `prefers-reduced-motion` wird beachtet |

## Ergänzungen (Vorschlag Phase 2 – noch nicht umgesetzt)
| Element | Regel |
|---|---|
| Gold-Akzent | neues Token `--gold: #c9a227` – **nur** für besondere Informationen (Depot-Summe, ALFRED-Kopf, kritische Hinweise). Max. 1–2 Stellen je Bildschirm. |
| Taktische Rahmen | Eckwinkel zusätzlich unten links/oben rechts als 6-px-Ticks, `--line-strong`; keine neuen Farben |
| Statusanzeigen | einheitliche „Status-Pille“: Punkt + Kurztext (LIVE · BOT-STAND · VERALTET · NICHT KONFIGURIERT) mit festen Farben grün/gelb/rot/grau |
| Radar/Scan | nur im Globus-Kopf und ALFRED-Kopf: dünner rotierender Strich, 6 s/Umdrehung, aus bei reduzierter Bewegung |
| Typografie | Überschriften wie bisher; Zahlen `font-variant-numeric: tabular-nums`; Labels in Versalien, Laufweite .12em |
| Icons | ein Satz einfacher Unicode/SVG-Linien-Icons, 1,5 px Strich, Farbe `currentColor`; keine Emoji-Mischung in neuen Elementen |
| Hover | Rahmen von `--line` → `--line-strong`, keine Größenänderung, 120 ms |
| Infofenster | max. 360 px breit, Kopfzeile mit Quelle + Zeitstempel, Schließen-Knopf rechts, Esc schließt |
| Abstände | 4-px-Raster: 4 / 8 / 12 / 16 / 24 |
| Branding | optional „WAYNE INTELLIGENCE · A.L.F.R.E.D.“ in `--muted`, klein, nur im Kopf; keine Batman-Logos |

## Country Intelligence – Reiter LAGEBILD (verbindlich, ab P2)
| Element | Regel |
|---|---|
| Reiter | dritter Reiter „LAGEBILD“ im bestehenden Länderfenster, gleiche Reiter-Optik wie ÜBERBLICK/DETAILS |
| Raster | Umschalter 1 · 2 · 2×2 (Standard 1); Kacheln 16:9; Abstand 8 px; Handy (< 600 px) immer einspaltig |
| Kachel | Rahmen 1 px `--line`, Eckwinkel wie Blöcke; Hintergrund `#000` (kein neues Panel-Grün); keine Überblendungen über dem Bild |
| Kachelkopf | links Betreiber + Art in Versalien (`--muted`), rechts Status-Pille; zweite Zeile „Stand HH:MM“ bzw. „Stand unbekannt“ |
| Kachelfuß | Links „QUELLE ↗“ und „LIZENZ ↗“ in `--muted`; Hinweis bei Konfliktzone: „Redaktionelles/zeitversetztes Lagebild“ |
| Status-Pillen | Punkt + Text, Versalien: **LIVE** `--matrix` · **DELAYED** `--warn` · **OFFLINE** `--down` · **UNAVAILABLE** `--muted`; statisch, kein Blinken |
| Vollbild | Knopf „⛶“ oben rechts in der Kachel; im Vollbild bleibt die Kopfzeile sichtbar; Esc beendet |
| Leerzustand | Rahmen gestrichelt `--line`, Text „Keine geprüfte öffentliche Quelle für {Land}“ + Grund, Status UNAVAILABLE |
| Ladehinweis | vor dem ersten Laden: „Beim Öffnen werden Daten an den Betreiber übertragen“, Knopf „LAGEBILD LADEN“ |
| Wayne-Anteil | kein Gold in Kacheln; optional ein kleiner Radar-Strich im Reiterkopf (aus bei reduzierter Bewegung) |

## Redesign Variante A „Noir“ (gewählt am 28.11.2026)
| Element | Regel |
|---|---|
| Vollbild-Ansichten (Lagezentrale, CHRONOS) | Hintergrund `#000`, Sternenhimmel nur in CHRONOS/Globus; Titel mit großer Laufweite, Lagezentrale gold, CHRONOS grün |
| Eckrahmen | oben links gold (2 px), unten rechts Matrix-Grün (2 px) – Kacheln, ALFRED-Fenster, Panels |
| Globus | d3-geo orthografisch auf Canvas; Atmosphärenleuchten grün, Grenzen leuchtend `rgba(0,255,65,.55)`, Auswahl gold; Licht von oben links rein gestalterisch |
| Datenfarben | unverändert die validierten Skalen der Weltkarte (Wachstum divergierend, Inflation sequenziell, Eskalation ordinal) |
| Zeitachse | Band „IMF-Daten“ grün, Jahre ohne Daten schraffiert + Text; Knopf grün; Tastatur ← → Leertaste Esc |
| Bewegung | Kamerafahrten 1,3–2,2 s ease-in-out; Eigendrehung ≤ 30 Bilder/s; bei reduzierter Bewegung keine Drehung/Fahrt |

## Verboten
Comic-Elemente, Fledermaus-Symbole, zusätzliche Dauer-Animationen, neue Hintergrundfarben, Glassmorphism-Effekte,
Schriftwechsel im Fließtext.
