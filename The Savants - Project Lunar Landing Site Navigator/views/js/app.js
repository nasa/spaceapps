const state = {
  sites: [],
  scn: null,
  index: 0,
  baseParams: null,
  mapper: null,
  compare: [],
  illumSeq: 0,
  illumTimer: null,
  globe: null,
  splashGlobe: null,
  viewer: null,
  panel: "site",
};

const el = (id) => document.getElementById(id);
const p2 = (n) => String(n).padStart(2, "0");

function fmtDur(h) {
  if (h == null || !isFinite(h)) return "\u2014";
  const d = Math.floor(h / 24);
  const hh = Math.floor(h % 24);
  const mm = Math.round((h * 60) % 60);
  if (d > 0) return `${d}d ${hh}h`;
  if (hh > 0) return `${hh}h ${p2(mm)}m`;
  return `${Math.max(0, mm)}m`;
}

function fmtPct(v, digits = 0) {
  return `${(v * 100).toFixed(digits)}%`;
}

function fmtClock(startISO, hours) {
  const t = new Date(new Date(startISO).getTime() + hours * 3600000);
  const off = hours >= 24 ? `  (+${(hours / 24).toFixed(1)}d)` : "";
  return `${t.toISOString().slice(0, 16).replace("T", " ")} UTC${off}`;
}

function inputFromDate(d) {
  return `${d.getUTCFullYear()}-${p2(d.getUTCMonth() + 1)}-${p2(d.getUTCDate())}T${p2(d.getUTCHours())}:${p2(d.getUTCMinutes())}`;
}

function phaseLabel(sep) {
  if (sep > 160) return "new moon";
  if (sep > 110) return "crescent moon";
  if (sep > 70) return "quarter moon";
  if (sep > 20) return "gibbous moon";
  return "full moon";
}

function renderPhase(separation, fraction) {
  el("phaseName").textContent = phaseLabel(separation);
  el("phaseBar").style.width = `${(fraction * 100).toFixed(1)}%`;
  el("separation").textContent = `${separation.toFixed(1)}\u00b0`;
}

function setStatus(text, isError) {
  const node = el("status");
  node.textContent = text || "";
  node.classList.toggle("err", Boolean(isError));
}

function siteParams() {
  const id = el("site").value;
  if (id === "custom") {
    return { lat: el("lat").value, lon: el("lon").value };
  }
  return { site_id: id };
}

function currentParams() {
  return {
    ...siteParams(),
    start: el("start").value.length === 16 ? `${el("start").value}:00` : el("start").value,
    hours: el("hours").value,
    step: el("step").value,
  };
}

function interpolateAt(index) {
  const s = state.scn.series;
  const i = Math.max(0, Math.min(s.hours.length - 1, Math.round(index)));
  return {
    i,
    hours: s.hours[i],
    sun_az: s.sun_az[i],
    sun_el: s.sun_el[i],
    sun_horizon: s.sun_horizon[i],
    sun_frac: s.sun_frac[i],
    earth_az: s.earth_az[i],
    earth_el: s.earth_el[i],
    earth_horizon: s.earth_horizon[i],
    earth_lit: s.earth_lit[i],
  };
}

function sunStatus(cur) {
  const gap = cur.sun_el - cur.sun_horizon;
  if (gap > 0.27) return ["clear of terrain", "gr"];
  if (gap > -0.27) return ["grazing horizon", "pos"];
  return ["below terrain horizon", "neg"];
}

function earthStatus(cur) {
  if (cur.earth_lit) return ["above horizon", "gr"];
  return [cur.earth_el > cur.earth_horizon - 1 ? "setting" : "below horizon", "neg"];
}

function renderKpis(scn) {
  const s = scn.summary;
  const cards = [
    ["Sunlight (window)", fmtPct(s.illumination, 1), `${fmtDur(s.longest_sun_hours)} longest run`],
    ["Earth visibility", fmtPct(s.earth_visibility, 1), `${fmtDur(s.longest_earth_hours)} longest run`],
    [s.sun_up_now ? "Sunset in" : "Sunrise in", fmtDur(s.next_sun_transition_h), s.sun_up_now ? "sun above terrain" : "sun hidden"],
    [s.earth_up_now ? "Earthset in" : "Earthrise in", fmtDur(s.next_earth_transition_h), s.earth_up_now ? "Earth in view" : "Earth hidden"],
    ["Peak Sun elevation", Charts.fmtDeg(s.max_sun_el), `min ${Charts.fmtDeg(s.min_sun_el)}`],
    ["Insolation", `${s.insolation_wh_m2.toFixed(0)}`, "Wh/m\u00b2 over window"],
  ];
  el("kpis").innerHTML = cards
    .map(([k, v, sub]) => `<div class="kpi"><div class="k">${k}</div><div class="v">${v}</div><div class="s">${sub}</div></div>`)
    .join("");
}

