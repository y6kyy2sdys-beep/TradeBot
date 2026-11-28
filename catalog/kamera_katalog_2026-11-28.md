# Quellenkatalog „Country Intelligence & Camera Wall“

Stand: 2026-11-28 · Status: **vom Eigentümer freigegeben am 28.11.2026** (Einbindung in Phase 4 auf `alfred-dev`)

## Freigabe-Entscheidungen (28.11.2026)
| Gruppe | Einträge | Entscheidung | Auflage |
|---|---|---|---|
| Satellit + Wetter (NASA GIBS, NOAA GOES, EUMETSAT, JMA, HKO, Weathernews) | 21 | freigegeben | Quellen-/Lizenzhinweis in der Kachel (NASA-Attribution, „© EUMETSAT 2026“, HKO-Hinweistext) |
| Unabhängige Nachrichten (DW, phoenix, France 24, Euronews, NHK, ABC, CBC, Sky News, Bloomberg, CNA, ANN, YTN, TVBS, NDTV, WION, CNN Brasil, NTN24, TSN) | 20 | freigegeben | – |
| Staatsnahe Sender (CGTN, TRT World, Al Jazeera EN/AR, Al Arabiya, Sky News Arabia, Iran International) | 7 | freigegeben | in der Kachel als „staatsnah“ bzw. „Exilsender“ kennzeichnen |
| SkylineWebcams-Panoramen | 10 | freigegeben | nur unveränderter Original-Embed (Vorschaubild mit Link und Logo, kein Beschnitt); Hinweis „Vorschau, kein Live-Player“ |
| Konfliktgebiete | – | feste Liste + WarMap-Hotspot ≥ 3 | Liste: UKR, RUS, ISR, PSE, LBN, SYR, YEM, SDN, IRN, SAU, **ARE (vorsorglich)**; Schlagzeilen-Zählung entscheidet nicht |

Hinweis: Freigabe gilt für die geprüfte Fassung vom 28.11.2026. Neue Quellen brauchen erneut eine Freigabe;
Einträge, die bei der späteren Prüfung nicht mehr einbettbar sind, werden als OFFLINE/UNAVAILABLE gezeigt, nicht ersetzt.
Maschinenlesbare Fassung: `katalog_entwurf.json` (58 Einträge)

| Art | Anzahl |
|---|---|
| nachrichten | 27 |
| zeitversetzt | 14 |
| panorama | 10 |
| wetter | 7 |

## Methodik (5 Zeilen)
1. YouTube: Kanal-ID aus der offiziellen Kanalseite (`externalId`) gelesen, dann `/channel/<ID>/live` abgerufen und `isLiveContent` + `playableInEmbed=true` des aktuellen Live-Videos geprüft; Embed als `youtube-nocookie.com/embed/live_stream?channel=<ID>`.
2. Panorama: Nutzungsbedingungen der Anbieter gelesen (SkylineWebcams: Einbettung nur über unveränderten „Embed“-Code; EarthCam: nur mit Lizenz); Embed-IDs aus den Kameraseiten gelesen, Vorschaubilder teilweise gesichtet.
3. Wetter/Satellit: Lizenzseiten der Behörden (HKO, JMA, EUMETSAT, NASA Earthdata) gelesen; jede Bild-/WMS-URL per HTTP-Abruf auf 200 + Bildtyp geprüft, Verzögerung per Zeitstempel/Last-Modified als Stichprobe geschätzt.
4. Ausschlussregeln strikt angewendet: in Konfliktzonen (UKR, RUS, ISR/PSE, LBN, YEM, SDN, zusätzlich IRN/SAU wegen aktueller Lage) nur Nachrichten und Satellitenübersicht; keine Straßen-, Hafen-, Grenz-, Flughafen-Nahsicht.
5. Nicht Belegtes steht als `null` bzw. im Abschnitt „Offene Punkte“; Vertrauen „hoch“ nur bei direkter technischer Prüfung **und** gelesener Erlaubnis.

