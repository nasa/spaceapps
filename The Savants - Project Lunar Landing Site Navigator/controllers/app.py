import io
import json
import math
import mimetypes
import os
import re
import sys
import threading
import traceback
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from models import ephemeris, horizon, metrics, render, sites, terrain, frames, viewer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIEW = os.path.join(ROOT, "views")
CACHE = os.path.join(ROOT, "data", "cache")
RADIUS_M = 12000.0
GRID_N = 257
TERRAIN_RES = 94.0

terrain.configure(CACHE)
from models import horizons
horizons.configure(CACHE)
os.makedirs(CACHE, exist_ok=True)

_SCENARIOS = {}
_TRACES = {}
_SKY = {}
_PATCHES = {}
_LOCK = threading.Lock()


def parse_time(text):
    if not text:
        return datetime.now(timezone.utc).replace(second=0, microsecond=0)
    text = text.strip().replace(" ", "T")
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(text[:len(fmt) + 2], fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"bad time: {text}")


def site_from(params):
    site_id = params.get("site_id", [None])[0]
    lat = params.get("lat", [None])[0]
    lon = params.get("lon", [None])[0]
    return sites.resolve(site_id, lat, lon)


def get_patch(site):
    key = (round(site["lat"], 3), round(site["lon"], 3))
    with _LOCK:
        if key in _PATCHES:
            return _PATCHES[key]
    data = terrain.patch(site["lat"], site["lon"], RADIUS_M, GRID_N, TERRAIN_RES)
    with _LOCK:
        _PATCHES[key] = data
    return data


def get_sky(data):
    key = (round(data["lat"], 3), round(data["lon"], 3), data["source"], data["min_m"], data["max_m"])
    with _LOCK:
        if key in _SKY:
            return _SKY[key]
    sky = horizon.skyline(data, 720)
    with _LOCK:
        _SKY[key] = sky
    return sky


def phase_name(sep):
    if sep > 160:
        return "new"
    if sep > 110:
        return "crescent"
    if sep > 70:
        return "quarter"
    if sep > 20:
        return "gibbous"
    return "full"