function renderHud(scn) {
  const n = scn.now;
  el("subsolar").textContent = `${Charts.fmtDeg(n.subsolar.lat, 1)}, ${n.subsolar.lon.toFixed(0)}\u00b0`;
  el("subearth").textContent = `${Charts.fmtDeg(n.subearth.lat, 1)}, ${n.subearth.lon.toFixed(0)}\u00b0`;
  el("siteCount").textContent = `${state.sites.length} sites`;
  el("globeMeta").textContent = `${scn.site.name}`;
  el("markerCount").textContent = `${state.sites.length}`;
  el("terrainState").textContent = scn.terrain.source;
  el("sampleCount").textContent = `${scn.series.sun_el.length}`;
  el("windowState").textContent = `${scn.hours} h`;
  el("ephemState").textContent = scn.summary.source === "horizons" ? "JPL Horizons" : "analytic";
  renderPhase(n.separation, n.phase_fraction);
}

function renderTerrain(scn) {
  const t = scn.terrain;
  const real = t.source === "lola";
  el("terrain").innerHTML = `
    <div>Source <span class="flag ${real ? "real" : ""}">${real ? "LOLA DEM (live)" : "synthetic (calibrated)"}</span></div>
    <div>Elevation <b>${t.center_m.toFixed(0)} m</b> at site, range <b>${t.min_m.toFixed(0)}</b> to <b>${t.max_m.toFixed(0)} m</b></div>
    <div>Grid <b>${t.grid}\u00d7${t.grid}</b> at <b>${t.res_m} m</b>, radius <b>${(t.radius_m / 1000).toFixed(0)} km</b></div>`;
  const badge = el("terrainBadge");
  badge.textContent = `terrain ${real ? "LOLA" : "synthetic"}`;
  badge.className = `badge ${real ? "ok" : "warn"}`;
}

function renderReadout(scn, cur) {
  const n = scn.now;
  const [sTxt, sCls] = sunStatus(cur);
  const [eTxt, eCls] = earthStatus(cur);
  el("readout").innerHTML = `
    <div class="bigpair">
      <div class="big"><div class="k">Sun elevation</div><div class="v ${cur.sun_el >= 0 ? "pos" : "neg"}">${Charts.fmtDeg(cur.sun_el)}</div><div class="s">${sTxt}</div></div>
      <div class="big"><div class="k">Earth elevation</div><div class="v cy">${Charts.fmtDeg(cur.earth_el)}</div><div class="s ${eCls}">${eTxt}</div></div>
    </div>
    <div class="rline"><span class="k">Sun</span><span class="v">az ${cur.sun_az.toFixed(2)}\u00b0 &middot; horizon ${Charts.fmtDeg(cur.sun_horizon)} &middot; disc lit ${fmtPct(cur.sun_frac)}</span></div>
    <div class="rline"><span class="k">Earth</span><span class="v">az ${cur.earth_az.toFixed(2)}\u00b0 &middot; horizon ${Charts.fmtDeg(cur.earth_horizon)} &middot; range ${n.earth_distance_km.toFixed(0)} km</span></div>
    <div class="rline"><span class="k">Phase</span><span class="v">${n.phase} &middot; separation ${n.separation.toFixed(1)}\u00b0 &middot; illuminated ${fmtPct(n.phase_fraction)}</span></div>
    <div class="rline"><span class="k">Sun range</span><span class="v">${n.sun_distance_au.toFixed(5)} AU</span></div>`;
}

function drawAll(cur) {
  Charts.drawPanorama(el("pano"), state.scn, cur);
  state.mapper = Charts.drawTimeline(el("timeline"), state.scn, state.index);
}

function scheduleIllumination(cur) {
  clearTimeout(state.illumTimer);
  state.illumTimer = setTimeout(() => refreshIllumination(cur), 280);
}

