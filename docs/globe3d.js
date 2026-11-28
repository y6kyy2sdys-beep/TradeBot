/* PROJECT A.L.F.R.E.D. – Globus-Renderer (Variante A „Noir“), gemeinsam für Lagezentrale und PROJECT CHRONOS.
   d3-geo (orthografisch) auf Canvas – keine zusätzliche Bibliothek. Zeichnet nur bei Bedarf (Drehen, Kamerafahrt, Datenwechsel);
   Eigendrehung nur ohne „reduzierte Bewegung“ und nur bei sichtbarem Tab. Licht/Schatten sind rein gestalterisch (keine Tageszeit). */
(function (global) {
  "use strict";
  const d3 = global.d3, topo = global.topojson, T = global.WORLD_TOPO;
  if (!d3 || !topo || !T) return;
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const feats = topo.feature(T, T.objects.countries).features.filter(f => f.id !== "010");
  feats.forEach(f => { f.iso = (global.ISO_NUM && global.ISO_NUM[f.id] || [])[0] || ""; });
  const byIso = new Map(feats.map(f => [f.iso, f]));
  const borders = topo.mesh(T, T.objects.countries, (a, b) => a !== b), coast = topo.mesh(T, T.objects.countries, (a, b) => a === b);
  const STYLE = { bg: "#000", star: "rgba(200,255,210,", atmo: "rgba(0,255,65,.15)", ocean1: "#03140a", ocean2: "#000603", land: "#0c2414",
    border: "rgba(0,255,65,.55)", glow: "rgba(0,255,65,.9)", blur: 5, grat: "rgba(0,255,65,.10)", rim: "rgba(0,255,65,.5)", hi: "#c9a227" };

  function create(canvas, opt = {}) {
    const ctx = canvas.getContext("2d"), proj = d3.geoOrthographic().clipAngle(90).precision(0.6), path = d3.geoPath(proj, ctx), grat = d3.geoGraticule10();
    let w = 0, h = 0, R = 0, cx = 0, cy = 0, stars = [], rot = (opt.rotate || [-10, -35, 0]).slice(), fly = null, spin = null, alive = true, dirty = true, raf = 0;
    const g = { fill: () => null, markers: [], sel: null, onPick: null, spinning: !!opt.spin && !reduced };
    function size() {
      const dpr = Math.min(2, global.devicePixelRatio || 1); w = canvas.clientWidth; h = canvas.clientHeight; if (!w || !h) return;
      canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr); ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      R = Math.min(w, h) * (opt.r || .42); cx = w * (opt.cx || .5); cy = h * (opt.cy || .5); proj.scale(R).translate([cx, cy]);
      let s = 7; const rnd = () => (s = (s * 16807) % 2147483647) / 2147483647;
      stars = Array.from({ length: opt.stars ?? 260 }, () => [rnd() * w, rnd() * h, rnd() * 1.1 + .2, rnd() * .6 + .15]); dirty = true;
    }
    function draw() {
      if (!w || !h) return;
      ctx.fillStyle = STYLE.bg; ctx.fillRect(0, 0, w, h);
      stars.forEach(([x, y, r, a]) => { ctx.fillStyle = STYLE.star + a + ")"; ctx.fillRect(x, y, r, r); });
      const at = ctx.createRadialGradient(cx, cy, R * .96, cx, cy, R * 1.28); at.addColorStop(0, STYLE.atmo); at.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = at; ctx.beginPath(); ctx.arc(cx, cy, R * 1.28, 0, 7); ctx.fill();
      proj.rotate(rot);
      const oc = ctx.createRadialGradient(cx - R * .35, cy - R * .4, R * .05, cx, cy, R); oc.addColorStop(0, STYLE.ocean1); oc.addColorStop(1, STYLE.ocean2);
      ctx.fillStyle = oc; ctx.beginPath(); path({ type: "Sphere" }); ctx.fill();
      ctx.beginPath(); path(grat); ctx.strokeStyle = STYLE.grat; ctx.lineWidth = .5; ctx.stroke();
      feats.forEach(f => { ctx.beginPath(); path(f); ctx.fillStyle = g.fill(f) || STYLE.land; ctx.fill(); });
      ctx.save(); ctx.shadowColor = STYLE.glow; ctx.shadowBlur = STYLE.blur;
      ctx.beginPath(); path(borders); ctx.strokeStyle = STYLE.border; ctx.lineWidth = .6; ctx.stroke();
      ctx.beginPath(); path(coast); ctx.lineWidth = .8; ctx.stroke(); ctx.restore();
      if (g.sel && byIso.get(g.sel)) { ctx.beginPath(); path(byIso.get(g.sel)); ctx.strokeStyle = STYLE.hi; ctx.lineWidth = 1.8; ctx.stroke(); }
      const sh = ctx.createRadialGradient(cx - R * .5, cy - R * .5, R * .15, cx, cy, R * 1.05);
      sh.addColorStop(0, "rgba(255,255,255,.07)"); sh.addColorStop(.55, "rgba(0,0,0,0)"); sh.addColorStop(1, "rgba(0,0,0,.6)");
      ctx.fillStyle = sh; ctx.beginPath(); path({ type: "Sphere" }); ctx.fill();
      ctx.beginPath(); path({ type: "Sphere" }); ctx.strokeStyle = STYLE.rim; ctx.lineWidth = 1.1; ctx.stroke();
      const center = [-rot[0], -rot[1]];
      g.markers.forEach(m => { if (d3.geoDistance([m.lon, m.lat], center) > Math.PI / 2 - .05) return; const [x, y] = proj([m.lon, m.lat]);
        ctx.beginPath(); ctx.arc(x, y, m.r || 4, 0, 7); ctx.fillStyle = m.color || STYLE.hi; ctx.fill(); ctx.lineWidth = 1; ctx.strokeStyle = "#000"; ctx.stroke();
        if (m.label) { ctx.fillStyle = "rgba(230,240,235,.92)"; ctx.font = "10px 'Share Tech Mono', monospace"; ctx.fillText(m.label, x + 7, y + 3); } });
      dirty = false;
    }
    function loop() { if (!alive) return; raf = requestAnimationFrame(loop); if (document.hidden) return; if (dirty) draw(); }
    g.redraw = () => { dirty = true; };
    g.flyTo = (lonlat, ms = 1600) => {
      const to = [-lonlat[0], -lonlat[1] + 8, 0];
      if (reduced || !ms) { rot = to; dirty = true; return; }
      const ip = d3.interpolate(rot.slice(), to); if (fly) fly.stop();
      fly = d3.timer(t => { const k = d3.easeCubicInOut(Math.min(1, t / ms)); rot = ip(k); dirty = true; if (k >= 1) { fly.stop(); fly = null; } });
    };
    g.setSpin = on => { g.spinning = on && !reduced; if (spin) { spin.stop(); spin = null; }
      if (g.spinning) { let last = 0; spin = d3.timer(t => { if (fly || dragging || t - last < 33) return; last = t; rot = [rot[0] + .06, rot[1], rot[2]]; dirty = true; }); } };
    let dragging = false;
    d3.select(canvas).call(d3.drag().on("start", () => { dragging = true; }).on("drag", ev => {
      rot = [rot[0] + ev.dx * .3, Math.max(-85, Math.min(85, rot[1] - ev.dy * .3)), 0]; dirty = true; }).on("end", () => { dragging = false; }))
      .on("click", ev => {
        if (!g.onPick) return; const r = canvas.getBoundingClientRect(), p = proj.invert([ev.clientX - r.left, ev.clientY - r.top]);
        if (!p || d3.geoDistance(p, [-rot[0], -rot[1]]) > Math.PI / 2) return;
        const f = feats.find(x => d3.geoContains(x, p)); if (f && f.iso) g.onPick(f.iso);
      });
    g.centroid = iso => { const f = byIso.get(iso); return f ? d3.geoCentroid(f) : null; };
    g.destroy = () => { alive = false; cancelAnimationFrame(raf); if (fly) fly.stop(); if (spin) spin.stop(); removeEventListener("resize", onResize); };
    const onResize = () => size(); addEventListener("resize", onResize);
    size(); g.setSpin(g.spinning); loop();
    return g;
  }
  global.TB_globe = { create, feats, byIso, reduced };
})(window);
