# INSTALLATION_GUIDE_MACOS.md – Sichere Einrichtung der Entwicklungswerkzeuge

Für Nutzer ohne Programmiererfahrung. **Nichts davon ist schon installiert, nichts wird automatisch ausgeführt.**
Du entscheidest Schritt für Schritt. Versionen wurden am **24.11.2026** in den offiziellen Registern geprüft.

## 0. Muss ich überhaupt etwas installieren?
Das Dashboard läuft komplett auf GitHub (Bot in GitHub Actions, Seite auf GitHub Pages).
**Für den Betrieb brauchst du auf dem Mac nichts.** Werkzeuge sind nur nötig, wenn du lokal mitentwickeln
oder Claude die Seite in einem echten Browser auf deinem Mac testen lassen willst.

## 1. Bewertung je Werkzeug

| Werkzeug | Nötig? | Schon da? | Passt zum Projekt? | Läuft | Rechte | Daten nach außen | Kosten | Empfehlung · Version | Quelle |
|---|---|---|---|---|---|---|---|---|---|
| **Git** | ja, wenn lokal gearbeitet wird | prüfen: `git --version` | ja | lokal | keine besonderen | nur zu GitHub beim Push | frei | Apple Command Line Tools oder git-scm | developer.apple.com · git-scm.com |
| **Node.js LTS + npm** | nur für Playwright/MCP/Lighthouse-CLI | prüfen: `node -v` | ja (Projekt selbst braucht kein Node) | lokal | keine besonderen | npm lädt Pakete von registry.npmjs.org | frei | **v26.13.1 „Lithium“ (Active LTS)**; Alternative v24.22.3 | nodejs.org |
| **Claude Code CLI** | optional – Claude Desktop enthält Claude Code bereits | in Claude Desktop vorhanden | ja | lokal, Modell in der Anthropic-Cloud | Dateizugriff im Projektordner nach Freigabe | Code/Text an Anthropic | im Claude-Abo | npm-Paket `@anthropic-ai/claude-code` **2.1.331** oder Anleitung auf code.claude.com | code.claude.com/docs |
| **Playwright MCP** | empfohlen für Browser-Tests durch Claude | nein | ja | lokal (startet Chromium) | keine; eigener Browser-Ordner | besuchte Seiten/Screenshots an Claude | frei | `@playwright/mcp` **0.0.86** (Microsoft, Apache-2.0) | github.com/microsoft/playwright-mcp |
| **Chrome DevTools MCP** | optional (überschneidet sich mit Playwright MCP; stärker bei Performance-Analysen) | nein | ja | lokal (steuert Chrome) | Zugriff auf ein Chrome-Profil – **nur separates Profil verwenden** | Seiteninhalte an Claude | frei | `chrome-devtools-mcp` **1.14.0** (Google, Apache-2.0) | github.com/ChromeDevTools/chrome-devtools-mcp |
| **Context7 MCP** | **nicht nötig** (Projekt nutzt nur d3/uPlot, gut dokumentiert) | nein | ja | lokal, Abfragen an Upstash-Server | keine | Suchanfragen (Bibliotheksnamen, Fragen) an Upstash | Gratis-Kontingent, danach kostenpflichtig | – (`@upstash/context7-mcp` 4.8.0) | github.com/upstash/context7 |
| **Lighthouse** | ja, aber **keine Installation**: in Chrome DevTools eingebaut | ja (in Chrome) | ja | lokal | keine | keine | frei | Chrome → Rechtsklick „Untersuchen“ → Lighthouse; CLI 13.6.0 nur bei Bedarf | developer.chrome.com/docs/lighthouse |
| **Frontend-Design-Plugin** | optional | – | ja | in Claude | keine | wie Claude | im Abo | nur aus dem offiziellen Anthropic-Plugin-Verzeichnis | Claude Desktop → Plugins |
| **Code-Review-Plugin** | optional – in Claude Code bereits als Befehl `/code-review` verfügbar | ja | ja | in Claude | keine | wie Claude | im Abo | vorhandene Funktion nutzen | – |
| **Vitest** | **überflüssig** – kein JavaScript-Build/Module; Tests besser mit Playwright (Oberfläche) und Python-`unittest` (Bot) | nein | schlecht | – | – | – | – | nicht installieren | – |
| **axe-core** | optional für Barrierefreiheit | nein | ja (über Playwright) | lokal | keine | keine | frei | `@axe-core/playwright` **4.14.1** (Deque, MPL-2.0) nur zusammen mit Playwright-Tests | github.com/dequelabs/axe-core-npm |
| **Sentry** | **nicht empfohlen** | nein | technisch ja | Cloud | – | Fehlerberichte inkl. Seiteninhalte/IP an sentry.io | Gratis-Kontingent, sonst Abo | weglassen (Datenschutz, kein Mehrwert für eine Privatseite) | sentry.io |

