import math

from . import horizon

SOLAR_CONSTANT = 1361.0


def _transition(mask, step_minutes):
    for i in range(len(mask) - 1):
        if mask[i] != mask[i + 1]:
            return i * step_minutes / 60.0
    return None


def _longest_run(mask, step_minutes):
    best = 0
    cur = 0
    for v in mask:
        if v:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best * step_minutes / 60.0


def analyse(series, sky):
    mins = series["minutes"]
    step_min = series["step_minutes"]
    dt_h = step_min / 60.0
    sun_frac = []
    earth_mask = []
    insolation = 0.0
    for i in range(len(mins)):
        az = series["sun_az"][i]
        el = series["sun_el"][i]
        hz = horizon.horizon_at(sky, az)
        diam = max(0.05, series["sun_diam"][i])
        frac = (el - hz) / diam + 0.5
        frac = max(0.0, min(1.0, frac))
        sun_frac.append(frac)
        if frac > 0.0:
            insolation += SOLAR_CONSTANT * math.sin(math.radians(max(0.0, el))) * frac * dt_h
        earth_mask.append(horizon.earth_visible(sky, series["earth_az"][i], series["earth_el"][i],
                                               max(0.5, series["earth_diam"][i] / 2.0)))
    sun_mask = [f > 0.25 for f in sun_frac]
    total_h = max(1e-9, len(mins) * dt_h)
    return {
        "sun_fraction": sun_frac,
        "sun_mask": sun_mask,
        "earth_mask": earth_mask,
        "illumination": sum(sun_frac) / len(sun_frac),
        "earth_visibility": sum(1 for v in earth_mask if v) / len(earth_mask),
        "longest_sun_hours": _longest_run(sun_mask, step_min),
        "longest_earth_hours": _longest_run(earth_mask, step_min),
        "next_sun_transition_h": _transition(sun_mask, step_min),
        "next_earth_transition_h": _transition(earth_mask, step_min),
        "insolation_wh_m2": insolation,
        "total_hours": total_h,
        "mean_sun_el": sum(series["sun_el"]) / len(series["sun_el"]),
        "max_sun_el": max(series["sun_el"]),
        "min_sun_el": min(series["sun_el"]),
        "horizon_at_sun": horizon.horizon_at(sky, series["sun_az"][0]),
        "horizon_at_earth": horizon.horizon_at(sky, series["earth_az"][0]),
    }


def daily(series, sky, day_hours=24.0):
    step_min = series["step_minutes"]
    per_day = int(round(day_hours * 60.0 / step_min))
    out = []
    n = len(series["minutes"])
    i = 0
    while i < n:
        j = min(n, i + per_day)
        seg = {"start_min": series["minutes"][i], "sun": [], "earth": [], "sun_el": []}
        lit = 0
        earth = 0
        for k in range(i, j):
            az = series["sun_az"][k]
            el = series["sun_el"][k]
            hz = horizon.horizon_at(sky, az)
            f = max(0.0, min(1.0, (el - hz) / max(0.05, series["sun_diam"][k]) + 0.5))
            seg["sun"].append(round(f, 3))
            seg["sun_el"].append(round(el, 2))
            seg["earth"].append(horizon.earth_visible(sky, series["earth_az"][k], series["earth_el"][k]))
            lit += f
            earth += seg["earth"][-1]
        count = max(1, j - i)
        seg["illumination"] = lit / count
        seg["earth_visibility"] = earth / count
        out.append(seg)
        i = j
    return out
