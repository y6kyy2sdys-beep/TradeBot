# TradeBot – Audit & Implementierungsplan (Investment Intelligence)

Stand: November 2026 · Grundlage: vollständige Durchsicht von `bot/*.py`, `docs/index.html`, `.github/workflows/*`.

## 1. Architektur heute

| Ebene | Umsetzung |
|---|---|
| Datenerhebung | Python-Bot (`bot/`) läuft in GitHub Actions (stündlich werktags, KI-Analyse 2×/Tag, Flugdaten alle 30 min) |
| Speicherung | JSON im Repo (`state/*.json`), Dashboard-Daten als JS-Dateien in `docs/` |
| Auslieferung | GitHub Pages (statisch, öffentlich), keine Server-Logik |
| Frontend | eine HTML-Datei (`docs/index.html`, ~2 500 Zeilen), uPlot, d3, kein Build-Schritt |
| Geheimnisse | GitHub-Secrets (Telegram, Anthropic, Depot) – nie im Frontend ✔ |

**Folgerung:** GitHub Pages kann keine geschützten API-Schlüssel halten. Alles, was einen Schlüssel braucht, muss im Actions-Lauf passieren und darf nur abgeleitete, lizenzrechtlich veröffentlichbare Ergebnisse ins Repo schreiben.

## 2. Datenquellen – Ist-Zustand und Qualität

| Quelle | Wofür | Art der Daten | Bewertung |
|---|---|---|---|
| Yahoo Finance (über `yfinance`) | Kurse, Indizes, Rohstoffe, FX, `info`-Kennzahlen | Tagesschluss bzw. ~15 min verzögert, inoffizielle Schnittstelle | brauchbar für privaten Gebrauch; keine Lizenz für Weitergabe, Datenpunkte ohne Bezugsperiode |
| IMF DataMapper / World Bank | BIP, Inflation, Schulden, Arbeitslosigkeit | offizielle Statistik + IMF-Prognose | gut, jährlich |
| Google News RSS | Schlagzeilen | Sekundärquelle | nur für Nachrichtenlage, nicht für Fundamentalbewertung |
| Claude + Websuche | Lageanalyse, Kaufideen | KI-Einschätzung | qualitative Meinung, muss als solche markiert sein |
| Wikidata/Wikimedia, adsb.lol, DeepStateMap | Staatsführung, Flugzeuge, Frontlinien | offen, Community | nur für Lagebild, nicht investmentrelevant |
| Statische Tabellen (`GOLD_RESERVES`, `WKN`) | Goldbestände, WKN | manuell gepflegt (Mitte 2025) | veraltet ohne Kennzeichnung des Alters im UI |

**Institutionelle Anbieter (Bloomberg, LSEG, FactSet, S&P CIQ, Morningstar, ICE):** Es gibt **keinen** Zugang und keine Lizenz. Sie werden daher **nicht** angebunden und nirgends als Quelle genannt. Die Architektur unten erlaubt eine spätere Anbindung (Abruf im Actions-Lauf mit Secret), aber die Lizenzbedingungen dieser Anbieter verbieten in der Regel die Veröffentlichung der Rohdaten auf einer öffentlichen Seite – dafür bräuchte es ein privates Backend.

**Frei verfügbare, offizielle Quellen, die neu dazukommen:**
- **FRED (Federal Reserve Bank of St. Louis)** – Zinsen (3M/2J/10J), Zinsstrukturkurve, Kreditspreads (ICE BofA HY/IG OAS über FRED), CPI/Core CPI/Core PCE, Arbeitsmarkt, Industrieproduktion, Finanzierungsbedingungen (Chicago Fed NFCI), Fed-Bilanz, Leitzinsen Fed/EZB, Bund-Rendite (OECD-Reihe). CSV-Abruf ohne Schlüssel.
- **Yahoo-Finanzberichte** (`income_stmt`, `balance_sheet`, `cashflow`, 4 Jahre + Quartale), **Analystenschätzungen**, **Gewinnrevisionen** (`eps_trend`, `eps_revisions`), **Earnings Surprise**, **Up-/Downgrades**, **Termine** – alles inoffiziell über Yahoo, aber echte Daten mit Bezugsperiode.
- **ETF-Bewertungsdaten** (`funds_data`: KGV, KBV, KUV, KCV des ETF-Portfolios und Top-Positionen).

