"""Live orbital objects from qualified public elements (V2.4c).

Source (verified 2026-09-19, keyless, no credentials):
  CelesTrak GP (General Perturbations) element sets, TLE format,
  per-group queries. Free for all users (501(c)(3) mission); the
  usage policy governs QUERY ETIQUETTE (documented queries, no
  hammering), not access. Bulk redistribution of the raw catalog is
  not mirrored here — elements are cached per TTL and only derived
  propagated positions leave this module.

Propagation uses the well-established `sgp4` package (Brandon
Rhodes, MIT), imported lazily: without the optional `satellites`
extra every entry point reports UNAVAILABLE instead of guessing.
No orbital mechanics are implemented here beyond the standard
ECI-to-geodetic rotation (GMST + WGS84 iteration), which is
coordinate conversion, not propagation.

Truth model (binding):
  OBSERVED_ELEMENTS  — the TLE set as published (epoch preserved)
  PROPAGATED_POSITION — lat/lon/alt computed by SGP4 at a stated
    time. Never labeled as a live fix without qualification.

Freshness rationale (element age, not cosmetic):
  CelesTrak refreshes groups ~daily and LEO SGP4 error grows on the
  order of km per day, so FRESH < 2 d, AGING < 7 d, STALE >= 7 d.
  Stale elements keep rendering ONLY with their actual age and a
  degraded status; ancient TLEs never silently persist (cache TTL
  bounds re-fetch, and STALE is always labeled).

Fail-closed: malformed TLE (bad checksum/structure), missing sgp4,
or source outage -> PROPAGATION_FAILED / SOURCE_UNAVAILABLE /
UNKNOWN_OBJECT. Synthetic placeholders are never substituted.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

SOURCE_ID = "celestrak"
SOURCE_NAME = "CelesTrak"
BASE_URL = "https://celestrak.org/NORAD/elements/gp.php"
TERMS_URLS = (
    "https://celestrak.org/usage-policy.php",
    "https://celestrak.org/NORAD/documentation/gp-data-formats.php",
)
ATTRIBUTION = "CelesTrak / Dr. T.S. Kelso"
USER_AGENT = "Tellurion-satellites/1.0 (+public demo)"

# Curated default groups: stations + visual + GNSS + GEO belt.
# Starlink-scale shells stay opt-in (bandwidth + render cost).
DEFAULT_GROUPS = ("stations", "visual", "gps-ops", "glo-ops",
                  "galileo", "beidou", "geo")
ELEMENT_TTL_S = 6 * 3600
SOURCE_UNAVAILABLE_AFTER_FAILS = 3
MAX_OBJECTS = 1500

TRUTH_LABEL = "ORBITAL OBJECTS (CelesTrak elements + SGP4)"

# Element-age classes (days). Rationale in module docstring.
FRESH_DAYS = 2.0
STALE_DAYS = 7.0

WGS84_A = 6378.137
WGS84_F = 1.0 / 298.257223563
WGS84_E2 = WGS84_F * (2.0 - WGS84_F)

RIGHTS = {
    "commercial_use": "YES (public data, lawful use)",
    "public_display": "YES",
    "redistribution": "YES (derived positions with attribution; "
                      "no raw-catalog mirroring per usage policy)",
    "derived_products": "YES (propagation + visualization)",
    "broadcast_use": "ATTRIBUTION_REQUIRED",
    "cache": "YES (bounded runtime cache, 6 h element TTL)",
    "attribution": ATTRIBUTION,
}
RIGHTS_STATUS = "ATTRIBUTION_REQUIRED"


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _now_dt(value: Optional[str] = None) -> datetime:
    if value:
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _parse_time(value: Any) -> Optional[datetime]:
    if not value or value == "UNKNOWN":
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _runtime_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in (here.parent, *here.parents):
        if (parent / "raw_store").is_dir() or parent.name == "gods-eye":
            cand = parent / "raw_store" / "satellites"
            cand.mkdir(parents=True, exist_ok=True)
            return cand
    cand = Path.cwd() / "raw_store" / "satellites"
    cand.mkdir(parents=True, exist_ok=True)
    return cand


def _meta_path() -> Path:
    return _runtime_dir() / "sat_meta.json"


def load_meta() -> Dict[str, Any]:
    try:
        data = json.loads(_meta_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"elements": {}, "health": {}}
    out = {"elements": {}, "health": {}}
    for key in out:
        if isinstance(data.get(key), dict):
            out[key] = data[key]
    return out


def save_meta(meta: Dict[str, Any]) -> None:
    path = _meta_path()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(meta, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8")
    tmp.replace(path)


def health_ok(meta: Dict[str, Any], host: str = "celestrak") -> bool:
    return int((meta.get("health", {}).get(host) or {}).get(
        "fails_consec", 0)) < SOURCE_UNAVAILABLE_AFTER_FAILS


def note_success(meta: Dict[str, Any], host: str, now: str) -> None:
    meta.setdefault("health", {})[host] = {"fails_consec": 0,
                                           "last_success": now,
                                           "state": "ONLINE"}


def note_failure(meta: Dict[str, Any], host: str, now: str,
                 detail: str = "") -> None:
    row = meta.setdefault("health", {}).setdefault(host, {})
    row["fails_consec"] = int(row.get("fails_consec", 0)) + 1
    row["last_error"] = detail[:200]
    row["state"] = ("SOURCE_UNAVAILABLE"
                    if row["fails_consec"] >= SOURCE_UNAVAILABLE_AFTER_FAILS
                    else "DEGRADED")


def sgp4_available() -> bool:
    try:
        import importlib.util
        return importlib.util.find_spec("sgp4") is not None
    except Exception:  # noqa: BLE001
        return False


# ------------------------------------------------------------ TLE ---


def _tle_checksum(line: str) -> bool:
    """Validate a TLE line checksum (fail closed on malformed)."""
    try:
        body = line[:68].ljust(68)
        total = 0
        for ch in body:
            if ch.isdigit():
                total += int(ch)
            elif ch == "-":
                total += 1
        return total % 10 == int(line[68])
    except (IndexError, ValueError):
        return False


def parse_tle(text: str) -> List[Dict[str, str]]:
    """Parse 3-line TLE blocks. Returns [{name, line1, line2}].
    Blocks with bad structure or checksums are dropped."""
    lines = [ln.rstrip("\r\n") for ln in str(text or "").splitlines()]
    lines = [ln for ln in lines if ln.strip()]
    out = []
    i = 0
    while i + 2 < len(lines) + 1 and i < len(lines):
        if (lines[i].startswith("1 ") and i + 1 < len(lines)
                and lines[i + 1].startswith("2 ")):
            name = lines[i - 1] if i > 0 and not lines[i - 1].startswith(
                ("1 ", "2 ")) else "UNKNOWN"
            l1, l2 = lines[i], lines[i + 1]
            if (_tle_checksum(l1) and _tle_checksum(l2)
                    and len(l1) >= 69 and len(l2) >= 69):
                out.append({"name": name.strip() or "UNKNOWN",
                            "line1": l1, "line2": l2})
            i += 2
        else:
            i += 1
    return out


def tle_epoch(line1: str) -> Optional[datetime]:
    """Epoch from TLE line-1 columns 19-32 (YYDDD.DDDDDDDD)."""
    try:
        yy = int(line1[18:20])
        day = float(line1[20:32])
        year = 2000 + yy if yy < 57 else 1900 + yy
        base = datetime(year, 1, 1, tzinfo=timezone.utc)
        return base + timedelta(days=day - 1.0)
    except (ValueError, IndexError):
        return None


def tle_fields(line1: str, line2: str) -> Optional[Dict[str, Any]]:
    """Numeric fields needed for model + classification."""
    try:
        norad = int(line1[2:7])
        incl = float(line2[8:16])
        ecc = float("0." + line2[26:33].strip())
        mean_motion = float(line2[52:63])
        return {"norad_id": norad, "inclination_deg": incl,
                "eccentricity": ecc, "mean_motion": mean_motion}
    except (ValueError, IndexError):
        return None


def orbit_class(mean_motion: float, eccentricity: float) -> str:
    """Generic orbit family from period/eccentricity. Documented,
    coarse, never sensational."""
    try:
        period_min = 1440.0 / float(mean_motion)
    except (TypeError, ValueError, ZeroDivisionError):
        return "UNKNOWN"
    if float(eccentricity) > 0.5:
        return "HEO"
    if abs(period_min - 1436.07) < 30.0 and float(eccentricity) < 0.05:
        return "GEO"
    if period_min < 128.0:
        return "LEO"
    return "MEO"


def freshness_class(age_days: Optional[float]) -> str:
    if age_days is None:
        return "UNKNOWN"
    if age_days < FRESH_DAYS:
        return "FRESH"
    if age_days < STALE_DAYS:
        return "AGING"
    return "STALE"


# --------------------------------------------------------- fetch ---


def fetch_group(group: str,
                opener: Optional[Callable] = None) -> Tuple[str, str]:
    """Fetch one group's TLE text. Returns (text, detail). Never raises."""
    import urllib.parse
    import urllib.request
    query = urllib.parse.urlencode({"GROUP": group, "FORMAT": "tle"})
    url = f"{BASE_URL}?{query}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        if opener is not None:
            resp = opener(req, timeout=60)
            text = resp.read().decode("utf-8", "replace")
        else:
            with urllib.request.urlopen(req, timeout=60) as resp:
                text = resp.read().decode("utf-8", "replace")
        return text, "ok"
    except Exception as e:  # noqa: BLE001 - honest detail string
        return "", f"{type(e).__name__}: {str(e)[:160]}"


