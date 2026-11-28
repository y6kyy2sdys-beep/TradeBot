/* PROJECT A.L.F.R.E.D. – Advanced Logistics, Financial Research & Event Detection (Phase 2).
   Arbeitet ausschließlich mit Daten, die das Dashboard bereits geladen hat (DASH, WORLD, DOOM, AIRCRAFT, NEWS).
   Erfindet keine Zahlen; nennt zu jedem Wert Quelle und Stand. Nicht vorhandene Funktionen erscheinen als „nicht konfiguriert“. */
(function alfred() {
  "use strict";
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const nf = (v, d = 1) => v == null || !isFinite(v) ? "–" : v.toLocaleString("de-DE", { minimumFractionDigits: d, maximumFractionDigits: d });
  const D = window.DASH || {}, WD = window.WORLD || {}, DOOM = window.DOOM || {}, AC = window.AIRCRAFT || {}, NEWS = window.NEWS || {};
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const ls = { get(k) { try { return localStorage.getItem(k); } catch { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch {} } };
  const when = iso => { const d = new Date(iso); return iso && !isNaN(d) ? d.toLocaleString("de-DE", { dateStyle: "short", timeStyle: "short" }) : "unbekannt"; };
  const ageH = iso => { const d = new Date(iso); return iso && !isNaN(d) ? (Date.now() - d) / 36e5 : null; };
  const ageTxt = iso => { const h = ageH(iso); if (h == null) return "Alter unbekannt"; const m = Math.round(h * 60);
    return m < 60 ? `vor ${m} Min.` : m < 2880 ? `vor ${Math.round(h)} Std.` : `vor ${Math.round(h / 24)} Tagen`; };
  const pill = (cls, txt) => `<span class="spill ${cls}">${txt}</span>`;
  // Datenstand: BOT-STAND solange innerhalb des erwarteten Takts, sonst VERALTET
  const fresh = (iso, maxH) => { const h = ageH(iso); return h == null ? pill("nc", "NICHT VERFÜGBAR") : h <= maxH ? pill("bot", "BOT-STAND") : pill("stale", "VERALTET"); };

  /* ---------------- Berichte (reine Funktionen über vorhandene Daten) ---------------- */
  function greeting() {
    const h = parseInt(new Intl.DateTimeFormat("en-GB", { hour: "2-digit", hourCycle: "h23", timeZone: "Europe/Berlin" }).format(new Date()), 10);
    const g = h < 5 ? "Gute Nacht" : h < 11 ? "Guten Morgen" : h < 18 ? "Guten Tag" : "Guten Abend";
    const esc3 = Object.values(WD.escalation || {}).filter(e => e.stufe >= 3).length;
    const hs = (DOOM.hotspots || []).filter(x => x.level >= 4).length;
    const regime = (D.regime || "").replace(/^[^\wÄÖÜäöü]+/, "").trim();
    return `${g}, Master Wayne. Datenstand ${when(D.generated)} (${ageTxt(D.generated)}).` +
      (regime ? ` Marktlage laut Bot: ${regime}.` : "") +
      ` ${esc3} Länder mit Eskalationsstufe ≥ 3, ${hs} Krisenregionen mit hoher Meldungsdichte.`;
  }
  function change(t) {
    const v = ((D.series || {})[t] || {}).v || [];
    let i = v.length - 1; while (i >= 0 && v[i] == null) i--;
    let j = i - 1; while (j >= 0 && v[j] == null) j--;
    return i > 0 && j >= 0 && v[j] ? { last: v[i], pct: (v[i] / v[j] - 1) * 100 } : null;
  }
  function market() {
    const S = D.series || {}, G = D.groups || {};
    const row = t => { const c = change(t); if (!c) return ""; const cls = c.pct > 0 ? "up" : c.pct < 0 ? "down" : "";
      return `<div class="al-row"><div class="l">${esc((S[t] || {}).name || t)}<small>${esc(t)}</small></div><b class="${cls}">${c.pct > 0 ? "+" : ""}${nf(c.pct, 2)} %</b></div>`; };
    const idx = (G["Indizes"] || []).map(row).join("");
    const movers = Object.keys(S).map(t => [t, change(t)]).filter(([, c]) => c).sort((a, b) => Math.abs(b[1].pct) - Math.abs(a[1].pct)).slice(0, 5).map(([t]) => row(t)).join("");
    return `<div class="al-sec"><h5>Marktlage</h5><div>${esc(D.regime || "nicht verfügbar")}</div></div>
      <div class="al-sec"><h5>Leitindizes · letzter Handelstag</h5>${idx || '<div class="muted">nicht verfügbar</div>'}</div>
      <div class="al-sec"><h5>Größte Bewegungen</h5>${movers || '<div class="muted">nicht verfügbar</div>'}</div>
      <div class="al-src">Fakten: Schlusskurse laut Bot (Yahoo Finance über yfinance), Veränderung zum vorherigen Handelstag. Stand ${esc(when(D.generated))}.
        Keine Prognose, keine Anlageberatung.</div>`;
  }
  function world() {
    const name = iso => window.TB_map ? window.TB_map.name(iso) : iso;
    const esc3 = Object.entries(WD.escalation || {}).filter(([, e]) => e.stufe >= 3).sort((a, b) => b[1].stufe - a[1].stufe).slice(0, 8);
    const hs = (DOOM.hotspots || []).filter(h => h.level >= 3).sort((a, b) => b.level - a.level).slice(0, 8);
    return `<div class="al-sec"><h5>Länder · Eskalationsstufe ≥ 3</h5>${esc3.map(([iso, e]) =>
        `<div class="al-row"><div class="l"><a href="#" data-al-iso="${esc(iso)}">${esc(name(iso))}</a><small>${esc(String(e.grund || "").slice(0, 110))}${String(e.grund || "").length > 110 ? " …" : ""}</small></div><b>${e.stufe}/4</b></div>`).join("") || '<div class="muted">keine</div>'}
        <div class="al-src">Zusammenhang, keine Lagebewertung: Zählung von Konflikt-Schlagzeilen (${esc((Object.values(WD.escalation || {})[0] || {}).quelle || "Nachrichten-Zählung")}). Stand ${esc(when(WD.generated))}.</div></div>
      <div class="al-sec"><h5>Krisenregionen · Meldungsdichte ≥ 3</h5>${hs.map(h =>
        `<div class="al-row"><div class="l">${esc(h.name)}<small>${(h.news || []).length} Meldungen (48 h)</small></div><b>${h.level}/5</b></div>`).join("") || '<div class="muted">keine</div>'}
        <div class="al-src">Meldungslage der letzten 48 Stunden, keine Positionsdaten von Truppen oder Schiffen. Stand ${esc(when(DOOM.generated))}.</div></div>`;
  }
  function system() {
    const files = [["Kurse & Signale", "data.js", D.generated, 12], ["Weltlage", "world.js", WD.generated, 12], ["Krisenregionen / WarMap", "doomsday.js", DOOM.generated, 12],
      ["Militärflugzeuge", "aircraft.js", AC.generated, 2], ["Nachrichten", "news.js", NEWS.generated, 12]];
    const cams = window.TB_camwall ? window.TB_camwall.summary() : { approved: 0 };
    let depotN = 0; try { depotN = (JSON.parse(ls.get("depot") || "[]") || []).length; } catch {}
    const voiceOk = "speechSynthesis" in window, voiceOn = ls.get("alfredVoice") === "1";
    const feat = [
      ["Sprachausgabe", voiceOk ? (voiceOn ? pill("live", "AN") : pill("nc", "AUS")) : pill("nc", "NICHT VERFÜGBAR"), "Web Speech API im Browser, kostenlos"],
      ["Spracheingabe", pill("nc", "NICHT KONFIGURIERT"), "Mikrofon-Freigabe nötig, Browser-abhängig"],
      ["KI-Dialog", pill("nc", "NICHT KONFIGURIERT"), "bräuchte API-Schlüssel + Server"],
      ["Lagebild-Quellen", cams.approved ? pill("bot", cams.approved + " FREIGEGEBEN") : pill("nc", "NICHT KONFIGURIERT"), cams.approved ? "Quellenkatalog cameras.js" : "Quellenkatalog noch nicht freigegeben"],
      ["Aktualisieren-Knopf", ls.get("ghToken") ? pill("bot", "KONFIGURIERT") : pill("nc", "NICHT KONFIGURIERT"), "GitHub-Token nur in diesem Browser"],
      ["Mein Depot", depotN ? pill("bot", depotN + " POSITIONEN") : pill("nc", "LEER"), "nur in diesem Browser gespeichert"]];
    return `<div class="al-sec"><h5>Datenquellen</h5>${files.map(([n, f, g, mx]) =>
        `<div class="al-row"><div class="l">${esc(n)}<small>${esc(f)} · ${esc(when(g))} · ${esc(ageTxt(g))}</small></div>${fresh(g, mx)}</div>`).join("")}
        <div class="al-src">BOT-STAND = vom Bot innerhalb des erwarteten Takts erzeugt (Flugzeuge 2 Std., sonst 12 Std.); VERALTET = älter.
          Live-Abrufe im Browser (Flugzeuge, Kurse) werden im jeweiligen Block angezeigt.</div></div>
      <div class="al-sec"><h5>Funktionen</h5>${feat.map(([n, p, h]) => `<div class="al-row"><div class="l">${esc(n)}<small>${esc(h)}</small></div>${p}</div>`).join("")}</div>`;
  }
  function alerts() {
    const A = (D.alerts || []).slice(-15).reverse();
    return `<div class="al-sec"><h5>Benachrichtigungen</h5><ul class="al-list">${A.map(a =>
      `<li>${esc(a.title)}<small>${esc(when(a.time))} · ${esc(a.kind || "")}</small></li>`).join("") || '<li class="muted">keine Meldungen</li>'}</ul>
      <div class="al-src">Alarm-Protokoll des Bots (Telegram-Meldungen ohne Depot-Inhalte). Stand ${esc(when(D.generated))}.</div></div>`;
  }

  // Depot-Risiko: Kurzfassung aus dem Portfolio Risk Center (risk.js), wird nach dem Rendern asynchron gefüllt
  function depot() {
    if (!window.TB_risk) return '<div class="al-sec"><div class="muted">Risk Center nicht geladen.</div></div>';
    if (!window.TB_risk.depotCount()) return `<div class="al-sec"><h5>Depot</h5><div>Master Wayne, in diesem Browser ist kein Depot erfasst.</div>
      <div class="al-src">Positionen im Block „Mein Depot“ erfassen – sie bleiben nur in diesem Browser.</div></div>`;
    return '<div class="al-sec" data-al-depot><h5>Depot-Risiko</h5><div class="muted">Berechne aus Kursprofilen …</div></div>';
  }
  function depotFill(el, R) {
    const T = window.TB_risk, p = R.port || {};
    if (!R.ok) { el.innerHTML = `<h5>Depot-Risiko</h5><div class="muted">${esc(R.error || "Keine auswertbaren Positionen.")}</div>`; return; }
    el.innerHTML = `<h5>Depot-Risiko · letzte 12 Monate</h5><div class="al-kv">
        <span>Depotwert heute</span><b>${R.total.toLocaleString("de-DE", { style: "currency", currency: "EUR", maximumFractionDigits: 0 })}</b>
        <span>Volatilität p. a.</span><b>${T.pct(p.vol)}</b><span>Max. Drawdown</span><b>${T.pct(p.mdd)}</b>
        <span>Größte Position</span><b>${esc(R.conc.max.n)} · ${T.pct(R.conc.max.w)}</b>
        <span>Effektive Anzahl Positionen</span><b>${T.num(R.conc.effN, 1)}</b>
        ${(p.bench || []).filter(b => b.ok).map(b => `<span>Beta zu ${esc(b.name)}</span><b>${T.num(b.beta)}</b>`).join("")}</div>
      <h5 style="margin-top:10px">Hinweise</h5>${R.hints.length ? `<ul class="al-list">${R.hints.slice(0, 6).map(h => `<li>${esc(h)}</li>`).join("")}</ul>` : '<div class="muted">Keine Schwelle überschritten.</div>'}
      <div class="al-src">Rückrechnung mit heutigen Stückzahlen, Kurse in Handelswährung, Sharpe ohne risikofreien Zins. Nur in diesem Browser berechnet. Keine Anlageberatung.
        <a href="#depot" data-al-risk>Zum Risk Center →</a></div>`;
  }

  /* ---------------- Oberfläche ---------------- */
  const TABS = [["lage", "LAGE", world], ["markt", "MARKT", market], ["depot", "DEPOT", depot], ["system", "SYSTEM", system], ["meld", "MELDUNGEN", alerts]];
  const box = document.createElement("aside");
  box.id = "alfred"; box.setAttribute("role", "dialog"); box.setAttribute("aria-label", "ALFRED – Assistent");
  document.body.appendChild(box);
  let tab = ls.get("alfredTab") || "lage";
  function render() {
    const voiceOn = ls.get("alfredVoice") === "1";
    box.innerHTML = `<div class="al-head"><span class="radar" aria-hidden="true"></span>
        <div class="t"><b>A.L.F.R.E.D.</b><small>Wayne Intelligence · Lageassistent</small></div>
        ${"speechSynthesis" in window ? `<button type="button" data-al-voice aria-pressed="${voiceOn}" title="Sprachausgabe ${voiceOn ? "ausschalten" : "einschalten"}">${voiceOn ? "🔊" : "🔈"}</button>` : ""}
        <button type="button" data-al-close aria-label="ALFRED schließen">✕</button></div>
      <div class="al-greet">${esc(greeting())}</div>
      <div class="tabs" role="tablist">${TABS.map(([k, l]) => `<button type="button" role="tab" data-al-tab="${k}" aria-selected="${k === tab}">${l}</button>`).join("")}</div>
      <div class="al-body">${(TABS.find(([k]) => k === tab) || TABS[0])[2]()}</div>
      <div class="al-foot"><span>Nur vorhandene Daten · Quelle und Stand je Wert</span><span>⌘K Befehle</span></div>`;
    const d = box.querySelector("[data-al-depot]");
    if (d) window.TB_risk.run().then(R => { if (d.isConnected) depotFill(d, R); });
  }
  const btn = document.getElementById("alfredBtn");
  function speak(text) {
    if (!("speechSynthesis" in window) || ls.get("alfredVoice") !== "1") return;
    speechSynthesis.cancel(); const u = new SpeechSynthesisUtterance(text); u.lang = "de-DE"; u.rate = 1; speechSynthesis.speak(u);
  }
  function open(t) { if (t) { tab = t; ls.set("alfredTab", t); } render(); box.classList.add("open"); if (btn) btn.setAttribute("aria-expanded", "true"); speak(greeting()); }
  function close() { box.classList.remove("open"); if (btn) btn.setAttribute("aria-expanded", "false"); if ("speechSynthesis" in window) speechSynthesis.cancel(); }
  const toggle = () => box.classList.contains("open") ? close() : open();
  if (btn) btn.addEventListener("click", toggle);
  box.addEventListener("click", e => {
    const t = e.target.closest("[data-al-tab]"); if (t) { tab = t.dataset.alTab; ls.set("alfredTab", tab); render(); return; }
    if (e.target.closest("[data-al-close]")) { close(); return; }
    if (e.target.closest("[data-al-voice]")) { ls.set("alfredVoice", ls.get("alfredVoice") === "1" ? "0" : "1"); if ("speechSynthesis" in window) speechSynthesis.cancel(); render(); return; }
    const c = e.target.closest("[data-al-iso]"); if (c) { e.preventDefault(); if (window.TB_map) window.TB_map.open(c.dataset.alIso); }
    if (e.target.closest("[data-al-risk]")) { e.preventDefault(); const r = document.getElementById("riskBox");
      if (r) { r.open = true; r.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" }); } }
  });

  /* ---------------- Befehlsliste ⌘K / Strg+K ---------------- */
  const pal = document.createElement("div");
  pal.id = "palette"; pal.setAttribute("role", "dialog"); pal.setAttribute("aria-label", "Befehlsliste");
  pal.innerHTML = `<div class="pal-box"><input type="text" autocomplete="off" spellcheck="false" placeholder="Befehl, Bereich oder Land …" aria-label="Befehl suchen" aria-controls="palList">
    <ul id="palList" role="listbox"></ul><div class="pal-hint">↑↓ auswählen · Enter ausführen · Esc schließen · Länder ab 2 Zeichen</div></div>`;
  document.body.appendChild(pal);
  const inp = pal.querySelector("input"), list = pal.querySelector("ul");
  const click = id => () => { const el = document.getElementById(id); if (el) el.click(); };
  function commands(q) {
    const C = [
      ["ALFRED öffnen / schließen", "Assistent", toggle],
      ...TABS.map(([k, l]) => [`ALFRED: ${l[0] + l.slice(1).toLowerCase()}`, "Assistent", () => open(k)]),
      ["Doomsday-Modus an/aus", "Globus", click("doomBtn")],
      ["Aktie suchen", "Suche", () => { const q2 = document.getElementById("q"); if (q2) { q2.scrollIntoView({ block: "center" }); q2.focus(); } }],
      ["Portfolio Risk Center öffnen", "Depot", () => { const r = document.getElementById("riskBox"); if (r) { r.open = true; r.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" }); } }],
      ["Daten aktualisieren (Bot starten)", "System", click("refreshBtn")],
      ["Matrix-Regen an/aus", "Ansicht", click("rainBtn")],
      ["App-/Desktop-Ansicht umschalten", "Ansicht", click("appBtn")],
      ["Schrift größer", "Ansicht", click("fsUp")], ["Schrift kleiner", "Ansicht", click("fsDown")],
      ...[...document.querySelectorAll("section.panel h2")].map(h => {
        const t = (h.firstChild && h.firstChild.textContent || h.textContent).replace(/^\/\/\s*/, "").trim();
        return [`Springe zu: ${t}`, "Bereich", () => h.closest("section").scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" })];
      }),
    ];
    if (q.length >= 2 && window.TB_map) window.TB_map.list().forEach(([iso, n]) => {
      C.push([`Land: ${n}`, iso, () => window.TB_map.open(iso)]);
      C.push([`Lagebild: ${n}`, iso, () => window.TB_map.open(iso, "cam")]);
    });
    const norm = s => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
    const words = norm(q).split(/\s+/).filter(Boolean);
    return C.filter(([l, k]) => words.every(w => norm(l + " " + k).includes(w))).slice(0, 40);
  }
  let cur = [], sel = 0;
  function draw() {
    cur = commands(inp.value.trim()); sel = Math.min(sel, Math.max(0, cur.length - 1));
    list.innerHTML = cur.map(([l, k], i) => `<li role="option" data-i="${i}" aria-selected="${i === sel}"><span>${esc(l)}</span><small>${esc(k)}</small></li>`).join("")
      || '<li class="muted" aria-disabled="true">Kein Treffer</li>';
    const a = list.querySelector('[aria-selected="true"]'); if (a) a.scrollIntoView({ block: "nearest" });
  }
  let lastFocus = null;
  function palOpen() { lastFocus = document.activeElement; pal.classList.add("open"); inp.value = ""; sel = 0; draw(); inp.focus(); }
  function palClose() { pal.classList.remove("open"); if (lastFocus && lastFocus.focus) lastFocus.focus(); }
  function run(i) { const c = cur[i]; if (!c) return; palClose(); c[2](); }
  inp.addEventListener("input", () => { sel = 0; draw(); });
  inp.addEventListener("keydown", e => {
    if (e.key === "ArrowDown") { e.preventDefault(); sel = Math.min(sel + 1, cur.length - 1); draw(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); sel = Math.max(sel - 1, 0); draw(); }
    else if (e.key === "Enter") { e.preventDefault(); run(sel); }
    else if (e.key === "Escape") { e.preventDefault(); palClose(); }
  });
  list.addEventListener("click", e => { const li = e.target.closest("li[data-i]"); if (li) run(+li.dataset.i); });
  pal.addEventListener("mousedown", e => { if (e.target === pal) palClose(); });
  addEventListener("keydown", e => {
    if ((e.metaKey || e.ctrlKey) && !e.altKey && e.key.toLowerCase() === "k") { e.preventDefault(); pal.classList.contains("open") ? palClose() : palOpen(); return; }
    if (e.key === "Escape" && !pal.classList.contains("open") && box.classList.contains("open") && !document.body.classList.contains("modal-open")) close();
  });

  window.TB_alfred = { open, close, report: { greeting, market, world, system, alerts } };
})();
