function createMoonGlobe(node, options) {
  const TEX_W = 1024;
  const TEX_H = 512;
  const RES = 400;
  const D2R = Math.PI / 180;
  const opts = options || {};
  const canvas = node;
  const ctx = canvas.getContext("2d");
  const off = document.createElement("canvas");
  off.width = RES;
  off.height = RES;
  const offCtx = off.getContext("2d");
  let w = 0;
  let h = 0;
  let dpr = 1;
  let yaw = 0.6;
  let pitch = 0.18;
  let velY = 0;
  let velX = 0;
  let spin = true;
  let dragging = false;
  let moved = false;
  let px = 0;
  let py = 0;
  let selected = null;
  let hovered = null;
  let sites = [];
  let sun = { lat: 0, lon: 0 };
  let markers = [];
  let stars = [];
  let needsRender = true;
  let last = 0;
  let running = true;

  function mulberry(a) {
    return function () {
      a |= 0;
      a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function buildTexture() {
    const c = document.createElement("canvas");
    c.width = TEX_W;
    c.height = TEX_H;
    const g = c.getContext("2d");
    const rnd = mulberry(20261115);
    g.fillStyle = "rgb(196,196,196)";
    g.fillRect(0, 0, TEX_W, TEX_H);
    for (let i = 0; i < 9; i++) {
      const x = rnd() * TEX_W;
      const y = TEX_H * (0.16 + 0.68 * rnd());
      const r = 7 + rnd() * 15;
      const v = 148 + Math.floor(rnd() * 34);
      g.fillStyle = `rgba(${v},${v},${v + 3},${0.35 + rnd() * 0.4})`;
      g.beginPath();
      g.arc(x, y, r, 0, Math.PI * 2);
      g.fill();
    }
    for (let i = 0; i < 900; i++) {
      const x = rnd() * TEX_W;
      const y = rnd() * TEX_H;
      const r = 0.7 + rnd() * 1.6;
      const v = 198 + Math.floor(rnd() * 30);
      g.fillStyle = `rgba(${v},${v},${v + 5},${0.12 + rnd() * 0.2})`;
      g.beginPath();
      g.arc(x, y, r, 0, Math.PI * 2);
      g.fill();
    }
    for (let i = 0; i < 260; i++) {
      const x = rnd() * TEX_W;
      const y = rnd() * TEX_H;
      const r = 2 + Math.pow(rnd(), 2.4) * 16;
      const v = 168 + Math.floor(rnd() * 30);
      g.fillStyle = `rgba(${v},${v},${v + 2},${0.1 + rnd() * 0.16})`;
      g.beginPath();
      g.arc(x, y, r, 0, Math.PI * 2);
      g.fill();
      g.strokeStyle = `rgba(226,226,230,${0.05 + rnd() * 0.1})`;
      g.lineWidth = 0.8;
      g.stroke();
    }
    return g.getImageData(0, 0, TEX_W, TEX_H).data;
  }

  const tex = buildTexture();

  function resize() {
    const rect = canvas.getBoundingClientRect();
    w = Math.max(180, rect.width);
    h = Math.max(180, rect.height);
    dpr = Math.min(2, window.devicePixelRatio || 1);
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const rnd = mulberry(77);
    stars = [];
    for (let i = 0; i < 140; i++) {
      stars.push({ x: rnd() * w, y: rnd() * h, r: rnd() * 1.2 + 0.1, a: 0.1 + rnd() * 0.35, p: rnd() * 6.28 });
    }
    needsRender = true;
  }

  function bodyVector(lat, lon) {
    const la = lat * D2R;
    const lo = lon * D2R;
    return [Math.cos(la) * Math.cos(lo), Math.cos(la) * Math.sin(lo), Math.sin(la)];
  }

  function project(b, cy, sy, cp, sp) {
    const x1 = cy * b[0] - sy * b[2];
    const y1 = b[1];
    const z1 = sy * b[0] + cy * b[2];
    return [x1, cp * y1 + sp * z1, -sp * y1 + cp * z1];
  }

  function render(time) {
    const R = Math.min(w, h) * 0.44;
    const cx = w / 2;
    const cy = h / 2;
    const cyw = Math.cos(yaw), syw = Math.sin(yaw);
    const cpi = Math.cos(pitch), spi = Math.sin(pitch);
    const sd = sun.lat * D2R;
    const sl = sun.lon * D2R;
    const s = [Math.cos(sd) * Math.cos(sl), Math.cos(sd) * Math.sin(sl), Math.sin(sd)];

    ctx.clearRect(0, 0, w, h);
    for (const st of stars) {
      const tw = 0.5 + 0.5 * Math.sin(time * 0.001 + st.p);
      ctx.fillStyle = `rgba(215,215,215,${(st.a * tw).toFixed(3)})`;
      ctx.beginPath();
      ctx.arc(st.x, st.y, st.r, 0, Math.PI * 2);
      ctx.fill();
    }

    const img = offCtx.createImageData(RES, RES);
    const buf = img.data;
    for (let j = 0; j < RES; j++) {
      const vy = ((j + 0.5) / RES) * 2 - 1;
      for (let i = 0; i < RES; i++) {
        const vx = ((i + 0.5) / RES) * 2 - 1;
        const r2 = vx * vx + vy * vy;
        const o = (j * RES + i) * 4;
        if (r2 > 1) {
          buf[o + 3] = 0;
          continue;
        }
        const vz = Math.sqrt(1 - r2);
        const cz = -vy;
        const bx = cyw * vx + syw * cpi * cz + syw * spi * vz;
        const by = cpi * cz - spi * vz;
        const bz = -syw * vx + cyw * cpi * cz + cyw * spi * vz;
        const lat = Math.asin(Math.max(-1, Math.min(1, bz)));
        const lon = Math.atan2(by, bx);
        let tu = Math.floor(((lon / (Math.PI * 2)) + 0.5) * TEX_W) % TEX_W;
        if (tu < 0) tu += TEX_W;
        let tv = Math.floor((0.5 - lat / Math.PI) * TEX_H);
        if (tv < 0) tv = 0;
        if (tv >= TEX_H) tv = TEX_H - 1;
        const t = (tv * TEX_W + tu) * 4;
        let dot = bx * s[0] + by * s[1] + bz * s[2];
        if (dot < 0) dot = 0;
        const light = 0.3 + 0.7 * dot;
        const limb = 0.72 + 0.28 * vz;
        const shade = light * limb;
        const glow = 16.0 * (1.0 - dot) * limb;
        buf[o] = tex[t] * shade;
        buf[o + 1] = tex[t + 1] * shade * 0.99;
        buf[o + 2] = tex[t + 2] * shade + glow;
        buf[o + 3] = 255;
      }
    }
    offCtx.putImageData(img, 0, 0);

    ctx.save();
    ctx.beginPath();
    ctx.arc(cx, cy, R, 0, Math.PI * 2);
    ctx.clip();
    ctx.imageSmoothingEnabled = true;
    ctx.drawImage(off, cx - R, cy - R, R * 2, R * 2);
    ctx.restore();

    markers = [];
    for (const site of sites) {
      const p = project(bodyVector(site.lat, site.lon), cyw, syw, cpi, spi);
      if (p[2] <= 0.02) continue;
      markers.push({ x: cx + p[0] * R, y: cy - p[1] * R, site, depth: p[2] });
    }
    markers.sort((a, b) => a.depth - b.depth);

    for (const m of markers) {
      if (m.site.id === selected || m.site.id === hovered) continue;
      ctx.fillStyle = `rgba(226,226,226,${0.2 + 0.35 * m.depth})`;
      ctx.beginPath();
      ctx.arc(m.x, m.y, 1.3 + m.depth * 0.6, 0, Math.PI * 2);
      ctx.fill();
    }

    for (const m of markers) {
      const active = m.site.id === selected;
      const hover = m.site.id === hovered;
      if (!active && !hover) continue;
      ctx.shadowColor = active ? "rgba(234,254,7,0.95)" : "rgba(46,150,245,0.95)";
      ctx.shadowBlur = active ? 16 : 10;
      ctx.fillStyle = active ? "#eafe07" : "#2e96f5";
      ctx.beginPath();
      ctx.arc(m.x, m.y, active ? 5 : 3.6, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.strokeStyle = active ? "rgba(234,254,7,0.6)" : "rgba(46,150,245,0.6)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(m.x, m.y, active ? 10 : 7, 0, Math.PI * 2);
      ctx.stroke();
      ctx.font = "600 10px \"Overpass\", system-ui, sans-serif";
      const label = m.site.name;
      const tw = ctx.measureText(label).width;
      let lx = m.x + 12;
      if (lx + tw + 10 > w) lx = m.x - tw - 22;
      const ly = Math.max(6, Math.min(h - 20, m.y - 8));
      ctx.fillStyle = "rgba(4,13,34,0.85)";
      ctx.fillRect(lx - 5, ly - 2, tw + 10, 18);
      ctx.strokeStyle = active ? "rgba(234,254,7,0.45)" : "rgba(46,150,245,0.45)";
      ctx.strokeRect(lx - 5, ly - 2, tw + 10, 18);
      ctx.fillStyle = active ? "#eafe07" : "#dbe9ff";
      ctx.textBaseline = "middle";
      ctx.fillText(label, lx + 1, ly + 7);
    }

    const sp = project(bodyVector(sun.lat, sun.lon), cyw, syw, cpi, spi);
    if (sp[2] > 0) {
      const sx = cx + sp[0] * R;
      const sy = cy - sp[1] * R;
      ctx.fillStyle = "#eafe07";
      ctx.shadowColor = "rgba(234,254,7,0.95)";
      ctx.shadowBlur = 18;
      ctx.beginPath();
      ctx.arc(sx, sy, 4, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;
    }
  }

  function loop(t) {
    if (!running) return;
    requestAnimationFrame(loop);
    if (t - last < 32) return;
    last = t;
    if (!dragging) {
      if (Math.abs(velY) > 0.0004 || Math.abs(velX) > 0.0004) {
        yaw += velY;
        pitch = Math.max(-1.25, Math.min(1.25, pitch + velX));
        velY *= 0.94;
        velX *= 0.94;
        needsRender = true;
      } else if (spin) {
        yaw += 0.0013;
        needsRender = true;
      }
    }
    if (needsRender) {
      render(t);
      needsRender = false;
    }
  }

  function nearest(x, y) {
    let best = null;
    let bestD = 16;
    for (const m of markers) {
      const d = Math.hypot(m.x - x, m.y - y);
      if (d < bestD) {
        best = m;
        bestD = d;
      }
    }
    return best;
  }

  function localPoint(ev) {
    const rect = canvas.getBoundingClientRect();
    return [ev.clientX - rect.left, ev.clientY - rect.top];
  }

  resize();
  const observer = new ResizeObserver(() => resize());
  observer.observe(canvas);

  canvas.addEventListener("pointerdown", (ev) => {
    dragging = true;
    moved = false;
    const pt = localPoint(ev);
    px = pt[0];
    py = pt[1];
    canvas.setPointerCapture(ev.pointerId);
    canvas.style.cursor = "grabbing";
  });

  canvas.addEventListener("pointermove", (ev) => {
    const pt = localPoint(ev);
    const x = pt[0];
    const y = pt[1];
    if (dragging) {
      const dx = x - px;
      const dy = y - py;
      yaw += dx * 0.0075;
      pitch = Math.max(-1.25, Math.min(1.25, pitch + dy * 0.0075));
      velY = dx * 0.0026;
      velX = dy * 0.0026;
      px = x;
      py = y;
      if (Math.abs(dx) + Math.abs(dy) > 2) moved = true;
      needsRender = true;
    } else {
      const hit = nearest(x, y);
      const id = hit ? hit.site.id : null;
      if (id !== hovered) {
        hovered = id;
        needsRender = true;
      }
      canvas.style.cursor = hit ? "pointer" : "grab";
    }
  });

  function endDrag(ev) {
    if (!dragging) return;
    dragging = false;
    canvas.style.cursor = "grab";
    if (!moved && opts.onSelect) {
      const pt = localPoint(ev);
      const hit = nearest(pt[0], pt[1]);
      if (hit) opts.onSelect(hit.site.id);
    }
  }

  canvas.addEventListener("pointerup", endDrag);
  canvas.addEventListener("pointercancel", endDrag);
  canvas.addEventListener("pointerleave", () => {
    if (hovered) {
      hovered = null;
      needsRender = true;
    }
  });

  requestAnimationFrame(loop);

  return {
    setSites(list) {
      sites = list || [];
      needsRender = true;
    },
    setSun(point) {
      if (point && Number.isFinite(point.lat) && Number.isFinite(point.lon)) {
        sun = point;
        needsRender = true;
      }
    },
    focus(lat, lon) {
      yaw = lon * D2R;
      pitch = Math.max(-1.2, Math.min(1.2, -lat * D2R));
      velX = 0;
      velY = 0;
      needsRender = true;
    },
    setSelected(id) {
      selected = id;
      needsRender = true;
    },
    setSpin(value) {
      spin = Boolean(value);
    },
    destroy() {
      running = false;
      observer.disconnect();
    },
  };
}