def refresh_elements(groups: Optional[Tuple[str, ...]] = None,
                     opener: Optional[Callable] = None,
                     now: Optional[str] = None,
                     force: bool = False) -> Dict[str, Any]:
    """Refresh cached element sets per TTL. Returns {ok, groups, errors}."""
    now = now or utcnow()
    meta = load_meta()
    groups = groups or DEFAULT_GROUPS
    ok, errors = [], []
    for group in groups:
        row = meta.get("elements", {}).get(group) or {}
        age = (_now_dt(now) - _now_dt(row.get("fetched_at"))).total_seconds()
        if not force and row.get("tle") and age < ELEMENT_TTL_S:
            ok.append(group)
            continue
        if not health_ok(meta):
            errors.append(f"{group}: backing off (see provider health)")
            continue
        text, detail = fetch_group(group, opener)
        parsed = parse_tle(text) if text else []
        if not parsed:
            note_failure(meta, "celestrak", now, detail or "empty set")
            save_meta(meta)
            if row.get("tle"):
                ok.append(group)  # serve aged cache honestly below
            else:
                errors.append(f"{group}: {detail or 'empty set'}")
            continue
        meta.setdefault("elements", {})[group] = {"fetched_at": now,
                                                  "tle": text,
                                                  "count": len(parsed)}
        note_success(meta, "celestrak", now)
        save_meta(meta)
        ok.append(group)
    return {"ok": ok, "errors": errors, "generated_at": now}


