"""Dependency-free geodesy for the world surface (spherical Earth).

* TopoJSON decoding and a point-on-land test over the Natural Earth
  1:50m land polygons shipped in ``console/data/land-50m.json``
* great-circle distance, bearing, destination, and interpolation
* the subsolar point and a night-side polygon for a UTC instant, using the
  low-precision solar position from the Astronomical Almanac (about 0.01
  degree in declination); ample for a day/night shading layer

Coordinates are (lat, lon) in degrees unless a name says otherwise.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

EARTH_RADIUS_KM = 6371.0088
LAND_FILE = ("console", "data", "land-50m.json")
J2000 = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)

LatLon = Tuple[float, float]
Ring = List[Tuple[float, float]]  # (lon, lat), as in GeoJSON and TopoJSON


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


# ------------------------------------------------------------- topojson ---

def _decode_arcs(topology: dict) -> List[Ring]:
    transform = topology.get("transform")
    arcs: List[Ring] = []
    for arc in topology["arcs"]:
        if transform:
            (sx, sy), (tx, ty) = transform["scale"], transform["translate"]
            x = y = 0
            ring: Ring = []
            for dx, dy in arc:
                x += dx
                y += dy
                ring.append((x * sx + tx, y * sy + ty))
        else:
            ring = [(float(p[0]), float(p[1])) for p in arc]
        arcs.append(ring)
    return arcs


def decode_polygons(topology: dict, object_name: str) -> List[List[Ring]]:
    """Polygons of one TopoJSON object as [outer, *holes] rings of (lon, lat)."""
    arcs = _decode_arcs(topology)

    def ring(indices: Sequence[int]) -> Ring:
        out: Ring = []
        for i in indices:
            pts = arcs[i] if i >= 0 else arcs[~i][::-1]
            out.extend(pts if not out else pts[1:])
        return out

    obj = topology["objects"][object_name]
    polygons: List[List[Ring]] = []
    for geom in obj.get("geometries", [obj]):
        if geom["type"] == "Polygon":
            polygons.append([ring(r) for r in geom["arcs"]])
        elif geom["type"] == "MultiPolygon":
            polygons.extend([ring(r) for r in poly] for poly in geom["arcs"])
    return polygons


def _inside(lon: float, lat: float, ring: Ring) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > lat) != (yj > lat) and \
                lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def ring_contains(ring_latlon: Sequence[LatLon], lat: float, lon: float) -> bool:
    """Even-odd test for a ring given as (lat, lon) pairs."""
    return _inside(lon, lat, [(p[1], p[0]) for p in ring_latlon])


class LandMask:
    """Point-on-land test with per-polygon bounding boxes."""

    def __init__(self, polygons: List[List[Ring]]):
        self._items = []
        for poly in polygons:
            lons = [p[0] for p in poly[0]]
            lats = [p[1] for p in poly[0]]
            box = (min(lons), min(lats), max(lons), max(lats))
            self._items.append((box, poly))

    def __len__(self) -> int:
        return len(self._items)

    def is_land(self, lat: float, lon: float) -> bool:
        for (x0, y0, x1, y1), poly in self._items:
            if (x0 <= lon <= x1 and y0 <= lat <= y1
                    and _inside(lon, lat, poly[0])
                    and not any(_inside(lon, lat, hole) for hole in poly[1:])):
                return True
        return False


@lru_cache(maxsize=4)
def land_mask(path: Optional[str] = None) -> Optional[LandMask]:
    """Natural Earth land mask, or None when the data file is not present."""
    source = Path(path) if path else repo_root().joinpath(*LAND_FILE)
    try:
        topology = json.loads(source.read_text(encoding="utf-8"))
        return LandMask(decode_polygons(topology, "land"))
    except (OSError, ValueError, KeyError):
        return None


# ---------------------------------------------------------- great circles ---

def _rad(p: LatLon) -> Tuple[float, float]:
    return math.radians(p[0]), math.radians(p[1])


def distance_km(a: LatLon, b: LatLon) -> float:
    (la1, lo1), (la2, lo2) = _rad(a), _rad(b)
    h = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2)
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(h)))


def bearing_deg(a: LatLon, b: LatLon) -> float:
    (la1, lo1), (la2, lo2) = _rad(a), _rad(b)
    y = math.sin(lo2 - lo1) * math.cos(la2)
    x = (math.cos(la1) * math.sin(la2)
         - math.sin(la1) * math.cos(la2) * math.cos(lo2 - lo1))
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def interpolate(a: LatLon, b: LatLon, fraction: float) -> LatLon:
    (la1, lo1), (la2, lo2) = _rad(a), _rad(b)
    d = distance_km(a, b) / EARTH_RADIUS_KM
    if d < 1e-12:
        return (a[0], a[1])
    k1 = math.sin((1 - fraction) * d) / math.sin(d)
    k2 = math.sin(fraction * d) / math.sin(d)
    x = k1 * math.cos(la1) * math.cos(lo1) + k2 * math.cos(la2) * math.cos(lo2)
    y = k1 * math.cos(la1) * math.sin(lo1) + k2 * math.cos(la2) * math.sin(lo2)
    z = k1 * math.sin(la1) + k2 * math.sin(la2)
    return (math.degrees(math.atan2(z, math.hypot(x, y))),
            math.degrees(math.atan2(y, x)))


def great_circle(a: LatLon, b: LatLon, n: int = 64) -> List[LatLon]:
    n = max(2, n)
    return [interpolate(a, b, i / (n - 1)) for i in range(n)]


def destination(p: LatLon, bearing: float, km: float) -> LatLon:
    la1, lo1 = _rad(p)
    b = math.radians(bearing)
    d = km / EARTH_RADIUS_KM
    la2 = math.asin(math.sin(la1) * math.cos(d)
                    + math.cos(la1) * math.sin(d) * math.cos(b))
    lo2 = lo1 + math.atan2(math.sin(b) * math.sin(d) * math.cos(la1),
                           math.cos(d) - math.sin(la1) * math.sin(la2))
    return (math.degrees(la2), (math.degrees(lo2) + 540.0) % 360.0 - 180.0)


def along_path(path: Sequence[LatLon], fraction: float) -> Tuple[LatLon, float]:
    """Point at ``fraction`` (wrapped to 0..1) of a polyline, plus its heading."""
    legs = [distance_km(path[i], path[i + 1]) for i in range(len(path) - 1)]
    target = (fraction % 1.0) * sum(legs)
    for i, leg in enumerate(legs):
        if target <= leg or i == len(legs) - 1:
            point = interpolate(path[i], path[i + 1],
                                0.0 if leg == 0 else min(1.0, target / leg))
            return point, bearing_deg(point, path[i + 1])
        target -= leg
    return (path[-1][0], path[-1][1]), 0.0


# ------------------------------------------------------------------ solar ---

def subsolar_point(when: datetime) -> LatLon:
    """Latitude/longitude where the Sun is at the zenith at ``when`` (UTC)."""
    if when.tzinfo is None:
        raise ValueError("when must be timezone-aware (UTC)")
    n = (when - J2000).total_seconds() / 86400.0
    mean_lon = (280.460 + 0.9856474 * n) % 360.0
    anomaly = math.radians((357.528 + 0.9856003 * n) % 360.0)
    ecliptic_lon = math.radians(mean_lon + 1.915 * math.sin(anomaly)
                                + 0.020 * math.sin(2 * anomaly))
    obliquity = math.radians(23.439 - 0.0000004 * n)
    declination = math.asin(math.sin(obliquity) * math.sin(ecliptic_lon))
    right_ascension = math.degrees(math.atan2(
        math.cos(obliquity) * math.sin(ecliptic_lon), math.cos(ecliptic_lon)))
    gmst = (280.46061837 + 360.98564736629 * n) % 360.0
    lon = (right_ascension - gmst + 540.0) % 360.0 - 180.0
    return (math.degrees(declination), lon)


def night_polygon(when: datetime, step_deg: float = 2.0) -> List[LatLon]:
    """Closed (lat, lon) ring covering the night side, for a shading layer."""
    dec, sun_lon = subsolar_point(when)
    if abs(dec) < 0.05:
        dec = math.copysign(0.05, dec if dec else 1.0)
    tan_dec = math.tan(math.radians(dec))
    ring: List[LatLon] = []
    steps = int(round(360.0 / step_deg))
    for i in range(steps + 1):
        lon = -180.0 + i * step_deg
        hour_angle = math.radians(lon - sun_lon)
        lat = math.degrees(math.atan(-math.cos(hour_angle) / tan_dec))
        ring.append((round(lat, 3), round(lon, 3)))
    pole = -90.0 if dec > 0 else 90.0
    ring += [(pole, 180.0), (pole, -180.0), ring[0]]
    return ring
