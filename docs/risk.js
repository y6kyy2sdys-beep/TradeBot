/* PROJECT A.L.F.R.E.D. – Portfolio Risk Center (Phase 4).
   Rechnet ausschließlich mit vorhandenen Daten: Depot im Browser (localStorage "depot"), Kursprofile (profiles.js, ~2 Jahre
   Schlusskurse), Wechselkurse und Indizes (data.js), Weltlage (world.js). Nichts verlässt den Browser.
   Kennzeichnung: Rückrechnung mit HEUTIGEN Stückzahlen (hypothetisch), Kurse in Handelswährung (keine historischen Wechselkurse),
   Sharpe ohne risikofreien Zins. Keine Prognose, keine Anlageberatung. */
(function (global) {
  "use strict";
  const DAYS_YEAR = 252;
  const LAND_ISO = { "United States": "USA", "Canada": "CAN", "Taiwan": "TWN", "China": "CHN", "Germany": "DEU", "Netherlands": "NLD",
    "France": "FRA", "Denmark": "DNK", "Switzerland": "CHE", "United Kingdom": "GBR", "Italy": "ITA", "Japan": "JPN", "Sweden": "SWE",
    "Ireland": "IRL", "Spain": "ESP", "Finland": "FIN", "Norway": "NOR", "South Korea": "KOR", "Australia": "AUS", "India": "IND",
    "South Africa": "ZAF", "Hong Kong": "HKG", "Israel": "ISR", "Belgium": "BEL", "Austria": "AUT", "Luxembourg": "LUX", "Brazil": "BRA" };
  const BENCH = [["^GDAXI", "DAX"], ["^GSPC", "S&P 500"]];

  /* ---------------- Rechenkern (rein, testbar) ---------------- */
  const mean = a => a.reduce((s, x) => s + x, 0) / a.length;
  const sd = a => { if (a.length < 2) return null; const m = mean(a); return Math.sqrt(a.reduce((s, x) => s + (x - m) ** 2, 0) / (a.length - 1)); };
  const cov = (a, b) => { const ma = mean(a), mb = mean(b); let s = 0; for (let i = 0; i < a.length; i++) s += (a[i] - ma) * (b[i] - mb); return s / (a.length - 1); };
  const corr = (a, b) => { const sa = sd(a), sb = sd(b); return sa && sb ? cov(a, b) / (sa * sb) : null; };
  const quantile = (a, q) => { const s = [...a].sort((x, y) => x - y), i = (s.length - 1) * q, lo = Math.floor(i), hi = Math.ceil(i); return s[lo] + (s[hi] - s[lo]) * (i - lo); };
  function maxDrawdown(prices) { let peak = -Infinity, mdd = 0; for (const p of prices) { if (p > peak) peak = p; const dd = p / peak - 1; if (dd < mdd) mdd = dd; } return mdd; }
  function seriesOfProfile(p) {
    const m = new Map(); let d = p.d0;
    for (let i = 0; i < p.px.length; i++) { if (i) d += +p.g[i - 1]; if (p.px[i] != null) m.set(d, p.px[i]); }
    return m;
  }
  function seriesOfDash(D, t) {
    const s = D && D.series && D.series[t]; if (!s) return null;
    const m = new Map(); D.dates.forEach((d, i) => { if (s.v[i] != null) m.set(d, s.v[i]); }); return m;
  }
  const returnsOn = (m, days) => days.slice(1).map((d, k) => m.get(d) / m.get(days[k]) - 1);
  function group(list, key) { const o = {}; list.forEach(x => { const k = x[key] || "unbekannt"; o[k] = (o[k] || 0) + x.w; }); return Object.entries(o).sort((a, b) => b[1] - a[1]); }

  function compute(depot, profiles, D, W, opts = {}) {
    const fx = (D && D.fx) || { EUR: 1 }, conflict = new Set(opts.konfliktzonen || []);
    const byT = new Map((profiles || []).map(p => [p.t, p]));
    // gleiche Symbole zusammenfassen
    const merged = new Map();
    (depot || []).forEach(x => { if (!x || !x.t || !(x.qty > 0)) return; const m = merged.get(x.t) || { t: x.t, qty: 0, cost: 0 }; m.qty += x.qty; m.cost += x.qty * (x.buy || 0); merged.set(x.t, m); });
    const pos = [], missing = [];
    for (const m of merged.values()) {
      const p = byT.get(m.t);
      if (!p || !p.px || p.px.length < 30) { missing.push({ t: m.t, grund: "keine Kursreihe" }); continue; }
      const rate = p.cur === "EUR" ? 1 : fx[p.cur];
      if (!rate) { missing.push({ t: m.t, grund: "Wechselkurs " + (p.cur || "unbekannt") + " fehlt" }); continue; }
      const s = seriesOfProfile(p), last = p.px[p.px.length - 1];
      pos.push({ t: m.t, n: p.n, sec: p.sec || "unbekannt", land: p.land || "unbekannt", cur: p.cur, iso: LAND_ISO[p.land] || null,
        qty: m.qty, cost: m.cost, value: m.qty * last * rate, k: m.qty * rate, s });
    }
    const total = pos.reduce((a, x) => a + x.value, 0);
    if (!pos.length || !(total > 0)) return { ok: false, positions: pos, missing, total: 0 };
    pos.forEach(x => { x.w = x.value / total; });
    pos.sort((a, b) => b.w - a.w);

    const lastDay = Math.max(...pos.map(x => Math.max(...x.s.keys())));
    const from = lastDay - 365;
    // Einzelwerte über ihr eigenes letztes Jahr
    pos.forEach(x => {
      const days = [...x.s.keys()].filter(d => d >= from).sort((a, b) => a - b), px = days.map(d => x.s.get(d));
      const r = returnsOn(x.s, days); const v = sd(r);
      x.vol = v == null ? null : v * Math.sqrt(DAYS_YEAR); x.mdd = px.length > 1 ? maxDrawdown(px) : null;
      x.ret = px.length > 1 ? px[px.length - 1] / px[0] - 1 : null; x.n_obs = px.length;
      const e = x.iso && W && W.escalation && W.escalation[x.iso];
      x.lage = { stufe: e ? e.stufe : null, konflikt: !!(x.iso && conflict.has(x.iso)) };
    });
    // Gemeinsame Handelstage aller Positionen
    let common = [...pos[0].s.keys()].filter(d => d >= from);
    pos.slice(1).forEach(x => { common = common.filter(d => x.s.has(d)); });
    common.sort((a, b) => a - b);
    const port = { days: common.length };
    // Rückrechnung: heutige Stückzahlen × Kurs am jeweiligen Tag × heutiger Wechselkurs (Kauf-und-Halten-Wert des heutigen Depots)
    const V = { get: d => pos.reduce((s, x) => s + x.k * x.s.get(d), 0) };
    if (common.length >= 60) {
      const R = pos.map(x => returnsOn(x.s, common));
      const rp = returnsOn(V, common), vals = common.map(d => V.get(d));
      port.vol = sd(rp) * Math.sqrt(DAYS_YEAR); port.mdd = maxDrawdown(vals); port.ret = vals[vals.length - 1] / vals[0] - 1;
      port.sharpe = port.vol ? (mean(rp) * DAYS_YEAR) / port.vol : null;
      port.var95 = -quantile(rp, 0.05) * total;
      port.corr = pos.map((_, i) => pos.map((__, j) => i === j ? 1 : corr(R[i], R[j])));
      port.bench = BENCH.map(([t, name]) => {
        const b = seriesOfDash(D, t); if (!b) return { t, name, ok: false };
        const days = common.filter(d => b.has(d)); if (days.length < 60) return { t, name, ok: false };
        const rpb = returnsOn(V, days); // gleiche Rückrechnung wie oben
        const rb = returnsOn(b, days), bpx = days.map(d => b.get(d)), v = sd(rb);
        return { t, name, ok: true, ret: bpx[bpx.length - 1] / bpx[0] - 1, vol: v * Math.sqrt(DAYS_YEAR), mdd: maxDrawdown(bpx),
          beta: cov(rpb, rb) / (v * v), corr: corr(rpb, rb), days: days.length };
      });
    }
    const hhi = pos.reduce((s, x) => s + x.w * x.w, 0);
    const conc = { max: pos[0], top3: pos.slice(0, 3).reduce((s, x) => s + x.w, 0), hhi, effN: 1 / hhi };
    const struct = { sec: group(pos, "sec"), land: group(pos, "land"), cur: group(pos, "cur") };
    const fremd = pos.filter(x => x.cur !== "EUR").reduce((s, x) => s + x.w, 0);
    // Faustregeln (keine Anlageberatung) – feste, sichtbare Schwellen
    const hints = [];
    pos.filter(x => x.w > 0.2).forEach(x => hints.push(`${x.n} macht ${pct(x.w)} des Depots aus (Schwelle 20 %).`));
    struct.sec.filter(([, w]) => w > 0.4).forEach(([k, w]) => hints.push(`Branche „${k}“ ${pct(w)} (Schwelle 40 %).`));
    struct.land.filter(([, w]) => w > 0.6 && pos.length > 1).forEach(([k, w]) => hints.push(`Land „${k}“ ${pct(w)} (Schwelle 60 %).`));
    if (fremd > 0.5) hints.push(`${pct(fremd)} in Fremdwährung – Wechselkursschwankungen sind in Volatilität und Drawdown nicht enthalten.`);
    if (port.corr) pos.forEach((a, i) => pos.forEach((b, j) => { if (j > i && port.corr[i][j] > 0.8) hints.push(`${a.n} und ${b.n} bewegen sich sehr ähnlich (Korrelation ${num(port.corr[i][j], 2)}).`); }));
    // wie bei der Camera Wall (Entscheidung 28.11.2026): Konfliktlage nur über die feste Liste, nicht über die Schlagzeilen-Zählung
    pos.filter(x => x.lage.konflikt).forEach(x => hints.push(`${x.n}: Sitzland ${x.land} steht auf der Konfliktliste.`));
    return { ok: true, total, positions: pos, missing, port, conc, struct, fremd, hints, lastDay, from };
  }
  const pct = (v, d = 1) => v == null || !isFinite(v) ? "–" : (v * 100).toLocaleString("de-DE", { minimumFractionDigits: d, maximumFractionDigits: d }) + " %";
  const num = (v, d = 2) => v == null || !isFinite(v) ? "–" : v.toLocaleString("de-DE", { minimumFractionDigits: d, maximumFractionDigits: d });
  const core = { compute, maxDrawdown, sd, corr, quantile, seriesOfProfile, pct, num, LAND_ISO };
  if (typeof module !== "undefined" && module.exports) { module.exports = core; return; }

  /* ---------------- Oberfläche ---------------- */
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const eur = v => v == null || !isFinite(v) ? "–" : v.toLocaleString("de-DE", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
  const signed = v => (v > 0 ? "+" : "") + pct(v);
  const dayStr = d => new Date(d * 864e5).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "2-digit" });
  const readDepot = () => { try { return JSON.parse(localStorage.getItem("depot") || "[]"); } catch { return []; } };
  let loading = null;
  function ensureProfiles() {
    if (global.PROFILES) return Promise.resolve(global.PROFILES);
    if (loading) return loading;
    loading = new Promise(res => {
      const done = () => res(global.PROFILES || null);
      const ex = document.querySelector('script[src^="profiles.js"]');
      if (ex) { ex.addEventListener("load", done, { once: true }); ex.addEventListener("error", () => { loading = null; res(null); }, { once: true }); setTimeout(() => global.PROFILES && done(), 0); return; }
      const sc = document.createElement("script"); sc.src = "profiles.js?v=" + ((global.DASH || {}).generated || "");
      sc.onload = done; sc.onerror = () => { sc.remove(); loading = null; res(null); }; document.head.appendChild(sc);
    });
    return loading;
  }
  function run() {
    return ensureProfiles().then(P => P ? compute(readDepot(), P, global.DASH, global.WORLD, { konfliktzonen: (global.CAMS || {}).konfliktzonen || [] }) : { ok: false, error: "Kursprofile nicht ladbar" });
  }

  function bars(list, top = 6) {
    const rest = list.slice(top).reduce((s, [, w]) => s + w, 0), rows = list.slice(0, top).concat(rest > 0 ? [["Sonstige", rest]] : []);
    return `<div class="rk-bars">${rows.map(([k, w]) => `<div class="rk-bar" title="${esc(k)}: ${pct(w)}"><span class="l">${esc(k)}</span>
      <span class="b"><i style="width:${Math.max(1, w * 100).toFixed(1)}%"></i></span><span class="v">${pct(w)}</span></div>`).join("")}</div>`;
  }
  function heat(pos, C) {
    if (!C || pos.length < 2) return '<div class="muted">Ab zwei Positionen mit gemeinsamer Kurshistorie.</div>';
    const n = Math.min(pos.length, 12), P = pos.slice(0, n);
    // divergierend: negativ = Blau (--s1), positiv = Orange (--s2), 0 = neutral (transparent)
    const cell = c => { if (c == null) return '<td class="na">–</td>'; const a = Math.min(1, Math.abs(c)) * 0.75;
      return `<td style="background:${c >= 0 ? `rgba(217,89,38,${a.toFixed(2)})` : `rgba(57,135,229,${a.toFixed(2)})`}" title="Korrelation ${num(c, 2)}">${num(c, 2)}</td>`; };
    return `<div class="rk-heatwrap"><table class="rk-heat"><tr><th></th>${P.map((x, j) => `<th title="${esc(x.n)}">${j + 1}</th>`).join("")}</tr>
      ${P.map((x, i) => `<tr><th title="${esc(x.n)}">${i + 1} ${esc(x.n.length > 14 ? x.n.slice(0, 13) + "…" : x.n)}</th>${P.map((_, j) => i === j ? '<td class="self">1</td>' : cell(C[i][j])).join("")}</tr>`).join("")}</table></div>
      <div class="rk-legend"><span><i style="background:rgba(57,135,229,.75)"></i>−1 gegenläufig</span><span><i style="background:transparent;border:1px solid var(--line)"></i>0 unabhängig</span><span><i style="background:rgba(217,89,38,.75)"></i>+1 gleichläufig</span>${pos.length > n ? `<span>· nur die ${n} größten Positionen</span>` : ""}</div>`;
  }
  function render(box, R) {
    if (!R.ok) { box.innerHTML = `<div class="cw-empty"><span class="spill unavailable">NICHT VERFÜGBAR</span><b>${R.error ? esc(R.error) : "Kein auswertbares Depot in diesem Browser."}</b>
      ${(R.missing || []).length ? "Ohne Kursdaten: " + R.missing.map(m => esc(m.t) + " (" + esc(m.grund) + ")").join(", ") : "Positionen oben im Depot erfassen."}</div>`; return; }
    const p = R.port, b = p.bench || [];
    const tile = (lbl, val, sub) => `<div class="rk-tile"><span>${lbl}</span><b>${val}</b><small>${sub}</small></div>`;
    box.innerHTML = `
      <div class="rk-tiles">
        ${tile("Depotwert heute", eur(R.total), `${R.positions.length} Positionen · Schlusskurse ${dayStr(R.lastDay)}`)}
        ${tile("Volatilität p. a.", pct(p.vol), "Schwankungsbreite, 1 Jahr")}
        ${tile("Max. Drawdown", pct(p.mdd), "größter Rückgang vom Hoch, 1 Jahr")}
        ${tile("Rendite 1 Jahr", p.ret == null ? "–" : signed(p.ret), "heutige Stückzahlen, zurückgerechnet")}
        ${tile("Sharpe-Quote", num(p.sharpe), "Rendite je Risiko, ohne risikofreien Zins")}
        ${tile("Value at Risk 95 %", eur(p.var95), "1-Tages-Verlust, an 1 von 20 Tagen überschritten")}
      </div>
      ${p.days < 60 ? `<div class="cw-note">Zu wenige gemeinsame Handelstage (${p.days}) für Depot-Kennzahlen – Einzelwerte unten.</div>` : ""}
      <div class="rk-grid">
        <div><h5>Vergleich · letzte 12 Monate</h5><div class="rk-tablewrap"><table class="det rk-cmp"><tr><td></td><td>Rendite</td><td>Volatilität</td><td>Max. DD</td><td>Beta</td><td>Korr.</td></tr>
          <tr><td>Mein Depot</td><td>${p.ret == null ? "–" : signed(p.ret)}</td><td>${pct(p.vol)}</td><td>${pct(p.mdd)}</td><td>1,00</td><td>1,00</td></tr>
          ${b.map(x => x.ok ? `<tr><td>${esc(x.name)}</td><td>${signed(x.ret)}</td><td>${pct(x.vol)}</td><td>${pct(x.mdd)}</td><td>${num(x.beta)}</td><td>${num(x.corr)}</td></tr>`
            : `<tr><td>${esc(x.name)}</td><td colspan="5" class="muted">nicht verfügbar</td></tr>`).join("")}</table></div>
          <div class="al-src">Beta und Korrelation: Depot gegenüber dem Index. Beta 1,2 = Depot schwankt ~20 % stärker als der Index.</div></div>
        <div><h5>Konzentration</h5><div class="al-kv">
          <span>Größte Position</span><b>${esc(R.conc.max.n)} · ${pct(R.conc.max.w)}</b>
          <span>Top 3 zusammen</span><b>${pct(R.conc.top3)}</b>
          <span>Effektive Anzahl Positionen</span><b>${num(R.conc.effN, 1)}</b>
          <span>Fremdwährungsanteil</span><b>${pct(R.fremd)}</b></div>
          <div class="al-src">Effektive Anzahl = 1 / Summe der quadrierten Gewichte (Herfindahl). 10 gleich große Positionen = 10.</div></div>
      </div>
      <div class="rk-grid three">
        <div><h5>Branchen</h5>${bars(R.struct.sec)}</div>
        <div><h5>Länder</h5>${bars(R.struct.land)}</div>
        <div><h5>Währungen</h5>${bars(R.struct.cur)}</div>
      </div>
      <h5>Positionen · letzte 12 Monate</h5>
      <div class="rk-tablewrap"><table class="det rk-pos"><tr><td>#</td><td>Wert</td><td>Gewicht</td><td>Volatilität</td><td>Max. DD</td><td>Rendite</td><td>Land / Lage</td></tr>
        ${R.positions.map((x, i) => `<tr><td>${i + 1} ${esc(x.n)} <span class="muted">${esc(x.t)}</span></td><td>${eur(x.value)}</td><td>${pct(x.w)}</td><td>${pct(x.vol)}</td><td>${pct(x.mdd)}</td><td>${x.ret == null ? "–" : signed(x.ret)}</td>
          <td>${esc(x.land)}${x.lage.konflikt ? ' <span class="spill offline" title="Sitzland auf der Konfliktliste">KONFLIKT</span>' : x.lage.stufe >= 3 ? ` <span class="spill delayed" title="Eskalationsstufe laut Schlagzeilen-Zählung">STUFE ${x.lage.stufe}</span>` : ""}</td></tr>`).join("")}</table></div>
      ${R.missing.length ? `<div class="al-src">Nicht berücksichtigt (keine Kurs-/Wechselkursdaten): ${R.missing.map(m => esc(m.t) + " – " + esc(m.grund)).join(", ")}</div>` : ""}
      <h5>Korrelation der Tagesrenditen</h5>${heat(R.positions, p.corr)}
      <h5>Hinweise <span class="muted">· Faustregeln mit festen Schwellen, keine Anlageberatung</span></h5>
      ${R.hints.length ? `<ul class="al-list">${R.hints.map(h => `<li>${esc(h)}</li>`).join("")}</ul>` : '<div class="muted">Keine Schwelle überschritten.</div>'}
      <div class="al-src">Methodik: Schlusskurse aus profiles.js (Bot, Yahoo Finance), Zeitraum ${dayStr(R.from)}–${dayStr(R.lastDay)}, ${p.days} gemeinsame Handelstage.
        Depotkennzahlen sind eine Rückrechnung: heutige Stückzahlen × damaliger Kurs × heutiger Wechselkurs (hypothetisch, nicht die tatsächliche Wertentwicklung mit Käufen und Verkäufen).
        Kurse in Handelswährung; Wechselkursschwankungen sind nicht enthalten (keine historischen Kurse vorhanden), der Depotwert nutzt den aktuellen Kurs.
        Korrelationen aus Tagesrenditen: Wegen unterschiedlicher Börsenschlusszeiten (z. B. USA/Europa/Asien) fallen sie zwischen Regionen eher zu niedrig aus.
        Lage: Hinweis nur bei Sitzland auf der Konfliktliste; die Eskalationsstufe (Schlagzeilen-Zählung) steht als Info in der Tabelle. Alle Berechnungen nur in diesem Browser.</div>`;
  }

  function mount() {
    const host = document.getElementById("riskCenter"); if (!host) return;
    host.innerHTML = `<details class="risk" id="riskBox"><summary><span class="radar" aria-hidden="true"></span> // Portfolio Risk Center
      <span class="sub">Volatilität · Drawdown · Konzentration · Korrelation · Benchmark · Lage</span></summary><div class="rk-body"><div class="muted">Wird beim Öffnen berechnet …</div></div></details>`;
    const det = host.querySelector("details"), body = host.querySelector(".rk-body");
    const refresh = () => { if (!det.open) return; body.innerHTML = '<div class="muted">Berechne …</div>'; run().then(R => render(body, R)); };
    det.addEventListener("toggle", refresh);
    let t = null; const list = document.getElementById("dList2");
    if (list) new MutationObserver(() => { clearTimeout(t); t = setTimeout(refresh, 400); }).observe(list, { childList: true });
    if (localStorage.getItem("riskOpen") === "1") det.open = true;
    det.addEventListener("toggle", () => { try { localStorage.setItem("riskOpen", det.open ? "1" : "0"); } catch {} });
  }
  global.TB_risk = { ...core, run, ensureProfiles, render, depotCount: () => readDepot().length };
  mount();
})(typeof window !== "undefined" ? window : globalThis);