## Übersicht je Land

Legende: Verz. = `verzoegerung_min` (0 = live, — = unbekannt/null)

### Krisenregionen

| ISO | id | Art | Betreiber | Embed | Verz. | Vertrauen |
|---|---|---|---|---|---|---|
| UKR | ukr-tsn | nachrichten | TSN / 1+1 Media | youtube | 0 | mittel |
| UKR | ukr-gibs | zeitversetzt | NASA GIBS (VIIRS NOAA-20) | bild | — | hoch |
| UKR | ukr-eumetsat | zeitversetzt | EUMETSAT MTG GeoColour | bild | 40 | mittel |
| RUS | rus-gibs-west | zeitversetzt | NASA GIBS | bild | — | mittel |
| ISR | isr-gibs | zeitversetzt | NASA GIBS | bild | — | mittel |
| ISR | isr-eumetsat-levante | zeitversetzt | EUMETSAT MTG GeoColour | bild | 40 | mittel |
| PSE | pse-gibs | zeitversetzt | NASA GIBS (gleicher Ausschnitt wie ISR) | bild | — | mittel |
| LBN | lbn-gibs | zeitversetzt | NASA GIBS | bild | — | mittel |
| IRN | irn-iran-international | nachrichten | Iran International (Exil, London) | youtube | 0 | mittel |
| IRN | irn-gibs | zeitversetzt | NASA GIBS | bild | — | mittel |
| YEM | yem-gibs-rotes-meer | zeitversetzt | NASA GIBS (Jemen/Rotes Meer) | bild | — | hoch |
| TWN | twn-tvbs | nachrichten | TVBS | youtube | 0 | mittel |
| TWN | twn-gibs-strasse | zeitversetzt | NASA GIBS (Taiwanstraße) | bild | — | hoch |
| SDN | sdn-gibs | zeitversetzt | NASA GIBS | bild | — | mittel |
| VEN | ven-ntn24 | nachrichten | NTN24 (Sitz Bogotá) | youtube | 0 | mittel |
| VEN | ven-gibs | zeitversetzt | NASA GIBS | bild | — | hoch |
| VEN | ven-goes-nsa | zeitversetzt | NOAA STAR GOES-19 | bild | — | mittel |
| QAT* | qat-aljazeera-en | nachrichten | Al Jazeera English | youtube | 0 | hoch |
| QAT* | qat-aljazeera-ar | nachrichten | Al Jazeera Arabic | youtube | 0 | hoch |
| TUR* | tur-trt-world | nachrichten | TRT World | youtube | 0 | mittel |

\* Nicht auf der Schwerpunktliste, aber als regionale Nachrichtenquelle für Nahost/Sudan/Jemen aufgenommen (dort gibt es keinen geprüften lokalen Stream).

### Finanz- und Rohstoffländer

