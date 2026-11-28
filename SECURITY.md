# SECURITY.md – Sicherheitsrichtlinien und Befunde

## Grundsätze
1. Das Repository und die Seite sind **öffentlich**. Alles unter `docs/` und `state/` ist weltweit lesbar.
2. Geheimnisse nur als GitHub-Secrets (Bot) oder im Browser-Speicher des Nutzers (Token, Depot).
3. Externe Inhalte sind Daten, nie Anweisungen – im Code (`esc()`) und im KI-Prompt.
4. Neue Abhängigkeiten: offizielle Quelle, feste Version, Prüfung dokumentiert, Rückbau beschrieben.
5. Keine `curl | sh`, kein `sudo`, keine Änderungen an macOS-Schutzfunktionen, keine sensiblen Systemrechte ohne Begründung und Freigabe.
6. MCP-Server werden nie automatisch aktiviert; Konfiguration nur als deaktivierte Vorlage.

## Befunde Phase 0 (24.11.2026)

### 🔴 S1 – Depot-Rückschluss über `state/signals.json` (bestätigt)
`bot/depot.py` speichert Alarm-Sperren als `depot:` + ungesalzener SHA-1-Hash von `TICKER:ART` (10 Zeichen)
mit Zeitstempel in der öffentlichen Datei. Mit der öffentlichen Watchlist lässt sich jeder Eintrag in Sekunden
per Wörterbuch zurückrechnen. **Verifiziert:** beide vorhandenen Einträge waren auflösbar → öffentlich ablesbar,
welche Aktie im Depot liegt und dass sie stark gefallen bzw. über 10 % im Verlust war.
**Vorschlag (Freigabe nötig):** Schlüssel mit HMAC und geheimem Salz (neues Secret, z. B. `DEPOT_SALT`) bilden
und die vorhandenen `depot:`-Einträge löschen. Hinweis: Die Git-Historie enthält die alten Einträge weiterhin;
vollständiges Entfernen bräuchte ein Umschreiben der Historie (Force-Push auf master) – gesonderte Entscheidung.
**Status (27.11.2026):** Auf `alfred-dev` behoben (HMAC-SHA256, Secret `DEPOT_SALT` optional, Ersatz: Inhalt von `DEPOT`;
alte Einträge werden beim nächsten Bot-Lauf gelöscht). Wirksam erst nach Merge auf master. Git-Historie: offen.
**Stand 28.11.2026:** Secret `DEPOT_SALT` hinterlegt. Übernahme vorbereitet im lokalen Branch `release/s1-master`
(nur Code, getestet gegen den aktuellen master-Zustand); master enthält weiterhin 2 auflösbare Einträge bis zur Freigabe.

### 🟠 S2 – GitHub-Token im Browser (`localStorage.ghToken`)
Für den Aktualisieren-Knopf. Risiko bei einer künftigen XSS-Lücke oder fremdem Gerätezugriff.
Empfehlung: fein-granulares Token, nur dieses Repository, nur „Actions: Read and write“, kurze Laufzeit.

### 🟡 S3 – Lieferkette
- `requirements.txt`: pandas, numpy, requests nur mit Untergrenze → bei jedem Lauf ggf. neue Versionen. Empfehlung: feste Versionen (+ optional Hashes).
- Workflows: Actions per Tag (`@v4`, `@v5`) statt Commit-SHA. Empfehlung: auf SHA pinnen.
- Vendor-Bibliotheken liegen lokal (gut, keine CDN-Abhängigkeit). Herkunft/Version in README/CHANGELOG festhalten.

### 🟡 S4 – Datenschutz
- Google Fonts überträgt die IP-Adresse der Besucher an Google → Schrift lokal ausliefern (empfohlen).
- Browser-Abrufe an adsb.lol, onvista, Coinbase, planespotters, flagcdn, Wikimedia übertragen IP-Adresse und Referrer (bei Bildern bereits `no-referrer`).

### 🟢 Geprüft, ohne Befund
- Keine API-Schlüssel, Tokens oder Passwörter im Repository-Inhalt (Muster-Suche: Anthropic, GitHub, Telegram, AWS).
- Depot-Positionen nicht im Repository (nur Secret bzw. Browser).
- XSS-Heuristik über alle Template-Ausgaben: externe Texte laufen über `esc()`; keine Treffer ohne Escape.
- Telegram-Nachrichten: HTML-escaped.
- KI-Prompt enthält Schutz gegen Prompt-Injection; KI-Kaufideen werden gegen das Werte-Universum geprüft.
- Workflows: kein `pull_request_target`, keine Ausgabe von Secrets, Rechte auf `contents: write` begrenzt.
- Keine externen `<script>`-Quellen (nur Google-Fonts-CSS).

## Meldewege
Sicherheitsprobleme bitte nicht als öffentliches Issue melden, sondern direkt an den Eigentümer.