Bekannte Sicherheitsprobleme: Für die genannten Versionen ist mir keine Warnung bekannt; vor der Installation
bitte jeweils die „Security“-Seite des GitHub-Projekts ansehen. Grundsätzlich gilt: npm-Pakete können bei Installation
Skripte ausführen → nur die exakten Namen oben verwenden (Tippfehler-Pakete/Typosquatting!).

## 2. Empfohlene Minimal-Ausstattung
1. Git
2. Node.js LTS (bringt npm mit)
3. Playwright MCP (in Claude Desktop als **deaktivierte** Vorlage, siehe `.mcp.json.example`)
Alles andere ist optional.

## 3. Schritt für Schritt

### 3.1 Git
1. Programm **Terminal** öffnen (Spotlight: ⌘ + Leertaste → „Terminal“).
2. Eingeben: `git --version` und Enter.
   - Erscheint eine Versionsnummer → fertig.
   - Erscheint ein Apple-Fenster „Befehlszeilenentwickler-Tools installieren?“ → **Installieren** klicken.
     Das ist Apples offizieller Installer (kein Download aus fremder Quelle, kein Passwort für Systemänderungen außer der üblichen macOS-Abfrage).
3. Prüfen: erneut `git --version`.
- **Rückgängig:** Ordner `/Library/Developer/CommandLineTools` löschen (Finder → Gehe zu Ordner) – betrifft nur diese Tools.

### 3.2 Node.js LTS
1. Im Browser **https://nodejs.org** öffnen (genau diese Adresse prüfen).
2. Die Version mit dem Hinweis **LTS** für macOS herunterladen (Datei endet auf `.pkg`).
3. Datei öffnen, dem Installer folgen (macOS fragt nach deinem Passwort – normal für Programme in /usr/local).
4. Terminal neu öffnen, prüfen: `node -v` (z. B. `v26.13.1`) und `npm -v`.
- **Nicht** über fremde Skripte oder „Ein-Zeilen-Installer“ installieren.
- **Rückgängig:** Anleitung „How to uninstall“ auf nodejs.org; im Kern die Ordner `/usr/local/lib/node_modules`,
  `/usr/local/bin/node`, `/usr/local/bin/npm`, `/usr/local/bin/npx` entfernen.

### 3.3 Playwright MCP (für Browser-Tests durch Claude)
Wird **nicht** installiert, sondern bei Bedarf von Claude Desktop mit fester Version gestartet.
1. Claude Desktop → Einstellungen → Entwickler (Developer) → Konfiguration bearbeiten.
2. Den Abschnitt aus `.mcp.json.example` (in diesem Repository) übernehmen – Version ist fest auf `0.0.86`.
   Die Option `--isolated` (eigenes, leeres Browserprofil) vorher in der README des Projekts gegenprüfen.
3. Claude Desktop neu starten. Beim ersten Start lädt `npx` das Paket und einen Test-Browser (einige hundert MB).
- Berechtigungen: keine macOS-Sonderrechte (kein Festplattenvollzugriff, keine Bedienungshilfen, keine Bildschirmaufnahme nötig).
- **Rückgängig:** Abschnitt aus der Konfiguration löschen, Claude neu starten; Browser-Daten liegen unter `~/Library/Caches/ms-playwright`.

### 3.4 Lighthouse (ohne Installation)
Google Chrome → Seite öffnen → Rechtsklick → „Untersuchen“ → Reiter **Lighthouse** → „Seitenaufbau analysieren“.

## 4. Was du niemals tun solltest
- Befehle der Form `curl … | sh` oder `sudo …` ausführen, die dir jemand schickt, ohne dass sie geprüft wurden.
- Gatekeeper, SIP, XProtect oder die Firewall abschalten.
- Programmen Festplattenvollzugriff, Bedienungshilfen oder Bildschirmaufnahme geben, wenn es nicht nachvollziehbar nötig ist.
- API-Schlüssel, Telegram-Token oder Depotdaten in Dateien im Repository speichern.
