# ROADMAP.md – Phasen (jede Phase nur nach ausdrücklicher Freigabe)

| Phase | Inhalt | Status |
|---|---|---|
| 0 | Repository-Analyse, Funktionen, Architektur, Datenquellen, Risiken | ✔ erledigt (24.11.2026) |
| 1 | Dokumentation, ALFRED-Konzept und -Architektur | ✔ erledigt (24.11.2026), Branch `alfred-dev` |
| **S** | **Sicherheits-Sofortmaßnahme S1** (Depot-Hashes salzen, öffentliche Einträge entfernen) | ✔ umgesetzt auf `alfred-dev` (27.11.2026) – wartet auf Merge nach master; Git-Historie offen |
| 2 | Designentwurf Matrix × Batcomputer (nur Tokens/Rahmen/Status-Pillen, siehe DESIGN_SYSTEM.md) | ⏳ Freigabe |
| 3 | Flugroute im bestehenden Globus | ⏳ Freigabe |
| 4 | Global-Risk-Ebenen, Camera Wall, Portfolio Risk Center (Architektur + Module mit vorhandenen Daten) | ⏳ Freigabe |
| 5 | Installationsanleitung umsetzen (Werkzeuge auf dem Mac, durch den Nutzer) | Anleitung liegt vor |

## Phase 3 – Plan Flugroute (Kurzfassung)
1. **Recherche** (ohne Code): adsb.lol-Endpunkte für Positionshistorie und Routen, CORS, Lizenz/AGB, Abdeckung bei Militärflügen.
2. **Sitzungs-Spur** (sicher umsetzbar): Bei jedem Live-Abruf (60 s) Position je ICAO-Adresse in einem Ringpuffer
   (max. ~120 Punkte, nur im Arbeitsspeicher/optional sessionStorage) speichern → echte, selbst aufgezeichnete Spur.
3. **Darstellung** im bestehenden SVG-Globus: aufgezeichnete Spur als durchgezogene grüne Großkreis-Linie
   (`d3.geoPath` mit `LineString` → Erdkrümmung und 180°-Übergang werden von d3 korrekt behandelt);
   geschätzte Weiterführung nur gestrichelt und beschriftet „geschätzt (Kurs × Tempo)“; Flughäfen nur, wenn eine Quelle sie liefert.
4. **Infofenster** ergänzen: Datenstand, verbleibende Strecke/ETA **nur** bei bekanntem Ziel – sonst „nicht verfügbar“.
5. Schalter: Folgen, Zentrieren, Route ein/aus, Auswahl aufheben (Esc).

## Kleine Optimierungen (Vorschläge, je einzeln freizugeben)
- Globus: Flugzeug-Marker bei > 300 Objekten bündeln oder auf Canvas zeichnen (SVG mit 800 Knoten bremst beim Drehen).
- Globus: Neuberechnung der Pfade während des Ziehens drosseln (requestAnimationFrame), 50m-Grenzen erst ab Zoom > 2.
- Live-Abrufe (adsb.lol, onvista) pausieren, wenn der Tab im Hintergrund ist (teilweise schon umgesetzt) und bei Fehlern exponentiell zurückfahren.
- `requirements.txt` und Actions-Versionen pinnen (SECURITY.md S3).
- Google-Schrift lokal ausliefern (SECURITY.md S4).
- `profiles.js` (1,4 MB) und `news.js` erst bei Bedarf laden (heute schon teilweise lazy).