# ----------------------------------------------------- propagation ---


def _gmst_rad(jd: float) -> float:
    """Greenwich mean sidereal time (radians). Standard formula."""
    tut1 = (jd - 2451545.0) / 36525.0
    gmst_deg = (280.46061837 + 360.98564736629 * (jd - 2451545.0)
                + 0.000387933 * tut1 * tut1
                - tut1 * tut1 * tut1 / 38710000.0)
    return math.radians(gmst_deg % 360.0)


def eci_to_geodetic(r_km: Tuple[float, float, float],
                    jd: float) -> Tuple[float, float, float]:
    """ECI (km) -> (lat deg, lon deg, alt km). WGS84 iteration."""
    x, y, z = r_km
    theta = _gmst_rad(jd)
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    xe = cos_t * x + sin_t * y
    ye = -sin_t * x + cos_t * y
    ze = z
    lon = math.degrees(math.atan2(ye, xe))
    p = math.hypot(xe, ye)
    lat = math.atan2(ze, p * (1.0 - WGS84_E2))
    for _ in range(3):
        sin_lat = math.sin(lat)
        n_ = WGS84_A / math.sqrt(1.0 - WGS84_E2 * sin_lat * sin_lat)
        alt = p / math.cos(lat) - n_
        lat = math.atan2(ze, p * (1.0 - WGS84_E2 * n_ / (n_ + alt)))
    sin_lat = math.sin(lat)
    n_ = WGS84_A / math.sqrt(1.0 - WGS84_E2 * sin_lat * sin_lat)
    alt = p / math.cos(lat) - n_
    return math.degrees(lat), ((lon + 540.0) % 360.0) - 180.0, alt