async function refreshIllumination(cur) {
  if (!state.scn) return;
  const seq = ++state.illumSeq;
  const params = {
    ...siteParams(),
    start: state.baseParams.start,
    minute: (cur.hours * 60).toFixed(1),
    size: "384",
    format: "json",
  };
  try {
    const stats = await API.illuminationStats(params);
    if (seq !== state.illumSeq) return;
    el("illum").src = API.illuminationURL({ ...params, format: "png" });
    el("mapFoot").textContent = `${stats.terrain_source === "lola" ? "LOLA" : "synthetic"} terrain \u00b7 ${stats.center_elevation_m.toFixed(0)} m`;
    if (state.globe) state.globe.setSun(stats.subsolar);
    renderPhase(stats.separation, (1 + Math.cos((stats.separation * Math.PI) / 180)) / 2);
    if (state.viewer && !el("viewerWindow").hidden) {
      el("vSun").textContent = `${stats.sun_az.toFixed(1)}\u00b0 / ${stats.sun_el.toFixed(2)}\u00b0`;
    }
  } catch (err) {
    if (seq !== state.illumSeq) return;
  }
}

function updateSelection(index) {
  if (!state.scn) return;
  const n = state.scn.series.hours.length;
  state.index = Math.max(0, Math.min(n - 1, index));
  const cur = interpolateAt(state.index);
  el("scrub").value = String(n > 1 ? Math.round((state.index / (n - 1)) * 1000) : 0);
  el("clock").textContent = fmtClock(state.scn.start, cur.hours);
  renderReadout(state.scn, cur);
  drawAll(cur);
  scheduleIllumination(cur);
}

function renderScenario(scn) {
  state.scn = scn;
  state.index = 0;
  renderTerrain(scn);
  renderHud(scn);
  renderKpis(scn);
  if (state.globe) {
    state.globe.focus(scn.site.lat, scn.site.lon);
    state.globe.setSelected(scn.site.id);
    state.globe.setSun(scn.now.subsolar);
  }
  const badge = el("ephemBadge");
  const real = scn.summary.source === "horizons";
  badge.textContent = real ? "ephemeris Horizons" : "ephemeris analytic";
  badge.className = `badge ${real ? "ok" : "warn"}`;
  updateSelection(0);
  markCatalog();
}

async function run() {
  const params = currentParams();
  state.baseParams = params;
  const btn = el("run");
  btn.disabled = true;
  setStatus("fetching ephemerides and terrain\u2026");
  try {
    const scn = await API.scenario(params);
    renderScenario(scn);
    setStatus(`ready \u00b7 ${scn.series.sun_el.length} samples`);
  } catch (err) {
    setStatus(err.message, true);
  } finally {
    btn.disabled = false;
  }
}

function addComparison() {
  if (!state.scn) return;
  const params = { ...siteParams(), start: state.baseParams.start, hours: state.baseParams.hours };
  const key = JSON.stringify(params);
  if (!state.compare.some((c) => JSON.stringify(c) === key)) state.compare.push(params);
  renderCompare();
}

async function renderCompare() {
  const box = el("compare");
  if (!state.compare.length) {
    box.className = "compare muted";
    box.textContent = "No scenarios added yet.";
    return;
  }
  box.className = "compare";
  box.textContent = "computing\u2026";
  try {
    const data = await API.compare(state.compare);
    const rows = data.rows
      .map((r, i) => `<tr>
        <td>${r.site}</td>
        <td class="num">${fmtPct(r.illumination, 1)}</td>
        <td class="num">${fmtPct(r.earth_visibility, 1)}</td>
        <td class="num">${fmtDur(r.longest_sun_hours)}</td>
        <td class="num">${r.max_sun_el.toFixed(2)}\u00b0</td>
        <td class="num">${r.insolation_wh_m2.toFixed(0)}</td>
        <td>${r.terrain}</td>
        <td><button class="del" data-i="${i}">\u00d7</button></td>
      </tr>`)
      .join("");
    box.innerHTML = `<table class="ct">
      <thead><tr><th>Site</th><th>Sun</th><th>Earth</th><th>Run</th><th>Peak</th><th>Wh/m\u00b2</th><th>DEM</th><th></th></tr></thead>
      <tbody>${rows}</tbody></table>`;
    box.querySelectorAll("button.del").forEach((b) => {
      b.addEventListener("click", () => {
        state.compare.splice(Number(b.dataset.i), 1);
        renderCompare();
      });
    });
  } catch (err) {
    box.textContent = err.message;
  }
}

