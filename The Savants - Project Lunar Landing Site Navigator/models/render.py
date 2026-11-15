import io
import math

from PIL import Image


def _ramp(v):
    v = max(0.0, min(1.0, v))
    shadow = (6, 8, 14)
    mid = (58, 74, 96)
    lit = (255, 246, 224)
    if v <= 0.0:
        return shadow
    if v < 0.45:
        t = v / 0.45
        return tuple(int(shadow[k] + (mid[k] - shadow[k]) * t) for k in range(3))
    t = (v - 0.45) / 0.55
    return tuple(int(mid[k] + (lit[k] - mid[k]) * (t ** 0.75)) for k in range(3))


def illumination_png(trace, out_size=384):
    intensity = trace["intensity"]
    n = len(intensity)
    img = Image.new("RGB", (n, n))
    px = img.load()
    for j in range(n):
        row = intensity[j]
        for i in range(n):
            px[i, j] = _ramp(row[i])
    if out_size != n:
        img = img.resize((out_size, out_size), Image.BICUBIC)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def horizon_svg(sky, width=1080, height=260, max_el=12.0):
    bins = len(sky)
    pts = []
    for i in range(bins + 1):
        az = i % bins
        x = width * i / float(bins)
        el = max(-max_el, min(max_el, sky[az]))
        y = height - (el + max_el) / (2 * max_el) * height
        pts.append(f"{x:.1f},{y:.1f}")
    return pts