| ISO | id | Art | Betreiber | Embed | Verz. | Vertrauen |
|---|---|---|---|---|---|---|
| USA | usa-abc-news-live | nachrichten | ABC News Live | youtube | 0 | hoch |
| USA | usa-bloomberg-tv | nachrichten | Bloomberg Television | youtube | 0 | hoch |
| USA | usa-boston-panorama | panorama | SkylineWebcams | bild | — | hoch |
| USA | usa-goes-conus | wetter | NOAA STAR GOES-19 | bild | — | mittel |
| DEU | deu-dw-news | nachrichten | Deutsche Welle | youtube | 0 | hoch |
| DEU | deu-phoenix | nachrichten | phoenix (ARD/ZDF) | youtube | 0 | mittel |
| DEU | deu-koeln-rhein | panorama | SkylineWebcams (Rheinufer) | bild | — | mittel |
| DEU | deu-eumetsat-mitteleuropa | wetter | EUMETSAT MTG GeoColour | bild | 40 | mittel |
| GBR | gbr-sky-news | nachrichten | Sky News | youtube | 0 | mittel |
| GBR | gbr-st-ives-coast | panorama | SkylineWebcams | bild | — | niedrig |
| FRA | fra-france24-en | nachrichten | France 24 English | youtube | 0 | hoch |
| FRA | fra-france24-ar | nachrichten | France 24 Arabic | youtube | 0 | hoch |
| FRA | fra-euronews-en | nachrichten | Euronews English | youtube | 0 | mittel |
| FRA | fra-paris-skyline | panorama | SkylineWebcams | bild | — | hoch |
| JPN | jpn-nhk-world | nachrichten | NHK WORLD-JAPAN | youtube | 0 | hoch |
| JPN | jpn-ann-news | nachrichten | TV Asahi / ANN | youtube | 0 | mittel |
| JPN | jpn-weathernews-live | wetter | Weathernews | youtube | 0 | hoch |
| JPN | jpn-jma-himawari | wetter | JMA Himawari | bild | 15 | mittel |
| CHN | chn-cgtn | nachrichten | CGTN (staatlich) | youtube | 0 | mittel |
| CHN | chn-shanghai-skyline | panorama | SkylineWebcams | bild | — | hoch |
| HKG | hkg-hko-central-pier | wetter | Hong Kong Observatory | bild | 10 | mittel |
| HKG | hkg-hko-icc | wetter | Hong Kong Observatory | bild | — | mittel |
| SAU | sau-al-arabiya | nachrichten | Al Arabiya | youtube | 0 | mittel |
| SAU | sau-gibs | zeitversetzt | NASA GIBS | bild | — | mittel |
| ARE | are-sky-news-arabia | nachrichten | Sky News Arabia | youtube | 0 | hoch |
| CHE | che-interlaken | panorama | SkylineWebcams | bild | — | mittel |
| CHE | che-st-moritz | panorama | SkylineWebcams | bild | — | mittel |
| SGP | sgp-cna | nachrichten | CNA | youtube | 0 | hoch |
| IND | ind-wion | nachrichten | WION | youtube | 0 | mittel |
| IND | ind-ndtv | nachrichten | NDTV | youtube | 0 | mittel |
| BRA | bra-cnn-brasil | nachrichten | CNN Brasil | youtube | 0 | mittel |
| BRA | bra-brasilia-panorama | panorama | SkylineWebcams | bild | — | mittel |
| AUS | aus-abc-news-au | nachrichten | ABC News Australia | youtube | 0 | mittel |
| AUS | aus-sydney-harbour | panorama | SkylineWebcams | bild | — | mittel |
| CAN | can-cbc-news | nachrichten | CBC News | youtube | 0 | hoch |
| CAN | can-toronto-waterfront | panorama | SkylineWebcams | bild | — | mittel |
| CAN | can-goes-canada | wetter | NOAA STAR GOES-19 | bild | — | mittel |
| KOR | kor-ytn | nachrichten | YTN | youtube | 0 | mittel |

**Lücken nach Art:** Für RUS, ISR, PSE, LBN, YEM und SDN gibt es keinen geprüften lokalen Nachrichtenstream. Diese Länder werden über Al Jazeera, DW, France 24 und TRT abgedeckt. Für die Schweiz fehlt ein Nachrichtenstream, für Südkorea, Singapur, Indien, die VAE und Saudi-Arabien fehlen Panorama- und Wetterquellen.

## Bewusst ausgeschlossen

