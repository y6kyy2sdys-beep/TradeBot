# DESIGN_SYSTEM.md – Matrix × Batcomputer

**Gewichtung:** 80 % bestehendes Matrix-Design · 15 % Batcomputer · 5 % Wayne-Eleganz.
Sicherung des heutigen Designs: Git-Tag `design-matrix-v1` (Stand vor allen ALFRED-Änderungen).

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

## Verboten
Comic-Elemente, Fledermaus-Symbole, zusätzliche Dauer-Animationen, neue Hintergrundfarben, Glassmorphism-Effekte,
Schriftwechsel im Fließtext.
