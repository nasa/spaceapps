import math

MOON_RADIUS_M = 1737400.0
SUN_RADIUS_DEG = 0.266
EARTH_RADIUS_DEG = 0.953


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


def skyline(data, bins=720):
    n = data["n"]
    res = data["res_m"]
    grid = data["heights"]
    radius = (n - 1) / 2.0 * res
    h0 = data["center_m"]
    out = []
    step = res * 1.5
    radii = []
    r = max(step, 300.0)
    while r <= radius:
        radii.append(r)
        r *= 1.13
    for b in range(bins):
        az = 2.0 * math.pi * b / bins
        dx, dy = math.sin(az), math.cos(az)
        best = -90.0
        for rr in radii:
            h = _sample(grid, n, res, dx * rr, dy * rr)
            if h is None:
                continue
            drop = rr * rr / (2.0 * MOON_RADIUS_M)
            th = math.degrees(math.atan2(h - h0 - drop, rr))
            if th > best:
                best = th
        out.append(best)
    return out


def horizon_at(sky, az_deg):
    bins = len(sky)
    f = (az_deg % 360.0) / 360.0 * bins
    i = int(f) % bins
    j = (i + 1) % bins
    return sky[i] + (sky[j] - sky[i]) * (f - int(f))


def sun_visible(sky, az, el, radius=SUN_RADIUS_DEG):
    return el + radius > horizon_at(sky, az)


def earth_visible(sky, az, el, radius=EARTH_RADIUS_DEG):
    return el + radius > horizon_at(sky, az)


def _bilinear(grid, n, fx, fy):
    if fx < 0 or fy < 0 or fx > n - 1 or fy > n - 1:
        return None
    x0 = min(int(fx), n - 2)
    y0 = min(int(fy), n - 2)
    tx = fx - x0
    ty = fy - y0
    r0 = grid[y0]
    r1 = grid[y0 + 1]
    a = r0[x0] + (r0[x0 + 1] - r0[x0]) * tx
    b = r1[x0] + (r1[x0 + 1] - r1[x0]) * tx
    return a + (b - a) * ty


def raytrace(data, sun_az, sun_el, out_n=192):
    n = data["n"]
    res = data["res_m"]
    grid = data["heights"]
    h0 = data["center_m"]
    radius = (n - 1) / 2.0 * res
    step = n // out_n
    if step < 1:
        step = 1
    az = math.radians(sun_az)
    dx, dy = math.sin(az), math.cos(az)
    tan_el = math.tan(math.radians(sun_el))
    lit = []
    intensities = []
    lit_count = 0
    for j in range(0, n, step):
        row_lit = []
        row_int = []
        for i in range(0, n, step):
            x = (i - (n - 1) / 2.0) * res
            y = (j - (n - 1) / 2.0) * res
            h = grid[j][i]
            visible = 1.0
            if sun_el <= 0.0:
                visible = 0.0
            else:
                r = res * 1.2
                while r < radius:
                    hh = _bilinear(grid, n, (x + dx * r) / res + (n - 1) / 2.0,
                                   (y + dy * r) / res + (n - 1) / 2.0)
                    if hh is not None:
                        drop = r * r / (2.0 * MOON_RADIUS_M)
                        if hh - h - drop > r * tan_el:
                            visible = 0.0
                            break
                    r *= 1.18
            grad_x = (_bilinear(grid, n, i + 1, j) or h) - (_bilinear(grid, n, i - 1, j) or h)
            grad_y = (_bilinear(grid, n, i, j + 1) or h) - (_bilinear(grid, n, i, j - 1) or h)
            nx, ny, nz = -grad_x / (2.0 * res), -grad_y / (2.0 * res), 1.0
            norm = math.sqrt(nx * nx + ny * ny + nz * nz)
            inc = (nx * dx * math.cos(math.radians(sun_el))
                   + ny * dy * math.cos(math.radians(sun_el))
                   + nz * math.sin(math.radians(sun_el))) / norm
            inten = visible * max(0.0, inc)
            row_lit.append(visible)
            row_int.append(inten)
            if visible > 0:
                lit_count += 1
        lit.append(row_lit)
        intensities.append(row_int)
    total = sum(len(r) for r in lit)
    flat = [v for row in intensities for v in row]
    return {
        "lit": lit, "intensity": intensities,
        "lit_fraction": lit_count / total if total else 0.0,
        "mean_intensity": sum(flat) / len(flat) if flat else 0.0,
        "size": len(lit),
    }