| Quelle / Kategorie | Grund |
|---|---|
| Alle Live-Straßen-, Stadt- und Webcams in UKR, RUS (Grenzregionen), ISR/PSE, LBN, YEM, SDN – inkl. SkylineWebcams-Kameras in Israel | Regel: Konfliktzone. In der Ukraine ruft der SBU Webcam-Betreiber zum Abschalten auf und hat Tausende Kameras blockiert; das Zeigen von Abwehr- und Einschlagsorten ist strafbar. Ein formelles Gesetz von 2022 speziell gegen Webcams habe ich **nicht** gefunden (siehe Offene Punkte). |
| Reuters-YouTube-Livestreams und „LiveNOW from FOX“ | Kanäle sind einbettbar, senden aber oft **unkommentierte Rohbilder** von Ereignisorten. Ein Reuters-Stream aus Kyjiw wurde 2025 auf Betreiben der Behörden gestoppt. Das ist kein redaktioneller 24/7-Nachrichtenkanal. |
| EarthCam (alle Kameras) | Einbetten oder Weitersenden nur mit Lizenz bzw. Erlaubnis von EarthCam (laut FAQ) |
| SkylineWebcams-Seiten ohne eigene Embed-ID („From the Web“, z. B. Hongkong-Skyline, Sydney-Panorama, Copacabana, Luzern, Basel, Vancouver, Calgary, Melbourne) | Es handelt sich um fremde YouTube-Streams, die Rechte liegen beim jeweiligen Kanal. Erlaubnis und Kanal nicht geprüft. |
| SkylineWebcams: Kwai Tsing Container Terminal (HK), Dover, Newcastle Port, Vancouver Port, Alberni Port, Campbell-River-Flughafen/Landebahn | Regel: Häfen, Grenzübergänge, Flughafen-Nahsicht |
| SkylineWebcams: Times Square (mehrere), Las Vegas (Little Vegas Chapel), Cardiff St. Mary Street, Canmore Railway Ave, NYC-Dachbar-Kameras | Straßennähe bzw. Personen erkennbar (Gesichts-/Kennzeichen-Nähe) |
| Insecam-ähnliche Verzeichnisse, ungesicherte IP-Kameras | Regel: private bzw. gefundene Kameras |
| Verkehrskameras (z. B. data.gov.sg, HK Transport Department) | Regel: Nahsicht auf Verkehr und Kennzeichen |
| Windy Webcams API | Nicht aufgenommen: API-Schlüssel nötig |
| Sentinel Hub / EO Browser, Copernicus Browser | Nicht aufgenommen: Konto, Login oder API-Schlüssel nötig, teils kostenpflichtig |
| NASA Worldview im Einbettmodus (`em=true`) | Einbettung auf Nicht-NASA-Seiten ist standardmäßig gesperrt und muss beim Worldview-Team beantragt werden. Ersatz: GIBS-WMS direkt. |
| FAA WeatherCams | Einbett- und Nutzungsbedingungen nicht auffindbar, teils Bilder Dritter; außerdem Flughafenkameras |
| RT und andere russische Staatssender | Auf YouTube gesperrt bzw. in der EU sanktioniert. Kein rechtmäßig einbettbarer Stream. |
| VIIRS SNPP und MODIS Terra (GIBS) | SNPP-Abruf lieferte ein leeres Bild. Die Terra-Beobachtungen enden laut NASA Earthdata am 01.12.2026. Stattdessen NOAA-20 verwendet. |

## Offene Punkte / Unsicherheiten