function buildCatalog(list) {
  const box = el("catalog");
  box.innerHTML = "";
  for (const s of list) {
    const row = document.createElement("div");
    row.className = "catalog-row";
    row.dataset.id = s.id;
    row.innerHTML = `<span class="nm">${s.name}</span><span class="co">${s.lat.toFixed(1)}\u00b0</span>`;
    row.addEventListener("click", () => {
      el("site").value = s.id;
      el("site").dispatchEvent(new Event("change"));
    });
    box.appendChild(row);
  }
}

function markCatalog() {
  const id = el("site").value;
  document.querySelectorAll(".catalog-row").forEach((r) => {
    r.classList.toggle("on", r.dataset.id === id);
  });
}

function populateSites(list) {
  const groups = { south_pole: "South pole", historic: "Historic landings" };
  const select = el("site");
  let html = "";
  for (const key of Object.keys(groups)) {
    const items = list.filter((s) => s.region === key);
    if (!items.length) continue;
    html += `<optgroup label="${groups[key]}">`;
    html += items
      .map((s) => `<option value="${s.id}">${s.name}${s.dem === "synthetic" ? "  (synthetic)" : ""}</option>`)
      .join("");
    html += "</optgroup>";
  }
  html += '<optgroup label="Custom"><option value="custom">Custom coordinates</option></optgroup>';
  select.innerHTML = html;
  select.value = "shackleton";
  if (state.globe) state.globe.setSites(list);
  buildCatalog(list);

  const note = el("siteNote");
  const sync = () => {
    const id = select.value;
    el("customRow").hidden = id !== "custom";
    if (id === "custom") {
      note.textContent = "Custom selenographic coordinates.";
      markCatalog();
      return;
    }
    const s = list.find((x) => x.id === id);
    note.textContent = s ? `${s.note} \u00b7 terrain ${s.dem === "lola" ? "LOLA DEM" : "synthetic"}` : "";
    if (s && state.globe) {
      state.globe.setSelected(id);
      state.globe.focus(s.lat, s.lon);
    }
    markCatalog();
  };
  select.addEventListener("change", () => {
    sync();
    run();
  });
  sync();
}

async function loadHealth() {
  try {
    const h = await API.health();
    const badge = el("healthBadge");
    badge.textContent = `cache ${h.coverage.chunks} chunk${h.coverage.chunks === 1 ? "" : "s"}`;
    badge.className = `badge ${h.coverage.chunks ? "ok" : "warn"}`;
    el("cacheState").textContent = `${h.coverage.chunks} chunks`;
  } catch (err) {
    el("healthBadge").textContent = "offline";
  }
}

function attachRipple() {
  document.addEventListener("pointerdown", (ev) => {
    const btn = ev.target.closest("button");
    if (!btn) return;
    const rect = btn.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const span = document.createElement("span");
    span.className = "ripple";
    span.style.width = `${size}px`;
    span.style.height = `${size}px`;
    span.style.left = `${ev.clientX - rect.left - size / 2}px`;
    span.style.top = `${ev.clientY - rect.top - size / 2}px`;
    btn.appendChild(span);
    setTimeout(() => span.remove(), 680);
  });
}

function selectFromGlobe(id) {
  const select = el("site");
  if (![...select.options].some((o) => o.value === id)) return;
  select.value = id;
  select.dispatchEvent(new Event("change"));
}

function openViewer() {
  if (!state.scn) return;
  const win = el("viewerWindow");
  win.hidden = false;
  el("viewerTitle").textContent = `${state.scn.site.name.toUpperCase()} \u00b7 SITE VIEW`;
  const cur = interpolateAt(state.index);
  const params = {
    ...siteParams(),
    start: state.baseParams.start,
    minute: (cur.hours * 60).toFixed(1),
  };
  state.viewer.open(state.scn.site, params);
  el("vSun").textContent = `${cur.sun_az.toFixed(1)}\u00b0 / ${cur.sun_el.toFixed(2)}\u00b0`;
  el("vEarth").textContent = `${cur.earth_az.toFixed(1)}\u00b0 / ${cur.earth_el.toFixed(2)}\u00b0`;
}

function closeViewer() {
  el("viewerWindow").hidden = true;
}

function setPanel(name) {
  state.panel = name;
  document.querySelectorAll(".menubar-btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.menu === name);
  });
  document.querySelectorAll(".dock-panel").forEach((p) => {
    p.classList.toggle("active", p.dataset.panel === name);
  });
}

