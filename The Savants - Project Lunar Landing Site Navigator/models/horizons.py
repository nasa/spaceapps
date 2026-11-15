import gzip
import json
import math
import re
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from . import frames

API = "https://ssd.jpl.nasa.gov/api/horizons.api"
CACHE_DIR = None
CHUNK_DAYS = 20.0
STEP_MINUTES = 30
_LOCK = threading.Lock()
_MEM = {}

_JD_RE = re.compile(r"^\s*(\d+\.\d+)\s*=\s*A\.D\.\s*(\d{4})-(\w{3})-(\d{2})\s+(\d{2}):(\d{2})")
_XYZ_RE = re.compile(
    r"X\s*=\s*(-?[\d.]+E[+-]\d+)\s*Y\s*=\s*(-?[\d.]+E[+-]\d+)\s*Z\s*=\s*(-?[\d.]+E[+-]\d+)")
_MONTHS = {m: i + 1 for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}


def configure(cache_dir):
    global CACHE_DIR
    CACHE_DIR = cache_dir


def _cache_path(kind, start):
    stamp = start.strftime("%Y%m%dT%H%M")
    return f"{CACHE_DIR}/vec_{kind}_{stamp}.json.gz"


def _fetch_vectors(command, start, stop):
    params = {
        "format": "text",
        "COMMAND": f"'{command}'",
        "EPHEM_TYPE": "'VECTORS'",
        "CENTER": "'500@399'",
        "START_TIME": f"'{start.strftime('%Y-%m-%d %H:%M')}'",
        "STOP_TIME": f"'{stop.strftime('%Y-%m-%d %H:%M')}'",
        "STEP_SIZE": f"'{STEP_MINUTES}m'",
        "REF_PLANE": "'FRAME'",
        "VEC_TABLE": "'2'",
        "OUT_UNITS": "'KM-S'",
    }
    url = API + "?" + urllib.parse.urlencode(params, safe="'@%:")
    req = urllib.request.Request(url, headers={"User-Agent": "lunar-site-planner/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        text = resp.read().decode("utf-8", "replace")
    if "$$SOE" not in text:
        tail = " ".join(text.strip().splitlines()[-3:])
        raise RuntimeError(f"horizons vectors failed: {tail[:200]}")
    body = text.split("$$SOE", 1)[1].split("$$EOE", 1)[0]
    rows = []
    current = None
    for line in body.splitlines():
        m = _JD_RE.match(line)
        if m:
            jd = float(m.group(1))
            current = [jd, None]
            rows.append(current)
            continue
        if current is not None and current[1] is None:
            v = _XYZ_RE.search(line)
            if v:
                current[1] = [float(v.group(1)), float(v.group(2)), float(v.group(3))]
    return [r for r in rows if r[1] is not None]


def _load_chunk(start):
    path = _cache_path("chunk", start)
    try:
        with gzip.open(path, "rt") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _save_chunk(start, payload):
    path = _cache_path("chunk", start)
    tmp = path + ".tmp"
    with gzip.open(tmp, "wt") as fh:
        json.dump(payload, fh, separators=(",", ":"))
    import os
    os.replace(tmp, path)


def _build_chunk(start):
    stop = start + timedelta(days=CHUNK_DAYS)
    moon = _fetch_vectors("301", start, stop)
    sun = _fetch_vectors("10", start, stop)
    n = min(len(moon), len(sun))
    if n < 2:
        raise RuntimeError("insufficient ephemeris samples")
    d0 = moon[0][0] - 2451545.0
    payload = {
        "d0": d0,
        "step": STEP_MINUTES / 1440.0,
        "moon": [moon[i][1] for i in range(n)],
        "sun": [sun[i][1] for i in range(n)],
        "created": time.time(),
    }
    _save_chunk(start, payload)
    return payload


def chunk_for(when, allow_fetch=True):
    start = when.replace(minute=0, second=0, microsecond=0)
    span = timedelta(days=CHUNK_DAYS)
    epoch = datetime(2024, 1, 1, tzinfo=timezone.utc)
    index = int((start - epoch) / span)
    start = epoch + index * span
    key = start.strftime("%Y%m%dT%H%M")
    with _LOCK:
        if key in _MEM:
            return _MEM[key]
    payload = _load_chunk(start)
    if payload is None:
        if not allow_fetch:
            return None
        try:
            payload = _build_chunk(start)
        except Exception:
            return None
    with _LOCK:
        _MEM[key] = payload
    return payload


def sample_at(d):
    when = frames.from_days(d)
    chunk = chunk_for(when, allow_fetch=True)
    if chunk is None:
        return None
    step = chunk["step"]
    idx = (d - chunk["d0"]) / step
    n = len(chunk["moon"])
    if idx < 0 or idx > n - 1:
        return None
    i = int(math.floor(idx))
    if i >= n - 1:
        i = n - 2
    f = idx - i
    out = []
    for key in ("moon", "sun"):
        a = chunk[key][i]
        b = chunk[key][i + 1]
        out.append(tuple(a[k] + (b[k] - a[k]) * f for k in range(3)))
    return out[0], out[1]


def ensure_range(start, hours):
    stop = start + timedelta(hours=hours)
    cursor = start
    built = 0
    while cursor <= stop:
        payload = chunk_for(cursor, allow_fetch=True)
        if payload is None:
            cursor += timedelta(days=CHUNK_DAYS)
            continue
        built += 1
        cursor = frames.from_days(payload["d0"] + payload["step"] * (len(payload["moon"]) - 1)) + timedelta(seconds=1)
    return built


def coverage():
    import glob
    files = sorted(glob.glob(f"{CACHE_DIR}/vec_chunk_*.json.gz")) if CACHE_DIR else []
    return {"chunks": len(files), "first": files[0].split("vec_chunk_")[-1][:13] if files else None,
            "last": files[-1].split("vec_chunk_")[-1][:13] if files else None}
