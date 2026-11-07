/* TradeBot Investment Intelligence – Hauptnavigation und Research-Module.
   Datenbasis: window.RESEARCH (docs/research.js, täglich aus bot/research.py). Alle Scores, Fair Values und
   Szenarien werden hier transparent aus den gelieferten Rohdaten berechnet; Gewichte und Annahmen sind editierbar. */
(() => {
"use strict";
const store = { get(k) { try { return localStorage.getItem(k); } catch { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch {} } };
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const nf = (v, d = 1) => v == null || !isFinite(v) ? "–" : v.toLocaleString("de-DE", { minimumFractionDigits: d, maximumFractionDigits: d });
const pc = (v, d = 1, sign = true) => v == null || !isFinite(v) ? "–" : (sign && v > 0 ? "+" : "") + nf(v * 100, d) + " %";
const cl = v => v == null ? "muted" : v > 0 ? "up" : v < 0 ? "down" : "muted";
const big = (v, cur = "") => { if (v == null || !isFinite(v)) return "–"; const a = Math.abs(v);
  const [d, u] = a >= 1e12 ? [1e12, " Bio."] : a >= 1e9 ? [1e9, " Mrd."] : a >= 1e6 ? [1e6, " Mio."] : [1, ""]; return nf(v / d, a >= 1e9 ? 2 : 1) + u + (cur ? " " + cur : ""); };
const NODATA = '<span class="muted">Keine belastbare Datengrundlage vorhanden.</span>';
const dfmt = s => s ? new Date(s).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" }) : "–";
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

/* ------------------------------------------------------------ Hauptnavigation */
const AREAS = [
  ["overview", "Market Overview", ["h-regime", "h-ovsum", "h-main", "h-com", "h-src"]],
  ["sector", "Sector Intelligence", ["h-sint", "h-bt", "h-sec"]],
  ["screener", "Stock Screener", ["h-scr", "h-picks"]],
  ["research", "Equity Research", ["h-eq"]],
  ["valuation", "Valuation", ["h-val"]],
  ["risk", "Risk Monitor", ["h-risk"]],
  ["macro", "Macro Intelligence", ["h-macro", "h-world"]],
  ["news", "News & Catalysts", ["h-news", "h-cat"]],
  ["watch", "Watchlist", ["h-depot", "h-wl", "h-log"]],
];
const areaOf = {}; AREAS.forEach(([k, , ids]) => ids.forEach(id => areaOf[id] = k));
const nav = document.getElementById("areanav");
nav.innerHTML = AREAS.map(([k, l], i) => `<button type="button" data-area="${k}"><span class="n">${i + 1}</span>${esc(l)}</button>`).join("");
let current = store.get("area") || "overview";
function show(area, opts = {}) {
  if (!AREAS.some(a => a[0] === area)) area = "overview";
  current = area; store.set("area", area);
  document.querySelectorAll("section.panel").forEach(s => s.classList.toggle("area-hidden", areaOf[s.getAttribute("aria-labelledby")] !== area));
  nav.querySelectorAll("button").forEach(b => b.setAttribute("aria-current", b.dataset.area === area ? "page" : "false"));
  if (!opts.keepScroll) scrollTo({ top: 0 });
  renderArea(area);
  setTimeout(() => { dispatchEvent(new Event("resize")); try { window.TB_renderAll && window.TB_renderAll(); } catch (e) {} }, 40);
}
nav.addEventListener("click", e => { const b = e.target.closest("button[data-area]"); if (b) show(b.dataset.area); });
document.addEventListener("click", e => {
  const a = e.target.closest("[data-goto]"); if (a) { e.preventDefault(); show(a.dataset.goto); }
  const o = e.target.closest("[data-rx]"); if (o) { e.preventDefault(); RX.open(o.dataset.rx, o.dataset.rxArea || "research"); }
});

/* ------------------------------------------------------------ Daten laden */
let R = null, loadState = "loading";
function loadData() {
  const sc = document.createElement("script"); sc.src = "research.js?t=" + Math.floor(Date.now() / 600000);
  sc.onload = () => { R = window.RESEARCH || null; loadState = R ? "ok" : "failed"; prep(); renderArea(current); headPill(); };
  sc.onerror = () => { R = null; loadState = "failed"; renderArea(current); };
  document.head.appendChild(sc);
}
const box = id => document.getElementById(id);
function pending(id) {
  const el = box(id); if (!el) return true;
  if (!R) { el.innerHTML = loadState === "loading" ? '<div class="muted">Research-Daten werden geladen …</div>'
    : '<div class="empty">Noch keine Research-Daten. Sie entstehen beim täglichen Lauf „Research-Daten“ (GitHub Actions).</div>'; return true; }
  return false;
}

/* ------------------------------------------------------------ Gewichtungen & Scores */
const SEC_F = [["valuation", "Bewertung", 20], ["fundamental", "Fundamental", 20], ["momentum", "Earnings Momentum", 20], ["strength", "Relative Stärke", 15], ["macro", "Makro", 15], ["risk", "Risiko", 10]];
const STK_F = [["quality", "Qualität", 25], ["valuation", "Bewertung", 20], ["growth", "Wachstum", 15], ["momentum", "Earnings Momentum", 15], ["strength", "Relative Stärke", 15], ["risk", "Risiko", 10]];
function weights(key, F) { try { const w = JSON.parse(store.get(key) || "null"); if (w && F.every(([k]) => typeof w[k] === "number")) return w; } catch (e) {} return Object.fromEntries(F.map(([k, , d]) => [k, d])); }
let wSec = weights("wSec", SEC_F), wStk = weights("wStk", STK_F);
function composite(z, w, F) {
  let s = 0, ws = 0, tot = 0;
  F.forEach(([k]) => { tot += w[k]; if (z && z[k] != null && w[k] > 0) { s += w[k] * z[k]; ws += w[k]; } });
  return ws >= tot * 0.5 && ws > 0 ? s / ws : null;
}
function standardize(map) {   // Gesamtscore als Perzentil im Querschnitt (0 = schwächster, 1 = stärkster Wert)
  const v = Object.values(map).filter(x => x != null).sort((a, b) => a - b); if (v.length < 2) return map;
  const rank = x => { let lo = 0, hi = v.length; while (lo < hi) { const m = (lo + hi) >> 1; v[m] < x ? lo = m + 1 : hi = m; } let eq = lo; while (eq < v.length && v[eq] === x) eq++; return ((lo + eq - 1) / 2) / (v.length - 1); };
  return Object.fromEntries(Object.entries(map).map(([k, x]) => [k, x == null ? null : rank(x)]));
}
let secZC = null, secStat = null, stkZC = null;
function secScores() {
  if (secZC) return secZC;
  const raw = Object.fromEntries(SECT.map(s => [s.key, composite(s.z, wSec, SEC_F)]));
  secStat = Object.values(raw).filter(x => x != null).sort((a, b) => a - b);
  return secZC = standardize(raw);
}
const secZ = s => secScores()[s.key];
const secZ4 = s => { secScores(); const r = s.z_4w ? composite(s.z_4w, wSec, SEC_F) : null; if (r == null || secStat.length < 2) return null;
  return secStat.filter(x => x < r).length / (secStat.length - 1); };   // Perzentil des damaligen Werts in der heutigen Verteilung
function stkScores() { return stkZC || (stkZC = standardize(Object.fromEntries(STK.map(s => [s.t, composite(s.z, wStk, STK_F)])))); }
const toScore = p => p == null ? null : Math.round(clamp(p, 0, 1) * 100);           // Gesamtscore = Perzentil
const fsc = z => z == null ? null : Math.round(clamp(50 + 20 * z, 0, 100));           // Faktorwert = 50 + 20 × z
const CLASSES = [[0.9, "Strongly Attractive", "c1"], [0.7, "Attractive", "c2"], [0.3, "Neutral", "c3"], [0.1, "Weak", "c4"], [-Infinity, "Avoid / High Risk", "c5"]];
const klass = (p, capped) => { if (p == null) return ["unvollständig", "c0"]; let c = CLASSES.find(([t]) => p >= t) || CLASSES[4]; if (capped && c === CLASSES[0]) c = CLASSES[1]; return c.slice(1); };
const badge = (p, capped) => { const [l, c] = klass(p, capped); return `<span class="kls ${c}"${capped && p >= 0.9 ? ' title="Wegen bestätigter Red Flag höchstens Attractive"' : ""}>${l}</span>`; };
const sbadge = s => badge(stockZ(s), confirmed(s) > 0);
const sub = z => z == null ? '<span class="muted">–</span>' : `<span class="sub ${z > 0.25 ? "up" : z < -0.25 ? "down" : ""}">${fsc(z)}</span>`;
function weightEditor(id, F, w, onChange) {
  const el = box(id);
  el.innerHTML = `<details class="wts"><summary>Gewichtung anpassen (aktuell: ${F.map(([k, l]) => `${l} ${w[k]} %`).join(" · ")})</summary>
    <div class="wgrid">${F.map(([k, l]) => `<label>${l}<input type="range" min="0" max="50" step="5" value="${w[k]}" data-k="${k}"><b>${w[k]} %</b></label>`).join("")}</div>
    <button type="button" class="tbtn reset">Standard</button> <span class="muted">Summe wird automatisch normiert. Fehlende Faktoren werden herausgerechnet; ab weniger als 50 % verfügbarem Gewicht gilt der Score als unvollständig.</span></details>`;
  el.querySelectorAll("input").forEach(i => i.addEventListener("input", () => { w[i.dataset.k] = +i.value; i.nextElementSibling.textContent = i.value + " %"; onChange(); }));
  el.querySelector(".reset").addEventListener("click", () => { F.forEach(([k, , d]) => w[k] = d); weightEditor(id, F, w, onChange); onChange(); });
}

/* ------------------------------------------------------------ Bewertungsmodelle */
function waccOf(v, ov = {}) {
  const rf = ov.rf ?? v.rf, erp = ov.erp ?? v.erp, beta = ov.beta ?? (v.beta == null ? 1 : 0.67 * clamp(v.beta, 0.3, 2.5) + 0.33);
  const ke = rf + beta * erp;
  const kd = clamp(v.intrate ?? rf + 0.015, rf + 0.005, rf + 0.06), tax = ov.tax ?? v.tax ?? 0.25;
  const E = v.px * v.shares, Dv = Math.max(0, v.debt || 0);
  return { ke, kd, beta, rf, erp, wacc: ov.wacc ?? (E + Dv > 0 ? (E * ke + Dv * kd * (1 - tax)) / (E + Dv) : ke), E, D: Dv };
}
function growthPath(g1, g2, tg) { const p = [g1, g2]; for (let i = 3; i <= 10; i++) p.push(g2 + (tg - g2) * (i - 2) / 8); return p; }
function dcfValue(v, a) {
  let rev = v.rev, pv = 0, fcf = 0;
  const path = growthPath(a.g1, a.g2, a.tg), rows = [];
  for (let t = 1; t <= 10; t++) {
    rev *= 1 + path[t - 1];
    const ebit = rev * a.margin;
    fcf = ebit * (1 - a.tax) + rev * a.da - rev * a.capex - rev * a.nwc;
    pv += fcf / Math.pow(1 + a.wacc, t);
    rows.push({ t, g: path[t - 1], rev, ebit, fcf });
  }
  const tv = fcf * (1 + a.tg) / (a.wacc - a.tg), pvtv = tv / Math.pow(1 + a.wacc, 10);
  const ev = pv + pvtv, eq = ev - (v.net_debt || 0);
  return { fv: eq / v.shares, ev, eq, pv, pvtv, tvShare: pvtv / ev, rows };
}
function dcfAssumptions(v, ov = {}) {
  const W = waccOf(v, ov);
  const g1 = ov.g1 ?? v.g0 ?? v.g_cagr3 ?? 0.03, g2 = ov.g2 ?? v.g1 ?? g1;
  return { g1: clamp(g1, -0.3, 0.6), g2: clamp(g2, -0.3, 0.6), margin: ov.margin ?? v.opm ?? v.opm_last, tax: ov.tax ?? v.tax ?? 0.25,
    da: ov.da ?? v.da ?? 0, capex: ov.capex ?? v.capex ?? 0, nwc: ov.nwc ?? v.nwc ?? 0, tg: ov.tg ?? v.tg, wacc: Math.max(W.wacc, (ov.tg ?? v.tg) + 0.02), W };
}
function dcfReady(v) {
  if (!v) return "Keine Bewertungsdaten";
  const miss = [["rev", "Umsatz"], ["px", "Kurs"], ["shares", "Aktienzahl"], ["rf", "risikofreier Zins"]].filter(([k]) => v[k] == null).map(([, l]) => l);
  if (v.opm == null && v.opm_last == null) miss.push("operative Marge");
  if (miss.length) return "Fehlende Daten: " + miss.join(", ");
  if ((v.opm ?? v.opm_last) <= 0) return "Negative operative Marge – ein DCF wäre nicht aussagekräftig";
  return null;
}
function scenarios(v, ov = {}) {
  if (v.method === "residual_income") return riScen(v, ov);
  const bad = dcfReady(v); if (bad) return { error: bad };
  const base = dcfAssumptions(v, ov);
  const dB = ov.bearG ?? Math.max(0.03, 0.4 * Math.abs(base.g1)), dU = ov.bullG ?? Math.max(0.02, 0.3 * Math.abs(base.g1));
  const mB = ov.bearM ?? 0.85, mU = ov.bullM ?? 1.1;
  const bear = { ...base, g1: base.g1 - dB, g2: base.g2 - dB, margin: base.margin * mB, wacc: base.wacc + 0.01 };
  const bull = { ...base, g1: base.g1 + dU, g2: base.g2 + dU, margin: Math.min(base.margin * mU, base.margin + 0.05), wacc: Math.max(base.tg + 0.02, base.wacc - 0.005) };
  const out = { method: "DCF (Free Cashflow to Firm, 10 Jahre + Endwert)", base: { a: base, ...dcfValue(v, base) }, bear: { a: bear, ...dcfValue(v, bear) }, bull: { a: bull, ...dcfValue(v, bull) } };
  out.implied = impliedGrowth(v, base);
  return out;
}
function impliedGrowth(v, a) {   // Reverse-DCF: welches Wachstum steckt im Kurs?
  let lo = -0.3, hi = 0.8;
  const f = g => dcfValue(v, { ...a, g1: g, g2: g }).fv - v.px;
  if (f(lo) > 0 || f(hi) < 0) return null;
  for (let i = 0; i < 50; i++) { const m = (lo + hi) / 2; f(m) > 0 ? hi = m : lo = m; }
  return (lo + hi) / 2;
}
function riScen(v, ov = {}) {
  if (v.equity == null || v.shares == null || v.roe == null || v.rf == null || v.px == null) return { error: "Fehlende Daten für das Residual-Income-Modell (Eigenkapital, ROE, Zins)" };
  const W = waccOf(v, ov), tg = ov.tg ?? v.tg, bvps = v.equity / v.shares;
  const calc = (roe, coe) => coe > tg + 0.005 ? { fv: bvps * Math.max(0, (roe - tg) / (coe - tg)), pb: (roe - tg) / (coe - tg), roe, coe } : { fv: null, roe, coe };
  const roe = ov.roe ?? v.roe;
  return { method: "Residual Income (gerechtfertigtes KBV = (ROE − g) / (Eigenkapitalkosten − g))", ri: true, bvps,
    base: { ...calc(roe, W.ke), a: { W, tg } }, bear: { ...calc(roe - 0.03, W.ke + 0.01), a: { W, tg } }, bull: { ...calc(roe + 0.02, W.ke - 0.005), a: { W, tg } } };
}
const valCache = {};
function fair(s) { if (!(s.t in valCache)) { const sc = scenarios(s.val || {}); valCache[s.t] = sc.error ? null : sc; } return valCache[s.t]; }
const upside = s => { const f = fair(s); return f && f.base.fv != null && s.val.px ? f.base.fv / s.val.px - 1 : null; };

/* ------------------------------------------------------------ Vorbereitung */
let STK = [], BY = {}, SECT = [];
const SECTOR_MAP = { Technology: "it", "Financial Services": "fin", Healthcare: "health", Energy: "energy", Industrials: "industrials", Utilities: "utilities",
  "Consumer Defensive": "staples", "Consumer Cyclical": "discretionary", "Real Estate": "realestate", "Basic Materials": "materials", "Communication Services": "comm" };
function prep() {
  if (!R) return;
  STK = R.stocks.rows; BY = Object.fromEntries(STK.map(s => [s.t, s])); SECT = R.sectors.rows;
  Object.keys(valCache).forEach(k => delete valCache[k]); secZC = stkZC = null;
}
const warnings = () => Object.values(R.regime.indicators).filter(i => i.vote != null && (i.axis === "inflation" ? i.vote > 0 : i.vote < 0));
const riskScore = z => z == null ? null : Math.round(clamp(50 - 20 * z, 0, 100));   // hoch = riskanter
const stockZ = s => stkScores()[s.t];
const confirmed = s => (s.flags || []).filter(f => f.level === "confirmed").length;
const flagBadges = s => { const c = { confirmed: 0, potential: 0, dq: 0 }; (s.flags || []).forEach(f => c[f.level]++);
  return `${c.confirmed ? `<span class="fl confirmed" title="Bestätigte Risiken">${c.confirmed}</span>` : ""}${c.potential ? `<span class="fl potential" title="Potenzielle Risiken">${c.potential}</span>` : ""}${c.dq ? `<span class="fl dq" title="Datenqualitäts-Hinweise">${c.dq}</span>` : ""}` || '<span class="muted">–</span>'; };
const region = s => /\.(DE|PA|AS|MI|SW|CO|L|MC|HE|ST|OL)$/.test(s.t) ? "Europa" : /\.(T|HK|KS|AX)$/.test(s.t) ? "Asien-Pazifik" : "USA";

/* ------------------------------------------------------------ Metrik-Formatierung */
const YIELD = new Set(["ey", "fwd_ey", "by", "sy", "cfy", "ev_ebitda_y", "fcf_y", "sales_y", "book_y"]);
const MULT = { ey: "KGV", fwd_ey: "Fwd-KGV", by: "KBV", sy: "KUV", cfy: "KCV", ev_ebitda_y: "EV/EBITDA", sales_y: "EV/Umsatz", book_y: "KBV" };
const CHANGE = new Set(["rev_g", "eps_g", "rs3", "rs6", "rs12", "r12_1", "r6", "trend", "eps_rev_1y", "eps_rev_0y", "surprise", "tailwind", "rev_cagr3", "rev_g_next", "eps_g_next", "volume"]);
function fmtMetric(k, v) {
  if (v == null) return "–";
  if (YIELD.has(k)) return pc(v, 1, false) + (MULT[k] && v > 0 ? ` <span class="muted">(≙ ${MULT[k]} ${nf(1 / v, 1)})</span>` : "");
  if (["beta"].includes(k)) return nf(v, 2);
  if (["int_cov", "nd_ebitda", "cash_conv"].includes(k)) return nf(v, 1) + "×";
  if (k === "breadth") return (v > 0 ? "+" : "") + nf(v, 2);
  if (k === "regime_fit") return pc(v, 2) + " / Monat";
  if (k === "mdd") return pc(-v, 1);
  return pc(v, 1, CHANGE.has(k));
}

function headPill() {
  const el = document.getElementById("regime"); if (!el || !R) return;
  el.innerHTML = `Regime: <b>${esc(R.regime.quadrant || "–")}</b> · ${esc(R.regime.risk || "–")}`; el.title = "Regelbasierte Indikator-Abstimmung – Details unter Market Overview";
}
/* ============================================================ 1 MARKET OVERVIEW */
const QUAD_TXT = { "Inflationary Growth": "Wachstum + steigender Preisdruck", "Disinflationary Growth": "Wachstum bei nachlassender Inflation",
  "Stagflation": "Schwaches Wachstum + hohe Inflation", "Stagflation-Risiko": "Wachstum unentschieden, Inflation hoch", "Slowdown": "Wachstum lässt nach",
  "Recession": "Mehrere Rezessionssignale" };
const PHASE_DE = { "Recession": "Rezession", "Recovery": "Erholung", "Early Cycle": "Früher Zyklus", "Mid Cycle": "Mittlerer Zyklus", "Late Cycle": "Später Zyklus" };
function axisBar(a, label, posTxt, negTxt) {
  if (!a || a.score == null) return `<div class="axis"><b>${label}</b> ${NODATA}</div>`;
  const x = (a.score + 1) / 2 * 100;
  return `<div class="axis"><div class="ah"><b>${label}</b><span>${a.score > 0.2 ? posTxt : a.score < -0.2 ? negTxt : "unentschieden"} · Sicherheit: <b>${a.certainty}</b></span></div>
    <div class="abar"><i style="left:${x}%"></i></div><div class="muted small">${a.pro} dafür · ${a.contra} dagegen · ${a.neutral} neutral (${a.n} von ${a.of} Indikatoren verfügbar)</div></div>`;
}
function renderRegime() {
  if (pending("rgBody")) return;
  const g = R.regime, p = g.previous || {}, ind = Object.values(g.indicators);
  const vote = v => v == null ? '<span class="muted">○</span>' : v > 0 ? '<span class="up">▲</span>' : v < 0 ? '<span class="down">▼</span>' : '<span class="muted">■</span>';
  const fmtV = i => i.value == null ? '<span class="muted">keine Daten</span>' : nf(i.value, Math.abs(i.value) >= 100 ? 0 : 2) + " " + esc(i.unit);
  const changed = (a, b) => a === b ? '<span class="muted">unverändert</span>' : `<span class="warn">vorher: ${esc(b || "–")}</span>`;
  const ph = g.phases.find(x => x.phase === g.phase);
  box("rgBody").innerHTML = `<div class="rg">
    <div class="rgmain"><div class="muted small">AKTUELLES MARKTREGIME (Stand ${dfmt(g.asof)})</div>
      <div class="rgq">${esc(g.quadrant || "unbestimmt")}</div><div class="muted">${esc(QUAD_TXT[g.quadrant] || "")}</div>
      <div class="rgtags"><span class="tag ${g.risk === "Risk-On" ? "up" : g.risk === "Risk-Off" ? "down" : ""}">${esc(g.risk || "–")}</span>
        <span class="tag">${esc(PHASE_DE[g.phase] || g.phase)} · ${g.phase_met}/${g.phase_of} Kriterien</span></div>
      <div class="small" style="margin-top:8px">Vor 3 Monaten (${dfmt(p.asof)}): ${esc(p.quadrant || "–")} · ${esc(p.risk || "–")} · ${esc(PHASE_DE[p.phase] || p.phase || "–")}<br>
        Regime: ${changed(g.quadrant, p.quadrant)} · Risiko: ${changed(g.risk, p.risk)} · Phase: ${changed(g.phase, p.phase)}</div></div>
    <div class="rgaxes">${axisBar(g.axes.growth, "Wachstum", "expandiert", "schwächt sich ab")}${axisBar(g.axes.inflation, "Inflation", "erhöht/steigend", "nachlassend")}
      ${axisBar(g.axes.risk, "Risikoappetit", "Risk-On", "Risk-Off")}</div></div>
    <details><summary>Begründung: alle Indikatoren, Schwellen und Quellen</summary>
      <table class="dt"><thead><tr><th>Indikator</th><th>Wert</th><th>Stimme</th><th>Regel</th><th>Stand</th><th>Quelle</th></tr></thead><tbody>
      ${ind.map(i => `<tr><td>${esc(i.name)} <span class="muted small">${{ growth: "Wachstum", inflation: "Inflation", risk: "Risiko", policy: "Geldpolitik" }[i.axis]}</span></td><td>${fmtV(i)}</td><td>${vote(i.vote)}</td><td class="small">${esc(i.rule)}</td><td>${dfmt(i.asof)}</td><td class="small">${esc(i.source)}</td></tr>`).join("")}
      </tbody></table>
      <div class="small" style="margin-top:8px"><b>Zyklusphase – erfüllte Kriterien je Phase:</b> ${g.phases.map(x => `${esc(PHASE_DE[x.phase])} ${x.met}/${x.of}`).join(" · ")}</div>
      ${ph ? `<ul class="small">${ph.criteria.map(c => `<li>${c.ok ? "✔" : "✘"} ${esc(c.text)}</li>`).join("")}</ul>` : ""}
      <p class="muted small">${esc(g.method)}</p></details>`;
}
function macroTiles() {
  const want = ["DGS10", "DGS2", "T10Y3M", "IRLTLT01DEM156N", "DFF", "ECBDFR", "BAMLH0A0HYM2", "VIXCLS", "CPILFESL", "CP0000EZ19M086NEST", "UNRATE"];
  const M = Object.fromEntries(R.macro.map(m => [m.id, m]));
  return `<div class="tiles">${want.map(id => M[id]).filter(Boolean).map(m => `<div class="tile" title="${esc(m.source)} · ${esc(m.freq)}">
    <div class="tl">${esc(m.label)}</div><div class="tv">${m.value == null ? "–" : nf(m.value, 2)} <small>${esc(m.unit === "%" || m.unit === "Prozentpunkte" ? (m.unit === "%" ? "%" : "pp") : "")}</small></div>
    <div class="small"><span class="${m.d3m == null ? "muted" : ""}">Δ 3 M ${m.d3m == null ? "–" : (m.d3m > 0 ? "+" : "") + nf(m.d3m, 2)}</span> · <span class="muted">${dfmt(m.asof)}</span></div></div>`).join("")}</div>`;
}
function renderOverview() {
  if (pending("ovBody")) return;
  const sec = SECT.map(s => ({ s, z: secZ(s) })).filter(x => x.z != null).sort((a, b) => b.z - a.z);
  const opp = STK.map(s => ({ s, z: stockZ(s) })).filter(x => x.z != null && !confirmed(x.s)).sort((a, b) => b.z - a.z).slice(0, 6);
  const risky = STK.map(s => ({ s, c: confirmed(s), p: (s.flags || []).filter(f => f.level === "potential").length })).filter(x => x.c >= 2).sort((a, b) => b.c - a.c || b.p - a.p).slice(0, 6);
  const mk = warnings();
  const cat = R.catalysts;
  const secRow = x => `<li><a href="#" data-goto="sector">${esc(x.s.name)}</a> ${badge(x.z)} <span class="muted small">Score ${toScore(x.z)}</span></li>`;
  box("ovBody").innerHTML = `${macroTiles()}
    <div class="g3">
      <div class="card"><h3>Branchenranking</h3><div class="muted small">Stärkste</div><ol>${sec.slice(0, 5).map(secRow).join("")}</ol>
        <div class="muted small">Schwächste</div><ol start="${sec.length - 2}">${sec.slice(-3).map(secRow).join("")}</ol>
        <a href="#" data-goto="sector" class="more">Alle Branchen & Methodik →</a></div>
      <div class="card"><h3>Interessanteste Unternehmen</h3><div class="muted small">Höchster Gesamtscore ohne bestätigte Red Flags – keine Kaufempfehlung</div>
        <ol>${opp.map(x => `<li><a href="#" data-rx="${esc(x.s.t)}">${esc(x.s.n)}</a> ${sbadge(x.s)} <span class="muted small">${toScore(x.z)} · DCF ${pc(upside(x.s), 0)}</span></li>`).join("") || `<li>${NODATA}</li>`}</ol>
        <a href="#" data-goto="screener" class="more">Zum Screener →</a></div>
      <div class="card"><h3>Größte Risiken</h3>
        ${mk.length ? `<div class="muted small">Markt (Regime-Indikatoren mit Warnsignal)</div><ul>${mk.map(i => `<li><span class="down">●</span> ${esc(i.name)}: ${nf(i.value, 2)} ${esc(i.unit)}</li>`).join("")}</ul>` : '<div class="muted small">Kein Regime-Indikator im Warnbereich.</div>'}
        <div class="muted small">Unternehmen mit mehreren bestätigten Red Flags</div>
        <ul>${risky.map(x => `<li><a href="#" data-rx="${esc(x.s.t)}">${esc(x.s.n)}</a> ${flagBadges(x.s)} <span class="small">${esc(x.s.flags.filter(f => f.level === "confirmed").map(f => f.text).slice(0, 2).join(", "))}</span></li>`).join("") || "<li class='muted'>keine</li>"}</ul>
        <a href="#" data-goto="risk" class="more">Zum Risk Monitor →</a></div>
    </div>
    <div class="card"><h3>Anstehende Katalysatoren</h3><div class="g2">
      <div><div class="muted small">Quartalszahlen (nächste 14 Tage)</div><ul>${cat.earnings.filter(e => (new Date(e.date) - Date.now()) / 864e5 <= 14).slice(0, 10).map(e => `<li>${dfmt(e.date)} · <a href="#" data-rx="${esc(e.t)}">${esc(e.n)}</a>${e.eps_avg != null ? ` <span class="muted small">EPS-Konsens ${nf(e.eps_avg, 2)}</span>` : ""}</li>`).join("") || "<li class='muted'>keine</li>"}</ul></div>
      <div><div class="muted small">Jüngste Analysten-Hoch-/Herabstufungen</div><ul>${cat.actions.slice(0, 8).map(a => `<li>${dfmt(a.date)} · <a href="#" data-rx="${esc(a.t)}">${esc(a.n)}</a> <span class="${a.action === "up" ? "up" : a.action === "down" ? "down" : ""}">${a.action === "up" ? "▲ Upgrade" : a.action === "down" ? "▼ Downgrade" : "Neu"}</span> <span class="small">${esc(a.firm)}: ${esc(a.from || "")}→${esc(a.to || "")}</span></li>`).join("") || "<li class='muted'>keine</li>"}</ul></div>
    </div><a href="#" data-goto="news" class="more">News & Catalysts →</a></div>`;
}
function renderSources() {
  if (pending("srcBody")) return;
  const s = R.sources, st = R.fetch_stats || {};
  box("srcBody").innerHTML = `<table class="dt"><tbody>
    <tr><td>Kurse</td><td>${esc(s.prices)}</td></tr><tr><td>Unternehmensdaten</td><td>${esc(s.fundamentals)}</td></tr>
    <tr><td>Makro</td><td>${esc(s.macro)}</td></tr><tr><td>ETF-Daten</td><td>${esc(s.etf)}</td></tr><tr><td>Nicht verwendet</td><td>${esc(s.not_used)}</td></tr>
    <tr><td>Datenstand</td><td>Research-Lauf ${dfmt(R.generated)} ${new Date(R.generated).toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" })} · Laufzeit ${R.runtime_s} s</td></tr>
    <tr><td>Abdeckung</td><td>${Object.entries(st).map(([k, v]) => `${{ info: "Kennzahlen", est: "Schätzungen", lest: "Schätzungen ETF-Positionen", events: "Termine/Analysten", stm: "Jahresabschlüsse", fund: "ETF-Daten" }[k] || k}: ${v.cached}/${v.requested}`).join(" · ")}</td></tr>
    </tbody></table>
    <p class="small muted">Datenarten: <b>Tagesschluss</b> (Kurse, verzögert, keine Echtzeit) · <b>Ist-Werte</b> (Jahres-/Quartalsabschlüsse, amtliche Statistik) · <b>Konsens</b> (Analystenschätzungen) · <b>Modell</b> (Scores, Regime, Fair Values – Annahmen jeweils sichtbar). Abrufzeit je Unternehmen unter Equity Research → Quellen.</p>`;
}

/* ============================================================ 2 SECTOR INTELLIGENCE */
let secOpen = null;
function renderSectors() {
  if (pending("siBody")) return;
  weightEditor("siW", SEC_F, wSec, () => { store.set("wSec", JSON.stringify(wSec)); secZC = null; drawSectorTable(); });
  drawSectorTable();
}
function drawSectorTable() {
  const rows = SECT.map(s => ({ s, z: secZ(s), z4: secZ4(s) }))
    .sort((a, b) => (b.z ?? -9) - (a.z ?? -9));
  const trend = x => x.z != null && x.z4 != null ? `<span class="${cl(x.z - x.z4)}" title="Veränderung in Perzentilpunkten ggü. vor 4 Wochen">${x.z - x.z4 > 0.05 ? "▲" : x.z - x.z4 < -0.05 ? "▼" : "■"} ${nf(100 * (x.z - x.z4), 0)}</span>`
    : x.s.z.strength != null && x.s.strength_prev != null ? `<span class="${cl(x.s.z.strength - x.s.strength_prev)}" title="Nur relative Stärke ggü. vor 4 Wochen (Gesamtscore-Historie baut sich täglich auf)">${x.s.z.strength - x.s.strength_prev > 0.1 ? "▲" : x.s.z.strength - x.s.strength_prev < -0.1 ? "▼" : "■"} RS</span>` : "–";
  box("siTable").innerHTML = `<div class="tscroll"><table class="dt rank"><thead><tr><th>#</th><th>Branche</th><th>Score</th><th>Klasse</th><th title="Veränderung des Gesamtscores ggü. vor 4 Wochen">Trend</th>
    ${SEC_F.map(([k, l]) => `<th title="0–100, 50 = Durchschnitt der Branchen">${l}${k === "risk" ? "<br><span class='muted small'>hoch = sicherer</span>" : ""}</th>`).join("")}</tr></thead><tbody>
    ${rows.map((x, i) => `<tr class="click${secOpen === x.s.key ? " open" : ""}" data-sec="${x.s.key}"><td>${i + 1}</td><td><b>${esc(x.s.name)}</b><div class="muted small">${x.s.proxy === "Korb" ? "" : esc(x.s.proxy) + " · "}${esc(x.s.gics)}</div></td>
      <td><b>${toScore(x.z) ?? "–"}</b></td><td>${badge(x.z)}</td><td>${trend(x)}</td>${SEC_F.map(([k]) => `<td title="Abdeckung ${esc(x.s.cov[k] || "")}">${sub(x.s.z[k])}</td>`).join("")}</tr>
      ${secOpen === x.s.key ? `<tr class="detail"><td colspan="${5 + SEC_F.length}">${sectorDetail(x.s, x.z)}</td></tr>` : ""}`).join("")}</tbody></table></div>
    <p class="small muted">Score: Je Kennzahl Z-Wert im Querschnitt der ${SECT.length} Branchen (winsorisiert ±2,5) → Faktor = Mittel seiner Kennzahlen → gewichteter Durchschnitt der Faktoren → Gesamtscore = Perzentil (0–100) im Branchenvergleich. Faktorspalten: 50 + 20 × z (50 = Durchschnitt). Klassen: ab 90 Strongly Attractive · ab 70 Attractive · ab 30 Neutral · ab 10 Weak · darunter Avoid / High Risk. Lückenhafte Faktoren werden zur Mitte geschrumpft. Das Ranking ist <b>relativ</b>: „Avoid“ heißt unattraktives Chance-Risiko-Verhältnis im Vergleich, nicht zwingend fallende Kurse. Zeile anklicken für Kennzahlen, Makro-Sensitivität und Top-Positionen.</p>`;
  box("siTable").querySelectorAll("tr[data-sec]").forEach(tr => tr.addEventListener("click", () => { secOpen = secOpen === tr.dataset.sec ? null : tr.dataset.sec; drawSectorTable(); }));
}
function sectorDetail(s, z) {
  const F = R.sectors.factors, fin = s.is_fin ? new Set(R.sectors.fin_exclude) : new Set();
  const sens = s.sens || {};
  return `<div class="g2"><div>${Object.entries(F).map(([f, items]) => `<div class="fblock"><b>${esc((SEC_F.find(x => x[0] === f) || [, f])[1])}</b> ${sub(s.z[f])} <span class="muted small">Abdeckung ${esc(s.cov[f])}</span>
      <table class="mini">${items.map(it => `<tr><td>${esc(it.label)}</td><td>${fin.has(it.key) ? '<span class="muted">bei Finanzwerten nicht sinnvoll</span>' : fmtMetric(it.key, s.m[it.key])}</td><td>${s.mz[it.key] == null ? "" : sub(s.mz[it.key])}</td></tr>`).join("")}</table></div>`).join("")}</div>
    <div><div class="fblock"><b>Makro-Sensitivität</b> <span class="muted small">Regression der wöchentlichen Überrendite ggü. S&P 500, ${sens.weeks || "–"} Wochen, R² ${sens.r2 == null ? "–" : nf(sens.r2, 2)}</span>
      ${sens.betas ? `<table class="mini">${sens.betas.map(b => `<tr><td>${esc(b.factor)}</td><td class="${cl(b.beta)}">${pc(b.beta, 2)}</td><td class="small ${Math.abs(b.t) >= 2 ? "" : "muted"}">t = ${nf(b.t, 1)}${Math.abs(b.t) >= 2 ? " ✱" : ""}</td></tr>`).join("")}</table>
        <div class="muted small">✱ = statistisch auffällig (|t| ≥ 2). Korrelation, keine Kausalität. Regime-Fit: ${s.regime_n} Vergleichsmonate im Regime „${esc(R.regime.quadrant || "–")}“.</div>` : NODATA}</div>
      <div class="fblock"><b>${s.proxy === "Korb" ? "Korb-Mitglieder (gleichgewichtet)" : "Top-10-Positionen " + esc(s.proxy)}</b>
        <table class="mini">${s.holdings.map(h => `<tr><td>${BY[h.t] ? `<a href="#" data-rx="${esc(h.t)}">${esc(h.n || h.t)}</a>` : esc(h.n || h.t)}</td><td class="muted">${esc(h.t)}</td><td>${pc(h.w, 1, false)}</td></tr>`).join("")}</table>
        <div class="muted small">Fundamental-/Revisionswerte = gewichteter Schnitt dieser Positionen (Abdeckung je Kennzahl ≥ 50 % des Gewichts). Daten seit ${dfmt(s.since)}.</div></div></div></div>`;
}
function renderBacktest() {
  if (pending("btBody")) return;
  const B = R.backtest;
  if (B.error) { box("btBody").innerHTML = `<div class="empty">${esc(B.error)}</div>`; return; }
  const v = B.variants, bm = B.benchmark;
  const rows = [["cagr", "CAGR", x => pc(x)], ["vol", "Volatilität", x => pc(x, 1, false)], ["sharpe", "Sharpe Ratio", x => nf(x, 2)], ["sortino", "Sortino Ratio", x => nf(x, 2)],
    ["mdd", "Max. Drawdown", x => pc(x)], ["alpha", "Alpha p. a. (CAPM)", x => pc(x)], ["beta", "Beta", x => nf(x, 2)], ["ir", "Information Ratio", x => nf(x, 2)],
    ["win", "Monate mit Gewinn", x => pc(x, 0, false)], ["beat", "Monate besser als Benchmark", x => pc(x, 0, false)], ["pf", "Profit Factor", x => nf(x, 2)], ["turnover", "Turnover/Monat", x => pc(x, 0, false)], ["months", "Monate", x => nf(x, 0)]];
  const cols = [["3", "Top 3"], ["5", "Top 5 (Haupt)"], ["7", "Top 7"]].filter(([k]) => v[k]);
  box("btBody").innerHTML = `<div class="muted small">${esc(B.start)} – ${esc(B.end)} · Universum: ${B.universe.length} Branchen-ETFs · Kosten ${pc(B.costs.commission, 2, false)} + ${pc(B.costs.slippage, 2, false)} Slippage je gehandeltem Betrag</div>
    ${equityChart([[v["5"].equity, "var(--s1)", "Strategie Top 5"], [bm.equity, "var(--muted)", "S&P 500"]])}
    <div class="tscroll"><table class="dt"><thead><tr><th>Kennzahl</th>${cols.map(([, l]) => `<th>${l}</th>`).join("")}<th>S&P 500</th></tr></thead><tbody>
    ${rows.map(([k, l, f]) => `<tr><td>${l}</td>${cols.map(([c]) => `<td>${v[c].stats[k] == null ? "–" : f(v[c].stats[k])}</td>`).join("")}<td>${bm.stats[k] == null || k === "beat" || k === "ir" || k === "alpha" ? "–" : f(bm.stats[k])}</td></tr>`).join("")}</tbody></table></div>
    <div class="g2"><div><b>Nach Marktregime</b> <span class="muted small">(Top 5; Regime zu Monatsbeginn bekannt)</span><table class="mini">${Object.entries(B.regimes).map(([k, x]) => `<tr><td>${esc(k)}</td><td>${x.ann == null ? `${x.months} M – zu wenig` : `${pc(x.ann)} vs. ${pc(x.bench_ann)} <span class="muted small">(${x.months} M, besser in ${pc(x.beat, 0, false)})</span>`}</td></tr>`).join("")}</table></div>
      <div><b>Teilzeiträume</b><table class="mini">${Object.entries(B.periods).map(([k, x]) => `<tr><td>${esc(k)}</td><td>${x.ann == null ? "–" : `${pc(x.ann)} vs. ${pc(x.bench_ann)} <span class="muted small">(${x.months} M)</span>`}</td></tr>`).join("")}</table></div></div>
    <p class="small"><b>Was getestet wird:</b> nur der kursbasierte Teil des Branchen-Scores (relative Stärke 60 %, Risiko 40 %). Bewertung, Fundamentaldaten und Gewinnrevisionen sind kostenlos nicht als historische Zeitpunktdaten verfügbar und werden deshalb <b>nicht</b> rückgetestet. Aktuelle Auswahl: ${B.latest_pick.map(esc).join(", ")}.</p>
    <p class="small muted">${esc(B.method)} Rest-Survivorship-Bias: Die Branchenliste wurde heute gewählt; ETFs gehen erst ab Auflage ein. Eigene Körbe (KI, Luxus) sind ausgeschlossen. Ein gutes Backtest-Ergebnis ist kein Beweis für zukünftige Performance.</p>`;
}
function equityChart(series) {
  const w = 760, h = 220, l = 44, r = 10, t = 10, b = 22;
  const all = series.flatMap(([s]) => s.map(p => p[1])).filter(v => v > 0);
  const mn = Math.log(Math.min(...all)), mx = Math.log(Math.max(...all));
  const dates = series[0][0].map(p => p[0]);
  const X = i => l + i / (dates.length - 1) * (w - l - r), Y = v => t + (1 - (Math.log(v) - mn) / (mx - mn || 1)) * (h - t - b);
  const ticks = [0.5, 1, 2, 4, 8, 16].filter(v => Math.log(v) >= mn && Math.log(v) <= mx);
  return `<svg viewBox="0 0 ${w} ${h}" class="eqc" role="img" aria-label="Wertentwicklung (log)">
    ${ticks.map(v => `<line x1="${l}" x2="${w - r}" y1="${Y(v)}" y2="${Y(v)}" stroke="var(--grid)"/><text x="${l - 6}" y="${Y(v) + 4}" text-anchor="end" class="ax">${nf(v, v < 1 ? 1 : 0)}×</text>`).join("")}
    ${[0, Math.floor(dates.length / 2), dates.length - 1].map(i => `<text x="${X(i)}" y="${h - 4}" text-anchor="middle" class="ax">${esc(dates[i])}</text>`).join("")}
    ${series.map(([s, c]) => { const m = Object.fromEntries(s); return `<polyline fill="none" stroke="${c}" stroke-width="2" points="${dates.map((d, i) => m[d] ? `${X(i).toFixed(1)},${Y(m[d]).toFixed(1)}` : "").join(" ")}"/>`; }).join("")}
  </svg><div class="lg">${series.map(([, c, n]) => `<span><i style="background:${c}"></i>${esc(n)}</span>`).join("")} <span class="muted small">logarithmische Skala, Startwert 1</span></div>`;
}

/* ============================================================ 3 STOCK SCREENER */
const flt = { sec: "", reg: "", noflag: false, fcf: false, roic: false, lev: false, rev: false, q: "" };
let sortKey = "score", sortDir = -1, showN = 40;
function renderScreener() {
  if (pending("scBody")) return;
  weightEditor("scW", STK_F, wStk, () => { store.set("wStk", JSON.stringify(wStk)); stkZC = null; drawScreener(); });
  const secs = [...new Set(STK.map(s => s.sec).filter(Boolean))].sort();
  box("scFilter").innerHTML = `<div class="filters"><input type="search" id="scQ" placeholder="Name/Ticker filtern" value="${esc(flt.q)}">
    <select id="scSec"><option value="">Alle Sektoren</option>${secs.map(s => `<option${flt.sec === s ? " selected" : ""}>${esc(s)}</option>`).join("")}</select>
    <select id="scReg"><option value="">Alle Regionen</option>${["USA", "Europa", "Asien-Pazifik"].map(s => `<option${flt.reg === s ? " selected" : ""}>${s}</option>`).join("")}</select>
    ${[["noflag", "ohne bestätigte Red Flags"], ["roic", "ROIC > WACC"], ["fcf", "Free Cashflow positiv"], ["lev", "Nettoverschuldung < 2,5× EBITDA"], ["rev", "Gewinnrevisionen positiv"]]
      .map(([k, l]) => `<label class="chk"><input type="checkbox" data-f="${k}"${flt[k] ? " checked" : ""}> ${l}</label>`).join("")}</div>`;
  box("scQ").addEventListener("input", e => { flt.q = e.target.value.toLowerCase(); drawScreener(); });
  box("scSec").addEventListener("change", e => { flt.sec = e.target.value; drawScreener(); });
  box("scReg").addEventListener("change", e => { flt.reg = e.target.value; drawScreener(); });
  box("scFilter").querySelectorAll("input[data-f]").forEach(i => i.addEventListener("change", () => { flt[i.dataset.f] = i.checked; drawScreener(); }));
  drawScreener();
}
function drawScreener() {
  let rows = STK.map(s => {
    const z = stockZ(s), f = fair(s), w = f && f.base.a && f.base.a.wacc;
    return { s, z, score: toScore(z), up: upside(s), risk: riskScore(s.z.risk), wacc: w };
  });
  rows = rows.filter(({ s, wacc }) => (!flt.q || (s.n + " " + s.t).toLowerCase().includes(flt.q)) && (!flt.sec || s.sec === flt.sec) && (!flt.reg || region(s) === flt.reg)
    && (!flt.noflag || !confirmed(s)) && (!flt.fcf || (s.m.fcf_m != null && s.m.fcf_m > 0)) && (!flt.lev || (s.m.nd_ebitda != null && s.m.nd_ebitda < 2.5))
    && (!flt.rev || (s.m.eps_rev_1y != null && s.m.eps_rev_1y > 0 && (s.m.breadth ?? 0) > 0)) && (!flt.roic || (s.m.roic != null && wacc != null && s.m.roic > wacc)));
  const val = { score: x => x.score, up: x => x.up, risk: x => x.risk, n: x => x.s.n, ...Object.fromEntries(STK_F.map(([k]) => [k, x => x.s.z[k]])) };
  rows.sort((a, b) => { const A = val[sortKey](a), B = val[sortKey](b); if (A == null) return 1; if (B == null) return -1; return (A > B ? 1 : A < B ? -1 : 0) * sortDir; });
  const th = (k, l, tip = "") => `<th class="sort${sortKey === k ? " on" : ""}" data-k="${k}" title="${esc(tip)}">${l}${sortKey === k ? (sortDir < 0 ? " ▼" : " ▲") : ""}</th>`;
  box("scTable").innerHTML = `<div class="muted small">${rows.length} von ${STK.length} Werten · Score = Perzentil im Gesamtuniversum · Faktorspalten 50 + 20 × z innerhalb des Sektors (ab 8 Werten, sonst Gesamtuniversum) · „Strongly Attractive“ nur ohne bestätigte Red Flag</div>
    <div class="tscroll"><table class="dt rank"><thead><tr><th>#</th>${th("n", "Unternehmen")}<th>Sektor</th>${th("score", "Score")}<th>Klasse</th>
    ${STK_F.map(([k, l]) => th(k, l, k === "risk" ? "hoch = geringeres Risiko" : "")).join("")}${th("up", "DCF-Upside", "Base Case, Annahmen editierbar unter Valuation")}<th>Red Flags</th></tr></thead><tbody>
    ${rows.slice(0, showN).map((x, i) => `<tr class="click" data-rx="${esc(x.s.t)}"><td>${i + 1}</td><td><b>${esc(x.s.n)}</b><div class="muted small">${esc(x.s.t)}${x.s.w ? " · WKN " + esc(x.s.w) : ""}</div></td>
      <td class="small">${esc(x.s.sec || "–")}</td><td><b>${x.score ?? "–"}</b></td><td>${sbadge(x.s)}</td>${STK_F.map(([k]) => `<td title="Abdeckung ${esc((x.s.cov || {})[k] || "")}">${sub(x.s.z[k])}</td>`).join("")}
      <td class="${cl(x.up)}">${pc(x.up, 0)}</td><td>${flagBadges(x.s)}</td></tr>`).join("")}</tbody></table></div>
    ${rows.length > showN ? `<button type="button" class="tbtn" id="scMore">Weitere ${Math.min(40, rows.length - showN)} anzeigen</button>` : ""}
    <p class="small muted">Rangfolge zeigt relative Attraktivität nach den gewählten Gewichten – keine Kaufempfehlung. Bei Finanzwerten entfallen ROIC, FCF- und EV-Kennzahlen. Daten: Yahoo Finance (Abrufzeit je Wert im Research).</p>`;
  box("scTable").querySelectorAll("th.sort").forEach(h => h.addEventListener("click", e => { e.stopPropagation(); const k = h.dataset.k; sortDir = sortKey === k ? -sortDir : (k === "n" ? 1 : -1); sortKey = k; drawScreener(); }));
  const more = box("scMore"); if (more) more.addEventListener("click", () => { showN += 40; drawScreener(); });
}

/* ============================================================ 4 EQUITY RESEARCH */
let sel = store.get("rxSel") || "SAP.DE";
function picker(id, area) {
  const el = box(id);
  el.innerHTML = `<div class="picker"><input list="${id}L" id="${id}I" placeholder="Unternehmen oder Ticker wählen …" autocomplete="off"><datalist id="${id}L">${STK.map(s => `<option value="${esc(s.n)} · ${esc(s.t)}">`).join("")}</datalist>
    <span class="muted small">${STK.length} Werte im Research-Universum · Suche oben öffnet zusätzlich den Kurz-Steckbrief</span></div>`;
  box(id + "I").addEventListener("change", e => { const t = e.target.value.split(" · ").pop().trim(); if (BY[t]) RX.open(t, area); });
}
function factorBars(s) {
  return `<div class="fbars">${STK_F.map(([k, l]) => { const z = s.z[k]; return `<div class="fb"><span>${l}</span><div class="bar"><i style="width:${z == null ? 0 : fsc(z)}%" class="${z == null ? "" : z > 0.25 ? "pos" : z < -0.25 ? "neg" : "mid"}"></i></div><b>${z == null ? "–" : fsc(z)}</b><span class="muted small">${esc((s.cov || {})[k] || "")}</span></div>`; }).join("")}</div>`;
}
const FALSIFY = {
  roic: "ROIC fällt unter die Kapitalkosten", op_m: "Operative Marge bricht ein", fcf_m: "Free Cashflow wird negativ", rev_g: "Umsatzwachstum kühlt deutlich ab",
  rev_g_next: "Konsens senkt die Umsatzerwartung", eps_g_next: "Konsens senkt die Gewinnerwartung", eps_rev_1y: "Gewinnrevisionen drehen ins Negative",
  breadth: "Mehr Analysten senken als heben die Schätzungen", surprise: "Quartalszahlen verfehlen die Erwartungen", r12_1: "Relative Stärke bricht weg (Kurs unter 200-Tage-Linie)",
  fwd_ey: "Bewertung steigt ohne Gewinnwachstum", fcf_y: "FCF-Rendite sinkt durch Kursanstieg oder schwächeren Cashflow", int_cov: "Zinsdeckung verschlechtert sich",
};
function thesis(s) {
  const lab = Object.fromEntries(Object.values(R.stocks.factors).flat().map(x => [x.key, x.label]));
  const items = Object.entries(s.mz || {}).map(([k, z]) => ({ k, z, l: lab[k], v: s.m[k] })).filter(x => x.l);
  const pro = items.filter(x => x.z >= 0.75).sort((a, b) => b.z - a.z).slice(0, 6), con = items.filter(x => x.z <= -0.75).sort((a, b) => a.z - b.z).slice(0, 6);
  return { pro, con, fals: pro.map(x => FALSIFY[x.k]).filter(Boolean).slice(0, 4) };
}
function histTable(s) {
  const H = s.hist || {}; if (!H.periods || !H.periods.length) return NODATA;
  const cur = s.fcur, n = H.periods.length, at = (k, i) => (H[k] || [])[i];
  const yoy = (k, i) => at(k, i) != null && at(k, i + 1) ? at(k, i) / at(k, i + 1) - 1 : null;
  const line = (label, f) => `<tr><td>${label}</td>${H.periods.map((p, i) => `<td>${f(i)}</td>`).join("")}</tr>`;
  return `<div class="tscroll"><table class="dt num"><thead><tr><th>Geschäftsjahr (Ist, ${esc(cur)})</th>${H.periods.map(p => `<th>${esc(p.slice(0, 7))}</th>`).join("")}</tr></thead><tbody>
    ${line("Umsatz", i => big(at("rev", i)))}${line("Wachstum", i => `<span class="${cl(yoy("rev", i))}">${pc(yoy("rev", i))}</span>`)}
    ${line("EBIT (operativ)", i => big(at("ebit", i)))}${line("Operative Marge", i => pc((H.opm || [])[i], 1, false))}
    ${line("EBITDA", i => big(at("ebitda", i)))}${line("Nettogewinn", i => big(at("ni", i)))}${line("EPS (verwässert)", i => nf(at("eps", i), 2))}
    ${line("Free Cashflow", i => big(at("fcf", i)))}${line("FCF-Marge", i => pc(at("fcf", i) != null && at("rev", i) ? at("fcf", i) / at("rev", i) : null, 1, false))}
    ${line("ROIC", i => pc((H.roic || [])[i], 1, false))}${line("Capex", i => big(at("capex", i)))}
    ${line("Nettoverschuldung", i => big(at("debt", i) != null ? at("debt", i) - (at("cash", i) || 0) : null))}${line("Eigenkapital", i => big(at("eq", i)))}
    ${line("Aktienzahl", i => big(at("shares", i)))}${line("Aktienrückkäufe", i => big(at("buyback", i)))}${line("Dividenden", i => big(at("div", i)))}
    </tbody></table></div><div class="muted small">Quelle: Jahresabschlüsse über Yahoo Finance · ${n} Geschäftsjahre verfügbar (kostenlos max. 4–5) · Werte in Berichtswährung ${esc(cur)}</div>`;
}
function quarterTable(s) {
  const q = s.q || {}; if (!q.periods) return "";
  return `<div class="tscroll"><table class="dt num"><thead><tr><th>Quartal (Ist)</th>${q.periods.map(p => `<th>${esc(p.slice(0, 7))}</th>`).join("")}</tr></thead><tbody>
    ${[["Umsatz", "rev"], ["EBIT", "ebit"], ["Nettogewinn", "ni"], ["Free Cashflow", "fcf"]].map(([l, k]) => `<tr><td>${l}</td>${q.periods.map((_, i) => `<td>${big((q[k] || [])[i])}</td>`).join("")}</tr>`).join("")}
    <tr><td>EPS</td>${q.periods.map((_, i) => `<td>${nf((q.eps || [])[i], 2)}</td>`).join("")}</tr></tbody></table></div>`;
}
function peers(s) {
  const P = STK.filter(x => x.sec === s.sec && x.t !== s.t);
  if (P.length < 3) return NODATA;
  const med = k => { const v = P.map(x => x.m[k]).filter(v => v != null).sort((a, b) => a - b); return v.length ? v[Math.floor(v.length / 2)] : null; };
  const ks = [["fwd_ey", "Erwartete Gewinnrendite"], ["ev_ebitda_y", "EBITDA/EV"], ["fcf_y", "FCF-Rendite"], ["roic", "ROIC"], ["op_m", "Operative Marge"], ["rev_g", "Umsatzwachstum"], ["eps_rev_1y", "EPS-Revision 90 T"], ["vol", "Volatilität"]];
  const top = P.map(x => ({ x, z: stockZ(x) })).filter(o => o.z != null).sort((a, b) => b.z - a.z).slice(0, 5);
  return `<table class="mini"><tr><th></th><th>${esc(s.n)}</th><th>Median Sektor (${P.length})</th></tr>${ks.map(([k, l]) => `<tr><td>${l}</td><td>${fmtMetric(k, s.m[k])}</td><td>${fmtMetric(k, med(k))}</td></tr>`).join("")}</table>
    <div class="small" style="margin-top:6px">Höchste Scores im Sektor: ${top.map(o => `<a href="#" data-rx="${esc(o.x.t)}">${esc(o.x.n)}</a> (${toScore(o.z)})`).join(", ")}</div>`;
}
function consensus(s) {
  const c = s.cons || {}, E = s.est || {}, cur = s.cur;
  const trend = E.trend || {}, revs = E.revs || {};
  const tr = p => { const v = trend[p]; return v ? `${nf(v[0], 2)} <span class="small ${cl(v[4] ? v[0] / v[4] - 1 : null)}">(${pc(v[4] ? v[0] / v[4] - 1 : null)} ggü. vor 90 T)</span>` : "–"; };
  return `<div class="g2"><div><table class="mini">
    <tr><td>Kursziel Ø / Median</td><td>${nf(c.targetMeanPrice, 2)} / ${nf(c.targetMedianPrice, 2)} ${esc(cur)} <span class="${cl(c.targetMeanPrice && s.val.px ? c.targetMeanPrice / s.val.px - 1 : null)}">${pc(c.targetMeanPrice && s.val.px ? c.targetMeanPrice / s.val.px - 1 : null, 0)}</span></td></tr>
    <tr><td>Spanne</td><td>${nf(c.targetLowPrice, 2)} – ${nf(c.targetHighPrice, 2)}</td></tr>
    <tr><td>Analysten / Empfehlung</td><td>${c.numberOfAnalystOpinions ?? "–"} · ${esc(c.key || "–")} ${c.recommendationMean ? `(${nf(c.recommendationMean, 1)} auf 1 = Kauf … 5 = Verkauf)` : ""}</td></tr>
    <tr><td>EPS lfd. GJ / nächstes GJ</td><td>${tr("0y")} / ${tr("+1y")}</td></tr>
    <tr><td>Revisionen 30 T (nächstes GJ)</td><td>${revs["+1y"] ? `▲ ${revs["+1y"][0]} · ▼ ${revs["+1y"][1]}` : "–"}</td></tr>
    <tr><td>Umsatz-Konsens nächstes GJ</td><td>${E.rev && E.rev["+1y"] ? `${big(E.rev["+1y"][0])} (${pc(E.rev["+1y"][4])}, ${E.rev["+1y"][3]} Analysten)` : "–"}</td></tr>
    </table></div><div><b class="small">Earnings Surprise (Ist vs. Konsens)</b><table class="mini">${(E.surprise || []).map(x => `<tr><td>${esc(x[0])}</td><td>${nf(x[1], 2)} vs. ${nf(x[2], 2)}</td><td class="${cl(x[3])}">${pc(x[3])}</td></tr>`).join("") || "<tr><td>–</td></tr>"}</table>
    <b class="small">Analystenaktionen (90 T)</b><table class="mini">${((s.ev || {}).actions || []).slice(0, 8).map(a => `<tr><td>${dfmt(a.date)}</td><td>${esc(a.firm)}</td><td class="${a.action === "up" ? "up" : a.action === "down" ? "down" : ""}">${esc(a.from ? a.from + " → " : "")}${esc(a.to || "")}</td><td class="small">${a.pt ? "Ziel " + nf(a.pt, 0) : ""}</td></tr>`).join("") || "<tr><td class='muted'>keine</td></tr>"}</table></div></div>
    <div class="muted small">Konsensdaten: Yahoo Finance (Schätzungen, Stand ${dfmt((s.src || {}).est)}). Konsens ist eine Erwartung, kein Ist-Wert.</div>`;
}
function flagList(s) {
  const F = s.flags || []; if (!F.length) return '<div class="muted">Keine Red Flags nach den definierten Regeln. Nicht abgedeckt: Governance, Rechtsstreitigkeiten, Bilanzierungsauffälligkeiten (keine strukturierten freien Daten).</div>';
  const L = { confirmed: "Confirmed Risk", potential: "Potential Risk", dq: "Data Quality Warning" };
  return `<table class="dt"><thead><tr><th>Stufe</th><th>Kategorie</th><th>Befund</th><th>Wert</th><th>Regel</th><th>Quelle</th></tr></thead><tbody>${F.map(f => `<tr><td><span class="fl ${f.level}">${L[f.level]}</span></td><td>${esc(f.cat)}</td><td>${esc(f.text)}</td><td>${esc(f.value)}</td><td class="small">${esc(f.rule)}</td><td class="small">${esc(f.src)}</td></tr>`).join("")}</tbody></table>
    <div class="muted small">Nicht abgedeckt: Governance, Managementwechsel, Rechtsstreitigkeiten (keine strukturierten freien Daten).</div>`;
}
function scenHtml(s, f) {
  if (!f) { const why = s.val.method === "residual_income" ? riScen(s.val).error : dcfReady(s.val); return `<div class="empty">${esc(why || "Keine belastbare Datengrundlage vorhanden.")}</div>`; }
  const px = s.val.px;
  return `<table class="dt"><thead><tr><th></th><th>Bear</th><th>Base</th><th>Bull</th></tr></thead><tbody>
    <tr><td>Fair Value je Aktie</td>${["bear", "base", "bull"].map(k => `<td><b>${nf(f[k].fv, 2)}</b> ${esc(s.val.cur)}</td>`).join("")}</tr>
    <tr><td>Abstand zum Kurs (${nf(px, 2)})</td>${["bear", "base", "bull"].map(k => `<td class="${cl(f[k].fv / px - 1)}">${pc(f[k].fv != null ? f[k].fv / px - 1 : null, 0)}</td>`).join("")}</tr>
    ${f.ri ? `<tr><td>ROE / Eigenkapitalkosten</td>${["bear", "base", "bull"].map(k => `<td>${pc(f[k].roe, 1, false)} / ${pc(f[k].coe, 1, false)}</td>`).join("")}</tr>`
      : `<tr><td>Umsatzwachstum J1 / J2</td>${["bear", "base", "bull"].map(k => `<td>${pc(f[k].a.g1)} / ${pc(f[k].a.g2)}</td>`).join("")}</tr>
         <tr><td>Operative Marge</td>${["bear", "base", "bull"].map(k => `<td>${pc(f[k].a.margin, 1, false)}</td>`).join("")}</tr>
         <tr><td>WACC</td>${["bear", "base", "bull"].map(k => `<td>${pc(f[k].a.wacc, 1, false)}</td>`).join("")}</tr>`}
    </tbody></table>${f.implied != null ? `<p class="small"><b>Im Kurs eingepreist:</b> Der aktuelle Kurs entspricht im Modell einem Umsatzwachstum von ca. <b>${pc(f.implied)}</b> p. a. in den ersten Jahren (danach Abflachung) – Konsens: ${pc(s.val.g0)} / ${pc(s.val.g1)}.</p>` : ""}
    <p class="muted small">${esc(f.method)} · Modellschätzung, kein Kursziel · Annahmen und Sensitivität unter <a href="#" data-rx="${esc(s.t)}" data-rx-area="valuation">Valuation</a>.</p>`;
}
function renderResearch() {
  if (pending("eqBody")) return;
  picker("eqPick", "research");
  const s = BY[sel] || STK[0]; if (!s) { box("eqBody").innerHTML = NODATA; return; }
  sel = s.t;
  const z = stockZ(s), f = fair(s), up = upside(s), th = thesis(s), secRow = SECT.find(x => x.key === SECTOR_MAP[s.sec]);
  const secZv = secRow ? secZ(secRow) : null, src = s.src || {};
  box("eqBody").innerHTML = `<div class="eqhead"><div><h3>${esc(s.n)} <span class="muted">${esc(s.t)}${s.w ? " · WKN " + esc(s.w) : ""}</span></h3>
      <div class="muted small">${esc(s.sec || "–")} · ${esc(s.ind || "–")} · ${esc(s.land || "–")}</div></div>
      <div class="eqbtns"><button type="button" class="tbtn" id="eqFav">${FAVS().includes(s.t) ? "★ Watchlist" : "☆ Watchlist"}</button> <button type="button" class="tbtn" id="eqReport">Research Report</button></div></div>
    <div class="kpis">
      <div><span>Kurs</span><b>${nf(s.px, 2)} ${esc(s.cur)}</b><small>Tagesschluss ${dfmt(s.pxd)}</small></div>
      <div><span>Tagesperformance</span><b class="${cl(s.d1)}">${pc(s.d1)}</b></div>
      <div><span>Marktkapitalisierung</span><b>${big(s.mcap, s.mcap_cur)}</b></div>
      <div><span>Fair Value (Base)</span><b>${f && f.base.fv != null ? nf(f.base.fv, 2) : "–"}</b><small>${f ? (f.ri ? "Residual Income" : "DCF") + " · Modell" : "nicht berechenbar"}</small></div>
      <div><span>Upside / Downside</span><b class="${cl(up)}">${pc(up, 0)}</b><small>${f ? `Bear ${pc(f.bear.fv / s.val.px - 1, 0)} · Bull ${pc(f.bull.fv / s.val.px - 1, 0)}` : ""}</small></div>
      <div><span>Investment Score</span><b>${toScore(z) ?? "–"}</b><small>${sbadge(s)} · Perzentil</small></div>
      <div><span>Risk Score</span><b>${riskScore(s.z.risk) ?? "–"}</b><small>hoch = riskanter · ${flagBadges(s)}</small></div></div>
    <details open><summary>Executive Summary & Investmentthese</summary>${factorBars(s)}
      <div class="g2"><div><b class="up">Was dafür spricht (Daten)</b><ul>${th.pro.map(x => `<li>${esc(x.l)}: <b>${fmtMetric(x.k, x.v)}</b> <span class="muted small">(${fsc(x.z)} im Sektorvergleich)</span></li>`).join("") || "<li class='muted'>Keine Kennzahl deutlich über dem Sektor.</li>"}</ul></div>
        <div><b class="down">Gegenargumente (Daten)</b><ul>${th.con.map(x => `<li>${esc(x.l)}: <b>${fmtMetric(x.k, x.v)}</b> <span class="muted small">(${fsc(x.z)})</span></li>`).join("")}${(s.flags || []).filter(x => x.level !== "dq").map(x => `<li>Red Flag: ${esc(x.text)} (${esc(x.value)})</li>`).join("") || (th.con.length ? "" : "<li class='muted'>Keine Kennzahl deutlich unter dem Sektor.</li>")}</ul></div></div>
      ${th.fals.length ? `<div class="small"><b>Was die These widerlegen würde:</b> ${th.fals.map(esc).join(" · ")}.</div>` : ""}
      <div class="small" style="margin-top:6px"><b>Branche:</b> ${secRow ? `${esc(secRow.name)} ${badge(secZv)}` : "keine Zuordnung"} · <b>Regime:</b> ${esc(R.regime.quadrant || "–")}, ${esc(R.regime.risk || "–")}</div>
      ${s.summary ? `<p class="small muted">${esc(s.summary)}</p>` : ""}</details>
    <details open><summary>Bewertung & Szenarien</summary>${scenHtml(s, f)}
      <table class="mini"><tr><td>KGV (TTM) / Forward</td><td>${nf(s.x.trailingPE, 1)} / ${nf(s.x.forwardPE, 1)}</td></tr><tr><td>EV/EBITDA · EV/Umsatz</td><td>${nf(s.x.enterpriseToEbitda, 1)} · ${nf(s.x.enterpriseToRevenue, 1)}</td></tr>
        <tr><td>KBV · PEG</td><td>${nf(s.x.priceToBook, 1)} · ${nf(s.x.trailingPegRatio, 2)}</td></tr><tr><td>FCF-Rendite · Dividendenrendite</td><td>${fmtMetric("fcf_y", s.m.fcf_y)} · ${s.x.dividendYield != null ? nf(s.x.dividendYield, 2) + " %" : "–"}</td></tr></table></details>
    <details><summary>Fundamentaldaten (Historie)</summary>${histTable(s)}${quarterTable(s)}
      <table class="mini"><tr><td>Bruttomarge / EBITDA-Marge / Nettomarge (TTM)</td><td>${pc(s.x.grossMargins, 1, false)} / ${pc(s.x.ebitdaMargins, 1, false)} / ${pc(s.x.profitMargins, 1, false)}</td></tr>
      <tr><td>ROE / ROA / ROIC</td><td>${pc(s.m.roe, 1, false)} / ${pc(s.x.returnOnAssets, 1, false)} / ${pc(s.m.roic, 1, false)}</td></tr><tr><td>Zinsdeckung · Nettoverschuldung/EBITDA</td><td>${fmtMetric("int_cov", s.m.int_cov)} · ${fmtMetric("nd_ebitda", s.m.nd_ebitda)}</td></tr>
      <tr><td>Cash Conversion · Debt/Equity · Current Ratio</td><td>${fmtMetric("cash_conv", s.m.cash_conv)} · ${s.x.debtToEquity != null ? nf(s.x.debtToEquity / 100, 2) : "–"} · ${nf(s.x.currentRatio, 2)}</td></tr></table></details>
    <details><summary>Analystenkonsens</summary>${consensus(s)}</details>
    <details><summary>Branchenvergleich</summary>${peers(s)}</details>
    <details><summary>Katalysatoren</summary>${catalystsOf(s)}</details>
    <details><summary>Risiken (Red Flags)</summary>${flagList(s)}</details>
    <details><summary>Quellen & Datenstand</summary><table class="mini">
      <tr><td>Kurs</td><td>Yahoo Finance, Tagesschluss ${dfmt(src.px)} (verzögert, keine Echtzeit)</td></tr><tr><td>Kennzahlen (TTM)</td><td>Yahoo Finance, abgerufen ${dfmt(src.info)}</td></tr>
      <tr><td>Jahresabschlüsse</td><td>Yahoo Finance, abgerufen ${dfmt(src.stm)} · letztes GJ ${esc(s.val.fy || "–")}</td></tr><tr><td>Schätzungen</td><td>Yahoo Finance, abgerufen ${dfmt(src.est)}</td></tr>
      <tr><td>Termine/Analysten</td><td>Yahoo Finance, abgerufen ${dfmt(src.events)}</td></tr><tr><td>Zins für Bewertung</td><td>${esc(s.val.rf_src || "–")}${s.val.rf_note ? " – " + esc(s.val.rf_note) : ""}</td></tr>
      <tr><td>Währung</td><td>Kurs ${esc(s.cur)}, Bericht ${esc(s.fcur)}${s.val.fx_note ? " – " + esc(s.val.fx_note) : ""}</td></tr>${s.val.share_note ? `<tr><td>Aktienzahl</td><td>${esc(s.val.share_note)}</td></tr>` : ""}</table></details>`;
  box("eqFav").addEventListener("click", () => { toggleFav(s.t); renderResearch(); });
  box("eqReport").addEventListener("click", () => report(s));
}
function catalystsOf(s) {
  const c = (s.ev || {}).calendar || {};
  return `<table class="mini"><tr><td>Nächste Quartalszahlen</td><td>${c["Earnings Date"] ? dfmt(c["Earnings Date"]) : "–"}${c["Earnings Average"] != null ? ` · EPS-Konsens ${nf(c["Earnings Average"], 2)}` : ""}</td></tr>
    <tr><td>Ex-Dividende</td><td>${c["Ex-Dividend Date"] ? dfmt(c["Ex-Dividend Date"]) : "–"}</td></tr>
    <tr><td>Analystenaktionen 90 T</td><td>${((s.ev || {}).actions || []).filter(a => a.action === "up").length} Upgrades · ${((s.ev || {}).actions || []).filter(a => a.action === "down").length} Downgrades</td></tr></table>
    <div class="muted small">Weitere Katalysatoren (Guidance, M&A, Regulierung) siehe News & Catalysts – nur wo durch Quellen belegt.</div>`;
}
function report(s) {
  const z = stockZ(s), f = fair(s), th = thesis(s), secRow = SECT.find(x => x.key === SECTOR_MAP[s.sec]), secZv = secRow ? secZ(secRow) : null;
  const sens = secRow && secRow.sens && secRow.sens.betas ? secRow.sens.betas.filter(b => Math.abs(b.t) >= 2) : [];
  const w = open("", "_blank");
  if (!w) return alert("Bitte Pop-ups erlauben, um den Report zu öffnen.");
  const H = s.hist || {};
  w.document.write(`<!doctype html><html lang="de"><head><meta charset="utf-8"><title>Research Report ${esc(s.n)}</title><style>
    body{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;max-width:860px;margin:30px auto;padding:0 20px;color:#111;line-height:1.5}h1{margin:0}h2{border-bottom:1px solid #ccc;padding-bottom:3px;margin-top:26px;font-size:18px}
    table{border-collapse:collapse;font-size:13px}td,th{border-bottom:1px solid #eee;padding:3px 8px;text-align:left}.m{color:#666;font-size:12px}</style></head><body>
    <h1>${esc(s.n)} (${esc(s.t)})</h1><div class="m">Research Report · Datenstand ${dfmt(R.generated)} · automatisch aus Daten erstellt, keine Anlageberatung</div>
    <h2>Executive Summary</h2><table><tr><td>Branche</td><td>${esc(s.sec || "–")} / ${esc(s.ind || "–")}</td></tr><tr><td>Kurs</td><td>${nf(s.px, 2)} ${esc(s.cur)} (Tagesschluss ${dfmt(s.pxd)})</td></tr>
      <tr><td>Investment Score</td><td>${toScore(z) ?? "–"} (Perzentil im Universum) – ${klass(z, confirmed(s) > 0)[0]}</td></tr><tr><td>Risk Score</td><td>${riskScore(s.z.risk) ?? "–"} (hoch = riskanter)</td></tr>
      <tr><td>Fair Value (Modell)</td><td>${f ? `Bear ${nf(f.bear.fv, 2)} · Base ${nf(f.base.fv, 2)} · Bull ${nf(f.bull.fv, 2)}` : "nicht berechenbar"}</td></tr>
      <tr><td>Faktoren</td><td>${STK_F.map(([k, l]) => `${l} ${fsc(s.z[k]) ?? "–"}`).join(" · ")}</td></tr></table>
    <h2>Investment Thesis</h2><p><b>Dafür:</b> ${th.pro.map(x => `${esc(x.l)} ${fmtMetric(x.k, x.v).replace(/<[^>]+>/g, "")}`).join("; ") || "keine herausragenden Kennzahlen"}.</p>
      <p><b>Dagegen:</b> ${th.con.map(x => `${esc(x.l)} ${fmtMetric(x.k, x.v).replace(/<[^>]+>/g, "")}`).join("; ") || "keine deutlich schwachen Kennzahlen"}.</p>${th.fals.length ? `<p><b>Widerlegt würde die These, wenn:</b> ${th.fals.map(esc).join("; ")}.</p>` : ""}
    <h2>Fundamental Analysis</h2>${H.periods ? `<table><tr><th>GJ</th>${H.periods.map(p => `<th>${esc(p.slice(0, 7))}</th>`).join("")}</tr>
      ${[["Umsatz", "rev"], ["EBIT", "ebit"], ["Nettogewinn", "ni"], ["Free Cashflow", "fcf"]].map(([l, k]) => `<tr><td>${l}</td>${H.periods.map((_, i) => `<td>${big((H[k] || [])[i])}</td>`).join("")}</tr>`).join("")}
      <tr><td>Operative Marge</td>${H.periods.map((_, i) => `<td>${pc((H.opm || [])[i], 1, false)}</td>`).join("")}</tr><tr><td>ROIC</td>${H.periods.map((_, i) => `<td>${pc((H.roic || [])[i], 1, false)}</td>`).join("")}</tr></table><div class="m">Berichtswährung ${esc(s.fcur)}</div>` : "<p>Keine belastbare Datengrundlage vorhanden.</p>"}
    <h2>Valuation</h2>${f ? `<p>${esc(f.method)}. Base Case ${nf(f.base.fv, 2)} ${esc(s.val.cur)} (${pc(f.base.fv / s.val.px - 1, 0)} zum Kurs). ${f.implied != null ? `Der Kurs impliziert ca. ${pc(f.implied)} Umsatzwachstum p. a. in den ersten Jahren.` : ""} Annahmen: ${f.ri ? `ROE ${pc(f.base.roe, 1, false)}, Eigenkapitalkosten ${pc(f.base.coe, 1, false)}` : `Wachstum ${pc(f.base.a.g1)} / ${pc(f.base.a.g2)}, Marge ${pc(f.base.a.margin, 1, false)}, WACC ${pc(f.base.a.wacc, 1, false)}, Endwachstum ${pc(f.base.a.tg, 1, false)}`}.</p>` : "<p>Keine belastbare Datengrundlage vorhanden.</p>"}
      <p>Multiples: KGV ${nf(s.x.trailingPE, 1)}, Forward-KGV ${nf(s.x.forwardPE, 1)}, EV/EBITDA ${nf(s.x.enterpriseToEbitda, 1)}, KBV ${nf(s.x.priceToBook, 1)}.</p>
    <h2>Sector Analysis</h2><p>${secRow ? `${esc(secRow.name)}: ${klass(secZv)[0]} (Score ${toScore(secZv) ?? "–"}).` : "Keine Branchenzuordnung."}</p>
    <h2>Macro Analysis</h2><p>Marktregime: ${esc(R.regime.quadrant || "–")}, ${esc(R.regime.risk || "–")}, ${esc(PHASE_DE[R.regime.phase] || "")}. ${sens.length ? "Statistisch auffällige Sensitivitäten der Branche: " + sens.map(b => `${esc(b.factor)} → ${pc(b.beta, 2)} Überrendite`).join("; ") + " (Korrelation, keine Kausalität)." : "Keine statistisch auffälligen Makro-Sensitivitäten der Branche."}</p>
    <h2>Catalysts</h2><p>${(() => { const c = (s.ev || {}).calendar || {}; return `Nächste Quartalszahlen: ${c["Earnings Date"] ? dfmt(c["Earnings Date"]) : "–"}. Analystenaktionen (90 T): ${((s.ev || {}).actions || []).length}.`; })()}</p>
    <h2>Risks</h2><ul>${(s.flags || []).map(x => `<li>${esc(x.text)} (${esc(x.value)}) – ${esc(x.rule)}; Quelle: ${esc(x.src)}</li>`).join("") || "<li>Keine Red Flags nach den definierten Regeln.</li>"}</ul>
    <h2>Scenario Analysis</h2>${f ? `<table><tr><th></th><th>Bear</th><th>Base</th><th>Bull</th></tr><tr><td>Fair Value</td>${["bear", "base", "bull"].map(k => `<td>${nf(f[k].fv, 2)}</td>`).join("")}</tr><tr><td>ggü. Kurs</td>${["bear", "base", "bull"].map(k => `<td>${pc(f[k].fv / s.val.px - 1, 0)}</td>`).join("")}</tr></table>` : "<p>–</p>"}
    <h2>Conclusion</h2><p>${esc(s.n)} erreicht nach den gewählten Gewichten einen Score von ${toScore(z) ?? "–"} von 100 (Perzentil, ${klass(z, confirmed(s) > 0)[0]}). ${f ? `Das Bewertungsmodell sieht den Kurs im Base Case ${f.base.fv > s.val.px ? "unter" : "über"} dem modellierten Wert; die Bandbreite Bear–Bull reicht von ${pc(f.bear.fv / s.val.px - 1, 0)} bis ${pc(f.bull.fv / s.val.px - 1, 0)}.` : ""} ${(s.flags || []).filter(x => x.level === "confirmed").length ? "Es bestehen bestätigte Risiken, die vor einer Entscheidung geprüft werden sollten." : ""} Diese Auswertung ersetzt kein eigenes Urteil und ist keine Anlageberatung.</p>
    <h2>Quellen</h2><p class="m">Kurse, Kennzahlen, Abschlüsse und Schätzungen: Yahoo Finance (inoffiziell, Abruf ${dfmt((s.src || {}).info)}). Zinsen: ${esc(s.val.rf_src || "–")}. Keine Daten institutioneller Anbieter.</p>
    <script>print()<\/script></body></html>`);
  w.document.close();
}

/* ============================================================ 5 VALUATION */
const ovr = {};
function renderValuation() {
  if (pending("vaBody")) return;
  picker("vaPick", "valuation");
  const s = BY[sel] || STK[0]; if (!s) return;
  const v = s.val, o = ovr[s.t] || (ovr[s.t] = {}), fin = v.method === "residual_income";
  const f = scenarios(v, o);
  const W = waccOf(v, o);
  const field = (k, label, val, step = 0.5, hint = "") => `<label>${label}<input type="number" step="${step}" data-k="${k}" value="${val == null ? "" : +(val * 100).toFixed(2)}"><span>%</span>${hint ? `<small>${hint}</small>` : ""}</label>`;
  const base = f.error ? null : f.base.a;
  box("vaBody").innerHTML = `<h3>${esc(s.n)} <span class="muted">${esc(s.t)} · Kurs ${nf(v.px, 2)} ${esc(v.cur)} (${dfmt(s.pxd)})</span></h3>
    ${f.error ? `<div class="empty">${esc(f.error)}</div>` : ""}
    <div class="g2"><div><b>Annahmen</b> <span class="muted small">(editierbar · leer = Standard aus Daten)</span><div class="vform">
      ${fin ? `${field("roe", "ROE (Ø 3 J)", o.roe ?? v.roe)}`
        : `${field("g1", "Umsatzwachstum Jahr 1", base ? base.g1 : v.g0, 0.5, "Konsens lfd. GJ: " + pc(v.g0))}${field("g2", "Umsatzwachstum Jahr 2", base ? base.g2 : v.g1, 0.5, "Konsens nächstes GJ: " + pc(v.g1))}
           ${field("margin", "Operative Marge", base ? base.margin : v.opm, 0.5, "Ø 3 GJ: " + pc(v.opm, 1, false))}${field("tax", "Steuerquote", base ? base.tax : v.tax)}
           ${field("capex", "Capex in % Umsatz", base ? base.capex : v.capex)}${field("da", "Abschreibungen in % Umsatz", base ? base.da : v.da)}${field("nwc", "Working-Capital-Bedarf in % Umsatz", base ? base.nwc : v.nwc)}`}
      ${field("rf", "Risikofreier Zins", o.rf ?? v.rf, 0.1, esc(v.rf_src || ""))}${field("erp", "Aktienrisikoprämie", o.erp ?? v.erp, 0.25, "Annahme")}
      <label>Beta (angepasst)<input type="number" step="0.05" data-k="beta" data-raw="1" value="${(o.beta ?? W.beta).toFixed(2)}"><span></span><small>Yahoo-Beta ${nf(v.beta, 2)} → Blume-Anpassung</small></label>
      ${field("tg", "Ewiges Wachstum", o.tg ?? v.tg, 0.25)}${fin ? "" : field("wacc", "WACC (überschreiben)", o.wacc ?? (base ? base.wacc : W.wacc), 0.25, `berechnet: Eigenkapital ${pc(W.ke, 1, false)}, Fremdkapital ${pc(W.kd, 1, false)}`)}
      </div><button type="button" class="tbtn" id="vaReset">Annahmen zurücksetzen</button></div>
      <div><b>Ergebnis</b>${scenHtml(s, f.error ? null : f)}${!f.error && !fin ? sensitivity(v, f.base.a) + dcfRows(f.base, v) : ""}</div></div>
    <p class="small muted">Ein Fair Value ist eine modellabhängige Schätzung, kein objektiv garantierter Kurs. Basis: letztes Geschäftsjahr ${esc(v.fy || "–")} (Ist, ${esc(s.fcur)}${s.fcur !== v.cur ? " → umgerechnet in " + esc(v.cur) : ""}). Wachstum Jahr 3–10 läuft linear auf das ewige Wachstum zu. Bear/Bull: Wachstum ∓, Marge ×0,85/×1,10, WACC +1/−0,5 pp. Nettoverschuldung ${big(v.net_debt, v.cur)} · Aktien ${big(v.shares)}</p>`;
  box("vaBody").querySelectorAll("input[data-k]").forEach(i => i.addEventListener("change", () => {
    const k = i.dataset.k; if (i.value === "") delete o[k]; else o[k] = i.dataset.raw ? +i.value : +i.value / 100; delete valCache[s.t]; renderValuation(); }));
  box("vaReset").addEventListener("click", () => { delete ovr[s.t]; delete valCache[s.t]; renderValuation(); });
}
function sensitivity(v, a) {
  const ws = [-0.01, -0.005, 0, 0.005, 0.01].map(d => a.wacc + d), gs = [-0.01, -0.005, 0, 0.005, 0.01].map(d => a.tg + d);
  return `<b class="small">Sensitivität: Fair Value je Aktie (WACC × ewiges Wachstum)</b><div class="tscroll"><table class="dt num sens"><tr><th></th>${gs.map(g => `<th>g ${pc(g, 1, false)}</th>`).join("")}</tr>
    ${ws.map(w => `<tr><th>WACC ${pc(w, 1, false)}</th>${gs.map(g => { if (w <= g + 0.005) return "<td>–</td>"; const fv = dcfValue(v, { ...a, wacc: w, tg: g }).fv; return `<td class="${fv > v.px ? "up" : "down"}">${nf(fv, 0)}</td>`; }).join("")}</tr>`).join("")}</table></div>`;
}
function dcfRows(b, v) {
  return `<details><summary class="small">Cashflow-Projektion Base Case (Endwert-Anteil ${pc(b.tvShare, 0, false)})</summary><div class="tscroll"><table class="dt num"><tr><th>Jahr</th>${b.rows.map(r => `<th>${r.t}</th>`).join("")}</tr>
    <tr><td>Wachstum</td>${b.rows.map(r => `<td>${pc(r.g, 1)}</td>`).join("")}</tr><tr><td>Umsatz</td>${b.rows.map(r => `<td>${big(r.rev)}</td>`).join("")}</tr>
    <tr><td>EBIT</td>${b.rows.map(r => `<td>${big(r.ebit)}</td>`).join("")}</tr><tr><td>FCFF</td>${b.rows.map(r => `<td>${big(r.fcf)}</td>`).join("")}</tr></table></div>
    <div class="muted small">Unternehmenswert ${big(b.ev, v.cur)} − Nettoverschuldung ${big(v.net_debt, v.cur)} = Eigenkapital ${big(b.eq, v.cur)}. Ein Endwert-Anteil über 75 % macht das Ergebnis stark annahmeabhängig.</div></details>`;
}

/* ============================================================ 6 RISK MONITOR */
const rf = { level: "confirmed", cat: "" };
function renderRisk() {
  if (pending("rkBody")) return;
  const all = STK.flatMap(s => (s.flags || []).map(f => ({ s, f })));
  const cnt = l => all.filter(x => x.f.level === l).length;
  const cats = [...new Set(all.map(x => x.f.cat))].sort();
  const mk = warnings();
  const watch = new Set([...FAVS(), ...depotSyms()]);
  const wl = STK.filter(s => watch.has(s.t) && (s.flags || []).some(f => f.level !== "dq"));
  const list = all.filter(x => (!rf.level || x.f.level === rf.level) && (!rf.cat || x.f.cat === rf.cat));
  const byS = {}; list.forEach(x => (byS[x.s.t] = byS[x.s.t] || { s: x.s, F: [] }).F.push(x.f));
  const L = { confirmed: "Confirmed Risk", potential: "Potential Risk", dq: "Data Quality Warning" };
  box("rkBody").innerHTML = `<div class="g3">
    <div class="card"><h3>Marktrisiken</h3>${mk.length ? `<ul>${mk.map(i => `<li><span class="down">▼</span> ${esc(i.name)}: <b>${nf(i.value, 2)} ${esc(i.unit)}</b> <span class="muted small">${esc(i.rule)} · ${esc(i.source)}</span></li>`).join("")}</ul>` : '<div class="muted">Kein Regime-Indikator im Warnbereich.</div>'}</div>
    <div class="card"><h3>Deine Watchlist & Depot</h3>${wl.length ? `<ul>${wl.map(s => `<li><a href="#" data-rx="${esc(s.t)}">${esc(s.n)}</a> ${flagBadges(s)} <span class="small">${esc(s.flags.filter(f => f.level !== "dq").map(f => f.text).join(", "))}</span></li>`).join("")}</ul>` : '<div class="muted">Keine Red Flags bei deinen Werten (oder keine Werte in Watchlist/Depot).</div>'}</div>
    <div class="card"><h3>Übersicht</h3><div><span class="fl confirmed">${cnt("confirmed")}</span> Confirmed · <span class="fl potential">${cnt("potential")}</span> Potential · <span class="fl dq">${cnt("dq")}</span> Datenqualität</div>
      <p class="small muted">Confirmed = aus Ist-Zahlen der Abschlüsse belegt · Potential = Markt-/Schätzsignale · Data Quality = Daten fehlen, sind alt oder in anderer Währung.</p></div></div>
    <div class="filters"><select id="rkL">${[["", "Alle Stufen"], ...Object.entries(L)].map(([k, l]) => `<option value="${k}"${rf.level === k ? " selected" : ""}>${l}</option>`).join("")}</select>
      <select id="rkC"><option value="">Alle Kategorien</option>${cats.map(c => `<option${rf.cat === c ? " selected" : ""}>${esc(c)}</option>`).join("")}</select> <span class="muted small">${Object.keys(byS).length} Unternehmen</span></div>
    <div class="tscroll"><table class="dt"><thead><tr><th>Unternehmen</th><th>Befunde</th></tr></thead><tbody>
    ${Object.values(byS).sort((a, b) => b.F.length - a.F.length).map(x => `<tr class="click" data-rx="${esc(x.s.t)}"><td><b>${esc(x.s.n)}</b><div class="muted small">${esc(x.s.t)} · ${esc(x.s.sec || "")}</div></td>
      <td>${x.F.map(f => `<div><span class="fl ${f.level}">${f.level === "confirmed" ? "C" : f.level === "potential" ? "P" : "D"}</span> ${esc(f.text)}: <b>${esc(f.value)}</b> <span class="muted small">${esc(f.rule)} · ${esc(f.src)}</span></div>`).join("")}</td></tr>`).join("")}</tbody></table></div>`;
  box("rkL").addEventListener("change", e => { rf.level = e.target.value; renderRisk(); });
  box("rkC").addEventListener("change", e => { rf.cat = e.target.value; renderRisk(); });
}

/* ============================================================ 7 MACRO INTELLIGENCE */
function sparkSvg(h) {
  const v = (h || []).map(p => p[1]).filter(x => x != null); if (v.length < 3) return "";
  const mn = Math.min(...v), mx = Math.max(...v), w = 120, hh = 28;
  return `<svg viewBox="0 0 ${w} ${hh}" class="spk"><polyline fill="none" stroke="var(--s1)" stroke-width="1.5" points="${v.map((x, i) => `${(i / (v.length - 1) * w).toFixed(1)},${(hh - 2 - (x - mn) / (mx - mn || 1) * (hh - 4)).toFixed(1)}`).join(" ")}"/></svg>`;
}
const QCOL = { "Inflationary Growth": "#c98500", "Disinflationary Growth": "#199e70", "Stagflation": "#d55181", "Stagflation-Risiko": "#9085e9", "Slowdown": "#3987e5", "Recession": "#e66767" };
function renderMacro() {
  if (pending("maBody")) return;
  const rows = R.macro;
  const S2 = SECT.filter(s => s.sens && s.sens.betas);
  const lists = (R.sectors.macro_factors || []).map((f, j) => {
    const arr = S2.map(s => ({ s, b: s.sens.betas[j] })).filter(x => x.b && Math.abs(x.b.t) >= 2);
    const pos = arr.filter(x => x.b.beta > 0).sort((a, b) => b.b.beta - a.b.beta).slice(0, 4), neg = arr.filter(x => x.b.beta < 0).sort((a, b) => a.b.beta - b.b.beta).slice(0, 4);
    return `<div class="card"><h3>${esc(f)}</h3><div class="small"><b class="up">relativ stärker:</b> ${pos.map(x => `${esc(x.s.name)} (${pc(x.b.beta, 1)})`).join(", ") || "<span class='muted'>keine signifikanten</span>"}</div>
      <div class="small"><b class="down">relativ schwächer:</b> ${neg.map(x => `${esc(x.s.name)} (${pc(x.b.beta, 1)})`).join(", ") || "<span class='muted'>keine signifikanten</span>"}</div></div>`;
  }).join("");
  const RH = R.regime_history || [];
  box("maBody").innerHTML = `<div class="tscroll"><table class="dt"><thead><tr><th>Indikator</th><th>Aktuell</th><th>Δ 3 M</th><th>Δ 12 M</th><th>Verlauf 10 J</th><th>Stand</th><th>Quelle</th></tr></thead><tbody>
    ${rows.map(m => `<tr><td>${esc(m.label)}<div class="muted small">${esc(m.freq)} · ${esc(m.type || "")}</div></td><td><b>${m.value == null ? "–" : nf(m.value, Math.abs(m.value) > 1000 ? 0 : 2)}</b> <span class="muted small">${esc(m.unit)}</span></td>
      <td class="${m.d3m == null ? "muted" : ""}">${m.d3m == null ? "–" : (m.d3m > 0 ? "+" : "") + nf(m.d3m, 2)}</td><td>${m.d12m == null ? "–" : (m.d12m > 0 ? "+" : "") + nf(m.d12m, 2)}</td>
      <td>${sparkSvg(m.hist)}</td><td>${dfmt(m.asof)}</td><td class="small"><a href="${esc(m.url)}" target="_blank" rel="noopener noreferrer">${esc(m.source)}</a></td></tr>`).join("")}</tbody></table></div>
    <h3 style="margin-top:18px">Regime-Verlauf (monatlich, regelbasiert)</h3>
    <div class="rhist">${RH.map(([d, q]) => `<i style="background:${QCOL[q] || "var(--line)"}" title="${esc(d)}: ${esc(q)}"></i>`).join("")}</div>
    <div class="lg">${Object.entries(QCOL).map(([q, c]) => `<span><i style="background:${c}"></i>${esc(q)}</span>`).join("")}</div>
    <div class="muted small">${RH.length ? `${esc(RH[0][0])} – ${esc(RH[RH.length - 1][0])}` : ""} · aus heutigem (revidiertem) FRED-Datenstand berechnet</div>
    <h3 style="margin-top:18px">Wie reagieren Branchen auf Makro-Faktoren? <span class="muted small">historisch, 3 Jahre wöchentlich, nur statistisch auffällige (|t| ≥ 2)</span></h3>
    <div class="g2">${lists}</div>
    <div class="tscroll"><table class="dt num"><thead><tr><th>Branche</th>${(R.sectors.macro_factors || []).map(f => `<th>${esc(f)}</th>`).join("")}<th>R²</th></tr></thead><tbody>
      ${S2.map(s => `<tr><td>${esc(s.name)}</td>${s.sens.betas.map(b => `<td class="${Math.abs(b.t) >= 2 ? cl(b.beta) : "muted"}">${pc(b.beta, 1)}${Math.abs(b.t) >= 2 ? " ✱" : ""}</td>`).join("")}<td>${nf(s.sens.r2, 2)}</td></tr>`).join("")}</tbody></table></div>
    <p class="small muted">Lesebeispiel: „Zins 10J (+1 pp) → −3 %“ = Die Branche lag in den letzten drei Jahren im Schnitt etwa 3 % hinter dem S&P 500, wenn die 10-jährige US-Rendite um einen Prozentpunkt stieg. Das ist ein statistischer Zusammenhang (Korrelation), keine Kausalität, und kann sich ändern. Fiskal- und Handelspolitik sind nicht quantifiziert.</p>`;
}

/* ============================================================ 8 NEWS & CATALYSTS */
function renderCatalysts() {
  if (pending("caBody")) return;
  const C = R.catalysts, ki = (window.DASH && window.DASH.ki && window.DASH.ki.news_analyse) || [];
  const DIR = { bullish: ["▲ Bullish", "up"], bearish: ["▼ Bearish", "down"], neutral: ["■ Neutral", "muted"], mixed: ["◆ Mixed", "warn"] };
  box("caBody").innerHTML = `${ki.length ? `<h3>KI-Einordnung der wichtigsten Nachrichten <span class="muted small">qualitative Einschätzung (Claude mit Websuche), Fakten und Interpretation getrennt</span></h3>
    ${ki.map(n => { const [l, c] = DIR[n.richtung] || ["–", "muted"]; return `<div class="card nk"><div><span class="${c}"><b>${l}</b></span> · Relevanz ${esc(n.relevanz)}/5 · Horizont: ${esc(n.horizont)} · Unsicherheit: ${esc(n.unsicherheit)}</div>
      <b>${esc(n.titel)}</b> <span class="muted small">${esc(n.quelle)} · ${esc(n.datum)}</span>
      <div class="small"><b>Fakten:</b> ${esc(n.fakten)}</div><div class="small"><b>Interpretation:</b> ${esc(n.interpretation)}</div>
      <div class="small"><b>Wirkung</b> Umsatz: ${esc(n.wirkung_umsatz)} · Gewinn: ${esc(n.wirkung_gewinn)} · Bewertung: ${esc(n.wirkung_bewertung)}</div>
      <div class="small muted">Betroffen: ${esc((n.unternehmen || []).join(", ") || "–")} · Branchen: ${esc((n.branchen || []).join(", ") || "–")}</div></div>`; }).join("")}` : ""}
    <div class="g2"><div><h3>Termine: Quartalszahlen (45 Tage)</h3><table class="dt"><tbody>${C.earnings.map(e => `<tr class="click" data-rx="${esc(e.t)}"><td>${dfmt(e.date)}</td><td>${esc(e.n)}</td><td class="small">${e.eps_avg != null ? "EPS-Konsens " + nf(e.eps_avg, 2) : ""}</td></tr>`).join("") || "<tr><td class='muted'>keine</td></tr>"}</tbody></table></div>
      <div><h3>Analysten: Hoch- und Herabstufungen (21 Tage)</h3><table class="dt"><tbody>${C.actions.map(a => `<tr class="click" data-rx="${esc(a.t)}"><td>${dfmt(a.date)}</td><td>${esc(a.n)}</td>
        <td class="${a.action === "up" ? "up" : a.action === "down" ? "down" : ""}">${a.action === "up" ? "▲ Upgrade" : a.action === "down" ? "▼ Downgrade" : "Neuaufnahme"}</td><td class="small">${esc(a.firm)}: ${esc(a.from || "")} → ${esc(a.to || "")}${a.pt ? ` · Ziel ${nf(a.pt, 0)}` : ""}</td></tr>`).join("") || "<tr><td class='muted'>keine</td></tr>"}</tbody></table></div></div>
    <p class="small muted">Quelle Termine & Analystenaktionen: Yahoo Finance. Doppelte Meldungen derselben Aktion werden zusammengefasst.</p>`;
}

/* ============================================================ 9 WATCHLIST */
function FAVS() { try { return JSON.parse(store.get("favs") || "[]"); } catch (e) { return []; } }
function toggleFav(t) { const l = FAVS(), i = l.indexOf(t); i >= 0 ? l.splice(i, 1) : l.push(t); store.set("favs", JSON.stringify(l)); try { window.TB_onFav && window.TB_onFav(); } catch (e) {} }
function depotSyms() { try { return (JSON.parse(store.get("depot") || "[]") || []).map(p => p.sym || p.t || p.ticker).filter(Boolean); } catch (e) { return []; } }
function renderWatch() {
  if (pending("wlBody")) return;
  const l = [...new Set([...depotSyms(), ...FAVS()])];
  const rows = l.map(t => BY[t]).filter(Boolean);
  box("wlBody").innerHTML = rows.length ? `<div class="tscroll"><table class="dt rank"><thead><tr><th>Unternehmen</th><th>Kurs</th><th>1 T</th><th>Score</th><th>Klasse</th><th>DCF-Upside</th><th>Risk Score</th><th>Red Flags</th><th>Nächste Zahlen</th></tr></thead><tbody>
    ${rows.map(s => { const z = stockZ(s), d = ((s.ev || {}).calendar || {})["Earnings Date"]; return `<tr class="click" data-rx="${esc(s.t)}"><td><b>${esc(s.n)}</b><div class="muted small">${esc(s.t)}${depotSyms().includes(s.t) ? " · im Depot" : ""}</div></td>
      <td>${nf(s.px, 2)} ${esc(s.cur)}</td><td class="${cl(s.d1)}">${pc(s.d1)}</td><td>${toScore(z) ?? "–"}</td><td>${sbadge(s)}</td><td class="${cl(upside(s))}">${pc(upside(s), 0)}</td><td>${riskScore(s.z.risk) ?? "–"}</td><td>${flagBadges(s)}</td><td>${d ? dfmt(d) : "–"}</td></tr>`; }).join("")}</tbody></table></div>
    ${l.length > rows.length ? `<div class="muted small">Ohne Research-Daten: ${l.filter(t => !BY[t]).map(esc).join(", ")}</div>` : ""}`
    : '<div class="muted">Noch keine Werte. Im Equity Research oder im Steckbrief mit ☆ hinzufügen; Depot-Werte erscheinen automatisch.</div>';
}

/* ------------------------------------------------------------ Bereich rendern */
const RENDER = {
  overview: () => { renderRegime(); renderOverview(); renderSources(); }, sector: () => { renderSectors(); renderBacktest(); }, screener: renderScreener,
  research: renderResearch, valuation: renderValuation, risk: renderRisk, macro: renderMacro, news: renderCatalysts, watch: renderWatch,
};
function renderArea(a) { try { (RENDER[a] || (() => {}))(); } catch (e) { console.error(e); } }
const RX = window.RX = {
  open(t, area = "research") { if (!R || !BY[t]) { alert("Für " + t + " liegen (noch) keine Research-Daten vor."); return; } sel = t; store.set("rxSel", t); try { window.TB && window.TB.close && window.TB.close(); } catch (e) {} show(area); },
  has: t => !!(R && BY[t]), show, _t: { dcfValue, impliedGrowth, riScen, waccOf },
};
show(current, { keepScroll: true });
loadData();
})();
