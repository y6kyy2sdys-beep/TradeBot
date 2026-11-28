/* PROJECT A.L.F.R.E.D. – PROJECT CHRONOS (Variante A „Noir“), ersetzt die frühere Doomsday-Animation.
   Zeitachse 2026–2050 auf dem Globus, ausschließlich mit belegten Daten:
   WIRTSCHAFT = IMF World Economic Outlook (Ist + IMF-Prognose bis zum letzten Datenjahr, derzeit 2030), danach KEINE Werte.
   GEOPOLITIK = nur heutiger Stand (Schlagzeilen-Zählung, Krisenregionen 48 h) – wird nicht fortgeschrieben.
   KLIMA = nicht konfiguriert (keine geprüfte Datenquelle im Projekt).
   Keine eigenen Prognosen, keine Eintrittswahrscheinlichkeiten. Unterstützt „reduzierte Bewegung“. */
(function (global) {
  "use strict";
  const Y0 = 2026, Y1 = 2050;
  const IND = { NGDP_RPCH: { label: "Reales BIP-Wachstum", unit: "%" }, PCPIPCH: { label: "Inflation", unit: "%" } };

  /* ---------------- Datenkern (rein, testbar) ---------------- */
  function lastDataYear(W, code) {
    const ind = (W && W.indicators && W.indicators[code]) || {}; let last = null;
    Object.values(ind).forEach(arr => arr.forEach((v, i) => { if (v != null && (last == null || W.years[i] > last)) last = W.years[i]; }));
    return last;
  }
  // only: optional Menge zulässiger ISO-Codes (Länder der Karte) – IMF-Ländergruppen (z. B. Euroraum, Welt) zählen nicht als Land
  function valuesFor(W, code, year, only) {
    const ind = (W && W.indicators && W.indicators[code]) || {}, i = W && W.years ? W.years.indexOf(year) : -1;
    if (i < 0) return [];
    return Object.entries(ind).filter(([iso, a]) => (!only || only.has(iso)) && a[i] != null && isFinite(a[i])).map(([iso, a]) => [iso, a[i]]);
  }
  function stats(vals) {
    if (!vals.length) return { n: 0, median: null, neg: 0, top: [], bottom: [] };
    const s = [...vals].sort((a, b) => b[1] - a[1]), v = s.map(x => x[1]).sort((a, b) => a - b), m = v.length >> 1;
    return { n: vals.length, median: v.length % 2 ? v[m] : (v[m - 1] + v[m]) / 2, neg: vals.filter(x => x[1] < 0).length, top: s.slice(0, 3), bottom: s.slice(-3).reverse() };
  }
  function seriesFor(W, code, iso) {
    const a = ((W && W.indicators && W.indicators[code]) || {})[iso] || [];
    const out = []; for (let y = Y0; y <= Y1; y++) { const i = W.years.indexOf(y); out.push([y, i >= 0 && a[i] != null ? a[i] : null]); }
    return out;
  }
  const core = { Y0, Y1, IND, lastDataYear, valuesFor, stats, seriesFor };
  if (typeof module !== "undefined" && module.exports) { module.exports = core; return; }

  /* ---------------- Oberfläche ---------------- */
  const W = global.WORLD, DOOM = global.DOOM || {};
  if (!W) return;
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const nf = (v, d = 1) => v == null || !isFinite(v) ? "–" : v.toLocaleString("de-DE", { minimumFractionDigits: d, maximumFractionDigits: d });
  const nameOf = iso => (global.TB_map && global.TB_map.name(iso)) || iso;
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  // Farben wie auf der Weltkarte (validierte Skalen): Wachstum divergierend, Inflation sequenziell, Eskalation ordinal
  const growthColor = v => v == null ? null : v <= -3 ? "#e66767" : v <= -1 ? "#a34a4a" : v < 1 ? "#4a4a46" : v < 3 ? "#1c5cab" : "#3987e5";
  const inflColor = v => v == null ? null : v < 2 ? "#184f95" : v < 4 ? "#2a78d6" : v < 8 ? "#5598e7" : "#86b6ef";
  const ESC = ["#1d2b22", "#92361f", "#c74726", "#f6623d", "#ff9b7f"];
  const LEG = {
    NGDP_RPCH: [["#e66767", "≤ −3"], ["#a34a4a", "−3 bis −1"], ["#4a4a46", "−1 bis 1"], ["#1c5cab", "1 bis 3"], ["#3987e5", "≥ 3 %"]],
    PCPIPCH: [["#184f95", "< 2"], ["#2a78d6", "2 bis 4"], ["#5598e7", "4 bis 8"], ["#86b6ef", "≥ 8 %"]],
  };
  const MODES = { geo: "GEOPOLITIK", wirt: "WIRTSCHAFT", klima: "KLIMA" };
  let el = null, g = null, st = null, timer = null, onClose = null;

  function close() {
    if (!el) return;
    clearTimeout(timer); timer = null; if (g) g.destroy(); g = null;
    if (document.fullscreenElement && el.contains(document.fullscreenElement)) document.exitFullscreen().catch(() => {});
    el.remove(); el = null; document.body.classList.remove("chronos-open"); removeEventListener("keydown", key);
    const cb = onClose; onClose = null; if (cb) cb();
  }
  function key(e) {
    if (!el) return;
    if (e.key === "Escape") { e.preventDefault(); close(); }
    else if (e.key === " " && e.target === document.body) { e.preventDefault(); togglePlay(); }
    else if (e.key === "ArrowRight" && !["INPUT"].includes(e.target.tagName)) { setYear(st.year + 1); }
    else if (e.key === "ArrowLeft" && !["INPUT"].includes(e.target.tagName)) { setYear(st.year - 1); }
  }
  const pos = y => ((y - Y0) / (Y1 - Y0) * 100) + "%";

  function open(opts = {}) {
    close(); onClose = opts.onClose || null;
    const last = lastDataYear(W, "NGDP_RPCH") || 2030;
    st = { mode: "wirt", code: "NGDP_RPCH", year: Math.max(Y0, Math.min(new Date().getFullYear(), Y1)), speed: 1, playing: false, sel: "DEU", last };
    el = document.createElement("div"); el.id = "chronos"; el.setAttribute("role", "dialog"); el.setAttribute("aria-label", "PROJECT CHRONOS");
    el.innerHTML = `<canvas class="ch-globe" aria-label="Globus – ziehen zum Drehen, Land anklicken für Details"></canvas>
      <div class="ch-top"><div class="ch-title">PROJECT CHRONOS<small>WAYNE INTELLIGENCE · ZEITACHSE ${Y0}–${Y1} · NUR BELEGTE DATEN</small></div>
        <div class="ch-tabs" role="tablist">${Object.entries(MODES).map(([k, l]) => `<button type="button" role="tab" data-ch-mode="${k}">${l}</button>`).join("")}</div>
        <div class="ch-ind" data-ch-indbox>${Object.entries(IND).map(([k, v]) => `<button type="button" data-ch-ind="${k}">${v.label.toUpperCase()}</button>`).join("")}</div>
        <div class="ch-sp"></div><button type="button" class="ch-btn" data-ch-map title="Kartenlage mit Flugzeugen und Frontlinien">◱ KARTENLAGE</button>
        <button type="button" class="ch-btn" data-ch-fs>⛶ VOLLBILD</button><button type="button" class="ch-btn" data-ch-close aria-label="CHRONOS schließen">✕</button></div>
      <aside class="ch-side"><div class="ch-panel ch-alf" aria-live="polite"></div><div class="ch-panel ch-leg"></div></aside>
      <div class="ch-time"><div class="ch-ctl"><button type="button" data-ch-restart title="Neustart (${Y0})" aria-label="Neustart">⏮</button>
          <button type="button" data-ch-play aria-label="Abspielen">▶</button><span class="ch-yr" data-ch-yr></span>
          <span class="ch-spd">${[1, 2, 4].map(s => `<button type="button" data-ch-speed="${s}">${s}×</button>`).join("")}</span>
          <span class="ch-note" data-ch-note></span></div>
        <div class="ch-axis" data-ch-axis><div class="ch-bl" style="left:0">IMF-DATEN (World Economic Outlook) ${Y0}–${last}</div>
          <div class="ch-bl" style="left:${pos(Math.min(Y1, last + 1))}">AB ${last + 1}: KEINE GESTÜTZTEN LÄNDERDATEN – NICHTS WIRD FORTGESCHRIEBEN</div>
          <div class="ch-bands"><div class="imf" style="width:${pos(last + .5)}"></div><div class="none"></div></div><div class="ch-track"></div>
          ${Array.from({ length: Y1 - Y0 + 1 }, (_, k) => Y0 + k).map(y => `<div class="ch-tick${y % 5 ? " s" : ""}" style="left:${pos(y)}"></div>${y % 4 === 2 || y === Y1 ? `<div class="ch-lab" style="left:${pos(y)}">${y}</div>` : ""}`).join("")}
          <input type="range" min="${Y0}" max="${Y1}" step="1" aria-label="Jahr" data-ch-range><div class="ch-knob" data-ch-knob></div></div></div>`;
    document.body.appendChild(el); document.body.classList.add("chronos-open"); addEventListener("keydown", key);
    if (global.TB_globe) {
      const wide = innerWidth > 900;   // Handy: Globus oben zwischen Kopfzeile und ALFRED-Fenster
      g = global.TB_globe.create(el.querySelector(".ch-globe"), { r: wide ? .36 : .30, cx: wide ? .40 : .5, cy: wide ? .46 : .36, stars: 420, rotate: [-10, -40, 0], spin: true });
      g.onPick = iso => { st.sel = iso; g.sel = iso; const ll = g.centroid(iso); g.setSpin(false); if (ll) g.flyTo(ll, 1300); render(); };
      g.sel = st.sel; const ll = g.centroid(st.sel); if (ll) g.flyTo(ll, reduced ? 0 : 2200);
    }
    el.addEventListener("click", onClick);
    el.querySelector("[data-ch-range]").addEventListener("input", e => { const y = +e.target.value; stop(); setYear(y); });   // Wert vor stop() lesen (render setzt den Regler)
    render(); el.querySelector("[data-ch-close]").focus();
  }
  function onClick(e) {
    const b = e.target.closest("button"); if (!b) return;
    if (b.dataset.chClose !== undefined) return close();
    if (b.dataset.chMap !== undefined) return close();
    if (b.dataset.chFs !== undefined) { if (document.fullscreenElement) document.exitFullscreen(); else if (el.requestFullscreen) el.requestFullscreen(); return; }
    if (b.dataset.chMode) { st.mode = b.dataset.chMode; render(); return; }
    if (b.dataset.chInd) { st.code = b.dataset.chInd; render(); return; }
    if (b.dataset.chPlay !== undefined) return togglePlay();
    if (b.dataset.chRestart !== undefined) { stop(); setYear(Y0); return; }
    if (b.dataset.chSpeed) { st.speed = +b.dataset.chSpeed; render(); }
  }
  function setYear(y) { st.year = Math.max(Y0, Math.min(Y1, y)); render(); }
  function stop() { st.playing = false; clearTimeout(timer); timer = null; if (el) render(); }
  function togglePlay() {
    if (st.playing) return stop();
    if (st.year >= Y1) st.year = Y0;
    st.playing = true; render();
    const step = () => { if (!st || !st.playing) return; if (st.year >= Y1) return stop(); setYear(st.year + 1); timer = setTimeout(step, 1400 / st.speed); };
    timer = setTimeout(step, 1400 / st.speed);
  }

  function render() {
    if (!el) return;
    const { mode, code, year, last, sel } = st, have = mode === "wirt" && year <= last, now = new Date().getFullYear();
    el.querySelectorAll("[data-ch-mode]").forEach(b => b.setAttribute("aria-selected", b.dataset.chMode === mode));
    el.querySelectorAll("[data-ch-ind]").forEach(b => b.setAttribute("aria-pressed", b.dataset.chInd === code));
    el.querySelector("[data-ch-indbox]").hidden = mode !== "wirt";
    el.querySelectorAll("[data-ch-speed]").forEach(b => b.setAttribute("aria-pressed", +b.dataset.chSpeed === st.speed));
    const pb = el.querySelector("[data-ch-play]"); pb.textContent = st.playing ? "❚❚" : "▶"; pb.setAttribute("aria-label", st.playing ? "Pause" : "Abspielen");
    el.querySelector("[data-ch-yr]").textContent = year; el.querySelector("[data-ch-knob]").style.left = pos(year); el.querySelector("[data-ch-range]").value = year;
    el.querySelector("[data-ch-note]").textContent = mode === "wirt" ? (have ? (year >= now ? "IMF-PROGNOSE" : "IMF-IST-WERT") : "KEIN DATENSATZ FÜR DIESES JAHR")
      : mode === "geo" ? "NUR HEUTIGER STAND – ZEITACHSE OHNE WIRKUNG" : "DATENQUELLE NICHT ANGEBUNDEN";
    const vals = have ? valuesFor(W, code, year, global.TB_globe ? new Set(global.TB_globe.byIso.keys()) : null) : [], vmap = new Map(vals), col = code === "PCPIPCH" ? inflColor : growthColor;
    if (g) {
      g.fill = f => mode === "wirt" ? (have ? col(vmap.get(f.iso)) : null)
        : mode === "geo" ? ((W.escalation[f.iso] || {}).stufe ? ESC[W.escalation[f.iso].stufe] : null) : null;
      g.markers = mode === "geo" ? (DOOM.hotspots || []).filter(h => h.level >= 1).map(h => ({ lon: h.lon, lat: h.lat, r: 2 + h.level * 1.2, color: h.level >= 4 ? "#ff3b3b" : "#fab219", label: h.level >= 4 ? h.name.split(" · ")[0] : "" })) : [];
      g.redraw();
    }
    const S = stats(vals), I = IND[code], head = `<div class="ch-alfh"><span class="radar" aria-hidden="true"></span><div><b>A.L.F.R.E.D.</b><small>ANALYSE · ${MODES[mode]} · ${year}</small></div></div>`;
    let body;
    if (mode === "wirt" && have) {
      const ser = seriesFor(W, code, sel).filter(([y, v]) => v != null && y <= last);
      body = `<div class="ch-kv"><span>Länder mit Daten</span><b>${S.n}</b><span>Median ${esc(I.label)}</span><b>${nf(S.median)} %</b>
          <span>${esc(nameOf(sel))}</span><b>${nf(vmap.get(sel))} %</b>${code === "NGDP_RPCH" ? `<span>Länder mit Rückgang</span><b>${S.neg}</b>` : ""}</div>
        <div class="ch-line">Höchste Werte: ${S.top.map(([i, v]) => esc(nameOf(i)) + " " + nf(v) + " %").join(" · ")}</div>
        <div class="ch-line">Niedrigste Werte: ${S.bottom.map(([i, v]) => esc(nameOf(i)) + " " + nf(v) + " %").join(" · ")}</div>
        ${ser.length ? `<table class="ch-ser"><tr>${ser.map(([y]) => `<td class="${y === year ? "on" : ""}">${y}</td>`).join("")}</tr><tr>${ser.map(([y, v]) => `<td class="${y === year ? "on" : ""}">${nf(v)}</td>`).join("")}</tr></table>
          <div class="ch-src">${esc(nameOf(sel))} · ${esc(I.label)} in % · Land auf dem Globus anklicken</div>` : ""}
        <div class="ch-src">${year >= now ? "PROGNOSE des IMF (World Economic Outlook) – keine eigene Schätzung." : "Ist-Wert laut IMF."} Keine Eintrittswahrscheinlichkeiten.
          Daten: world.js, Stand ${esc(String(W.generated || "").slice(0, 10))}.</div>`;
    } else if (mode === "wirt") {
      body = `<div>Für <b>${year}</b> liegen keine gestützten Länderdaten vor. Der IMF World Economic Outlook reicht bis ${last}.</div>
        <div class="ch-src">CHRONOS schreibt bewusst nichts fort. Das frühere interne Szenariomodell (Fortschreibung bis 2050, „Dystopie“-Schocks) wird hier nicht verwendet.</div>`;
    } else if (mode === "geo") {
      const e = W.escalation[sel] || {};
      body = `<div>Geopolitik wird <b class="ch-warn">nicht fortgeschrieben</b>. Gezeigt ist der heutige Stand: Eskalationsstufe (Zählung von Konflikt-Schlagzeilen) und Krisenregionen (Meldungsdichte 48 h).</div>
        <div class="ch-kv"><span>Länder Stufe ≥ 3</span><b>${Object.values(W.escalation || {}).filter(x => x.stufe >= 3).length}</b>
          <span>Krisenregionen ≥ 3/5</span><b>${(DOOM.hotspots || []).filter(h => h.level >= 3).length}</b>
          <span>${esc(nameOf(sel))}</span><b>${e.stufe != null ? "Stufe " + e.stufe : "–"}</b></div>
        ${e.grund ? `<div class="ch-line">${esc(String(e.grund).slice(0, 180))}</div>` : ""}
        <div class="ch-src">Quelle: world.js / doomsday.js (Bot), Stand ${esc(String(DOOM.generated || W.generated || "").slice(0, 16).replace("T", " "))}. Keine Prognose, keine Positionsdaten.</div>`;
    } else {
      body = `<div><span class="spill nc">NICHT KONFIGURIERT</span></div><div class="ch-line">Im Projekt gibt es keine Klimadaten. Mögliche Quellen nach Prüfung von Lizenz und Abruf:
        IPCC AR6 (SSP-Pfade, global) oder das Climate Change Knowledge Portal der Weltbank (CMIP6 je Land).</div>
        <div class="ch-src">Solche Szenariopfade wären Projektionen Dritter und würden ausdrücklich als solche gekennzeichnet.</div>`;
    }
    el.querySelector(".ch-alf").innerHTML = head + body;
    el.querySelector(".ch-leg").innerHTML = mode === "wirt" ? `<h5>LEGENDE · ${esc(I.label.toUpperCase())}</h5><div class="ch-legend">${LEG[code].map(([c, l]) => `<span><i style="background:${c}"></i>${l}</span>`).join("")}<span><i class="nd"></i>keine Daten</span></div>`
      : mode === "geo" ? `<h5>LEGENDE · ESKALATION (HEUTE)</h5><div class="ch-legend">${["Spannungen", "ernste Krise", "bewaffneter Konflikt", "Krieg mit globaler Wirkung"].map((l, i) => `<span><i style="background:${ESC[i + 1]}"></i>${i + 1} ${l}</span>`).join("")}<span><i style="background:#fab219;border-radius:50%"></i>Krisenregion</span></div>`
      : `<h5>LEGENDE</h5><div class="ch-legend">keine Daten</div>`;
  }
  global.TB_chronos = { ...core, open, close, isOpen: () => !!el };
})(typeof window !== "undefined" ? window : globalThis);
