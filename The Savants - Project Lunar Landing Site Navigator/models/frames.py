import math
from datetime import datetime, timezone, timedelta

J2000 = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
SECONDS_PER_DAY = 86400.0
MOON_RADIUS_KM = 1737.4
SUN_RADIUS_KM = 695700.0
EARTH_RADIUS_KM = 6378.137


def to_days(dt):
    return (dt - J2000).total_seconds() / SECONDS_PER_DAY


def from_days(d):
    return J2000 + timedelta(days=d)


def _rz(a):
    c, s = math.cos(a), math.sin(a)
    return ((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0))


def _rx(a):
    c, s = math.cos(a), math.sin(a)
    return ((1.0, 0.0, 0.0), (0.0, c, -s), (0.0, s, c))


def _mv(m, v):
    return (m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
            m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
            m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2])


def _mm(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def iau(d):
    T = d / 36525.0
    args = [
        125.045 - 0.0529921 * d,
        250.089 - 0.1059842 * d,
        260.008 + 13.0120009 * d,
        176.625 + 13.3407154 * d,
        357.529 + 0.9856003 * d,
        311.589 + 26.4057084 * d,
        134.963 + 13.0649930 * d,
        276.617 + 0.3287146 * d,
        34.226 + 1.7484877 * d,
        15.134 - 0.1589763 * d,
        119.743 + 0.0036096 * d,
        239.961 + 0.1643573 * d,
        25.053 + 12.9590088 * d,
    ]
    e = [math.radians(x) for x in args]
    s = [math.sin(x) for x in e]
    c = [math.cos(x) for x in e]
    a0 = math.radians(269.9949 + 0.0031 * T - 3.8787 * s[0] - 0.1204 * s[1] + 0.0700 * s[2]
                      - 0.0172 * s[3] + 0.0072 * s[5] - 0.0052 * s[9] + 0.0043 * s[12])
    d0 = math.radians(66.5392 + 0.0130 * T + 1.5419 * c[0] + 0.0239 * c[1] - 0.0278 * c[2]
                      + 0.0068 * c[3] - 0.0029 * c[5] + 0.0009 * c[6] + 0.0008 * c[9] - 0.0009 * c[12])
    W = math.radians(38.3213 + 13.17635815 * d - 1.4e-12 * d * d + 3.5610 * s[0] + 0.1208 * s[1]
                     - 0.0642 * s[2] + 0.0158 * s[3] + 0.0252 * s[4] - 0.0066 * s[5] - 0.0047 * s[6]
                     - 0.0046 * s[7] + 0.0028 * s[8] + 0.0052 * s[9] + 0.0040 * s[10]
                     + 0.0019 * s[11] - 0.0044 * s[12])
    return a0, d0, W


def to_body(v, d):
    a0, d0, W = iau(d)
    m = _mm(_mm(_rz(-W), _rx(d0 - math.pi / 2.0)), _rz(-(a0 + math.pi / 2.0)))
    return _mv(m, v)


def to_icrf(v, d):
    a0, d0, W = iau(d)
    m = _mm(_mm(_rz(a0 + math.pi / 2.0), _rx(math.pi / 2.0 - d0)), _rz(W))
    return _mv(m, v)


def site_vector(lat, lon, radius_km):
    la = math.radians(lat)
    lo = math.radians(lon)
    return (radius_km * math.cos(la) * math.cos(lo),
            radius_km * math.cos(la) * math.sin(lo),
            radius_km * math.sin(la))


def basis(lat, lon):
    la = math.radians(lat)
    lo = math.radians(lon)
    up = (math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la))
    east = (-math.sin(lo), math.cos(lo), 0.0)
    north = (-math.sin(la) * math.cos(lo), -math.sin(la) * math.sin(lo), math.cos(la))
    return up, east, north


def az_el(target, site, lat, lon):
    up, east, north = basis(lat, lon)
    v = (target[0] - site[0], target[1] - site[1], target[2] - site[2])
    n = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
    if n == 0.0:
        return 0.0, 90.0, 0.0
    dot_e = (v[0] * east[0] + v[1] * east[1] + v[2] * east[2]) / n
    dot_n = (v[0] * north[0] + v[1] * north[1] + v[2] * north[2]) / n
    dot_u = (v[0] * up[0] + v[1] * up[1] + v[2] * up[2]) / n
    az = math.degrees(math.atan2(dot_e, dot_n)) % 360.0
    el = math.degrees(math.asin(max(-1.0, min(1.0, dot_u))))
    return az, el, n


def unit(v):
    n = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
    return (v[0] / n, v[1] / n, v[2] / n)
