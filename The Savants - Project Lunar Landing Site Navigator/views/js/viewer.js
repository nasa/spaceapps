function createSiteViewer(node, options) {
  const opts = options || {};
  const canvas = node;
  const ctx = canvas.getContext("2d");
  let yaw = 0;
  let pitch = -3;
  let fov = 62;
  let camX = 0;
  let camY = 0;
  let dragging = false;
  let lastX = 0;
  let lastY = 0;
  let seq = 0;
  let timer = null;
  let pending = false;
  let busy = false;
  let keys = new Set();
  let baseParams = null;
  let site = null;

  function hud() {
    const o = opts.hud;
    if (!o) return;
    if (o.compass) o.compass.style.transform = `rotate(${-yaw}deg)`;
    if (o.heading) o.heading.textContent = `${((yaw % 360) + 360) % 360 | 0}°`;
    if (o.pitch) o.pitch.textContent = `${pitch.toFixed(0)}°`;
    if (o.zoom) o.zoom.textContent = `${fov.toFixed(0)}°`;
    if (o.position) o.position.textContent = `${(camX / 1000).toFixed(2)} E · ${(camY / 1000).toFixed(2)} N km`;
  }

  function paint(loading) {
    const w = canvas.width;
    const h = canvas.height;
    if (loading) {
      ctx.fillStyle = "#04091a";
      ctx.fillRect(0, 0, w, h);
      const g = ctx.createLinearGradient(0, 0, w, 0);
      g.addColorStop(0, "rgba(46,150,245,0.05)");
      g.addColorStop(0.5, "rgba(46,150,245,0.22)");
      g.addColorStop(1, "rgba(46,150,245,0.05)");
      ctx.fillStyle = g;
      ctx.fillRect(0, h * 0.45, w, h * 0.1);
      ctx.fillStyle = "#a9c4e4";
      ctx.font = "600 12px Overpass, system-ui, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("resolving terrain…", w / 2, h * 0.52);
      ctx.textAlign = "left";
      return;
    }
    if (canvas.dataset.src) {
      const img = new Image();
      img.onload = () => {
        ctx.fillStyle = "#04091a";
        ctx.fillRect(0, 0, w, h);
        ctx.imageSmoothingEnabled = true;
        ctx.drawImage(img, 0, 0, w, h);
      };
      img.src = canvas.dataset.src;
    }
  }

  function request(immediate) {
    if (!site || !baseParams) return;
    clearTimeout(timer);
    const go = () => {
      const id = ++seq;
      const url = "/api/view?" + new URLSearchParams({
        ...baseParams,
        yaw: yaw.toFixed(2),
        pitch: pitch.toFixed(2),
        fov: fov.toFixed(2),
        cx: camX.toFixed(1),
        cy: camY.toFixed(1),
        w: String(Math.round(canvas.width)),
        h: String(Math.round(canvas.height)),
      });
      busy = true;
      pending = true;
      paint(true);
      fetch(url)
        .then((r) => (r.ok ? r.blob() : Promise.reject(new Error("view failed"))))
        .then((blob) => {
          if (id !== seq) return;
          busy = false;
          pending = false;
          canvas.dataset.src = URL.createObjectURL(blob);
          paint(false);
          if (opts.onMeta) opts.onMeta();
        })
        .catch(() => {
          if (id !== seq) return;
          busy = false;
          pending = false;
          paint(false);
        });
    };
    if (immediate) go();
    else timer = setTimeout(go, 110);
  }

  function move(dx, dy) {
    const scale = (fov / canvas.width) * 12.0;
    camX += dx * scale;
    camY += dy * scale;
    const lim = 9000;
    if (camX > lim) camX = lim;
    if (camX < -lim) camX = -lim;
    if (camY > lim) camY = lim;
    if (camY < -lim) camY = -lim;
  }

  canvas.addEventListener("pointerdown", (ev) => {
    dragging = true;
    lastX = ev.clientX;
    lastY = ev.clientY;
    canvas.setPointerCapture(ev.pointerId);
    canvas.style.cursor = "grabbing";
  });

  canvas.addEventListener("pointermove", (ev) => {
    if (!dragging) return;
    const dx = ev.clientX - lastX;
    const dy = ev.clientY - lastY;
    lastX = ev.clientX;
    lastY = ev.clientY;
    yaw = (yaw + dx * 0.28 + 360) % 360;
    pitch = Math.max(-35, Math.min(35, pitch + dy * 0.22));
    hud();
    request(false);
  });

  function endDrag() {
    dragging = false;
    canvas.style.cursor = "grab";
  }

  canvas.addEventListener("pointerup", endDrag);
  canvas.addEventListener("pointercancel", endDrag);

  canvas.addEventListener("wheel", (ev) => {
    ev.preventDefault();
    fov = Math.max(14, Math.min(100, fov + Math.sign(ev.deltaY) * 5));
    hud();
    request(false);
  }, { passive: false });

  window.addEventListener("keydown", (ev) => {
    const k = ev.key.toLowerCase();
    if (["w", "a", "s", "d", "arrowup", "arrowdown", "arrowleft", "arrowright"].includes(k)) {
      keys.add(k);
      ev.preventDefault();
    }
  });

  window.addEventListener("keyup", (ev) => {
    keys.delete(ev.key.toLowerCase());
  });

  let moveTimer = null;
  setInterval(() => {
    if (!keys.size || busy) return;
    let dx = 0;
    let dy = 0;
    if (keys.has("w") || keys.has("arrowup")) dy += 1;
    if (keys.has("s") || keys.has("arrowdown")) dy -= 1;
    if (keys.has("d") || keys.has("arrowright")) dx += 1;
    if (keys.has("a") || keys.has("arrowleft")) dx -= 1;
    if (!dx && !dy) return;
    const fwd = [Math.sin((yaw * Math.PI) / 180), Math.cos((yaw * Math.PI) / 180)];
    const rgt = [fwd[1], -fwd[0]];
    move(fwd[0] * dy + rgt[0] * dx, fwd[1] * dy + rgt[1] * dx);
    hud();
    if (!moveTimer) {
      moveTimer = setTimeout(() => {
        moveTimer = null;
      }, 120);
      request(false);
    }
  }, 90);

  return {
    open(nextSite, params) {
      site = nextSite;
      baseParams = params;
      yaw = 0;
      pitch = -3;
      fov = 62;
      camX = 0;
      camY = 0;
      hud();
      request(true);
    },
    refresh() {
      request(true);
    },
    setHud(h) {
      opts.hud = h;
      hud();
    },
    isBusy() {
      return busy || pending;
    },
  };
}