def propagate(line1: str, line2: str,
              when: datetime) -> Dict[str, Any]:
    """SGP4 propagate one element set to `when` (UTC).
    Returns ECI state (r/v vectors) converted to geodetic, or raises
    on failure (never guessed)."""
    from sgp4.api import Satrec, jday
    sat = Satrec.twoline2rv(line1, line2)
    jd, fr = jday(when.year, when.month, when.day, when.hour,
                  when.minute, when.second + when.microsecond / 1e6)
    err, r, v = sat.sgp4(jd, fr)
    if err != 0:
        raise ValueError(f"sgp4 error {err}")
    lat, lon, alt = eci_to_geodetic((r[0], r[1], r[2]), jd + fr)
    speed = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
    return {"latitude": lat, "longitude": lon, "altitude_km": alt,
            "velocity_km_s": speed,
            "propagated_at": when.replace(
                microsecond=0).isoformat()}


def ground_track(line1: str, line2: str, center: datetime,
                 span_min: float = 45.0,
                 step_min: float = 3.0) -> List[List[float]]:
    """Recent/future ground track around `center` (lon/lat pairs)."""
    pts = []
    t = center - timedelta(minutes=span_min)
    end = center + timedelta(minutes=span_min)
    while t <= end:
        try:
            pos = propagate(line1, line2, t)
            pts.append([round(pos["longitude"], 3),
                        round(pos["latitude"], 3)])
        except ValueError:
            pass
        t += timedelta(minutes=step_min)
    return pts


# ---------------------------------------------------------- model ---


def _object_type(group: str) -> str:
    group = (group or "").lower()
    if group in ("stations",):
        return "PAYLOAD"
    if group in ("debris", "analyst"):
        return "DEBRIS"
    if "rocket" in group or "r/b" in group:
        return "ROCKET BODY"
    return "UNKNOWN"


def build_object(name: str, line1: str, line2: str, group: str,
                 when: datetime, now: str) -> Optional[Dict[str, Any]]:
    """Canonical orbital object. None when unpropagatable (fail closed)."""
    fields = tle_fields(line1, line2)
    epoch = tle_epoch(line1)
    if fields is None or epoch is None:
        return None
    if not sgp4_available():
        return None
    try:
        pos = propagate(line1, line2, when)
    except ValueError:
        return None
    age_days = max(0.0, (when - epoch).total_seconds() / 86400.0)
    norad = fields["norad_id"]
    oclass = orbit_class(fields["mean_motion"], fields["eccentricity"])
    year = epoch.year
    return {
        "object_id": f"SAT:{norad}",
        "name": name, "norad_id": norad, "source": SOURCE_NAME,
        "epoch": epoch.replace(microsecond=0).isoformat(),
        "age_seconds": int(age_days * 86400.0),
        "element_format": "TLE",
        "orbit_type": oclass,
        "object_type": _object_type(group),
        "group": group,
        "inclination_deg": fields["inclination_deg"],
        "eccentricity": fields["eccentricity"],
        "mean_motion": fields["mean_motion"],
        "altitude_km": round(pos["altitude_km"], 1),
        "latitude": round(pos["latitude"], 3),
        "longitude": round(pos["longitude"], 3),
        "velocity_km_s": round(pos["velocity_km_s"], 2),
        "propagated_at": pos["propagated_at"],
        "truth_mode": "PROPAGATED",
        "freshness": freshness_class(age_days),
        "source_url": f"{BASE_URL}?GROUP={group}&FORMAT=tle",
        "rights": dict(RIGHTS),
        "attribution": f"{ATTRIBUTION} [{year}]",
    }


