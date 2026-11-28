/* PROJECT A.L.F.R.E.D. – Global Risk Layer (Phase 4).
   Einheitliche Anbieter-Schnittstelle { id, name, source, license, licenseUrl, needsKey, refreshSec, url, toEvents(json, fetchedAt) }
   → Ereignis { id, type, lat, lon, time, severity 0–4, title, source, url, fetchedAt, confidence: fact|possible|forecast, details }.
   Quellen (geprüft 28.11.2026): USGS Erdbeben-Feed (gemeinfrei, CORS offen, ohne Schlüssel) und NASA EONET v3 (offen, ohne Schlüssel).
   Lädt NICHTS, solange die Ebene ausgeschaltet ist. Keine kostenpflichtigen Dienste. Zivile Naturereignisse, keine militärischen Daten. */
(function (global) {
  "use strict";
  const SEV_TXT = ["gering", "niedrig", "mittel", "hoch", "sehr hoch"];
  const TYPES = {   // Farben validiert (alle Paare, dunkle Fläche); Form als zweites Merkmal, „Sonstiges“ nur Umriss
    wildfire: { label: "Waldbrand", color: "#c98500", shape: "triangle" },
    earthquake: { label: "Erdbeben", color: "#d55181", shape: "circle" },
    storm: { label: "Sturm", color: "#3987e5", shape: "diamond" },
    other: { label: "Sonstiges (Vulkan, Flut …)", color: null, shape: "square" },
  };

  /* ---------------- Umwandlung (rein, testbar) ---------------- */
  function sevUSGS(p) {
    const m = p.mag;
    let s = m == null ? 0 : m < 5.5 ? 1 : m < 6.5 ? 2 : m < 7.5 ? 3 : 4;
    const alert = { green: 1, yellow: 2, orange: 3, red: 4 }[p.alert];       // USGS PAGER-Einstufung, falls vorhanden
    if (alert) s = Math.max(s, alert);
    if (p.tsunami === 1) s = Math.max(s, 3);
    return s;
  }
  function usgsToEvents(json, fetchedAt) {
    return ((json && json.features) || []).filter(f => f && f.geometry && f.properties).map(f => {
      const p = f.properties, [lon, lat, depth] = f.geometry.coordinates;
      return { id: "usgs:" + f.id, type: "earthquake", lat, lon, time: new Date(p.time).toISOString(), severity: sevUSGS(p),
        title: p.title || `M ${p.mag} – ${p.place}`, source: "U.S. Geological Survey", url: p.url, fetchedAt,
        confidence: p.status === "reviewed" ? "fact" : "possible",
        details: { Magnitude: p.mag != null ? `${p.mag} ${p.magType || ""}`.trim() : null, Tiefe: depth != null ? `${Math.round(depth)} km` : null,
          "PAGER-Alarm": p.alert ? ({ green: "grün", yellow: "gelb", orange: "orange", red: "rot" }[p.alert] || p.alert) : null, Tsunami: p.tsunami === 1 ? "Hinweis vorhanden (siehe NOAA/USGS)" : null, Status: p.status === "reviewed" ? "geprüft" : "automatisch, vorläufig" } };
    });
  }
  const EONET_TYPE = { wildfires: "wildfire", severeStorms: "storm" };
  const EONET_SKIP = new Set(["seaLakeIce", "waterColor", "earthquakes"]);   // Eisberge/Wasserfarbe ohne Risiko; Erdbeben kommen von USGS
  function sevEONET(cat, g) {
    const v = g && g.magnitudeValue, u = g && g.magnitudeUnit;
    if (cat === "severeStorms") return v == null ? 1 : v < 64 ? 1 : v < 96 ? 2 : v < 130 ? 3 : 4;      // Wind in kts (Saffir-Simpson-Stufen)
    if (cat === "wildfires") return u === "acres" && v >= 100000 ? 3 : u === "acres" && v >= 10000 ? 2 : 1;
    if (cat === "volcanoes" || cat === "floods") return 2;
    return 1;
  }
  function centroid(geo) {
    if (geo.type === "Point") return geo.coordinates;
    const ring = geo.type === "Polygon" ? geo.coordinates[0] : null; if (!ring || !ring.length) return null;
    return [ring.reduce((s, c) => s + c[0], 0) / ring.length, ring.reduce((s, c) => s + c[1], 0) / ring.length];
  }
  function eonetToEvents(json, fetchedAt) {
    const out = [];
    ((json && json.events) || []).forEach(e => {
      const cat = ((e.categories || [])[0] || {}).id; if (!cat || EONET_SKIP.has(cat)) return;
      const g = (e.geometry || [])[e.geometry.length - 1]; if (!g) return;
      const c = centroid(g); if (!c) return;
      out.push({ id: "eonet:" + e.id, type: EONET_TYPE[cat] || "other", lat: c[1], lon: c[0], time: g.date, severity: sevEONET(cat, g),
        title: e.title, source: "NASA EONET" + ((e.sources || [])[0] ? " · " + e.sources[0].id : ""), url: ((e.sources || [])[0] || {}).url || e.link,
        fetchedAt, confidence: "fact",
        details: { Kategorie: ((e.categories || [])[0] || {}).title || cat, Größe: g.magnitudeValue != null ? `${g.magnitudeValue} ${g.magnitudeUnit || ""}`.trim() : null,
          Messpunkte: (e.geometry || []).length } });
    });
    return out;
  }
  const PROVIDERS = [
    { id: "usgs-eq", name: "Erdbeben M4.5+ · 7 Tage", source: "U.S. Geological Survey", license: "gemeinfrei (U.S. Public Domain) · Credit: U.S. Geological Survey",
      licenseUrl: "https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits", needsKey: false, refreshSec: 600,
      url: "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.geojson", toEvents: usgsToEvents },
    { id: "nasa-eonet", name: "Naturereignisse · offen, 14 Tage", source: "NASA EONET v3", license: "offene NASA-Daten · EONET-Disclaimer",
      licenseUrl: "https://eonet.gsfc.nasa.gov/what-is-eonet", needsKey: false, refreshSec: 1800,
      url: "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&days=14", toEvents: eonetToEvents },
  ];
  const core = { PROVIDERS, TYPES, SEV_TXT, usgsToEvents, eonetToEvents, sevUSGS, sevEONET, centroid };
  if (typeof module !== "undefined" && module.exports) { module.exports = core; return; }

  /* ---------------- Oberfläche ---------------- */
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const when = iso => { const d = new Date(iso); return isNaN(d) ? "unbekannt" : d.toLocaleString("de-DE", { dateStyle: "short", timeStyle: "short" }); };
  const CONF = { fact: "bestätigt", possible: "vorläufig", forecast: "Prognose" };
  const btn = document.getElementById("riskLayerBtn"), mapBox = document.getElementById("worldMap");
  if (!btn || !mapBox || !global.TB_map || !global.d3) return;
  const state = { on: false, data: {}, timer: null };
  const bar = document.createElement("div"); bar.className = "rl-bar"; bar.hidden = true; mapBox.insertAdjacentElement("afterend", bar);
  let g = null;   // erst nach dem Registrieren vorhanden; draw() wartet darauf
  const node = global.TB_map.overlay((pos, s) => draw(pos, s));
  g = global.d3.select(node).append("g").attr("class", "risklayer").attr("display", "none");

  const events = () => Object.values(state.data).flatMap(d => d.events || []).filter(e => e.severity >= 1);
  function shapePath(shape, r) {
    if (shape === "triangle") return `M0,${-r * 1.15}L${r},${r * 0.75}L${-r},${r * 0.75}Z`;
    if (shape === "diamond") return `M0,${-r * 1.2}L${r * 1.2},0L0,${r * 1.2}L${-r * 1.2},0Z`;
    if (shape === "square") return `M${-r * 0.85},${-r * 0.85}h${r * 1.7}v${r * 1.7}h${-r * 1.7}Z`;
    return `M${-r},0a${r},${r} 0 1,0 ${r * 2},0a${r},${r} 0 1,0 ${-r * 2},0`;
  }
  function tipHtml(e) {
    return `<div class="d">${esc(e.title)}</div><div>${esc(TYPES[e.type].label)} · Schwere ${e.severity}/4 (${SEV_TXT[e.severity]})</div>
      <div class="muted">${esc(when(e.time))} · ${esc(CONF[e.confidence])} · ${esc(e.source)}</div>`;
  }
  function draw(pos, s) {
    if (!g) return;
    if (!state.on) { g.attr("display", "none"); return; }
    g.attr("display", null);
    const list = events().sort((a, b) => a.severity - b.severity);   // schwere Ereignisse oben
    const sel = g.selectAll("path.rl").data(list, d => d.id).join(enter => enter.append("path").attr("class", d => "rl rl-" + d.type)
      .attr("tabindex", 0).attr("role", "button").attr("aria-label", d => `${TYPES[d.type].label}: ${d.title}, Schwere ${d.severity} von 4`)
      .on("mousemove", (ev, d) => global.TB_map.showTip(tipHtml(d), ev)).on("mouseleave", () => global.TB_map.hideTip())
      .on("click", (ev, d) => info(d)).on("keydown", (ev, d) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); info(d); } }));
    sel.each(function (d) {
      const p = pos(d.lon, d.lat), el = global.d3.select(this);
      if (!p) { el.attr("display", "none"); return; }
      const r = 2.2 + d.severity * 1.3, T = TYPES[d.type];
      el.attr("display", null).attr("d", shapePath(T.shape, r))
        .attr("transform", `translate(${p[0].toFixed(1)},${p[1].toFixed(1)}) scale(${s.toFixed(3)})`)
        .attr("fill", T.color ? T.color : "none").attr("fill-opacity", T.color ? 0.85 : null)
        .attr("stroke", T.color ? "#000300" : "#c9f7d3").attr("stroke-width", T.color ? 1 : 1.2);
    });
  }
  function info(e) {
    const rows = Object.entries(e.details || {}).filter(([, v]) => v != null && v !== "").map(([k, v]) => `<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`).join("");
    global.TB_map.info(`<h4>${esc(e.title)}</h4>
      <div style="margin-bottom:6px"><span class="spill ${e.severity >= 3 ? "offline" : e.severity === 2 ? "delayed" : "nc"}">SCHWERE ${e.severity}/4 · ${SEV_TXT[e.severity].toUpperCase()}</span>
        <span class="spill ${e.confidence === "fact" ? "live" : "delayed"}">${esc(CONF[e.confidence]).toUpperCase()}</span></div>
      <table class="det"><tr><td>Art</td><td>${esc(TYPES[e.type].label)}</td></tr><tr><td>Zeitpunkt</td><td>${esc(when(e.time))}</td></tr>
        <tr><td>Position</td><td>${e.lat.toFixed(2)}° / ${e.lon.toFixed(2)}°</td></tr>${rows}</table>
      <div style="margin-top:8px"><a class="dbtn" style="display:inline-block;text-decoration:none" href="${esc(e.url)}" target="_blank" rel="noopener noreferrer">QUELLE ↗</a></div>
      <div class="doomnote">Quelle: ${esc(e.source)} · abgerufen ${esc(when(e.fetchedAt))}. Schwere 0–4 ist eine einheitliche Einordnung des Dashboards (Regeln in risklayer.js), keine amtliche Warnstufe.</div>`);
  }
  function renderBar() {
    const L = events(), cnt = t => L.filter(e => e.type === t).length;
    const legend = Object.entries(TYPES).map(([k, T]) => `<span class="rl-key"><svg viewBox="-8 -8 16 16" aria-hidden="true"><path d="${shapePath(T.shape, 5)}" fill="${T.color || "none"}" stroke="${T.color ? "none" : "#c9f7d3"}" stroke-width="1.2"/></svg>${esc(T.label)} <b>${cnt(k)}</b></span>`).join("");
    const st = PROVIDERS.map(p => { const d = state.data[p.id] || {};
      const pill = d.loading ? '<span class="spill nc">LÄDT</span>' : d.error ? `<span class="spill offline" title="${esc(d.error)}">OFFLINE</span>` : d.fetchedAt ? '<span class="spill live">LIVE</span>' : '<span class="spill nc">–</span>';
      return `<span class="rl-src">${pill} ${esc(p.source)} · ${esc(p.name)}${d.fetchedAt ? " · Abruf " + esc(when(d.fetchedAt).split(", ")[1] || when(d.fetchedAt)) : ""} · <a href="${esc(p.licenseUrl)}" target="_blank" rel="noopener noreferrer">${esc(p.license)}</a></span>`; }).join("");
    const top = [...L].sort((a, b) => b.severity - a.severity || new Date(b.time) - new Date(a.time));
    bar.innerHTML = `<div class="rl-legend">${legend}<span class="muted">· Größe = Schwere 1–4</span></div><div class="rl-srcs">${st}</div>
      <details class="rl-list"><summary>Ereignisliste (${L.length})</summary><div class="rk-tablewrap"><table class="det"><tr><td>Ereignis</td><td>Art</td><td>Schwere</td><td>Zeit</td><td>Status</td></tr>
        ${top.slice(0, 60).map((e, i) => `<tr><td><a href="#" data-rl="${i}">${esc(e.title)}</a></td><td>${esc(TYPES[e.type].label)}</td><td>${e.severity}/4</td><td>${esc(when(e.time))}</td><td>${esc(CONF[e.confidence])}</td></tr>`).join("")}</table></div></details>`;
    bar.querySelectorAll("[data-rl]").forEach(a => a.addEventListener("click", ev => { ev.preventDefault(); info(top[+a.dataset.rl]); }));
  }
  async function load(p) {
    const d = state.data[p.id] = Object.assign(state.data[p.id] || {}, { loading: true }); renderBar();
    try {
      const ctl = new AbortController(), to = setTimeout(() => ctl.abort(), 20000);
      const r = await fetch(p.url, { signal: ctl.signal, cache: "no-store", referrerPolicy: "no-referrer" }); clearTimeout(to);
      if (!r.ok) throw new Error("HTTP " + r.status);
      const now = new Date().toISOString();
      d.events = p.toEvents(await r.json(), now); d.fetchedAt = now; d.error = null;
    } catch (e) { d.error = e.name === "AbortError" ? "Zeitüberschreitung" : String(e.message || e); }
    d.loading = false; renderBar(); global.TB_map.redraw();
  }
  function tick() { if (!state.on || document.hidden) return; const now = Date.now();
    PROVIDERS.forEach(p => { const d = state.data[p.id]; if (!d || (!d.loading && now - new Date(d.fetchedAt || 0) > p.refreshSec * 1000)) load(p); }); }
  function set(on) {
    state.on = on; btn.setAttribute("aria-pressed", on); bar.hidden = !on;
    try { localStorage.setItem("riskLayer", on ? "1" : "0"); } catch {}
    clearInterval(state.timer); state.timer = null;
    if (on) { tick(); state.timer = setInterval(tick, 60000); } else global.TB_map.hideTip();
    global.TB_map.redraw();
  }
  btn.addEventListener("click", () => set(!state.on));
  document.addEventListener("visibilitychange", () => { if (!document.hidden) tick(); });
  global.TB_risklayer = { ...core, set, isOn: () => state.on, events,
    summary: () => ({ on: state.on, n: events().length, top: events().sort((a, b) => b.severity - a.severity)[0] || null,
      status: PROVIDERS.map(p => ({ id: p.id, source: p.source, ok: !!(state.data[p.id] || {}).fetchedAt && !(state.data[p.id] || {}).error, fetchedAt: (state.data[p.id] || {}).fetchedAt || null })) }) };
  if ((() => { try { return localStorage.getItem("riskLayer") === "1"; } catch { return false; } })()) set(true);
})(typeof window !== "undefined" ? window : globalThis);
