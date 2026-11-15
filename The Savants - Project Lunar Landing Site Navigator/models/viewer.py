import math
import threading

from PIL import Image

from . import horizon

MOON_RADIUS_M = 1737400.0
SUN_RADIUS_DEG = 0.266
EARTH_RADIUS_DEG = 0.953
_REGOLITH = (176.0, 172.0, 164.0)
_SKY = (3.0, 5.0, 13.0)
_AMBIENT = (13.0, 16.0, 26.0)
_NORMALS = {}
_LOCK = threading.Lock()


def _sample(grid, n, res, x, y):
    half = (n - 1) / 2.0
    fx = x / res + half
    fy = y / res + half
    if fx < 0.0 or fy < 0.0 or fx > n - 1 or fy > n - 1:
        return None
    x0 = int(fx)
    y0 = int(fy)
    if x0 >= n - 1:
        x0 = n - 2
    if y0 >= n - 1:
        y0 = n - 2
    tx = fx - x0
    ty = fy - y0
    r0 = grid[y0]
    r1 = grid[y0 + 1]
    a = r0[x0] + (r0[x0 + 1] - r0[x0]) * tx
    b = r1[x0] + (r1[x0 + 1] - r1[x0]) * tx
    return a + (b - a) * ty


def _normals(data):
    key = (data["lat"], data["lon"], data["n"], data["res_m"])
    with _LOCK:
        cached = _NORMALS.get(key)
    if cached is not None:
        return cached
    n = data["n"]
    res = data["res_m"]
    grid = data["heights"]
    nx = [0.0] * (n * n)
    ny = [0.0] * (n * n)
    nz = [1.0] * (n * n)
    for j in range(1, n - 1):
        row = grid[j]
        up = grid[j + 1]
        dn = grid[j - 1]
        base = j * n
        for i in range(1, n - 1):
            k = base + i
            gx = (row[i + 1] - row[i - 1]) / (2.0 * res)
            gy = (up[i] - dn[i]) / (2.0 * res)
            inv = 1.0 / math.sqrt(gx * gx + gy * gy + 1.0)
            nx[k] = -gx * inv
            ny[k] = -gy * inv
            nz[k] = inv
    with _LOCK:
        _NORMALS[key] = (nx, ny, nz)
    return nx, ny, nz


def _hash01(a, b):
    v = (a * 73856093) ^ (b * 19349663)
    v = (v ^ (v >> 13)) * 1274126177
    v = v ^ (v >> 16)
    return (v & 0xFFFFFF) / 16777215.0


def _disc(px, py, cx, cy, r, inner, outer, halo):
    d = math.hypot(px - cx, py - cy)
    if d <= r:
        t = 1.0 - d / max(r, 0.001)
        k = 0.35 + 0.65 * t
        return (inner[0] * k + outer[0] * (1.0 - k),
                inner[1] * k + outer[1] * (1.0 - k),
                inner[2] * k + outer[2] * (1.0 - k))
    if d <= r + halo:
        t = 1.0 - (d - r) / max(halo, 0.001)
        t = t * t
        return (outer[0] * t, outer[1] * t, outer[2] * t)
    return None