def build_scenario(site, start, hours, step):
    data = get_patch(site)
    sky = get_sky(data)
    series = ephemeris.series(site["lat"], site["lon"], data["center_m"], start, hours, step)
    summary = metrics.analyse(series, sky)
    daily = metrics.daily(series, sky, 24.0)
    n = len(series["minutes"])
    stride = max(1, int(math.ceil(n / 720.0)))
    idx = list(range(0, n, stride))
    t = []
    s_az, s_el, s_hz, s_lit = [], [], [], []
    e_az, e_el, e_hz, e_lit = [], [], [], []
    for i in idx:
        az = series["sun_az"][i]
        el = series["sun_el"][i]
        eaz = series["earth_az"][i]
        eel = series["earth_el"][i]
        shz = horizon.horizon_at(sky, az)
        ehz = horizon.horizon_at(sky, eaz)
        frac = max(0.0, min(1.0, (el - shz) / max(0.05, series["sun_diam"][i]) + 0.5))
        t.append(round(series["minutes"][i] / 60.0, 3))
        s_az.append(round(az, 3))
        s_el.append(round(el, 4))
        s_hz.append(round(shz, 4))
        s_lit.append(round(frac, 4))
        e_az.append(round(eaz, 3))
        e_el.append(round(eel, 4))
        e_hz.append(round(ehz, 4))
        e_lit.append(1 if horizon.earth_visible(sky, eaz, eel, series["earth_diam"][i] / 2.0) else 0)
    now_state = ephemeris.state(site["lat"], site["lon"], data["center_m"], frames.to_days(start))
    sep = now_state["separation"]
    return {
        "site": site,
        "start": start.isoformat(),
        "hours": hours,
        "step_minutes": step,
        "terrain": {
            "source": data["source"],
            "min_m": data["min_m"],
            "max_m": data["max_m"],
            "mean_m": data["mean_m"],
            "center_m": data["center_m"],
            "res_m": round(data["res_m"], 1),
            "radius_m": RADIUS_M,
            "grid": data["n"],
        },
        "skyline": [round(v, 4) for v in sky],
        "series": {
            "hours": t,
            "sun_az": s_az,
            "sun_el": s_el,
            "sun_horizon": s_hz,
            "sun_frac": s_lit,
            "earth_az": e_az,
            "earth_el": e_el,
            "earth_horizon": e_hz,
            "earth_lit": e_lit,
            "stride": stride,
        },
        "summary": {
            "illumination": round(summary["illumination"], 5),
            "earth_visibility": round(summary["earth_visibility"], 5),
            "longest_sun_hours": round(summary["longest_sun_hours"], 3),
            "longest_earth_hours": round(summary["longest_earth_hours"], 3),
            "next_sun_transition_h": summary["next_sun_transition_h"],
            "next_earth_transition_h": summary["next_earth_transition_h"],
            "insolation_wh_m2": round(summary["insolation_wh_m2"], 1),
            "max_sun_el": round(summary["max_sun_el"], 3),
            "min_sun_el": round(summary["min_sun_el"], 3),
            "mean_sun_el": round(summary["mean_sun_el"], 3),
            "sun_up_now": summary["sun_mask"][0],
            "earth_up_now": summary["earth_mask"][0],
            "horizon_at_sun": round(summary["horizon_at_sun"], 3),
            "horizon_at_earth": round(summary["horizon_at_earth"], 3),
            "source": series["source"],
        },
        "now": {
            "sun_az": round(now_state["sun"]["az"], 3),
            "sun_el": round(now_state["sun"]["el"], 3),
            "earth_az": round(now_state["earth"]["az"], 3),
            "earth_el": round(now_state["earth"]["el"], 3),
            "earth_distance_km": round(now_state["earth"]["dist_km"], 1),
            "sun_distance_au": round(now_state["sun"]["dist_km"] / 149597870.7, 5),
            "separation": round(sep, 3),
            "phase": phase_name(sep),
            "phase_fraction": round((1.0 + math.cos(math.radians(sep))) / 2.0, 4),
            "subsolar": now_state["subsolar"],
            "subearth": now_state["subearth"],
        },
        "daily": daily,
    }


def cached_scenario(params):
    site = site_from(params)
    start = parse_time(params.get("start", [None])[0])
    hours = float(params.get("hours", ["720"])[0])
    step = int(float(params.get("step", ["20"])[0]))
    hours = max(1.0, min(24.0 * 400.0, hours))
    step = max(1, min(240, step))
    key = (site["id"], round(site["lat"], 3), round(site["lon"], 3), start.isoformat(), hours, step)
    with _LOCK:
        if key in _SCENARIOS:
            return _SCENARIOS[key]
    payload = build_scenario(site, start, hours, step)
    with _LOCK:
        if len(_SCENARIOS) > 32:
            _SCENARIOS.clear()
        _SCENARIOS[key] = payload
    return payload


def get_trace(data, lat, lon, az, el):
    key = (round(lat, 3), round(lon, 3), round(az, 1), round(el, 2), data["source"])
    with _LOCK:
        trace = _TRACES.get(key)
    if trace is None:
        trace = horizon.raytrace(data, az, el, 128)
        with _LOCK:
            if len(_TRACES) > 48:
                _TRACES.clear()
            _TRACES[key] = trace
    return trace


