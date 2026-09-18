"""World-scale synthetic scene for the globe (CC0, deterministic, offline).

Adds globe-scale context around the regional replay in ``ultra_demo``:
long-haul air corridors between real major airports, sea lanes over open
water, a synthetic storm system, and a synthetic Earth-observation
satellite on a physically plausible sun-synchronous orbit. Every object is
synthetic and labelled so: none is a real flight, vessel, storm, or
spacecraft. Airport and city coordinates are public reference facts used
only as geographic context.

Determinism: the same tick always yields the same payload.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Sequence, Tuple

from gods_eye.future import geo

DATASET_ID = "world-demo-v1"
LICENSE = "CC0-1.0 (synthetic)"
PROVENANCE = "synthetic world generator (seeded, deterministic)"
RIGHTS = "CC0: generated in-repo; reference coordinates are public facts"
SCENE_EPOCH = datetime(2026, 9, 15, 16, 40, tzinfo=timezone.utc)
MAX_TICK = 12  # replay minutes, shared with the regional scene

LatLon = Tuple[float, float]

AIRPORTS: Dict[str, Tuple[str, float, float]] = {
    "LHR": ("London Heathrow", 51.470, -0.454),
    "CDG": ("Paris Charles de Gaulle", 49.010, 2.548),
    "FRA": ("Frankfurt", 50.037, 8.562),
    "AMS": ("Amsterdam Schiphol", 52.310, 4.768),
    "MAD": ("Madrid Barajas", 40.472, -3.561),
    "DUB": ("Dublin", 53.421, -6.270),
    "LIS": ("Lisbon", 38.774, -9.134),
    "KEF": ("Keflavik", 63.985, -22.605),
    "JFK": ("New York JFK", 40.641, -73.778),
    "BOS": ("Boston Logan", 42.365, -71.010),
    "YYZ": ("Toronto Pearson", 43.678, -79.625),
    "ORD": ("Chicago O'Hare", 41.974, -87.907),
    "IAD": ("Washington Dulles", 38.953, -77.456),
    "MIA": ("Miami", 25.793, -80.290),
    "IST": ("Istanbul", 41.275, 28.752),
    "DXB": ("Dubai", 25.253, 55.366),
}

CORRIDORS: Tuple[Tuple[str, str, int], ...] = (
    ("LHR", "JFK", 9), ("LHR", "BOS", 5), ("CDG", "JFK", 6), ("FRA", "ORD", 5),
    ("AMS", "YYZ", 4), ("DUB", "BOS", 4), ("MAD", "MIA", 4), ("LIS", "IAD", 3),
    ("KEF", "JFK", 3), ("LHR", "DXB", 5), ("FRA", "IST", 4), ("CDG", "DXB", 4),
)

# Waypoints over open water (verified against the land mask by tests).
SEA_LANES: Dict[str, Tuple[str, Tuple[LatLon, ...], int]] = {
    "LANE-ATL": ("Western approaches to the North Atlantic",
                 ((49.90, -2.50), (49.40, -5.60), (48.30, -9.00), (45.00, -16.00),
                  (40.50, -25.00), (36.50, -35.00), (32.00, -48.00),
                  (29.50, -62.00)), 10),
    "LANE-CHN": ("English Channel",
                 ((51.00, 1.45), (50.55, 0.50), (50.20, -1.00), (49.90, -2.50)), 8),
    "LANE-NSE": ("North Sea",
                 ((51.60, 2.40), (52.80, 3.20), (54.50, 4.00), (56.50, 4.20),
                  (58.50, 3.00), (60.50, 2.50)), 8),
    "LANE-BRI": ("Bristol Channel approaches",
                 ((51.33, -3.45), (51.25, -4.30), (51.05, -5.40), (50.40, -6.30),
                  (49.40, -5.60)), 4),
    "LANE-IBE": ("Iberian coast to Gibraltar",
                 ((48.30, -9.00), (44.50, -10.20), (40.00, -10.30), (37.00, -9.60),
                  (36.15, -7.00), (35.95, -5.55), (36.10, -3.00), (37.50, 2.00)), 8),
}

# Synthetic storm track: past positions, "now" (index 3), +6 h illustration.
STORM_TRACK: Tuple[LatLon, ...] = ((46.5, -31.0), (48.0, -24.0), (49.4, -17.0),
                                    (50.6, -10.5), (51.2, -6.5))
STORM_BANDS = ((520.0, 330.0, "outer rain shield", "LOW"),
               (330.0, 200.0, "rain band", "MODERATE"),
               (150.0, 95.0, "heavy rain core", "HIGH"))

SATELLITE = {"id": "SYN-SAT-1", "name": "SYN-SAT-1 (synthetic Earth observation)",
             "altitude_km": 705.0, "inclination_deg": 98.2, "swath_km": 290.0}
PASS_TICK = 6
PASS_POINT: LatLon = (51.40, -3.20)
EARTH_MU = 398600.4418
SIDEREAL_DAY_S = 86164.0905

CITIES: Tuple[Tuple[str, float, float, int], ...] = (
    ("London", 51.51, -0.13, 1), ("Paris", 48.86, 2.35, 1), ("Berlin", 52.52, 13.40, 1),
    ("Madrid", 40.42, -3.70, 1), ("Rome", 41.90, 12.50, 1), ("Amsterdam", 52.37, 4.90, 2),
    ("Brussels", 50.85, 4.35, 2), ("Dublin", 53.35, -6.26, 2), ("Lisbon", 38.72, -9.14, 2),
    ("Oslo", 59.91, 10.75, 2), ("Stockholm", 59.33, 18.07, 2), ("Copenhagen", 55.68, 12.57, 2),
    ("Warsaw", 52.23, 21.01, 2), ("Vienna", 48.21, 16.37, 2), ("Zurich", 47.37, 8.54, 2),
    ("Istanbul", 41.01, 28.98, 1), ("Moscow", 55.76, 37.62, 1), ("Cairo", 30.04, 31.24, 1),
    ("Lagos", 6.52, 3.38, 1), ("Nairobi", -1.29, 36.82, 1), ("Johannesburg", -26.20, 28.05, 1),
    ("Dubai", 25.20, 55.27, 1), ("Mumbai", 19.08, 72.88, 1), ("Delhi", 28.61, 77.21, 1),
    ("Beijing", 39.90, 116.40, 1), ("Shanghai", 31.23, 121.47, 1), ("Tokyo", 35.68, 139.69, 1),
    ("Seoul", 37.57, 126.98, 1), ("Singapore", 1.35, 103.82, 1), ("Sydney", -33.87, 151.21, 1),
    ("Reykjavik", 64.15, -21.94, 2), ("New York", 40.71, -74.01, 1), ("Boston", 42.36, -71.06, 2),
    ("Toronto", 43.65, -79.38, 2), ("Chicago", 41.88, -87.63, 2), ("Washington", 38.91, -77.04, 2),
    ("Miami", 25.76, -80.19, 2), ("Mexico City", 19.43, -99.13, 1), ("Los Angeles", 34.05, -118.24, 1),
    ("Sao Paulo", -23.55, -46.63, 1), ("Buenos Aires", -34.60, -58.38, 1), ("Lima", -12.05, -77.04, 2),
    ("Bogota", 4.71, -74.07, 2), ("Cardiff", 51.48, -3.18, 3), ("Bristol", 51.45, -2.59, 3),
    ("Swansea", 51.62, -3.94, 3), ("Newport", 51.59, -3.00, 3),
)


def _clamp_tick(tick: Any) -> int:
    try:
        return max(0, min(MAX_TICK, int(tick)))
    except (TypeError, ValueError):
        return 0


def _iso(when: datetime) -> str:
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


def _r(p: LatLon) -> List[float]:
    return [round(p[0], 4), round(p[1], 4)]


def _tag(obj: Dict[str, Any]) -> Dict[str, Any]:
    return {**obj, "synthetic": True, "provenance": PROVENANCE, "rights": RIGHTS,
            "observation": obj.get("observation", "OBSERVED"), "freshness": "replay"}


def _densify(path: Sequence[LatLon], km_step: float) -> List[LatLon]:
    out: List[LatLon] = []
    for i in range(len(path) - 1):
        n = max(2, int(geo.distance_km(path[i], path[i + 1]) // km_step) + 1)
        pts = geo.great_circle(path[i], path[i + 1], n)
        out.extend(pts if not out else pts[1:])
    return out


# ------------------------------------------------------------------ air ---

def corridors() -> List[Dict[str, Any]]:
    rows = []
    for a, b, _n in CORRIDORS:
        pa, pb = AIRPORTS[a][1:], AIRPORTS[b][1:]
        rows.append({"id": f"COR-{a}-{b}", "from": a, "to": b,
                     "distance_km": round(geo.distance_km(pa, pb)),
                     "path": [_r(p) for p in geo.great_circle(pa, pb, 72)]})
    return rows


def aircraft(tick: int = 0) -> List[Dict[str, Any]]:
    out = []
    serial = 0
    for j, (a, b, n) in enumerate(CORRIDORS):
        pa, pb = AIRPORTS[a][1:], AIRPORTS[b][1:]
        total = geo.distance_km(pa, pb)
        for k in range(n):
            outbound = k % 2 == 0
            origin, dest = (a, b) if outbound else (b, a)
            path = (pa, pb) if outbound else (pb, pa)
            speed_kt = 465 + (k * 7 + j * 3) % 40
            step = speed_kt * 1.852 / 60.0 / total
            f = ((k + 0.37 * j) / n + tick * step) % 1.0
            point, heading = geo.along_path(path, f)
            cruise = 0.06 < f < 0.94
            out.append(_tag({
                "id": f"SYN-LH{serial:03d}", "callsign": f"SYN{serial:03d}",
                "lat": round(point[0], 4), "lon": round(point[1], 4),
                "heading": round(heading), "speed_kt": speed_kt,
                "alt_ft": (35000 + (k % 4) * 2000) if cruise else 14000,
                "route": f"{origin}-{dest}", "corridor": f"COR-{a}-{b}",
                "precision": "APPROXIMATE"}))
            serial += 1
    return out


# ------------------------------------------------------------------ sea ---

def lanes() -> List[Dict[str, Any]]:
    return [{"id": lid, "name": name, "path": [_r(p) for p in _densify(pts, 40.0)]}
            for lid, (name, pts, _n) in SEA_LANES.items()]


def vessels(tick: int = 0) -> List[Dict[str, Any]]:
    out = []
    serial = 0
    for j, (lid, (_name, pts, n)) in enumerate(SEA_LANES.items()):
        total = sum(geo.distance_km(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
        for k in range(n):
            path = pts if k % 2 == 0 else tuple(reversed(pts))
            speed_kt = 11 + (k * 3 + j) % 9
            f = ((k + 0.21 * j) / n + tick * speed_kt * 1.852 / 60.0 / total) % 1.0
            point, course = geo.along_path(path, f)
            out.append(_tag({
                "id": f"SYN-LV{serial:03d}", "name": f"Synthetic Carrier {serial}",
                "lat": round(point[0], 4), "lon": round(point[1], 4),
                "course": round(course), "speed_kt": speed_kt,
                "nav_state": "UNDERWAY", "lane": lid, "precision": "APPROXIMATE"}))
            serial += 1
    return out


# -------------------------------------------------------------- weather ---

def _ellipse(center: LatLon, a_km: float, b_km: float, orientation: float,
             step: int = 12) -> List[List[float]]:
    ring = []
    for deg in range(0, 360, step):
        t = math.radians(deg)
        r = a_km * b_km / math.hypot(b_km * math.cos(t), a_km * math.sin(t))
        ring.append(_r(geo.destination(center, orientation + deg, r)))
    ring.append(ring[0])
    return ring


def storm(tick: int = 0) -> Dict[str, Any]:
    now, forecast = STORM_TRACK[3], STORM_TRACK[4]
    center = geo.interpolate(now, forecast, tick / 360.0)
    orientation = geo.bearing_deg(STORM_TRACK[2], now)
    bands = [{"name": name, "intensity": level,
              "polygon": _ellipse(center, a, b, orientation)}
             for a, b, name, level in STORM_BANDS]
    return _tag({
        "id": "SYN-STORM-01", "name": "Synthetic storm system",
        "label": "Synthetic storm system (illustrative, not a forecast)",
        "center": _r(center), "heading": round(orientation),
        "track_past": [_r(p) for p in _densify(STORM_TRACK[:4], 60.0)],
        "track_illustrative": [_r(p) for p in geo.great_circle(center, forecast, 16)],
        "bands": bands, "wind_kt_max": 58, "observation": "INFERRED",
        "precision": "REGIONAL"})


# ------------------------------------------------------------ satellite ---

def _period_s() -> float:
    a = geo.EARTH_RADIUS_KM + SATELLITE["altitude_km"]
    return 2 * math.pi * math.sqrt(a ** 3 / EARTH_MU)


def _subsatellite(t_s: float) -> LatLon:
    """Circular-orbit ground point ``t_s`` seconds after the scenario pass."""
    inc = math.radians(SATELLITE["inclination_deg"])
    u_pass = math.pi - math.asin(math.sin(math.radians(PASS_POINT[0])) / math.sin(inc))
    u = u_pass + 2 * math.pi * t_s / _period_s()
    lat = math.asin(math.sin(inc) * math.sin(u))
    node_offset = math.atan2(math.cos(inc) * math.sin(u), math.cos(u))
    node_offset_pass = math.atan2(math.cos(inc) * math.sin(u_pass), math.cos(u_pass))
    lon = (PASS_POINT[1] + math.degrees(node_offset - node_offset_pass)
           - 360.0 * t_s / SIDEREAL_DAY_S)
    return (math.degrees(lat), (lon + 540.0) % 360.0 - 180.0)


def _unwrap(points: List[LatLon]) -> List[List[float]]:
    out: List[List[float]] = []
    offset = 0.0
    for lat, lon in points:
        if out:
            prev = out[-1][1] - offset
            if lon - prev > 180:
                offset -= 360.0
            elif prev - lon > 180:
                offset += 360.0
        out.append([round(lat, 4), round(lon + offset, 4)])
    return out


def satellite(tick: int = 0) -> Dict[str, Any]:
    t_now = (tick - PASS_TICK) * 60.0
    track = [_subsatellite(t_now + m * 60.0) for m in range(-25, 26)]
    centre_line = [_subsatellite(t_now + s) for s in range(-240, 241, 30)]
    half = SATELLITE["swath_km"] / 2
    left, right = [], []
    for i in range(len(centre_line) - 1):
        heading = geo.bearing_deg(centre_line[i], centre_line[i + 1])
        left.append(_r(geo.destination(centre_line[i], heading - 90, half)))
        right.append(_r(geo.destination(centre_line[i], heading + 90, half)))
    swath = left + list(reversed(right))
    swath.append(swath[0])
    return _tag({
        "id": SATELLITE["id"], "name": SATELLITE["name"],
        "label": "Synthetic satellite on a plausible sun-synchronous orbit",
        "orbit": {"altitude_km": SATELLITE["altitude_km"],
                  "inclination_deg": SATELLITE["inclination_deg"],
                  "period_min": round(_period_s() / 60.0, 2),
                  "model": "circular two-body orbit + Earth rotation"},
        "position": _r(_subsatellite(t_now)), "track": _unwrap(track),
        "swath": swath, "swath_km": SATELLITE["swath_km"],
        "pass_over_scenario_tick": PASS_TICK, "precision": "MODELED",
        "observation": "INFERRED"})


# ------------------------------------------------------------------ scene ---

def events(storm_obj: Dict[str, Any], sat: Dict[str, Any]) -> List[Dict[str, Any]]:
    from gods_eye.future import ultra_demo as u
    quake = u.seismic()[0]
    return [
        {"id": "SYN-STORM-01", "title": "Synthetic storm system nears western Europe",
         "severity": "WATCH", "category": "WEATHER", "lat": storm_obj["center"][0],
         "lon": storm_obj["center"][1], "t": "T0", "sources": 3},
        {"id": "SYN-ALERT-01", "title": "Severe gale warning for the Port Meridian approaches",
         "severity": "ALERT", "category": "WEATHER", "lat": 51.45, "lon": -3.2,
         "t": "T0", "sources": 2},
        {"id": quake["id"], "title": f"M{quake['mag']} offshore earthquake",
         "severity": "ALERT" if quake["mag"] >= 4.5 else "WATCH", "category": "EARTH",
         "lat": quake["lat"], "lon": quake["lon"], "t": "T0", "sources": 2},
        {"id": sat["id"], "title": "Synthetic satellite overpass covers the estuary",
         "severity": "INFO", "category": "SPACE", "lat": PASS_POINT[0],
         "lon": PASS_POINT[1], "t": f"T+{PASS_TICK}m", "sources": 1},
    ]


def scene(tick: Any = 0) -> Dict[str, Any]:
    t = _clamp_tick(tick)
    when = SCENE_EPOCH + timedelta(minutes=t)
    storm_obj = storm(t)
    sat = satellite(t)
    air = aircraft(t)
    sea = vessels(t)
    return {
        "dataset_id": DATASET_ID, "license": LICENSE, "provenance": PROVENANCE,
        "rights": RIGHTS, "synthetic": True, "live": False, "tick": t,
        "world_time": _iso(when), "epoch": _iso(SCENE_EPOCH),
        "airports": [{"code": c, "name": n, "lat": la, "lon": lo}
                     for c, (n, la, lo) in AIRPORTS.items()],
        "cities": [{"name": n, "lat": la, "lon": lo, "rank": r}
                   for n, la, lo, r in CITIES],
        "corridors": corridors(), "aircraft": air,
        "lanes": lanes(), "vessels": sea,
        "storm": storm_obj, "satellite": sat,
        "events": events(storm_obj, sat),
        "solar": {"subsolar": _r(geo.subsolar_point(when)),
                  "night": geo.night_polygon(when),
                  "model": "Astronomical Almanac low-precision solar position"},
        "counts": {"aircraft": len(air), "vessels": len(sea), "storms": 1,
                   "satellites": 1},
    }
