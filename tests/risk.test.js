// Rechenkern des Portfolio Risk Center (docs/risk.js) mit festen Beispieldaten – ohne Netzwerk.
// Ausführen: node --test tests/
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const R = require("../docs/risk.js");

const near = (a, b, eps = 1e-9) => assert.ok(Math.abs(a - b) < eps, `${a} ≈ ${b}`);
// Profil mit täglichen Kursen ab Tag 20000 (Lücke 1 Tag), Kurse aus Funktion
function prof(t, f, extra = {}) {
  const n = 300, px = Array.from({ length: n }, (_, i) => f(i));
  return { t, n: t, sec: "Tech", land: "Germany", cur: "EUR", d0: 20000, g: "1".repeat(n - 1), px, ...extra };
}
const wave = i => 100 * (1 + 0.05 * Math.sin(i / 5));
const D = { fx: { EUR: 1, USD: 0.9 }, dates: Array.from({ length: 300 }, (_, i) => 20000 + i),
  series: { "^GDAXI": { v: Array.from({ length: 300 }, (_, i) => wave(i)) }, "^GSPC": { v: Array.from({ length: 300 }, (_, i) => 50 + i * 0.1) } } };

test("Max. Drawdown", () => {
  near(R.maxDrawdown([100, 120, 90, 130]), -0.25);
  near(R.maxDrawdown([1, 2, 3]), 0);
});

test("Kursreihe aus d0 + Lückenstring", () => {
  const m = R.seriesOfProfile({ d0: 10, g: "13", px: [1, 2, 3] });
  assert.deepEqual([...m.entries()], [[10, 1], [11, 2], [14, 3]]);
});

test("Gewichte, Konzentration, Wechselkurs", () => {
  const P = [prof("A", wave), prof("B", i => 50 + i * 0.01, { cur: "USD", land: "United States" })];
  const out = R.compute([{ t: "A", qty: 1, buy: 90 }, { t: "B", qty: 10, buy: 40 }], P, D, {});
  assert.ok(out.ok);
  const a = out.positions.find(x => x.t === "A"), b = out.positions.find(x => x.t === "B");
  near(a.value, wave(299)); near(b.value, 10 * (50 + 299 * 0.01) * 0.9);
  near(a.w + b.w, 1);
  near(out.conc.effN, 1 / (a.w ** 2 + b.w ** 2));
  near(out.fremd, b.w);
});

test("Identische Werte: Korrelation 1, Beta zum gleichen Index 1", () => {
  const P = [prof("A", wave), prof("B", wave)];
  const out = R.compute([{ t: "A", qty: 1, buy: 1 }, { t: "B", qty: 1, buy: 1 }], P, D, {});
  near(out.port.corr[0][1], 1, 1e-9);
  const dax = out.port.bench.find(x => x.t === "^GDAXI");
  near(dax.beta, 1, 1e-9); near(dax.corr, 1, 1e-9);
  assert.ok(out.hints.some(h => h.includes("sehr ähnlich")));
});

test("Gegenläufige Werte: negative Korrelation, geringere Depot-Volatilität", () => {
  const P = [prof("A", wave), prof("B", i => 200 - wave(i))];
  const out = R.compute([{ t: "A", qty: 1, buy: 1 }, { t: "B", qty: 1, buy: 1 }], P, D, {});
  assert.ok(out.port.corr[0][1] < -0.9);
  assert.ok(out.port.vol < Math.min(...out.positions.map(x => x.vol)));
});

test("Fehlende Daten werden ausgewiesen, nicht geschätzt", () => {
  const P = [prof("A", wave), prof("C", wave, { cur: "XYZ" })];
  const out = R.compute([{ t: "A", qty: 1, buy: 1 }, { t: "C", qty: 1, buy: 1 }, { t: "ZZZ", qty: 1, buy: 1 }], P, D, {});
  assert.deepEqual(out.missing.map(m => m.t).sort(), ["C", "ZZZ"]);
  assert.equal(out.positions.length, 1);
  near(out.positions[0].w, 1);
  assert.equal(R.compute([], P, D, {}).ok, false);
});

test("Lage: Konfliktliste und Eskalationsstufe", () => {
  const P = [prof("I", wave, { land: "Israel" }), prof("U", wave, { land: "United States" })];
  const W = { escalation: { USA: { stufe: 3 } } };
  const out = R.compute([{ t: "I", qty: 1, buy: 1 }, { t: "U", qty: 1, buy: 1 }], P, D, W, { konfliktzonen: ["ISR"] });
  assert.equal(out.positions.find(x => x.t === "I").lage.konflikt, true);
  assert.equal(out.positions.find(x => x.t === "U").lage.stufe, 3);
  // Hinweis nur für die Konfliktliste; die Schlagzeilen-Stufe ist Info in der Tabelle, kein Hinweis
  assert.deepEqual(out.hints.filter(h => h.includes("Sitzland")), ["I: Sitzland Israel steht auf der Konfliktliste."]);
});

test("Depot-Rendite = heutige Stückzahlen zurückgerechnet (Kauf und Halten)", () => {
  const fa = i => 100 + i, fb = i => 200 - i * 0.2;
  const P = [prof("A", fa), prof("B", fb, { cur: "USD" })];
  const out = R.compute([{ t: "A", qty: 2, buy: 1 }, { t: "B", qty: 3, buy: 1 }], P, D, {});
  // Fenster: letzte 365 Kalendertage → Tage 299-365 … 299 = Index 0 … 299 (alle 300 Tage liegen im Fenster)
  const v = i => 2 * fa(i) + 3 * 0.9 * fb(i);
  near(out.port.ret, v(299) / v(0) - 1, 1e-12);
});

test("Gleiche Symbole werden zusammengefasst", () => {
  const out = R.compute([{ t: "A", qty: 1, buy: 1 }, { t: "A", qty: 2, buy: 1 }], [prof("A", wave)], D, {});
  assert.equal(out.positions.length, 1); near(out.positions[0].qty, 3);
});