def site_view(params):
    site = site_from(params)
    start = parse_time(params.get("start", [None])[0])
    minute = float(params.get("minute", ["0"])[0])
    yaw = float(params.get("yaw", ["0"])[0])
    pitch = float(params.get("pitch", ["0"])[0])
    fov = float(params.get("fov", ["62"])[0])
    cam_x = float(params.get("cx", ["0"])[0])
    cam_y = float(params.get("cy", ["0"])[0])
    w = int(float(params.get("w", ["336"])[0]))
    h = int(float(params.get("h", ["210"])[0]))
    w = max(160, min(960, w))
    h = max(100, min(600, h))
    data = get_patch(site)
    d = frames.to_days(start) + minute / 1440.0
    st = ephemeris.state(site["lat"], site["lon"], data["center_m"], d)
    az = st["sun"]["az"]
    el = st["sun"]["el"]
    eaz = st["earth"]["az"]
    eel = st["earth"]["el"]
    trace = get_trace(data, site["lat"], site["lon"], az, el)
    sky = get_sky(data)
    img = viewer.render(data, sky, trace, cam_x, cam_y, yaw, pitch, fov,
                        az, el, eaz, eel, w, h)
    return img, {
        "sun_az": round(az, 3), "sun_el": round(el, 3),
        "earth_az": round(eaz, 3), "earth_el": round(eel, 3),
        "terrain_source": data["source"],
        "center_elevation_m": data["center_m"],
        "lit_fraction": round(trace["lit_fraction"], 4),
        "subsolar": st["subsolar"], "subearth": st["subearth"],
        "separation": round(st["separation"], 3),
    }


def illumination(params):
    site = site_from(params)
    start = parse_time(params.get("start", [None])[0])
    minute = float(params.get("minute", ["0"])[0])
    size = int(float(params.get("size", ["384"])[0]))
    data = get_patch(site)
    d = frames.to_days(start) + minute / 1440.0
    st = ephemeris.state(site["lat"], site["lon"], data["center_m"], d)
    az = st["sun"]["az"]
    el = st["sun"]["el"]
    key = (round(site["lat"], 3), round(site["lon"], 3), round(az, 1), round(el, 2), data["source"])
    with _LOCK:
        trace = _TRACES.get(key)
    if trace is None:
        trace = horizon.raytrace(data, az, el, 128)
        with _LOCK:
            if len(_TRACES) > 48:
                _TRACES.clear()
            _TRACES[key] = trace
    stats = {
        "sun_az": round(az, 3),
        "sun_el": round(el, 3),
        "lit_fraction": round(trace["lit_fraction"], 4),
        "mean_intensity": round(trace["mean_intensity"], 4),
        "terrain_source": data["source"],
        "center_elevation_m": data["center_m"],
        "sun_up": el > 0,
        "subsolar": st["subsolar"],
        "subearth": st["subearth"],
        "separation": round(st["separation"], 3),
    }
    return trace, stats, size


MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "LunarSitePlanner/1.0"

    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, payload, code=200):
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self._send(code, body, "application/json; charset=utf-8")

    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            path = parsed.path
            params = parse_qs(parsed.query)
            if path == "/" or path == "/index.html":
                return self._static("index.html")
            if path.startswith("/static/"):
                return self._static(unquote(path[len("/static/"):]))
            if path == "/api/sites":
                out = []
                for s in sites.catalogue():
                    item = dict(s)
                    item["dem"] = "lola" if terrain.available(s["lat"]) else "synthetic"
                    out.append(item)
                return self._json({"sites": out})
            if path == "/api/scenario":
                return self._json(cached_scenario(params))
            if path == "/api/compare":
                items = json.loads(params.get("items", ["[]"])[0])
                rows = []
                for item in items[:8]:
                    sub = {k: [str(v)] for k, v in item.items()}
                    payload = cached_scenario(sub)
                    rows.append({
                        "site": payload["site"]["name"],
                        "lat": payload["site"]["lat"],
                        "lon": payload["site"]["lon"],
                        "start": payload["start"],
                        "illumination": payload["summary"]["illumination"],
                        "earth_visibility": payload["summary"]["earth_visibility"],
                        "longest_sun_hours": payload["summary"]["longest_sun_hours"],
                        "insolation_wh_m2": payload["summary"]["insolation_wh_m2"],
                        "max_sun_el": payload["summary"]["max_sun_el"],
                        "terrain": payload["terrain"]["source"],
                    })
                return self._json({"rows": rows})
            if path == "/api/phase":
                kind = params.get("kind", ["new"])[0]
                site = site_from(params)
                start = parse_time(params.get("start", [None])[0])
                span = 34
                samples = span * 24
                d0 = frames.to_days(start)
                base = ephemeris.state(site["lat"], site["lon"], 0.0, d0)
                seps = []
                for i in range(samples + 1):
                    st = ephemeris.state(site["lat"], site["lon"], 0.0, d0 + i / 24.0)
                    seps.append(st["separation"])
                best = 0
                if kind == "new":
                    best = max(range(len(seps)), key=lambda i: seps[i])
                elif kind == "full":
                    best = min(range(len(seps)), key=lambda i: seps[i])
                elif kind in ("first", "last"):
                    want_down = kind == "first"
                    for i in range(1, len(seps)):
                        a, b = seps[i - 1], seps[i]
                        if (a - 90.0) * (b - 90.0) <= 0.0 and a != b and (b < a) == want_down:
                            best = i
                            break
                when = start + timedelta(hours=best)
                return self._json({
                    "kind": kind,
                    "time": when.isoformat(),
                    "separation": round(seps[best], 3),
                    "illuminated": round((1.0 + math.cos(math.radians(seps[best]))) / 2.0, 4),
                })
            if path == "/api/view":
                img, meta = site_view(params)
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                return self._send(200, buf.getvalue(), "image/png",
                                  {"X-Terrain": meta["terrain_source"]})
            if path == "/api/viewmeta":
                img, meta = site_view(params)
                return self._json(meta)
            if path == "/api/illumination":
                trace, stats, size = illumination(params)
                fmt = params.get("format", ["png"])[0]
                if fmt == "json":
                    return self._json(stats)
                png = render.illumination_png(trace, size)
                return self._send(200, png, "image/png", {"X-Terrain": stats["terrain_source"]})
            if path == "/api/health":
                return self._json({"ok": True, "cache": CACHE, "coverage": horizons.coverage(),
                                   "scenarios": len(_SCENARIOS), "patches": len(_PATCHES)})
            if path == "/api/warm":
                start = parse_time(params.get("start", [None])[0])
                hours = float(params.get("hours", ["720"])[0])
                threading.Thread(target=lambda: ephemeris.warm(start, hours), daemon=True).start()
                return self._json({"warming": True, "start": start.isoformat(), "hours": hours})
            return self._json({"error": "not found", "path": path}, 404)
        except KeyError as exc:
            return self._json({"error": f"unknown site: {exc}"}, 400)
        except ValueError as exc:
            return self._json({"error": str(exc)}, 400)
        except Exception as exc:
            traceback.print_exc()
            return self._json({"error": f"{type(exc).__name__}: {exc}"}, 500)

    def _static(self, rel):
        rel = rel.replace("\\", "/")
        if ".." in rel.split("/"):
            return self._json({"error": "bad path"}, 400)
        target = os.path.normpath(os.path.join(VIEW, rel or "index.html"))
        if not target.startswith(VIEW + os.sep) and target != VIEW:
            return self._json({"error": "bad path"}, 400)
        if not os.path.isfile(target):
            return self._json({"error": "missing asset", "asset": rel}, 404)
        with open(target, "rb") as fh:
            body = fh.read()
        ext = os.path.splitext(target)[1]
        ctype = MIME.get(ext) or mimetypes.guess_type(target)[0] or "application/octet-stream"
        self._send(200, body, ctype)


def serve(port=8765, host="127.0.0.1"):
    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    stamp = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    threading.Thread(target=lambda: ephemeris.warm(stamp, 720), daemon=True).start()
    print(f"lunar site planner listening on http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