1. **YouTube `live_stream?channel=`**: Der Embed zeigt nur den „aktuellen“ Live-Stream des Kanals. Laufen mehrere Streams parallel, ist nicht festgelegt, welcher erscheint; ohne laufenden Stream zeigt er nichts. `playableInEmbed` wurde nur für das Live-Video am 2026-11-28 geprüft und kann sich je Video ändern. Alternativ die feste Video-ID verwenden (ändert sich bei 24/7-Streams gelegentlich).
2. **Bei der Prüfung nicht live** (deshalb nicht aufgenommen, später erneut prüfen): tagesschau, WELT, BBC News, CBS News, CNBC, NBC (live, aber wegen 4er-Grenze weggelassen), Euronews deutsch und DW Arabic (live, weggelassen), i24NEWS English, Times of Israel, Arirang News, TaiwanPlus, RTHK, Al Jadeed, TV Rain, Al Arabiya English, Al Jazeera Mubasher, Global News, NewsNation.
3. **Viele Streams sind nur „mittel“ eingestuft**, weil bei der Prüfung eine Einzelsendung oder ein Sonderstream lief statt eines erkennbaren 24/7-Simulcasts: Sky News, ABC Australia, TVBS, YTN, ANN, NDTV, WION, CNN Brasil, phoenix.
4. **Redaktionelle Ausrichtung prüfen**: CGTN (chinesischer Staatssender), TRT World (türkischer Staatssender), Al Arabiya (saudisch), Al Jazeera (katarisch finanziert), Iran International (Exilsender, Finanzierung umstritten). Bitte bewusst freigeben.
5. **Aktuelle Lage**: Laut den Live-Titeln vom 28.11. laufen ein Konflikt USA–Iran und saudische Angriffe im Jemen bzw. Angriffe auf Riad. Deshalb sind IRN und SAU vorsorglich wie Konfliktzonen behandelt (keine Kameras). Ob das auch für die VAE gelten soll, muss der Mensch entscheiden.
6. **Ukraine-„Verbot“**: Gefunden habe ich SBU-Appelle, Sperrungen und das Kriegsrecht (Verbot, Militärinformationen zu verbreiten), aber kein ausdrückliches Webcam-Verbotsgesetz von 2022. Am Ausschluss ändert das nichts.
7. **SkylineWebcams**: Der offizielle Embed ist ein verlinktes Vorschaubild (kein Live-Player). Laut Bedingungen nur unverändert verwenden, also Link und Logo behalten und nicht beschneiden. Nutzung „journalistisch oder kommerziell“ ist ausgeschlossen. Ob ein privates Dashboard mit Marktbezug darunter fällt, muss der Mensch einschätzen. Aktualisierungsrate unbekannt (`null`). Bilder für Interlaken, St. Moritz und St Ives habe ich nicht gesichtet.
8. **GIBS**: `TIME` muss auf den Vortag (UTC) gesetzt werden, sonst ist das Bild oft leer. Die NRT-Verzögerung ist laut Anbieter nicht belegt (`null`). Die Attribution der NASA ist erbeten.
9. **EUMETSAT**: Die Datenpolitik stellt „Core“-Daten unter CC BY 4.0. Ob die GeoColour-RGB-Darstellung in EUMETView dazugehört, ist nicht ausdrücklich bestätigt. Die Website-Bedingungen sind enger („persönlich, nicht kommerziell“). Credit „© EUMETSAT 2026“ immer anzeigen. Gemessene Verzögerung ca. 40 min (eine Stichprobe).
10. **NOAA STAR GOES**: Als Werk einer US-Bundesbehörde vermutlich gemeinfrei. Eine ausdrückliche Nutzungsangabe auf der STAR-Seite habe ich nicht gefunden (`lizenz_url` verweist auf die allgemeine US-Regierungs-Copyright-Seite).
11. **HKO**: Nicht-kommerzielle Nutzung mit Quellenangabe ist erlaubt, aber jederzeit widerrufbar. Ob direktes Hotlinking erlaubt ist, steht dort nicht. Der Hinweis-/Bedingungstext muss mit angezeigt werden.
12. **JMA Himawari**: Die URL ist eine Vorlage mit `{HHMM}` (UTC, 10-Minuten-Raster, rollierend 24 h). Das Dashboard muss die Zeit berechnen. Die Bilder habe ich nicht gesichtet.
13. **Panorama-Lücken**: Für Feratel, Roundshot und Tourismusämter habe ich keine öffentliche Einbett-Erlaubnis gefunden. Bei Roundshot liegen die Rechte beim jeweiligen Kunden (Bedingungs-PDF nicht maschinenlesbar). Kandidaten müssten einzeln beim Betreiber angefragt werden.
14. **Länderzuordnung**: Euronews (Lyon/Brüssel), Al Arabiya (Dubai/Riad), NTN24 (Bogotá → VEN), Iran International (London → IRN) sind nach Berichtsschwerpunkt zugeordnet, nicht nach Sitz.