def _matches(obj: Dict[str, Any],
             bbox: Optional[Tuple[float, float, float, float]],
             orbit_type: str, freshness: str) -> bool:
    if orbit_type and obj.get("orbit_type") != orbit_type.upper():
        return False
    if freshness and obj.get("freshness") != freshness.upper():
        return False
    if bbox:
        x0, y0, x1, y1 = bbox
        lon = obj.get("longitude")
        lat = obj.get("latitude")
        try:
            if not (x0 <= float(lon) <= x1 and y0 <= float(lat) <= y1):
                return False
        except (TypeError, ValueError):
            return False
    return True


def get_satellites(refresh: bool = False,
                   bbox: Optional[Tuple[float, float, float, float]] = None,
                   region: str = "",
                   orbit_type: str = "",
                   freshness: str = "",
                   limit: int = 500,
                   opener: Optional[Callable] = None,
                   now: Optional[datetime] = None,
                   groups: Optional[Tuple[str, ...]] = None
                   ) -> Dict[str, Any]:
    """Machine-readable satellite payload (positions PROPAGATED)."""
    when = now or datetime.now(timezone.utc)
    now_s = when.replace(microsecond=0).isoformat()
    base: Dict[str, Any] = {"generated_at": now_s, "live": False,
                            "real_data": True,
                            "truth_label": TRUTH_LABEL,
                            "truth_note": "positions are PROPAGATED "
                            "from published elements via SGP4; "
                            "never live GPS observations",
                            "objects": [], "coverage": {},
                            "source": {}}
    if not sgp4_available():
        return {**base, "real_data": False, "objects": [],
                "status": "UNAVAILABLE",
                "note": "sgp4 package not installed (optional "
                        "'satellites' extra); no positions guessed"}
    meta = load_meta()
    if refresh:
        res = refresh_elements(groups=groups, opener=opener, now=now_s)
        if not res["ok"] and not meta.get("elements"):
            return {**base, "status": "SOURCE_UNAVAILABLE",
                    "note": "; ".join(res["errors"])[:300]}
    if region:
        bbox = _region_bbox(region)
        if bbox is None:
            return {**base, "status": "FAILED", "objects": [],
                    "note": f"unknown region: {region}"}
    objects: List[Dict[str, Any]] = []
    epochs: List[str] = []
    groups_hit: List[str] = []
    stale_served = False
    for group, row in (meta.get("elements") or {}).items():
        if groups and group not in groups:
            continue
        for item in parse_tle(row.get("tle") or ""):
            obj = build_object(item["name"], item["line1"],
                               item["line2"], group, when, now_s)
            if obj is None:
                continue
            if obj["freshness"] == "STALE":
                stale_served = True
            if _matches(obj, bbox, orbit_type or "", freshness or ""):
                objects.append(obj)
                epochs.append(obj["epoch"])
        groups_hit.append(group)
    try:
        limit = max(1, min(MAX_OBJECTS, int(limit)))
    except (TypeError, ValueError):
        limit = 500
    objects.sort(key=lambda o: (o.get("norad_id") or 0))
    capped = len(objects) > limit
    objects = objects[:limit]
    warnings = []
    if stale_served:
        warnings.append("some elements are STALE; ages shown per object")
    if capped:
        warnings.append(f"result capped at {limit} objects")
    if not health_ok(meta):
        warnings.append("source degraded (see provider health)")
    return {**base, "status": "AVAILABLE" if objects else "NO_COVERAGE",
            "objects": objects, "count": len(objects),
            "element_epoch_range": [min(epochs), max(epochs)] if epochs
            else [],
            "groups": sorted(groups_hit),
            "coverage": {"groups": len(groups_hit),
                         "note": "regional tiles are receiver-"
                                 "independent; oceans covered"},
            "source": {"id": SOURCE_ID, "name": SOURCE_NAME,
                       "terms": list(TERMS_URLS),
                       "rights": RIGHTS_STATUS},
            "warnings": warnings}


