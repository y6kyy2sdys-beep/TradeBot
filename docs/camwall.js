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
  function sourcesFor(iso, stufe) {
    const all = approved().filter(c => c.iso === iso);
    const conflict = stufe >= 3 || hotspotLevel(iso) >= 3;
    const ok = all.filter(c => !conflict || (CONFLICT_ART.has(c.art) && c.konfliktzone_zulaessig === true));
    return { all, ok, conflict, blocked: all.length - ok.length };
  }
  // Status nur aus belegten Angaben: Katalogprüfung (status_pruefung) oder erklärte Verzögerung – sonst „unbekannt“
  function statusOf(c) {
    const chk = c.status_pruefung;
    if (chk && STATUS[chk.status]) return { s: chk.status, zeit: chk.zeit || null };
    if (c.verzoegerung_min > 0) return { s: "delayed", zeit: null };
    return { s: null, zeit: null };
  }
  const pill = s => s ? `<span class="spill ${s}">${STATUS[s]}</span>` : `<span class="spill nc" title="Status nicht feststellbar">STAND UNBEKANNT</span>`;
  const hhmm = iso => { const d = new Date(iso); return isNaN(d) ? null : d.toLocaleString("de-DE", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }); };

  function tileHtml(c, i) {
    const st = statusOf(c), when = st.zeit ? "Stand " + hhmm(st.zeit) : c.verzoegerung_min > 0 ? `verzögert ca. ${c.verzoegerung_min} Min.` : "Stand unbekannt";
    return `<div class="cw-tile" data-i="${i}">
      <div class="cw-th"><div class="who">${esc(ART[c.art] || c.art)}<b title="${esc(c.betreiber)} · ${esc(c.ort || "")}">${esc(c.betreiber)}${c.ort ? " · " + esc(c.ort) : ""}</b>${esc(when)}</div>
        <div class="r">${pill(st.s)}<button type="button" class="cw-fs" data-fs="${i}" title="Vollbild (Esc beendet)" aria-label="Vollbild">⛶</button></div></div>
      <div class="cw-media"></div>
      <div class="cw-tf"><a href="${esc(c.quelle_url)}" target="_blank" rel="noopener noreferrer">QUELLE ↗</a><a href="${esc(c.lizenz_url)}" target="_blank" rel="noopener noreferrer">LIZENZ ↗</a></div>
    </div>`;
  }

  function html(iso, name, stufe) {
    const S = sourcesFor(iso, stufe), n = S.ok.length;
    const choice = [1, 2, 4].includes(+ss.get(GRID_KEY)) ? +ss.get(GRID_KEY) : 1;
    const grid = n < 2 ? 1 : choice;
    const seg = `<span class="cw-seg" role="group" aria-label="Anzahl Quellen nebeneinander">${[1, 2, 4].map(g =>
      `<button type="button" data-grid="${g}" aria-pressed="${g === grid}"${g > 1 && n < 2 ? " disabled" : ""}>${g === 4 ? "2×2" : g}</button>`).join("")}</span>`;
    const head = `<div class="cw-head"><span class="radar" aria-hidden="true"></span><span class="t">Country Intelligence · Lagebild</span>${seg}</div>`;
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
    let u = c.embed.url;
    if (c.embed.typ === "youtube") u += (u.includes("?") ? "&" : "?") + "autoplay=1&mute=1&playsinline=1&rel=0";
    return u;
  }
  function mountTile(tile, c) {
    const m = tile.querySelector(".cw-media"); if (!m || m.firstChild) return;
    let el;
    if (c.embed.typ === "bild") {
      el = document.createElement("img"); el.alt = `${ART[c.art] || ""} ${c.betreiber} ${c.ort || ""}`.trim(); el.loading = "lazy";
    } else {
      el = document.createElement("iframe"); el.title = `${c.betreiber} – ${ART[c.art] || c.art}`; el.loading = "lazy";
      el.setAttribute("sandbox", "allow-scripts allow-same-origin allow-presentation");
      el.setAttribute("allow", "fullscreen; picture-in-picture");
    }
    el.referrerPolicy = "no-referrer"; el.src = c.embed.typ === "bild" ? c.embed.url : embedUrl(c);
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

  window.TB_camwall = { html, bind, hotspotLink, summary };
})();
