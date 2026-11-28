// Global Risk Layer (docs/risklayer.js): Umwandlung der Anbieter-Antworten ins einheitliche Ereignisformat.
// Beispielantworten im Originalformat von USGS GeoJSON und NASA EONET v3 – ohne Netzwerk. Ausführen: node --test tests/
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const RL = require("../docs/risklayer.js");

const T = "2026-11-28T10:00:00.000Z";
const usgs = { type: "FeatureCollection", features: [
  { id: "us1", geometry: { type: "Point", coordinates: [-172.73, -18.52, 10] },
    properties: { mag: 4.6, magType: "mb", place: "132 km E of Neiafu, Tonga", time: 1795857400051, alert: null, tsunami: 0, status: "reviewed",
      url: "https://earthquake.usgs.gov/earthquakes/eventpage/us1", title: "M 4.6 - 132 km E of Neiafu, Tonga" } },
  { id: "us2", geometry: { type: "Point", coordinates: [142.1, 38.2, 30] },
    properties: { mag: 6.8, magType: "mww", place: "Japan", time: 1795857400051, alert: "orange", tsunami: 1, status: "automatic", url: "u", title: "M 6.8 - Japan" } },
  { id: "us3", geometry: { type: "Point", coordinates: [0, 0, 5] }, properties: { mag: 5.0, time: 0, alert: "red", status: "reviewed", url: "u", title: "x" } },
] };
const eonet = { events: [
  { id: "E1", title: "Wildfire A", link: "l1", categories: [{ id: "wildfires", title: "Wildfires" }], sources: [{ id: "IRWIN", url: "https://irwin/1" }],
    geometry: [{ magnitudeValue: 900, magnitudeUnit: "acres", date: "2026-11-21T23:15:00Z", type: "Point", coordinates: [-79.79, 38.31] }] },
  { id: "E2", title: "Typhoon B", link: "l2", categories: [{ id: "severeStorms", title: "Severe Storms" }], sources: [],
    geometry: [{ magnitudeValue: 50, magnitudeUnit: "kts", date: "2026-11-26T00:00:00Z", type: "Point", coordinates: [130, 15] },
               { magnitudeValue: 115, magnitudeUnit: "kts", date: "2026-11-27T00:00:00Z", type: "Point", coordinates: [131, 16] }] },
  { id: "E3", title: "Iceberg", categories: [{ id: "seaLakeIce" }], geometry: [{ date: "2026-11-20T00:00:00Z", type: "Point", coordinates: [0, -70] }] },
  { id: "E4", title: "Volcano C", link: "l4", categories: [{ id: "volcanoes", title: "Volcanoes" }], sources: [],
    geometry: [{ date: "2026-11-25T00:00:00Z", type: "Polygon", coordinates: [[[10, 10], [12, 10], [12, 12], [10, 12]]] }] },
] };

test("USGS: Format, Schwere, Bestätigung", () => {
  const ev = RL.usgsToEvents(usgs, T);
  assert.equal(ev.length, 3);
  const [a, b, c] = ev;
  assert.deepEqual([a.type, a.lat, a.lon, a.severity, a.confidence, a.fetchedAt], ["earthquake", -18.52, -172.73, 1, "fact", T]);
  assert.equal(b.severity, 3);            // M6.8 → 3, PAGER orange 3, Tsunami ≥ 3
  assert.equal(b.confidence, "possible"); // automatisch = vorläufig
  assert.equal(c.severity, 4);            // PAGER rot hebt auf 4
  for (const e of ev) for (const k of ["id", "type", "lat", "lon", "time", "severity", "title", "source", "url", "fetchedAt", "confidence"]) assert.ok(k in e, k);
});

test("EONET: Typen, letzter Messpunkt, Polygon-Mitte, Eisberge ausgelassen", () => {
  const ev = RL.eonetToEvents(eonet, T);
  assert.deepEqual(ev.map(e => e.id), ["eonet:E1", "eonet:E2", "eonet:E4"]);
  const [fire, storm, volc] = ev;
  assert.equal(fire.type, "wildfire"); assert.equal(fire.severity, 1); assert.equal(fire.url, "https://irwin/1");
  assert.equal(storm.type, "storm"); assert.equal(storm.severity, 3); assert.deepEqual([storm.lon, storm.lat], [131, 16]);
  assert.equal(volc.type, "other"); assert.equal(volc.severity, 2); assert.deepEqual([volc.lon, volc.lat], [11, 11]);  // Mitte des Quadrats 10–12
});

test("Schwere-Stufen Sturm (kts) und Brand (acres)", () => {
  assert.deepEqual([40, 64, 96, 130].map(v => RL.sevEONET("severeStorms", { magnitudeValue: v, magnitudeUnit: "kts" })), [1, 2, 3, 4]);
  assert.deepEqual([500, 10000, 100000].map(v => RL.sevEONET("wildfires", { magnitudeValue: v, magnitudeUnit: "acres" })), [1, 2, 3]);
});

test("Anbieter-Schnittstelle: ohne Schlüssel, HTTPS, Lizenz angegeben", () => {
  for (const p of RL.PROVIDERS) {
    assert.equal(p.needsKey, false);
    assert.ok(p.url.startsWith("https://") && p.licenseUrl.startsWith("https://"));
    assert.ok(p.license && p.refreshSec >= 300 && typeof p.toEvents === "function");
  }
});

test("Leere oder kaputte Antworten führen nicht zu erfundenen Ereignissen", () => {
  assert.deepEqual(RL.usgsToEvents(null, T), []);
  assert.deepEqual(RL.eonetToEvents({}, T), []);
  assert.deepEqual(RL.usgsToEvents({ features: [{ id: "x" }] }, T), []);
});