function wire() {
  el("start").value = inputFromDate(new Date());
  el("run").addEventListener("click", run);
  el("start").addEventListener("change", run);
  el("hours").addEventListener("change", run);
  el("step").addEventListener("change", run);
  el("lat").addEventListener("change", () => {
    if (el("site").value === "custom") run();
  });
  el("lon").addEventListener("change", () => {
    if (el("site").value === "custom") run();
  });

  document.querySelectorAll("button[data-shift]").forEach((b) => {
    b.addEventListener("click", () => {
      const shift = Number(b.dataset.shift);
      const base = el("start").value ? new Date(`${el("start").value}:00Z`) : new Date();
      const next = shift === 0 ? new Date() : new Date(base.getTime() + shift * 3600000);
      el("start").value = inputFromDate(next);
      run();
    });
  });

  document.querySelectorAll("button[data-phase]").forEach((b) => {
    b.addEventListener("click", () => {
      el("phase").value = b.dataset.phase;
      el("phase").dispatchEvent(new Event("change"));
    });
  });

  el("phase").addEventListener("change", async () => {
    setStatus("searching for phase\u2026");
    try {
      const res = await API.phase({ kind: el("phase").value, start: `${el("start").value}:00`, ...siteParams() });
      el("start").value = res.time.slice(0, 16);
      setStatus(`${res.kind} moon at ${res.time.slice(0, 16).replace("T", " ")} UTC \u00b7 ${fmtPct(res.illuminated)} lit`);
      await run();
    } catch (err) {
      setStatus(err.message, true);
    }
  });

  el("scrub").addEventListener("input", (e) => {
    const n = state.scn ? state.scn.series.hours.length : 1;
    updateSelection(Math.round((Number(e.target.value) / 1000) * (n - 1)));
  });

  el("timeline").addEventListener("click", (e) => {
    if (state.mapper) updateSelection(state.mapper.indexAt(e.clientX));
  });

  el("spinToggle").addEventListener("click", () => {
    const on = el("spinToggle").getAttribute("aria-pressed") !== "true";
    el("spinToggle").setAttribute("aria-pressed", String(on));
    el("spinToggle").textContent = on ? "SPIN" : "HOLD";
    el("spinState").textContent = on ? "on" : "off";
    if (state.globe) state.globe.setSpin(on);
  });

  el("addCompare").addEventListener("click", addComparison);
  el("clearCompare").addEventListener("click", () => {
    state.compare = [];
    renderCompare();
  });

  el("explore").addEventListener("click", openViewer);
  el("explore2").addEventListener("click", openViewer);
  el("viewerClose").addEventListener("click", closeViewer);
  el("viewerRefresh").addEventListener("click", () => {
    if (state.viewer) state.viewer.refresh();
  });

  document.querySelectorAll(".menubar-btn").forEach((b) => {
    b.addEventListener("click", () => {
      const name = b.dataset.menu;
      setPanel(state.panel === name ? "" : name);
    });
  });

  window.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape") closeViewer();
  });

  let resizeTimer = null;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      if (state.scn) drawAll(interpolateAt(state.index));
    }, 180);
  });
}

function launch() {
  const splash = el("splash");
  const app = el("app");
  splash.classList.add("zoom");
  setTimeout(() => {
    app.hidden = false;
    requestAnimationFrame(() => app.classList.add("shown"));
  }, 520);
  setTimeout(() => {
    splash.classList.add("gone");
    if (state.splashGlobe) state.splashGlobe.destroy();
  }, 1500);
  setPanel("site");
}

async function boot() {
  attachRipple();
  wire();
  state.splashGlobe = createMoonGlobe(el("splashMoon"), {});
  state.globe = createMoonGlobe(el("globe"), { onSelect: selectFromGlobe });
  state.viewer = createSiteViewer(el("viewCanvas"), {
    hud: {
      compass: el("compass"),
      heading: el("vHeading"),
      pitch: el("vPitch"),
      zoom: el("vZoom"),
      position: el("vPosition"),
    },
  });
  el("launch").addEventListener("click", launch);
  loadHealth();
  try {
    const data = await API.sites();
    state.sites = data.sites;
    populateSites(data.sites);
  } catch (err) {
    setStatus(`site catalogue unavailable: ${err.message}`, true);
    return;
  }
  await run();
}

boot();
