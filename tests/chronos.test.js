// PROJECT CHRONOS (docs/chronos.js): Datenkern – nur belegte Werte, nach dem letzten Datenjahr nichts.
// Ausführen: node --test tests/
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const C = require("../docs/chronos.js");

const years = Array.from({ length: 31 }, (_, i) => 2000 + i);   // 2000–2030 wie world.js
const arr = f => years.map(f);
const W = { years, indicators: {
  NGDP_RPCH: { DEU: arr(y => y >= 2026 ? 1 + (y - 2026) * 0.1 : 0.5), USA: arr(y => y === 2028 ? -0.5 : 2), FRA: arr(y => y === 2029 ? null : 1.5) },
  PCPIPCH: { DEU: arr(() => 2) },
} };

test("Zeitachse 2026–2050", () => { assert.equal(C.Y0, 2026); assert.equal(C.Y1, 2050); });

test("Letztes Datenjahr aus den Daten, nicht fest verdrahtet", () => {
  assert.equal(C.lastDataYear(W, "NGDP_RPCH"), 2030);
  const W2 = { years, indicators: { NGDP_RPCH: { DEU: arr(y => y <= 2027 ? 1 : null) } } };
  assert.equal(C.lastDataYear(W2, "NGDP_RPCH"), 2027);
  assert.equal(C.lastDataYear(W, "UNBEKANNT"), null);
});

test("Werte je Jahr: nur vorhandene, nach 2030 keine", () => {
  assert.deepEqual(C.valuesFor(W, "NGDP_RPCH", 2028).map(x => x[0]).sort(), ["DEU", "FRA", "USA"]);
  assert.deepEqual(C.valuesFor(W, "NGDP_RPCH", 2029).map(x => x[0]).sort(), ["DEU", "USA"]);   // FRA fehlt → nicht geschätzt
  for (const y of [2031, 2040, 2050]) assert.deepEqual(C.valuesFor(W, "NGDP_RPCH", y), []);
});

test("Nur Länder der Karte: Ländergruppen werden ausgeschlossen", () => {
  const W3 = { years, indicators: { NGDP_RPCH: { DEU: arr(() => 1), EUQ: arr(() => 2), WEQ: arr(() => 3) } } };
  assert.deepEqual(C.valuesFor(W3, "NGDP_RPCH", 2028, new Set(["DEU", "FRA"])), [["DEU", 1]]);
});

test("Statistik: Median, Rückgänge, Rangfolge", () => {
  const s = C.stats(C.valuesFor(W, "NGDP_RPCH", 2028));
  assert.equal(s.n, 3); assert.equal(s.neg, 1); assert.equal(s.median, 1.2);
  assert.equal(s.top[0][0], "FRA"); assert.equal(s.bottom[0][0], "USA");
  assert.deepEqual(C.stats([]), { n: 0, median: null, neg: 0, top: [], bottom: [] });
});

test("Länderreihe 2026–2050: nach dem Datenende null, nie fortgeschrieben", () => {
  const s = C.seriesFor(W, "NGDP_RPCH", "DEU");
  assert.equal(s.length, 25); assert.deepEqual(s[0], [2026, 1]);
  assert.ok(s.filter(([y]) => y > 2030).every(([, v]) => v === null));
  assert.ok(C.seriesFor(W, "NGDP_RPCH", "XXX").every(([, v]) => v === null));
});