def get_object(norad_id: Any,
               opener: Optional[Callable] = None,
               now: Optional[datetime] = None) -> Dict[str, Any]:
    """Single propagated object by NORAD id (or UNKNOWN_OBJECT)."""
    try:
        wanted = int(norad_id)
    except (TypeError, ValueError):
        return {"status": "UNKNOWN_OBJECT", "object": None,
                "note": f"bad norad id: {norad_id}"}
    payload = get_satellites(refresh=False, limit=MAX_OBJECTS,
                             opener=opener, now=now)
    for obj in payload.get("objects", []):
        if obj.get("norad_id") == wanted:
            return {"status": "AVAILABLE", "object": obj,
                    "truth_note": payload.get("truth_note", "")}
    if payload.get("status") == "UNAVAILABLE":
        return {"status": "UNAVAILABLE", "object": None,
                "note": payload.get("note", "")}
    return {"status": "UNKNOWN_OBJECT", "object": None,
            "note": f"no object with NORAD id {wanted} in cache; "
                    "refresh elements and retry"}


def get_ground_track(norad_id: Any,
                     now: Optional[datetime] = None) -> Dict[str, Any]:
    """Ground track polyline for one object (or failure status)."""
    try:
        wanted = int(norad_id)
    except (TypeError, ValueError):
        return {"status": "UNKNOWN_OBJECT", "track": [],
                "note": f"bad norad id: {norad_id}"}
    if not sgp4_available():
        return {"status": "UNAVAILABLE", "track": [],
                "note": "sgp4 package not installed"}
    when = now or datetime.now(timezone.utc)
    meta = load_meta()
    for group, row in (meta.get("elements") or {}).items():
        for item in parse_tle(row.get("tle") or ""):
            fields = tle_fields(item["line1"], item["line2"])
            if fields and fields["norad_id"] == wanted:
                try:
                    track = ground_track(item["line1"], item["line2"],
                                         when)
                except ValueError as e:
                    return {"status": "PROPAGATION_FAILED",
                            "track": [], "note": str(e)[:200]}
                return {"status": "AVAILABLE", "track": track,
                        "norad_id": wanted, "group": group,
                        "generated_at": when.replace(
                            microsecond=0).isoformat()}
    return {"status": "UNKNOWN_OBJECT", "track": [],
            "note": f"no elements for NORAD id {wanted} in cache"}


_REGION_BOXES = {
    "europe": (-10.0, 36.0, 30.0, 60.0),
    "japan": (129.0, 31.0, 146.0, 45.5),
    "california": (-124.5, 32.5, -114.0, 42.0),
    "north america": (-170.0, 15.0, -55.0, 72.0),
    "austria": (9.5, 46.4, 17.2, 49.0),
}


def _region_bbox(region: str) -> Optional[Tuple[float, float, float, float]]:
    return _REGION_BOXES.get((region or "").lower().strip())


def supported_regions() -> List[str]:
    return sorted(_REGION_BOXES)


def credentials_status() -> Dict[str, Any]:
    """CelesTrak needs no credentials. Reports that fact structurally."""
    return {"account_required": False,
            "api_key_required": False,
            "auth": "none (keyless public GP data)",
            "terms": list(TERMS_URLS)}