def render(data, sky, lit, cam_x, cam_y, yaw, pitch, fov,
           sun_az, sun_el, earth_az, earth_el, w=320, h=200):
    n = data["n"]
    res = data["res_m"]
    grid = data["heights"]
    half = (n - 1) / 2.0
    rmax = half * res
    nx, ny, nz = _normals(data)
    lit_n = lit["size"]
    lit_map = lit["intensity"]
    base_h = _sample(grid, n, res, cam_x, cam_y)
    if base_h is None:
        base_h = data["center_m"]
    eye = base_h + 1.75
    fov = max(12.0, min(110.0, fov))
    fov_v = fov * (h / float(w))
    deg_per_px = fov / float(w)
    deg_per_py = fov_v / float(h)
    saz = math.radians(sun_az)
    sel = math.radians(sun_el)
    sx = math.sin(saz) * math.cos(sel)
    sy = math.cos(saz) * math.cos(sel)
    sz = math.sin(sel)
    radii = []
    r = 12.0
    while r <= rmax:
        radii.append(r)
        r *= 1.05
    buf = bytearray(w * h * 3)
    mask = bytearray(w * h)
    peak = 0.001
    sun_px = None
    earth_px = None
    sun_hz = horizon.horizon_at(sky, sun_az) if sky else -90.0
    earth_hz = horizon.horizon_at(sky, earth_az) if sky else -90.0
    if sun_el - sun_hz > -SUN_RADIUS_DEG:
        sun_px = _project(sun_az, sun_el, yaw, pitch, fov, fov_v, w, h, deg_per_px, deg_per_py)
    if earth_el - earth_hz > -EARTH_RADIUS_DEG:
        earth_px = _project(earth_az, earth_el, yaw, pitch, fov, fov_v, w, h, deg_per_px, deg_per_py)
    for col in range(w):
        az = yaw + (col - (w - 1) / 2.0) * deg_per_px
        ar = math.radians(az)
        dx = math.sin(ar)
        dy = math.cos(ar)
        recs = []
        best = -90.0
        for rr in radii:
            hh = _sample(grid, n, res, cam_x + dx * rr, cam_y + dy * rr)
            if hh is None:
                break
            drop = rr * rr / (2.0 * MOON_RADIUS_M)
            ang = math.degrees(math.atan2(hh - eye - drop, rr))
            if ang > best:
                best = ang
                recs.append((rr, ang, hh))
        ptr = 0
        for row in range(h - 1, -1, -1):
            phi = pitch + ((h - 1) / 2.0 - row) * deg_per_py
            while ptr < len(recs) and recs[ptr][1] < phi:
                ptr += 1
            offset = (row * w + col) * 3
            if ptr >= len(recs):
                sx_sky = int(_hash01(int(az * 4.0) & 0xFFFF, int((phi + 90.0) * 4.0) & 0xFFFF) * 100000)
                if sx_sky > 99700:
                    b = 120 + (sx_sky % 130)
                    buf[offset] = b
                    buf[offset + 1] = b
                    buf[offset + 2] = min(255, b + 18)
                else:
                    buf[offset] = int(_SKY[0])
                    buf[offset + 1] = int(_SKY[1])
                    buf[offset + 2] = int(_SKY[2])
                continue
            rr, ang, hh = recs[ptr]
            hx = cam_x + dx * rr
            hy = cam_y + dy * rr
            fi = hx / res + half
            fj = hy / res + half
            if fi < 0.0:
                fi = 0.0
            if fj < 0.0:
                fj = 0.0
            if fi > n - 1:
                fi = n - 1
            if fj > n - 1:
                fj = n - 1
            ci = int(fi)
            cj = int(fj)
            k = cj * n + ci
            li = int(fi / (n - 1) * (lit_n - 1))
            lj = int(fj / (n - 1) * (lit_n - 1))
            if li < 0:
                li = 0
            if lj < 0:
                lj = 0
            if li > lit_n - 1:
                li = lit_n - 1
            if lj > lit_n - 1:
                lj = lit_n - 1
            iv = lit_map[lj][li]
            inc = nx[k] * sx + ny[k] * sy + nz[k] * sz
            if inc < 0.0:
                inc = 0.0
            lam = iv * (0.35 + 0.65 * inc)
            if lam > peak:
                peak = lam
            alb = 0.86 + 0.14 * max(0.0, min(1.0, (hh - data["min_m"]) / max(1.0, data["max_m"] - data["min_m"])))
            alb *= 0.93 + 0.14 * _hash01(int(fi) * 7 + int(fj) * 13, int(fj) * 31 + int(fi) * 17)
            micro = 0.82 + 0.36 * _hash01(int(fi) * 3, int(fj) * 5)
            lam *= micro
            mask[row * w + col] = 1
            buf[offset] = min(255, int(_REGOLITH[0] * lam * alb + _AMBIENT[0]))
            buf[offset + 1] = min(255, int(_REGOLITH[1] * lam * alb + _AMBIENT[1]))
            buf[offset + 2] = min(255, int(_REGOLITH[2] * lam * alb + _AMBIENT[2]))
    gain = 1.0
    if peak > 0.001:
        gain = min(3.2, 0.78 / peak)
    if gain > 1.02:
        for p in range(w * h):
            if not mask[p]:
                continue
            i = p * 3
            v = buf[i] * gain
            buf[i] = 255 if v > 255 else int(v)
            v = buf[i + 1] * gain
            buf[i + 1] = 255 if v > 255 else int(v)
            v = buf[i + 2] * gain
            buf[i + 2] = 255 if v > 255 else int(v)
    img = Image.frombytes("RGB", (w, h), bytes(buf))
    _draw_bodies(img, sun_px, earth_px, yaw, pitch, w, h, deg_per_px, deg_per_py)
    return img


def _project(az, el, yaw, pitch, fov, fov_v, w, h, deg_per_px, deg_per_py):
    daz = az - yaw
    if daz > 180.0:
        daz -= 360.0
    if daz < -180.0:
        daz += 360.0
    px = w / 2.0 + daz / deg_per_px
    py = h / 2.0 - (el - pitch) / deg_per_py
    if px < -80 or px > w + 80 or py < -80 or py > h + 80:
        return None
    return (px, py)


def _draw_bodies(img, sun_px, earth_px, yaw, pitch, w, h, deg_per_px, deg_per_py):
    px = img.load()
    if sun_px is not None:
        cx, cy = sun_px
        r = max(1.6, SUN_RADIUS_DEG / deg_per_px)
        halo = r * 9.0
        for yy in range(max(0, int(cy - halo)), min(h, int(cy + halo) + 1)):
            for xx in range(max(0, int(cx - halo)), min(w, int(cx + halo) + 1)):
                d = math.hypot(xx + 0.5 - cx, yy + 0.5 - cy)
                if d <= r:
                    px[xx, yy] = (255, 255, 252)
                elif d <= halo:
                    t = 1.0 - (d - r) / halo
                    t = t ** 2.6
                    cr, cg, cb = px[xx, yy]
                    px[xx, yy] = (min(255, int(cr + 250 * t)),
                                  min(255, int(cg + 246 * t)),
                                  min(255, int(cb + 210 * t)))
    if earth_px is not None:
        cx, cy = earth_px
        r = max(2.0, EARTH_RADIUS_DEG / deg_per_px)
        for yy in range(max(0, int(cy - r - 1)), min(h, int(cy + r + 2))):
            for xx in range(max(0, int(cx - r - 1)), min(w, int(cx + r + 2))):
                d = math.hypot(xx + 0.5 - cx, yy + 0.5 - cy)
                if d > r:
                    continue
                t = 1.0 - d / r
                if t > 0.55:
                    px[xx, yy] = (238, 240, 236)
                else:
                    px[xx, yy] = (44, 96, 176)