Nicht verfügbar (und deshalb nicht angezeigt): ISM/PMI (lizenziert), Short Interest außerhalb der USA, Point-in-Time-Fundamentaldaten, Earnings-Call-Transkripte, Reuters/Bloomberg-Volltexte.

## 3. Befunde

### 3.1 Analytische Schwächen
1. **Marktregime** (`main.market_context`) ist binär: „Risk-off“, wenn VIX > 30 *oder* S&P 500 unter 200-Tage-Linie, sonst „Risk-on“. Keine Zinsen, Spreads, Inflation, Arbeitsmarkt, Marktbreite.
2. **Hot-Picks** (`dashboard.hot_picks`) sind reines Kursmomentum (1/3/6 Monate, RSI). Keine Bewertung, Qualität oder Gewinnrevisionen.
3. **Steckbrief-Urteil** (`profiles.verdict`) vergibt feste Punkte (±5/10/15) nach Faustregeln (z. B. „KGV < 15 = günstig“) – branchenunabhängig, ohne Normierung, nicht validiert.
4. **Branchen** (`sectors.py`) zeigen nur ETF-Kursveränderungen und Schlagzeilen; kein Scoring.
5. **KI-Kaufideen**: Szenario-Wahrscheinlichkeiten (z. B. „Bull 30 %“) und daraus berechneter Erwartungswert stammen vom Sprachmodell → **scheinpräzise**. Werden künftig als „qualitative KI-Einschätzung“ markiert, nicht als Modellergebnis.
6. **Eskalationsstufen** ohne KI zählen Konflikt-Schlagzeilen je Land → Länder, die in Meldungen *erwähnt* werden (z. B. USA bei einem Iran-Konflikt), bekommen hohe Stufen. Heuristik, als solche kennzeichnen.
7. **Depot-Prognose** extrapoliert die historische Drift lognormal – historische Rendite ist kein Schätzer der Zukunft; als Spannbreite/Illustration kennzeichnen.
8. **Szenarien bis 2050** und **Dystopie** sind Modell bzw. Fiktion – bereits gekennzeichnet ✔.

### 3.2 Backtest (`strategies.backtest`)
- ✔ Einstieg zur Eröffnung des Folgetags (kein Look-Ahead beim Einstieg), Gebühren berücksichtigt, Wilson-Untergrenze für Trefferquote.
- ✘ **Survivorship Bias**: Universum = heutige Großkonzerne.
- ✘ Kein Slippage, keine Benchmark, keine Rendite-/Risiko-Kennzahlen (CAGR, Sharpe, Drawdown).
- ✘ Bei gleichem Tag für Ziel und Stop ist die Reihenfolge unbekannt (wird konservativ als Stop gewertet – prüfen).

### 3.3 Datenintegrität
- Kennzahlen aus `yfinance.info` haben **keinen Zeitstempel und keine Bezugsperiode** im UI.
- **Währungsmix**: Bei ADRs/Auslandswerten (z. B. TSM) sind Berichtswährung und Kurswährung verschieden; Kennzahlen wie Free-Cashflow-Rendite werden dann falsch, wenn man sie mischt.
- Das Dashboard kennzeichnet nicht, dass Kurse **Tagesschluss/verzögert** sind.
- Statische Tabellen (Goldreserven, WKN) ohne sichtbares Datum.

### 3.4 UX
- Ein sehr langer Scroll-Bereich mit 8 Blöcken, viele Animationen (Matrix-Regen, Intro) – widerspricht „klare Hierarchie, keine unnötigen Animationen“.
- Die wichtigste Frage „In welchem Marktumfeld sind wir?“ steht nur als eine Zeile im Kopf.
- Doomsday/Flugzeuge/Front sind Lagebild-Spielerei ohne Investmentbezug → bleiben erhalten, aber unter „Macro → Geopolitik“ statt prominent.

