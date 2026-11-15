import gzip
import io
import json
import math
import os
import threading
import urllib.parse
import urllib.request

from PIL import Image

from . import frames

DEM_BASE = ("https://trek.nasa.gov/moon/trekarcgis2/rest/services/"
            "{service}/ImageServer/exportImage")
SERVICES = {
    "LRO_LOLA_DEM_SPole875_5mp_v04": (-89.985, -86.5),
    "LRO_LOLA_DEM_SPole75_30mp_v04": (-89.985, -75.05),
    "LRO_LOLA_DEM_SPole45_100mp_v04": (-89.985, -45.05),
}
CACHE_DIR = None
_MEM = {}
_LOCK = threading.Lock()
MAX_LON_SPAN = 40.0


def configure(cache_dir):
    global CACHE_DIR
    CACHE_DIR = cache_dir


def m_per_deg(lat):
    la = math.radians(max(-89.999, min(89.999, lat)))
    return 111320.0 * math.cos(la), 111320.0


def enu_to_latlon(lat0, lon0, x_m, y_m):
    mlon, mlat = m_per_deg(lat0)
    lat = lat0 + y_m / mlat
    lon = lon0 + x_m / max(mlon, 0.3)
    lon = ((lon + 180.0) % 360.0) - 180.0
    return lat, lon


def service_for(lat):
    if lat > -75.0:
        return "LRO_LOLA_DEM_SPole45_100mp_v04" if lat >= -45.05 else None
    if lat >= -88.05:
        if lat <= -86.46:
            return "LRO_LOLA_DEM_SPole875_5mp_v04"
        return "LRO_LOLA_DEM_SPole75_30mp_v04"
    return None


def available(lat):
    return service_for(lat) is not None


def _fetch_window(lat0, lon0, radius_m, res_m, service):
    lat_min, lat_max = SERVICES[service]
    mlon, mlat = m_per_deg(lat0)
    lon_span = 2.0 * radius_m / max(mlon, 0.3)
    lat_span = 2.0 * radius_m / mlat
    if lon_span > MAX_LON_SPAN:
        lon_span = MAX_LON_SPAN
    if lon_span > lat_span * 20.0:
        lat_span = lon_span / 20.0
    lo = lon0 - lon_span / 2.0
    hi = lon0 + lon_span / 2.0
    lat_lo = max(lat_min, lat0 - lat_span / 2.0)
    lat_hi = min(lat_max, lat_lo + lat_span)
    if lat_hi <= lat_lo:
        lat_lo = max(lat_min, lat_hi - 0.05)
    px_x = max(48, min(1400, int(round(lon_span * mlon / res_m))))
    px_y = max(48, min(1400, int(round((lat_hi - lat_lo) * mlat / res_m))))
    params = {
        "bbox": f"{lo:.6f},{lat_lo:.6f},{hi:.6f},{lat_hi:.6f}",
        "bboxSR": "4326",
        "imageSR": "4326",
        "size": f"{px_x},{px_y}",
        "format": "tiff",
        "pixelType": "S16",
        "interpolation": "RSP_NearestNeighbor",
        "f": "image",
    }
    url = DEM_BASE.format(service=service) + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "lunar-site-planner/1.0"})
    with urllib.request.urlopen(req, timeout=55) as resp:
        raw = resp.read()
    img = Image.open(io.BytesIO(raw))
    if img.mode not in ("I", "I;16", "I;16S"):
        img = img.convert("I")
    return [{"box": (lo, lat_lo, hi, lat_hi), "w": img.size[0], "h": img.size[1],
             "data": list(img.getdata())}]


def _bilinear(window, lat, lon, fallback=None):
    lo, la, hi, ha = window["box"]
    w, h = window["w"], window["h"]
    if lon < lo or lon > hi:
        return fallback
    fx = (lon - lo) / (hi - lo) * (w - 1)
    fy = (ha - lat) / (ha - la) * (h - 1)
    x0 = int(math.floor(fx))
    y0 = int(math.floor(fy))
    if x0 < 0 or y0 < 0 or x0 >= w - 1 or y0 >= h - 1:
        return fallback
    tx = fx - x0
    ty = fy - y0
    d = window["data"]
    i = y0 * w + x0
    v00, v10 = d[i], d[i + 1]
    v01, v11 = d[i + w], d[i + w + 1]
    for v in (v00, v10, v01, v11):
        if v == 32767 or v == -32768:
            return fallback
    a = v00 + (v10 - v00) * tx
    b = v01 + (v11 - v01) * tx
    return a + (b - a) * ty


