# Trading-Signal-Bot (Telegram)

Beobachtet Weltlage und Märkte und schickt per Telegram vier Arten von Nachrichten:

| Nachricht | Quelle | Wann |
|---|---|---|
| 🌍 **Makro-Signal** – Öl, Gas, Zinsen, Währungen, Rohstoffe, Szenarien wie „Angriff auf Iran → Öl ↑ → Airlines ↓, Rüstung ↑“ | Regeln (kostenlos) + KI | bei jedem Lauf bzw. morgens |
| ⚠️ **Marktwarnung** – VIX, Korrektur, Trendbruch, Kreditstress, inverse Zinskurve, KI-Risikoeinschätzung | Regeln + KI | sobald ausgelöst |
| 🟢 **Kaufidee** – mit Begründung, Auslösern, Risiken, Zeithorizont (Wochen–Monate), Ziel und Stop | KI (Claude) | morgens |
| 🟢 **Kaufsignal (Swing)** – technisches Signal für wenige Tage, per Backtest geprüft | Regeln | nach Börsenschluss |

Kaufideen werden automatisch verworfen, wenn sie sich für 100 € nicht realistisch lohnen:
Kursziel unter 8 % oder Chance/Risiko nach Gebühren unter 1,5.

## KI-Lageanalyse (optional)

Werktags vor Börsenstart und Sonntagabend recherchiert Claude per Websuche die aktuelle Lage
und leitet Wirkungsketten, Warnungen und Kaufideen ab. Dafür braucht es das Secret
`ANTHROPIC_API_KEY` (console.anthropic.com → API Keys). Ohne Schlüssel laufen alle
regelbasierten Meldungen trotzdem weiter. Kosten: grob 0,30–0,60 $ pro Analyse, also etwa
8–15 $ im Monat; begrenzbar über ein Ausgabenlimit in der Anthropic-Console.
Modell änderbar über die Variable `AI_MODEL`.

## Swing-Signale

## So entscheidet der Bot

1. **Technik** – drei Strategien auf Tageskerzen:
   - *Rücksetzer im Aufwärtstrend* (RSI(2) < 10 über der 200-Tage-Linie)
   - *Ausbruch auf 20-Tage-Hoch* mit erhöhtem Volumen
   - *MACD-Wende* im Aufwärtstrend
2. **Backtest je Wert** über 6 Jahre: Jedes historische Signal wird mit
   Kursziel, Stop-Loss, maximaler Haltedauer **und Gebühren** nachgehandelt.
   Ein Signal geht nur raus, wenn die **Trefferquote ≥ 70 %** liegt (mindestens 12 Trades) und
   die Durchschnittsrendite nach Gebühren positiv ist.
3. **Fundamentaldaten** (nur Aktien): Verlustfirmen, stark schrumpfender Umsatz
   oder sehr hohe Verschuldung werden aussortiert.
4. **Marktumfeld & Weltlage**: VIX, S&P 500, DAX, Zinsen, Öl, Gold, Dollar.
   Bei Stress (VIX > 30 oder S&P unter 200-Tage-Linie) steigt die Mindest-Trefferquote auf 75 %.
   Der Tagesbericht enthält aktuelle Schlagzeilen zu Wirtschaft und Geopolitik.
5. **Nachverfolgung**: Offene Signale werden bei jedem Lauf geprüft. Du bekommst
   eine Nachricht bei Kursziel, Stop-Loss oder Ablauf der Haltedauer, dazu die **echte Live-Bilanz**.

Läufe: werktags nach Börsenschluss Asien, Europa und USA, am Wochenende für Krypto.

## Einrichtung

1. Repo → **Settings → Secrets and variables → Actions → New repository secret**
   - `TELEGRAM_BOT_TOKEN` – Token von @BotFather
   - `TELEGRAM_CHAT_ID` – deine Chat-ID
   - `ANTHROPIC_API_KEY` – optional, für die KI-Lageanalyse
2. Optional unter **Variables**: `BUDGET_EUR` (Standard 100),
   `FEE_PER_ORDER_EUR` (Standard 1), `MIN_HIT_RATE` (Standard 0.70)
3. **Actions → Trading-Signale → Run workflow** mit Modus `test` → Testnachricht in Telegram,
   mit Modus `analysis` → sofortige KI-Lageanalyse.

## Wichtig

- Backtest-Trefferquoten beschreiben die Vergangenheit, sie sind keine Garantie.
- Bei 100 € und 1 € Gebühr pro Order kosten Kauf + Verkauf 2 %. Der Bot rechnet das ein,
  deshalb kommen nur wenige Signale. Das ist Absicht.
- Keine Anlageberatung. Immer Stop-Loss setzen und nur Geld einsetzen, dessen Verlust du verkraftest.

## Dashboard (Kommandozentrale)

`docs/index.html` ist ein Dashboard im Matrix-Look: marktbewegende News, die größten Weltindizes
mit Zeitregler (1W bis 10 Jahre, Datumsauswahl, Zoom per Ziehen), Hot-Picks, Rohstoffe/Öl/Gas
und das Signal-Protokoll. Der Bot schreibt die Daten bei jedem Lauf nach `docs/data.js`.

Einschalten: **Settings → Pages → Source: Deploy from a branch → Branch `master`, Ordner `/docs` → Save**.
Nach 1–2 Minuten ist es unter `https://<benutzername>.github.io/TradeBot/` erreichbar.
(GitHub Pages ist bei öffentlichen Repos kostenlos.)
