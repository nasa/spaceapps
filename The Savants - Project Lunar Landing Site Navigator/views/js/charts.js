const Charts = (() => {
  const C = {
    sun: "#eafe07",
    sunSoft: "rgba(234,254,7,0.26)",
    earth: "#2e96f5",
    earthSoft: "rgba(46,150,245,0.32)",
    grid: "rgba(46,150,245,0.14)",
    text: "#a9c4e4",
    terrainTop: "rgba(186,214,250,0.7)",
    terrainFill: "rgba(64,116,188,0.24)",
    axis: "rgba(46,150,245,0.32)",
  };

  function setup(canvas) {
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    const w = Math.max(320, Math.round(rect.width || canvas.parentElement.clientWidth || 640));
    const h = Number(canvas.getAttribute("height")) || 300;
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    canvas.style.height = h + "px";
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    return { ctx, w, h };
  }

  function niceStep(range, target) {
    const raw = range / Math.max(1, target);
    const mag = Math.pow(10, Math.floor(Math.log10(raw)));
    const norm = raw / mag;
    const step = norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 5 ? 5 : 10;
    return step * mag;
  }

  function fmtDeg(v, digits = 2) {
    const s = v >= 0 ? "+" : "\u2212";
    return s + Math.abs(v).toFixed(digits) + "\u00b0";
  }

  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  function labelBox(ctx, x, y, text, color) {
    ctx.font = "600 11px ui-sans-serif, system-ui, sans-serif";
    const w = ctx.measureText(text).width + 12;
    const h = 18;
    let bx = x + 9;
    let by = y - h - 6;
    if (bx + w > ctx.canvas.width) bx = x - w - 9;
    if (by < 2) by = y + 8;
    ctx.fillStyle = "rgba(4,13,34,0.9)";
    roundRect(ctx, bx, by, w, h, 5);
    ctx.fill();
    ctx.strokeStyle = color;
    ctx.globalAlpha = 0.55;
    ctx.stroke();
    ctx.globalAlpha = 1;
    ctx.fillStyle = color;
    ctx.fillText(text, bx + 6, by + 12.5);
  }

  function drawPanorama(canvas, scn, cur) {
    const { ctx, w, h } = setup(canvas);
    const sky = scn.skyline || [];
    const s = scn.series;
    const pad = { l: 46, r: 14, t: 16, b: 30 };
    const pw = w - pad.l - pad.r;
    const ph = h - pad.t - pad.b;

    let elMin = -6;
    let elMax = 8;
    for (const v of sky) {
      elMin = Math.min(elMin, v - 0.5);
      elMax = Math.max(elMax, v + 1.5);
    }
    for (const v of s.sun_el) elMax = Math.max(elMax, v + 1.5);
    elMax = Math.min(elMax, 92);
    elMin = Math.max(elMin, -30);

    const xOf = (az) => pad.l + (az / 360) * pw;
    const yOf = (el) => pad.t + ph - ((el - elMin) / (elMax - elMin)) * ph;

    const grad = ctx.createLinearGradient(0, pad.t, 0, pad.t + ph);
    grad.addColorStop(0, "#082048");
    grad.addColorStop(1, "#030b1e");
    ctx.fillStyle = grad;
    ctx.fillRect(pad.l, pad.t, pw, ph);

    const step = niceStep(elMax - elMin, 6);
    ctx.font = "10.5px ui-sans-serif, system-ui, sans-serif";
    ctx.textBaseline = "middle";
    for (let e = Math.ceil(elMin / step) * step; e <= elMax; e += step) {
      const y = yOf(e);
      ctx.strokeStyle = Math.abs(e) < 1e-9 ? "rgba(46,150,245,0.5)" : C.grid;
      ctx.beginPath();
      ctx.moveTo(pad.l, y);
      ctx.lineTo(pad.l + pw, y);
      ctx.stroke();
      ctx.fillStyle = C.text;
      ctx.textAlign = "right";
      ctx.fillText(`${e.toFixed(step < 1 ? 1 : 0)}\u00b0`, pad.l - 8, y);
    }

    const dirs = [["N", 0], ["E", 90], ["S", 180], ["W", 270], ["N", 360]];
    ctx.textAlign = "center";
    for (const [name, az] of dirs) {
      const x = xOf(az);
      ctx.strokeStyle = C.grid;
      ctx.beginPath();
      ctx.moveTo(x, pad.t);
      ctx.lineTo(x, pad.t + ph);
      ctx.stroke();
      ctx.fillStyle = C.text;
      ctx.fillText(name, x, pad.t + ph + 14);
    }

    if (sky.length) {
      ctx.beginPath();
      ctx.moveTo(xOf(0), yOf(sky[0]));
      for (let i = 1; i < sky.length; i++) {
        ctx.lineTo(xOf((i / (sky.length - 1)) * 360), yOf(sky[i]));
      }
      ctx.lineTo(pad.l + pw, pad.t + ph + 2);
      ctx.lineTo(pad.l, pad.t + ph + 2);
      ctx.closePath();
      ctx.fillStyle = C.terrainFill;
      ctx.fill();
      ctx.strokeStyle = C.terrainTop;
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.moveTo(xOf(0), yOf(sky[0]));
      for (let i = 1; i < sky.length; i++) {
        ctx.lineTo(xOf((i / (sky.length - 1)) * 360), yOf(sky[i]));
      }
      ctx.stroke();
    }

    const n = s.sun_el.length;
    const stride = Math.max(1, Math.ceil(n / 420));
    ctx.fillStyle = C.sunSoft;
    for (let i = 0; i < n; i += stride) {
      const x = xOf(s.sun_az[i]);
      const y = yOf(s.sun_el[i]);
      ctx.beginPath();
      ctx.arc(x, y, 1.7, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.fillStyle = C.earthSoft;
    for (let i = 0; i < n; i += stride) {
      const x = xOf(s.earth_az[i]);
      const y = yOf(s.earth_el[i]);
      ctx.beginPath();
      ctx.arc(x, y, 1.7, 0, Math.PI * 2);
      ctx.fill();
    }

    const drawBody = (az, el, color, name, below) => {
      const x = xOf(((az % 360) + 360) % 360);
      const y = yOf(el);
      if (below) {
        ctx.strokeStyle = color;
        ctx.globalAlpha = 0.7;
        ctx.setLineDash([3, 3]);
        ctx.beginPath();
        ctx.arc(x, y, 7, 0, Math.PI * 2);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.globalAlpha = 1;
      } else {
        ctx.shadowColor = color;
        ctx.shadowBlur = 14;
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(x, y, 5.5, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;
      }
      labelBox(ctx, x, y, `${name} ${fmtDeg(el)}`, color);
    };

    if (cur) {
      drawBody(cur.sun_az, cur.sun_el, C.sun, "Sun", cur.sun_el < cur.sun_horizon);
      drawBody(cur.earth_az, cur.earth_el, C.earth, "Earth", cur.earth_el < cur.earth_horizon);
    }

    ctx.strokeStyle = C.axis;
    ctx.lineWidth = 1;
    ctx.strokeRect(pad.l + 0.5, pad.t + 0.5, pw, ph);
  }

  function drawTimeline(canvas, scn, curIndex) {
    const { ctx, w, h } = setup(canvas);
    const s = scn.series;
    const n = s.sun_el.length;
    const pad = { l: 46, r: 14, t: 14, b: 34 };
    const bandH = 13;
    const pw = w - pad.l - pad.r;
    const ph = h - pad.t - pad.b - bandH * 2 - 8;
    const hours = scn.hours;

    let elMin = Math.min(-2, Math.floor(Math.min(...s.sun_el)) - 1);
    let elMax = Math.max(5, Math.ceil(Math.max(...s.sun_el)) + 1);
    elMin = Math.max(elMin, -35);
    elMax = Math.min(elMax, 92);
    if (elMax - elMin < 4) elMax = elMin + 4;

    const xOf = (hh) => pad.l + (hh / hours) * pw;
    const yOf = (el) => pad.t + ph - ((el - elMin) / (elMax - elMin)) * ph;
    const iToX = (i) => xOf(s.hours[i]);
    const hoursPerIndex = hours / Math.max(1, n - 1);

    const grad = ctx.createLinearGradient(0, pad.t, 0, pad.t + ph);
    grad.addColorStop(0, "#082048");
    grad.addColorStop(1, "#030b1e");
    ctx.fillStyle = grad;
    ctx.fillRect(pad.l, pad.t, pw, ph);

    const step = niceStep(elMax - elMin, 6);
    ctx.font = "10.5px ui-sans-serif, system-ui, sans-serif";
    ctx.textBaseline = "middle";
    for (let e = Math.ceil(elMin / step) * step; e <= elMax; e += step) {
      const y = yOf(e);
      ctx.strokeStyle = Math.abs(e) < 1e-9 ? "rgba(46,150,245,0.5)" : C.grid;
      ctx.beginPath();
      ctx.moveTo(pad.l, y);
      ctx.lineTo(pad.l + pw, y);
      ctx.stroke();
      ctx.fillStyle = C.text;
      ctx.textAlign = "right";
      ctx.fillText(`${e.toFixed(step < 1 ? 1 : 0)}\u00b0`, pad.l - 8, y);
    }

    ctx.beginPath();
    ctx.moveTo(iToX(0), yOf(s.sun_el[0]));
    for (let i = 1; i < n; i++) ctx.lineTo(iToX(i), yOf(s.sun_el[i]));
    for (let i = n - 1; i >= 0; i--) ctx.lineTo(iToX(i), yOf(s.sun_horizon[i]));
    ctx.closePath();
    ctx.fillStyle = "rgba(234,254,7,0.14)";
    ctx.fill();

    ctx.beginPath();
    ctx.moveTo(iToX(0), yOf(s.sun_horizon[0]));
    for (let i = 1; i < n; i++) ctx.lineTo(iToX(i), yOf(s.sun_horizon[i]));
    ctx.strokeStyle = "rgba(169,196,228,0.45)";
    ctx.setLineDash([4, 3]);
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.setLineDash([]);

    ctx.beginPath();
    ctx.moveTo(iToX(0), yOf(s.earth_el[0]));
    for (let i = 1; i < n; i++) ctx.lineTo(iToX(i), yOf(s.earth_el[i]));
    ctx.strokeStyle = C.earthSoft;
    ctx.lineWidth = 1.2;
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(iToX(0), yOf(s.sun_el[0]));
    for (let i = 1; i < n; i++) ctx.lineTo(iToX(i), yOf(s.sun_el[i]));
    ctx.strokeStyle = C.sun;
    ctx.lineWidth = 1.6;
    ctx.stroke();

    const bandY = pad.t + ph + 8;
    for (let i = 0; i < n; i++) {
      const x0 = iToX(i);
      const x1 = iToX(Math.min(n - 1, i + 1));
      const f = s.sun_frac[i];
      if (f > 0) {
        ctx.fillStyle = `rgba(234,254,7,${0.12 + 0.88 * f})`;
        ctx.fillRect(x0, bandY, Math.max(1, x1 - x0 + 0.6), bandH);
      }
    }
    for (let i = 0; i < n; i++) {
      const x0 = iToX(i);
      const x1 = iToX(Math.min(n - 1, i + 1));
      if (s.earth_lit[i]) {
        ctx.fillStyle = "rgba(46,150,245,0.9)";
        ctx.fillRect(x0, bandY + bandH + 3, Math.max(1, x1 - x0 + 0.6), bandH);
      }
    }
    ctx.fillStyle = C.text;
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";
    ctx.fillText("sun", pad.l - 8 - ctx.measureText("sun").width + 8, pad.t + ph + 14);
    ctx.fillText("earth", pad.l - 8 - ctx.measureText("earth").width + 8, pad.t + ph + bandH + 17);
    ctx.textAlign = "left";

    const hStep = niceStep(hours, Math.max(3, Math.floor(pw / 90)));
    ctx.textAlign = "center";
    for (let hh = 0; hh <= hours + 1e-6; hh += hStep) {
      const x = xOf(hh);
      ctx.strokeStyle = C.grid;
      ctx.beginPath();
      ctx.moveTo(x, pad.t + ph);
      ctx.lineTo(x, pad.t + ph + 4);
      ctx.stroke();
      ctx.fillStyle = C.text;
      ctx.fillText(hh === 0 ? "0" : `${hh}h`, x, pad.t + ph + 26);
    }

    if (curIndex != null) {
      const x = iToX(curIndex);
      ctx.strokeStyle = "rgba(255,255,255,0.42)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x, pad.t);
      ctx.lineTo(x, bandY + bandH * 2 + 3);
      ctx.stroke();
      const el = s.sun_el[Math.round(curIndex)];
      ctx.fillStyle = C.sun;
      ctx.beginPath();
      ctx.arc(x, yOf(el), 4, 0, Math.PI * 2);
      ctx.fill();
    }

    ctx.strokeStyle = C.axis;
    ctx.lineWidth = 1;
    ctx.strokeRect(pad.l + 0.5, pad.t + 0.5, pw, ph);

    return {
      indexAt(clientX) {
        const rect = canvas.getBoundingClientRect();
        const x = Math.min(Math.max(clientX - rect.left, pad.l), pad.l + pw);
        const hh = ((x - pad.l) / pw) * hours;
        return Math.max(0, Math.min(n - 1, Math.round(hh / hoursPerIndex)));
      },
    };
  }

  return { drawPanorama, drawTimeline, fmtDeg };
})();
