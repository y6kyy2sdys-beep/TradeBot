# Trading-Signal-Bot (Telegram)

Scannt automatisch ~95 Werte weltweit (US-, EU- und Asien-Aktien, ETFs, Krypto)
auf Swing-Signale mit Haltedauer von wenigen Tagen und schickt sie per Telegram.

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
2. Optional unter **Variables**: `BUDGET_EUR` (Standard 100),
   `FEE_PER_ORDER_EUR` (Standard 1), `MIN_HIT_RATE` (Standard 0.70)
3. **Actions → Trading-Signale → Run workflow** mit Modus `test` → Testnachricht in Telegram.

## Wichtig

- Backtest-Trefferquoten beschreiben die Vergangenheit, sie sind keine Garantie.
- Bei 100 € und 1 € Gebühr pro Order kosten Kauf + Verkauf 2 %. Der Bot rechnet das ein,
  deshalb kommen nur wenige Signale. Das ist Absicht.
- Keine Anlageberatung. Immer Stop-Loss setzen und nur Geld einsetzen, dessen Verlust du verkraftest.
