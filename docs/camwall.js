/* PROJECT A.L.F.R.E.D. – Country Intelligence: Reiter LAGEBILD im Länderfenster (Globus/WarMap).
   Regeln (PROJECT_ALFRED.md): Es wird NICHTS geladen, solange das Länderfenster geschlossen, der Reiter nicht aktiv
   oder „LAGEBILD LADEN“ nicht bestätigt ist. Beim Schließen, Reiter- oder Länderwechsel werden alle Einbettungen entfernt.
   In Konfliktgebieten nur redaktionelle Nachrichten-Streams und zeitversetzte zivile Übersichten. Kein Status wird geraten. */
(function camwall() {
  "use strict";
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const ART = { nachrichten: "Nachrichten-Livestream", panorama: "Panorama", wetter: "Wetter", zeitversetzt: "Zivile Übersicht · zeitversetzt" };
  const CONFLICT_ART = new Set(["nachrichten", "zeitversetzt"]);
  const STATUS = { live: "LIVE", delayed: "DELAYED", offline: "OFFLINE", unavailable: "UNAVAILABLE" };
  // WarMap-Hotspots → Land für den Verweis „LAGEBILD“ (Meeresgebiete ohne eindeutiges Land fehlen bewusst)
  const HOTSPOT_ISO = { ukr_front: "UKR", blacksea: "UKR", sudan_darfur: "SDN", sudan_khartoum: "SDN", gaza: "PSE", lebanon: "LBN",
    syria: "SYR", hormuz: "IRN", redsea: "YEM", taiwan: "TWN", korea: "KOR", kashmir: "IND", sahel: "MLI", congo: "COD",
    myanmar: "MMR", caribbean: "VEN" };
  const GRID_KEY = "cwGrid", CONSENT_KEY = "cwConsent";
  const ss = { get(k) { try { return sessionStorage.getItem(k); } catch { return null; } }, set(k, v) { try { sessionStorage.setItem(k, v); } catch {} } };

  const items = () => (window.CAMS && Array.isArray(window.CAMS.items) ? window.CAMS.items : []);
  const approved = () => items().filter(c => c && c.freigegeben === true && c.embed && /^https:\/\//.test(c.embed.url || ""));
  function hotspotLevel(iso) {
    const hs = (window.DOOM && window.DOOM.hotspots) || [];
    return hs.filter(h => HOTSPOT_ISO[h.key] === iso).reduce((m, h) => Math.max(m, h.level || 0), 0);
  }
  // Konfliktgebiet = feste, von Hand gepflegte Liste im Katalog ODER WarMap-Hotspot ab Stufe 3
  // (Freigabe 28.11.2026; die Schlagzeilen-Zählung der Eskalationsstufe entscheidet bewusst nicht mehr)
  const DEFAULT_CONFLICT = ["UKR", "RUS", "ISR", "PSE", "LBN", "SYR", "YEM", "SDN", "IRN", "SAU", "ARE"];
  const conflictList = () => new Set((window.CAMS && Array.isArray(window.CAMS.konfliktzonen) ? window.CAMS.konfliktzonen : DEFAULT_CONFLICT));
  const isConflict = iso => conflictList().has(iso) || hotspotLevel(iso) >= 3;
  function sourcesFor(iso) {
    const all = approved().filter(c => c.iso === iso);
    const conflict = isConflict(iso);
    const ok = all.filter(c => !conflict || (CONFLICT_ART.has(c.art) && c.konfliktzone_zulaessig === true))
      .sort((a, b) => (ART_ORDER[a.art] ?? 9) - (ART_ORDER[b.art] ?? 9));
    return { all, ok, conflict, blocked: all.length - ok.length };
  }
  // URL-Vorlagen: {YYYY-MM-DD} = Vortag in UTC (NASA GIBS Tagesbild, heute oft noch leer),
  // {HHMM} = UTC-Zeit 30 Min. zurück, auf 10 Min. abgerundet (JMA Himawari, rollierender Dateisatz)
  const pad = n => String(n).padStart(2, "0");
  function resolve(c) {
    let url = c.embed.url, zeit = null, tag = false;
    if (url.includes("{YYYY-MM-DD}")) {
      const d = new Date(Date.now() - 864e5), s = `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}`;
      url = url.split("{YYYY-MM-DD}").join(s); zeit = s + "T12:00:00Z"; tag = true;
    }
    if (url.includes("{HHMM}")) {
      const d = new Date(Date.now() - 30 * 6e4); d.setUTCMinutes(Math.floor(d.getUTCMinutes() / 10) * 10, 0, 0);
      url = url.split("{HHMM}").join(pad(d.getUTCHours()) + pad(d.getUTCMinutes())); zeit = d.toISOString();
    }
    return { url, zeit, tag };
  }
  // Status nur aus belegten Angaben: Katalogprüfung, berechneter Bildzeitpunkt oder erklärte Verzögerung – sonst „unbekannt“.
  // OFFLINE setzt die Kachel selbst, wenn ein Bild nicht abrufbar ist. YouTube-Livestatus ist ohne Player-API nicht feststellbar.
  // Ergebnis der Bot-Prüfung (docs/streamstatus.js, bot/streamcheck.py) – nur verwendet, wenn höchstens 24 h alt
  const CHECK_MAX_H = 24;
  function checked(c) {
    const S = window.CAMSTATUS, r = S && S.items && S.items[c.id];
    if (!r || !r.checked) return null;
    const age = (Date.now() - new Date(r.checked)) / 36e5;
    return age >= 0 && age <= CHECK_MAX_H ? r : null;
  }
  const liveVideo = c => { const k = checked(c); return c.embed.typ === "youtube" && k && k.status === "live" && /^[\w-]{11}$/.test(k.videoId || "") ? k : null; };
  function statusOf(c) {
    const chk = c.status_pruefung;
    if (chk && STATUS[chk.status]) return { s: chk.status, zeit: chk.zeit || null };
    const k = checked(c);
    if (k && k.status === "offline") return { s: "offline", zeit: k.checked, checked: true, note: k.note };
    if (liveVideo(c)) return { s: "live", zeit: k.checked, checked: true };
    const r = resolve(c);
    if (r.zeit) return { s: "delayed", zeit: r.zeit, tag: r.tag };
    if (c.verzoegerung_min > 0) return { s: "delayed", zeit: null };
    return { s: null, zeit: null };
  }
  const ART_ORDER = { nachrichten: 0, wetter: 1, zeitversetzt: 2, panorama: 3 };
  const pill = s => s ? `<span class="spill ${s}">${STATUS[s]}</span>` : `<span class="spill nc" title="Status nicht feststellbar">STAND UNBEKANNT</span>`;
  const hhmm = iso => { const d = new Date(iso); return isNaN(d) ? null : d.toLocaleString("de-DE", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }); };

  const day = iso => new Date(iso).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", timeZone: "UTC" });
  function tileHtml(c, i) {
    const st = statusOf(c);
    const when = st.checked ? (st.s === "live" ? "live laut Prüfung " : (st.note || "nicht erreichbar") + " · Prüfung ") + hhmm(st.zeit)
      : st.tag ? "Tagesbild " + day(st.zeit) + " (UTC)" : st.zeit ? "Stand " + hhmm(st.zeit)
      : c.verzoegerung_min > 0 ? `verzögert ca. ${c.verzoegerung_min} Min.` : c.embed.typ === "skyline" ? "Vorschau · Stand unbekannt" : "Stand unbekannt";
    return `<div class="cw-tile" data-i="${i}">
      <div class="cw-th"><div class="who">${esc(ART[c.art] || c.art)}${c.kennzeichnung ? ` <span class="cw-tag">${esc(c.kennzeichnung)}</span>` : ""}<b title="${esc(c.betreiber)} · ${esc(c.ort || "")}">${esc(c.betreiber)}${c.ort ? " · " + esc(c.ort) : ""}</b>${esc(when)}</div>
        <div class="r"><span data-pill>${pill(st.s)}</span><button type="button" class="cw-fs" data-fs="${i}" title="Vollbild (Esc beendet)" aria-label="Vollbild">⛶</button></div></div>
      <div class="cw-media"></div>
      ${c.credit ? `<div class="cw-credit">${esc(c.credit)}</div>` : ""}
      <div class="cw-tf"><a href="${esc(c.quelle_url)}" target="_blank" rel="noopener noreferrer">QUELLE ↗</a><a href="${esc(c.lizenz_url)}" target="_blank" rel="noopener noreferrer">LIZENZ ↗</a></div>
    </div>`;
  }

  function html(iso, name, stufe) {
    const S = sourcesFor(iso, stufe), n = S.ok.length;
    const choice = [1, 2, 4].includes(+ss.get(GRID_KEY)) ? +ss.get(GRID_KEY) : 1;
    const grid = n < 2 ? 1 : choice;
    const seg = `<span class="cw-seg" role="group" aria-label="Anzahl Quellen nebeneinander">${[1, 2, 4].map(g =>
      `<button type="button" data-grid="${g}" aria-pressed="${g === grid}"${g > 1 && n < 2 ? " disabled" : ""}>${g === 4 ? "2×2" : g}</button>`).join("")}</span>`;
    const head = `<div class="cw-head"><span class="radar" aria-hidden="true"></span><span class="t">Country Intelligence · Lagebild</span>${seg}
      <button type="button" class="cw-wallbtn" data-cw-wall title="Bildschirmfüllende Lagezentrale">⛶ LAGEZENTRALE</button></div>`;
    const conflictNote = S.conflict ? `<div class="cw-note" style="margin-bottom:8px">Krisen-/Konfliktgebiet: nur redaktionelle Lagebilder und zeitversetzte zivile Übersichten. Keine Kameras auf Stellungen, Truppenbewegungen, Schutzräume oder sensible Einrichtungen.</div>` : "";
    if (!n) {
      const reason = !approved().length ? "Quellenkatalog noch nicht freigegeben."
        : S.blocked ? "Vorhandene Quellen sind für Konfliktgebiete nicht zugelassen."
        : "Für dieses Land ist keine geprüfte Quelle im Katalog.";
      return `${head}${conflictNote}<div class="cw-empty"><span class="spill unavailable">UNAVAILABLE</span>
        <b>Keine geprüfte öffentliche Quelle für ${esc(name)}</b>${esc(reason)}<br>Aktuelle Nachrichtenlage: Reiter ÜBERBLICK.</div>`;
    }
    const consent = ss.get(CONSENT_KEY) === "1";
    return `${head}${conflictNote}
      <div class="cw-note" data-cw-gate${consent ? " hidden" : ""}>Beim Laden werden Daten (u. a. IP-Adresse) an die Betreiber der Quellen übertragen. Ton ist aus.
        <br><button type="button" class="dbtn" data-cw-load>▶ LAGEBILD LADEN (${n} ${n === 1 ? "Quelle" : "Quellen"})</button></div>
      <div class="cw-grid g${grid}">${S.ok.slice(0, grid).map((c, i) => tileHtml(c, i)).join("")}</div>`;
  }

  function embedUrl(c) {
    const k = liveVideo(c);   // geprüfte Video-ID: Einbettung per Video funktioniert auch, wo der Kanal-Embed versagt
    let u = k ? "https://www.youtube-nocookie.com/embed/" + k.videoId : c.embed.url;
    if (c.embed.typ === "youtube") u += (u.includes("?") ? "&" : "?") + "autoplay=1&mute=1&playsinline=1&rel=0";
    return u;
  }
  function markOffline(tile, msg) {
    const p = tile.querySelector("[data-pill]"); if (p) p.innerHTML = pill("offline");
    const m = tile.querySelector(".cw-media");
    if (m) m.innerHTML = `<div class="cw-off">${esc(msg)}</div>`;
  }
  function imgEl(c, tile) {
    const img = document.createElement("img");
    img.alt = `${ART[c.art] || ""} ${c.betreiber} ${c.ort || ""}`.trim(); img.loading = "lazy"; img.referrerPolicy = "no-referrer";
    img.addEventListener("error", () => markOffline(tile, "Bild derzeit nicht abrufbar"), { once: true });
    img.src = resolve(c).url;
    return img;
  }
  function mountTile(tile, c) {
    const m = tile.querySelector(".cw-media"); if (!m || m.firstChild) return;
    const st = statusOf(c);
    if (st.checked && st.s === "offline" && c.embed.typ === "youtube") { markOffline(tile, `${st.note || "kein laufender Livestream"} · Prüfung ${hhmm(st.zeit)}`); return; }
    if (c.embed.typ === "skyline") {
      // Auflage SkylineWebcams: unveränderter Original-Embed = Vorschaubild, verlinkt auf die Kameraseite
      const a = document.createElement("a"); a.href = c.quelle_url; a.target = "_blank"; a.rel = "noopener noreferrer";
      a.title = "Kamera bei SkylineWebcams öffnen"; a.appendChild(imgEl(c, tile)); m.appendChild(a); return;
    }
    if (c.embed.typ === "bild") { m.appendChild(imgEl(c, tile)); return; }
    const el = document.createElement("iframe"); el.title = `${c.betreiber} – ${ART[c.art] || c.art}`; el.loading = "lazy";
    el.setAttribute("sandbox", "allow-scripts allow-same-origin allow-presentation");
    el.setAttribute("allow", "fullscreen; picture-in-picture");
    // YouTube-Player verlangen einen Referrer (sonst Fehler 153) – nur die Herkunft, kein Pfad; andere Einbettungen ohne Referrer
    el.referrerPolicy = c.embed.typ === "youtube" ? "strict-origin" : "no-referrer";
    el.src = embedUrl(c);
    m.appendChild(el);
  }
  function unmountAll(root) { root.querySelectorAll(".cw-media").forEach(m => m.replaceChildren()); }

  function bind(card, iso, name, stufe) {
    const pane = card.querySelector('.tabpane[data-pane="cam"]'); if (!pane) return;
    const S = sourcesFor(iso, stufe);
    const visible = () => card.classList.contains("open") && !pane.hidden && pane.isConnected;
    const mountVisible = () => { if (ss.get(CONSENT_KEY) !== "1" || !visible()) return;
      pane.querySelectorAll(".cw-tile").forEach(t => mountTile(t, S.ok[+t.dataset.i])); };
    pane.addEventListener("click", e => {
      if (e.target.closest("[data-cw-load]")) { ss.set(CONSENT_KEY, "1"); const g = pane.querySelector("[data-cw-gate]"); if (g) g.hidden = true; mountVisible(); }
      const gb = e.target.closest("[data-grid]");
      if (gb && !gb.disabled) { ss.set(GRID_KEY, gb.dataset.grid); unmountAll(pane); pane.innerHTML = html(iso, name, stufe); mountVisible(); }
      if (e.target.closest("[data-cw-wall]")) { openWall({ iso, name, stufe }); return; }
      const fb = e.target.closest("[data-fs]");
      if (fb) { const t = fb.closest(".cw-tile"); if (document.fullscreenElement) document.exitFullscreen(); else if (t.requestFullscreen) t.requestFullscreen(); }
    });
    // Aufräumen: Fenster zu, anderer Reiter, anderes Land → alle Einbettungen entfernen; Reiter wieder offen → nach Zustimmung laden
    const layout = () => { const v = visible(), multi = v && S.ok.length > 1 && +(ss.get(GRID_KEY) || 1) > 1;
      if (card.classList.contains("cam") !== v) card.classList.toggle("cam", v);
      if (card.classList.contains("camwide") !== multi) card.classList.toggle("camwide", multi); };
    const mo = new MutationObserver(() => {
      if (!pane.isConnected) { card.classList.remove("cam", "camwide"); mo.disconnect(); return; }
      layout();
      if (visible()) mountVisible(); else unmountAll(pane);
    });
    layout();
    mo.observe(card, { attributes: true, attributeFilter: ["class", "hidden"], subtree: true, childList: true });
  }

  function hotspotLink(key, nameOf) {
    const iso = HOTSPOT_ISO[key]; if (!iso) return "";
    return `<div><button type="button" class="dbtn cw-link" data-cam-iso="${iso}">◉ LAGEBILD ${esc(nameOf ? nameOf(iso) : iso)}</button></div>`;
  }
  function summary() { return { total: items().length, approved: approved().length, stand: (window.CAMS || {}).stand || null }; }

  /* ---------------- Lagezentrale „GLOBAL INTELLIGENCE NETWORK“ (Variante A Noir) ----------------
     Bildschirmfüllend, für ein Land oder eine Weltauswahl. Gleiche Regeln wie im Reiter: Laden erst nach Zustimmung,
     Konfliktfilter, Ton aus, beim Schließen werden alle Einbettungen entfernt. */
  const WORLD_PICK = ["deu-dw-news", "usa-abc-news-live", "jpn-nhk-world", "gbr-sky-news", "usa-goes-conus", "deu-eumetsat-mitteleuropa"];
  function worldSources() {
    const A = approved();
    return WORLD_PICK.map(id => A.find(c => c.id === id)).filter(c => c && (!isConflict(c.iso) || (CONFLICT_ART.has(c.art) && c.konfliktzone_zulaessig === true)));
  }
  let wallEl = null;
  function closeWall() {
    if (!wallEl) return;
    if (document.fullscreenElement && wallEl.contains(document.fullscreenElement)) document.exitFullscreen().catch(() => {});
    unmountAll(wallEl); if (wallEl._globe) wallEl._globe.destroy(); wallEl.remove(); wallEl = null;
    document.body.classList.remove("cw-wall-open"); removeEventListener("keydown", wallKey);
  }
  function wallKey(e) { if (e.key === "Escape" && !document.fullscreenElement) closeWall(); }
  function openWall(scope) {
    closeWall();
    const list = scope && scope.iso ? sourcesFor(scope.iso).ok.slice(0, 6) : worldSources();
    const title = scope && scope.iso ? esc(scope.name) : "WELTÜBERSICHT";
    const consent = ss.get(CONSENT_KEY) === "1";
    const hs = ((window.DOOM || {}).hotspots || []).filter(h => h.level >= 3).sort((a, b) => b.level - a.level).slice(0, 6);
    const conflict = scope && scope.iso && isConflict(scope.iso);
    wallEl = document.createElement("div"); wallEl.id = "cwWall"; wallEl.setAttribute("role", "dialog"); wallEl.setAttribute("aria-label", "Lagezentrale");
    wallEl.innerHTML = `<div class="gw-head"><div class="gw-title">GLOBAL INTELLIGENCE NETWORK<small>WAYNE INTELLIGENCE · A.L.F.R.E.D. · LAGEZENTRALE · ${title}</small></div>
        <div class="gw-sp"></div><span class="gw-k">QUELLEN <b>${list.length}</b></span><span class="gw-k">KATALOG <b>${esc((window.CAMS || {}).stand || "–")}</b></span>
        <span class="gw-k"><b data-gw-clock></b></span>
        ${scope && scope.iso ? `<button type="button" class="gw-btn" data-gw-world>◎ WELT</button>` : ""}
        <button type="button" class="gw-btn" data-gw-fs>⛶ VOLLBILD</button><button type="button" class="gw-btn" data-gw-close aria-label="Lagezentrale schließen">✕</button></div>
      <div class="gw-body">
        <div class="gw-grid n${Math.max(1, list.length)}">${list.length ? list.map((c, i) => tileHtml(c, i)).join("")
          : `<div class="cw-empty gw-empty"><span class="spill unavailable">UNAVAILABLE</span><b>Keine geprüfte öffentliche Quelle für ${title}</b>${approved().length ? "Für dieses Land ist keine zugelassene Quelle im Katalog." : "Quellenkatalog noch nicht freigegeben."}</div>`}
          ${list.length && !consent ? `<div class="gw-gate"><div>Beim Laden werden Daten (u. a. IP-Adresse) an die Betreiber der Quellen übertragen. Ton ist aus.</div>
            <button type="button" class="dbtn" data-gw-load>▶ LAGEBILD LADEN (${list.length} ${list.length === 1 ? "Quelle" : "Quellen"})</button></div>` : ""}</div>
        <aside class="gw-rail">
          <div class="gw-panel gw-globe"><h5>GLOBUS · QUELLEN</h5><div class="gw-mini"><canvas aria-label="Globus mit Quellenstandorten"></canvas></div></div>
          <div class="gw-panel"><h5>A.L.F.R.E.D. · LAGE</h5>${hs.map(h => `<div class="gw-row"><span>${esc(h.name)}</span><b>${h.level}/5</b></div>`).join("") || '<div class="muted">keine Krisenregion ≥ 3</div>'}
            <div class="gw-src">Meldungsdichte 48 h (doomsday.js) · keine Positionsdaten</div></div>
          <div class="gw-panel"><h5>REGELN</h5>${conflict ? "<b class='gw-warn'>Konfliktgebiet:</b> nur redaktionelle/zeitversetzte Lagebilder. " : ""}Laden nur nach Zustimmung · Ton aus · keine Aufzeichnung · keine Kameras auf militärische oder sensible Orte</div>
        </aside></div>
      <div class="gw-foot">STATUS: LIVE = Quelle sendet · DELAYED = zeitversetzt/Standbild · OFFLINE = nicht erreichbar · STAND UNBEKANNT = nicht prüfbar · Esc schließt</div>`;
    document.body.appendChild(wallEl); document.body.classList.add("cw-wall-open"); addEventListener("keydown", wallKey);
    const clock = wallEl.querySelector("[data-gw-clock]"), tick = () => { if (clock.isConnected) { clock.textContent = new Date().toISOString().slice(11, 16) + " UTC"; setTimeout(tick, 20000); } }; tick();
    const mount = () => wallEl.querySelectorAll(".cw-tile").forEach(t => mountTile(t, list[+t.dataset.i]));
    if (consent) mount();
    wallEl.addEventListener("click", e => {
      if (e.target.closest("[data-gw-close]")) return closeWall();
      if (e.target.closest("[data-gw-world]")) return openWall(null);
      if (e.target.closest("[data-gw-load]")) { ss.set(CONSENT_KEY, "1"); const gt = wallEl.querySelector(".gw-gate"); if (gt) gt.remove(); mount(); return; }
      if (e.target.closest("[data-gw-fs]")) { if (document.fullscreenElement) document.exitFullscreen(); else if (wallEl.requestFullscreen) wallEl.requestFullscreen(); return; }
      const fb = e.target.closest("[data-fs]");
      if (fb) { const t = fb.closest(".cw-tile"); if (document.fullscreenElement === t) document.exitFullscreen(); else if (t.requestFullscreen) t.requestFullscreen(); }
    });
    if (window.TB_globe) {
      const g = window.TB_globe.create(wallEl.querySelector(".gw-mini canvas"), { r: .44, stars: 90, rotate: [-5, -40, 0], spin: true });
      g.markers = list.map(c => { const ll = g.centroid(c.iso) || [0, 0]; return { lon: ll[0], lat: ll[1], r: 4, label: c.iso }; });
      if (scope && scope.iso) { g.sel = scope.iso; const ll = g.centroid(scope.iso); if (ll) { g.setSpin(false); g.flyTo(ll, 1400); } }
      g.redraw(); wallEl._globe = g;
    }
    wallEl.querySelector("[data-gw-close]").focus();
  }

  window.TB_camwall = { html, bind, hotspotLink, summary, openWall, closeWall };
})();
