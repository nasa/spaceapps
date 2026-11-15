import math
from datetime import timedelta

from . import frames, horizons

AU_KM = 149597870.7
SUN_ANGULAR_RADIUS = 0.266
EARTH_ANGULAR_RADIUS = 0.953


def _analytic_vectors(d):
    T = d / 36525.0
    rad = math.radians
    L = 280.46646 + 36000.76983 * T
    Ms = 357.52911 + 35999.05029 * T
    C = ((1.914602 - 0.004817 * T) * math.sin(rad(Ms))
         + 0.019993 * math.sin(rad(2 * Ms))
         + 0.000289 * math.sin(rad(3 * Ms)))
    lam = rad(L + C)
    eps = rad(23.439291 - 0.0130042 * T)
    r_sun = AU_KM * 1.000001018 * (1 - 0.0167 ** 2) / (1 + 0.0167 * math.cos(rad(Ms + C)))
    sun = (r_sun * math.cos(lam),
           r_sun * math.sin(lam) * math.cos(eps),
           r_sun * math.sin(lam) * math.sin(eps))
    Lp = 218.3164477 + 481267.88123421 * T
    D = 297.8501921 + 445267.1114034 * T
    Mp = 134.9633964 + 477198.8675055 * T
    F = 93.2720950 + 483202.0175233 * T
    lon_m = Lp + (6.289 * math.sin(rad(Mp)) + 1.274 * math.sin(rad(2 * D - Mp))
                  + 0.658 * math.sin(rad(2 * D)) + 0.214 * math.sin(rad(2 * Mp))
                  - 0.186 * math.sin(rad(Ms)) - 0.114 * math.sin(rad(2 * F))
                  + 0.059 * math.sin(rad(2 * D - 2 * Mp)) + 0.057 * math.sin(rad(2 * D - Ms - Mp))
                  + 0.053 * math.sin(rad(2 * D + Mp)) + 0.046 * math.sin(rad(2 * D - Ms)))
    lat_m = (5.128 * math.sin(rad(F)) + 0.281 * math.sin(rad(Mp + F))
             + 0.278 * math.sin(rad(Mp - F)) + 0.173 * math.sin(rad(2 * D - F))
             + 0.055 * math.sin(rad(2 * D - Mp + F)) + 0.046 * math.sin(rad(2 * D - Mp - F)))
    dist_m = (385000.56 - 20905.0 * math.cos(rad(Mp)) - 3699.0 * math.cos(rad(2 * D - Mp))
              - 2956.0 * math.cos(rad(2 * D)) - 570.0 * math.cos(rad(2 * Mp)))
    lam_m = rad(lon_m)
    bet_m = rad(lat_m)
    moon = (dist_m * math.cos(bet_m) * math.cos(lam_m),
            dist_m * math.cos(bet_m) * math.sin(lam_m) * math.cos(eps) - dist_m * math.sin(bet_m) * math.sin(eps),
            dist_m * math.cos(bet_m) * math.sin(lam_m) * math.sin(eps) + dist_m * math.sin(bet_m) * math.cos(eps))
    return moon, sun


def _body_vectors(d):
    pair = horizons.sample_at(d)
    if pair is not None:
        moon, sun = pair
        return frames.to_body(moon, d), frames.to_body(sun, d), "horizons"
    moon, sun = _analytic_vectors(d)
    return frames.to_body(moon, d), frames.to_body(sun, d), "analytic"


def _subpoint(v):
    n = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
    if n == 0.0:
        return {"lat": 0.0, "lon": 0.0}
    return {"lat": math.degrees(math.asin(max(-1.0, min(1.0, v[2] / n)))),
            "lon": math.degrees(math.atan2(v[1], v[0]))}


def state(lat, lon, height_m, d):
    moon_bf, sun_bf, source = _body_vectors(d)
    site = frames.site_vector(lat, lon, frames.MOON_RADIUS_KM + height_m / 1000.0)
    sun_target = (sun_bf[0] - moon_bf[0], sun_bf[1] - moon_bf[1], sun_bf[2] - moon_bf[2])
    earth_target = (-moon_bf[0], -moon_bf[1], -moon_bf[2])
    sun_az, sun_el, sun_d = frames.az_el(sun_target, site, lat, lon)
    earth_az, earth_el, earth_d = frames.az_el(earth_target, site, lat, lon)
    sun_diam = math.degrees(2.0 * math.asin(frames.SUN_RADIUS_KM / max(sun_d, 1.0)))
    earth_diam = math.degrees(2.0 * math.asin(frames.EARTH_RADIUS_KM / max(earth_d, 1.0)))
    sep = math.degrees(math.acos(max(-1.0, min(1.0,
        (sun_target[0] * earth_target[0] + sun_target[1] * earth_target[1] + sun_target[2] * earth_target[2])
        / (math.sqrt(sum(c * c for c in sun_target)) * math.sqrt(sum(c * c for c in earth_target)))))))
    return {
        "sun": {"az": sun_az, "el": sun_el, "dist_km": sun_d, "ang_diam": sun_diam},
        "earth": {"az": earth_az, "el": earth_el, "dist_km": earth_d, "ang_diam": earth_diam},
        "separation": sep,
        "source": source,
        "subsolar": _subpoint(sun_target),
        "subearth": _subpoint(earth_target),
    }


def series(lat, lon, height_m, start, hours, step_minutes):
    step = float(step_minutes) / 1440.0
    n = int(round(hours * 60.0 / step_minutes)) + 1
    d0 = frames.to_days(start)
    t, sun_az, sun_el, ear_az, ear_el, sun_d, ear_d, src = [], [], [], [], [], [], [], "analytic"
    for i in range(n):
        d = d0 + i * step
        s = state(lat, lon, height_m, d)
        src = s["source"]
        t.append(i * step_minutes)
        sun_az.append(s["sun"]["az"])
        sun_el.append(s["sun"]["el"])
        ear_az.append(s["earth"]["az"])
        ear_el.append(s["earth"]["el"])
        sun_d.append(s["sun"]["ang_diam"])
        ear_d.append(s["earth"]["ang_diam"])
    return {
        "minutes": t, "sun_az": sun_az, "sun_el": sun_el,
        "earth_az": ear_az, "earth_el": ear_el,
        "sun_diam": sun_d, "earth_diam": ear_d,
        "step_minutes": step_minutes, "hours": hours, "source": src,
    }


def warm(start, hours):
    return horizons.ensure_range(start, hours)