def _synthetic(lat0, lon0, radius_m, n):
    res = 2.0 * radius_m / (n - 1)
    seed = int(abs(lat0) * 7919 + abs(lon0) * 104729) % 2147483647
    state = seed or 12345

    def rnd():
        nonlocal state
        state = (1103515245 * state + 12345) % 2147483648
        return state / 2147483648.0

    craters = []
    for _ in range(28):
        r = 150.0 + 3850.0 * (rnd() ** 2.4)
        cx = (rnd() * 2.0 - 1.0) * radius_m * 1.05
        cy = (rnd() * 2.0 - 1.0) * radius_m * 1.05
        depth = r * (0.14 + 0.08 * rnd())
        ds = math.sqrt(cx * cx + cy * cy)
        if ds < r * 1.15:
            if ds < 1.0:
                ang = rnd() * 2.0 * math.pi
                cx, cy = math.cos(ang), math.sin(ang)
                ds = 1.0
            cx *= (r * 1.15) / ds
            cy *= (r * 1.15) / ds
        craters.append((cx, cy, r, depth))
    base = -1900.0 - 900.0 * math.sin(math.radians(lat0) * 2.2)
    grid = []
    for j in range(n):
        y = (j - (n - 1) / 2.0) * res
        row = []
        for i in range(n):
            x = (i - (n - 1) / 2.0) * res
            d = math.sqrt(x * x + y * y)
            z = base + 45.0 * math.sin(d / 1100.0) + 18.0 * math.sin(x / 240.0 + 0.7) * math.cos(y / 280.0)
            for (cx, cy, cr, dep) in craters:
                dd = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                if dd < cr:
                    z -= dep * (1.0 - (dd / cr) ** 2)
                z += 0.16 * dep * math.exp(-(((dd - cr) / (0.22 * cr)) ** 2))
            z += 170.0 * math.exp(-((d / 1250.0) ** 2)) + 55.0 * math.exp(-((d / 4200.0) ** 2))
            row.append(z)
        grid.append(row)
    return grid, res


def patch(lat, lon, radius_m=6000.0, n=257, res_m=48.0):
    key = (round(lat, 3), round(lon, 3), int(radius_m), int(n))
    with _LOCK:
        if key in _MEM:
            return _MEM[key]
    path = f"{CACHE_DIR}/dem_{key[0]}_{key[1]}_{key[2]}_{key[3]}.json.gz" if CACHE_DIR else None
    payload = None
    if path:
        try:
            with gzip.open(path, "rt") as fh:
                payload = json.load(fh)
        except (OSError, ValueError):
            payload = None
    if payload is None:
        payload = _build_patch(lat, lon, radius_m, n, res_m)
        if path:
            tmp = path + ".tmp"
            with gzip.open(tmp, "wt") as fh:
                json.dump(payload, fh, separators=(",", ":"))
            os.replace(tmp, path)
    with _LOCK:
        _MEM[key] = payload
    return payload


def _build_patch(lat, lon, radius_m, n, res_m):
    res = 2.0 * radius_m / (n - 1)
    grid = None
    source = "synthetic"
    service = service_for(lat)
    if service:
        try:
            windows = _fetch_window(lat, lon, radius_m, res_m, service)
            rows = []
            valid = 0
            total = 0
            for j in range(n):
                y = (j - (n - 1) / 2.0) * res
                row = []
                for i in range(n):
                    x = (i - (n - 1) / 2.0) * res
                    la, lo = enu_to_latlon(lat, lon, x, y)
                    v = None
                    for wnd in windows:
                        v = _bilinear(wnd, la, lo)
                        if v is not None:
                            break
                    total += 1
                    if v is None:
                        row.append(None)
                    else:
                        valid += 1
                        row.append(v)
                rows.append(row)
            if total and valid / total >= 0.45:
                grid = _fill_holes(rows)
                source = "lola"
        except Exception:
            grid = None
    if grid is None:
        grid, res = _synthetic(lat, lon, radius_m, n)
        source = "synthetic"
    flat = [v for row in grid for v in row]
    payload = {
        "lat": lat, "lon": lon, "n": n, "res_m": res,
        "heights": [[round(v, 1) for v in row] for row in grid],
        "source": source,
        "min_m": round(min(flat), 1), "max_m": round(max(flat), 1),
        "mean_m": round(sum(flat) / len(flat), 1),
        "center_m": round(grid[n // 2][n // 2], 1),
    }
    return payload


def _fill_holes(rows):
    n = len(rows)
    grid = [list(r) for r in rows]
    valid = [v for r in grid for v in r if v is not None]
    if not valid:
        raise ValueError("no data")
    mean = sum(valid) / len(valid)
    for _ in range(4):
        holes = []
        for j in range(n):
            for i in range(n):
                if grid[j][i] is None:
                    acc = 0.0
                    cnt = 0
                    for dj in (-1, 0, 1):
                        for di in (-1, 0, 1):
                            jj, ii = j + dj, i + di
                            if 0 <= jj < n and 0 <= ii < n and grid[jj][ii] is not None:
                                acc += grid[jj][ii]
                                cnt += 1
                    if cnt:
                        holes.append((j, i, acc / cnt))
        if not holes:
            break
        for j, i, v in holes:
            grid[j][i] = v
    for j in range(n):
        for i in range(n):
            if grid[j][i] is None:
                grid[j][i] = mean
    return grid