### 3.5 Sicherheit
- ✔ Schlüssel nur als GitHub-Secrets; Depot nur als Secret, Alarme gehasht.
- ⚠ Der Aktualisieren-Knopf speichert ein GitHub-Token im `localStorage` des Browsers. Empfehlung: fein-granulares Token **nur** mit „Actions: write“ für dieses eine Repository, kurze Laufzeit.
- ⚠ Repository und Seite sind öffentlich: alles in `docs/` und `state/` ist weltweit lesbar.

## 4. Was erhalten bleibt
Kurs-/Rohstoff-Charts mit Zeitraumwahl, Suche mit Steckbrief, Depot & Favoriten, Telegram-Signale und Warnungen, Weltkarte mit IMF-Daten, Branchen-News, Block-Verschiebung, App-Modus. Nichts davon wird entfernt.

## 5. Implementierungsplan

| Phase | Inhalt | Datenbasis | Status |
|---|---|---|---|
| 1 Audit | dieses Dokument | – | ✔ |
| 2 Daten | FRED-Makroreihen; Finanzberichte, Schätzungen, Revisionen je Aktie (Cache 7 Tage); Metadaten je Datensatz (Quelle, Stand, Typ, Währung, Periode) | FRED, Yahoo | in Arbeit |
| 3 Sector Intelligence | 25 Branchen über liquide ETFs (GICS-nahe Abgrenzung); Faktoren A–F (Bewertung, Fundamentaldaten, Gewinnrevisionen, relative Stärke, Makro-Sensitivität per Regression, Risiko); Z-Scores, konfigurierbare Gewichte im Browser, Klassen „Strongly Attractive … Avoid“ | ETF-Kurse, ETF-Bewertung, Top-Positionen, FRED | in Arbeit |
| 4 Equity Research | Detailseite: Kopfkennzahlen, 4 Jahre Finanzhistorie, Margen/Rendite/Bilanz, Konsens, Branchenvergleich, These *mit* Gegenargumenten, Quellen | Yahoo | in Arbeit |
| 5 Valuation | DCF (Bear/Base/Bull, Sensitivität WACC × Wachstum, alle Annahmen editierbar); Banken/Versicherer: Residual-Income-Ansatz (P/B vs. ROE) | Finanzberichte, FRED-Zins | in Arbeit |
| 6 Risk Monitor | Red Flags mit Regel, Wert, Quelle; Klassen „Confirmed / Potential / Data Quality Warning“ | Finanzberichte, Kurse | in Arbeit |
| 7 Redesign | Hauptnavigation mit 9 Bereichen, ruhiges Profi-Design als Standard (Matrix-Look optional), Market Overview als Startseite | – | in Arbeit |
| 8 Backtesting | Branchenrotation mit rein kursbasierten Faktoren (nur diese sind point-in-time verfügbar), monatlich, Kosten + Slippage, gegen S&P 500; CAGR, Sharpe, Sortino, Max DD, Alpha/Beta, IR, Trefferquote, Profit Factor, Turnover, Ergebnis je Regime | ETF-Kurse (Total Return) | in Arbeit |
| 9 QS | Unit-Tests der Berechnungen, Browser-Tests aller Bereiche | – | offen |
| 10 Deployment | eigener Workflow `research.yml` (täglich + manuell), schreibt `docs/research.js` | – | offen |

### Methodische Leitplanken
- Fehlt ein Wert, steht „Keine belastbare Datengrundlage vorhanden.“ – es wird nichts geschätzt oder aufgefüllt.
- Regime ohne Wahrscheinlichkeiten: stattdessen **Indikator-Abstimmung** („5 von 7 Indikatoren sprechen für …“) mit Einzelbegründung; Unsicherheit = Uneinigkeit der Indikatoren.
- Makro-Sensitivitäten sind historische Regressionen (Korrelation, keine Kausalität) und werden so beschriftet.
- Fundamentaldaten sind **nicht** point-in-time verfügbar → das Fundamental-Scoring wird **nicht** rückgetestet; das steht im UI.
- Fair Values sind Modellschätzungen mit sichtbaren Annahmen, keine Kursziele.
- Keine automatischen Kaufempfehlungen: Scanner liefert Rangfolge + Begründung + Gegenargumente.
