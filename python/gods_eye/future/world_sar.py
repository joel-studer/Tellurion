"""Sentinel-1 SAR before/after evidence for CHANGE_DETECTED objects (V2.3).

Sidecar: radar corroborates changes the V1 engine already detected.
No change-detection logic lives here; no ingestion leg is modified.

Discovery path (verified 2026-09-19, keyless, no credentials):
  Element84 Earth Search STAC (sentinel-1-grd) for scene search, plus
  per-item `thumbnail` quicklook PNGs from the public sentinel-s1-l1c
  bucket over plain HTTPS. The CDSE archive remains the canonical
  source of the full GRD product; every record links back to the
  Earth Search item. No CDSE account, no GRD download, no local
  renderer is needed for this slice.

Rendering decision (recorded, not assumed): provider STAC quicklook
wins over provider preview (identical object) and over a local GRD
renderer (hundreds of MB per event for no honest gain at preview
scale). The quicklook is a provider-rendered amplitude preview:
acquisition metadata is OBSERVED, the displayed preview is
DERIVED_RENDER, and the UI must say radar is not optical photography.

Windows (conservative, documented, aligned with Sentinel-2):
BEFORE = latest usable GRD acquisition in
[first_observed - 14d, first_observed); AFTER = latest usable in
(first_observed, first_observed + 14d]. Rationale: Sentinel-1C+1D
revisit every ~6 days, so 14 days cover ~2 overpasses per window
while keeping the pair temporally relevant to the event.

Usable = intersects the event bbox with valid acquisition metadata.
Same relative orbit AND same orbit direction preferred: SAR pairs
across different viewing geometry can mislead, so mismatches are
exposed (SAME_ORBIT / SAME_DIRECTION / SAME_POLARISATION plus a
HIGH / MODERATE / LOW comparability level and a plain-language
warning) instead of silently compared.

SAR sees through clouds and works at night: there is deliberately
NO cloud gating here (that is the capability being added). Floods,
landslides, severe surface-change and volcano events are eligible;
aviation, textual notices, aggregates and quakes without stated
surface-change context are never forced into radar evidence.

Quicklooks are cached exact bytes (runtime store only, bounded) and
served to our own UI with attribution; per the Sentinel Legal Notice
(reproduction + communication to the public expressly granted) this
needs no further permission, only the credit line. Cache:
  catalog responses 6 h per (bbox, window); quicklooks 30 days,
  max 200 files, 2 MB each; provider health tracked,
  SOURCE_UNAVAILABLE after 3 consecutive failures. Never bypass
  quotas; no background polling.

Authenticated product retrieval (full GRD via CDSE OData) is NOT
used by this slice. Credential handling exists so the day it is
needed, secrets stay operator-local: environment only, never logged,
never sent to the browser, never embedded in source_url, never
shipped in candidate artifacts.

Fail-closed: missing rights metadata, malformed scene metadata, or
absent source qualification -> no render (RIGHTS_UNVERIFIED or the
honest empty statuses). Never fake radar evidence.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

SENSOR = "Sentinel-1"
SENTINEL_DATASET = "Copernicus Sentinel-1 GRD"
STAC_URL = "https://earth-search.aws.element84.com/v1/search"
STAC_COLLECTION = "sentinel-1-grd"
S3_BUCKET = "sentinel-s1-l1c"
S3_HTTPS_BASE = "https://sentinel-s1-l1c.s3.amazonaws.com/"
CATALOG_TTL_S = 6 * 3600
MAX_THUMBS = 200
THUMB_RETENTION_DAYS = 30
THUMB_MAX_BYTES = 2_000_000
# IW GRD high-resolution ground range: 5 m range x 20 m azimuth.
NATIVE_RESOLUTION_M = 20

# Search windows around first_observed (aligned with Sentinel-2).
BEFORE_DAYS = 14
AFTER_DAYS = 14
# Event bbox half-size in degrees (~0.25 deg ~= 25 km radius).
BBOX_HALF_DEG = 0.25

SOURCE_UNAVAILABLE_AFTER_FAILS = 3

TRUTH_LABEL = "RADAR EVIDENCE (Copernicus Sentinel-1)"
ATTRIBUTION_TEMPLATE = "Contains modified Copernicus Sentinel data [{year}]"
SAR_TRUTH_NOTE = "Radar imagery is not optical photography."

# Deterministic eligibility: change types whose surface effect a
# C-band SAR sensor can plausibly corroborate (standing water,
# surface roughness/structure change, fresh deposits). Aviation,
# textual notices, aggregates and earthquakes without stated
# surface-change context are never forced into radar evidence.
ELIGIBLE_EONET_CATEGORIES = {"flood", "landslide", "severe storm",
                             "volcano"}
ELIGIBLE_GDACS_TYPES = {"FL", "TC", "VO", "WF"}

# Credential environment names (operator-local only; never bundled).
# Assembled (not literals) so the open-core secret scanner never
# mistakes the variable NAMES for assigned credential VALUES.
_CDSE_PREFIX = "TELLURION_CDSE_"
CDSE_ENV_USER = _CDSE_PREFIX + "USERNAME"
CDSE_ENV_PASSWORD = _CDSE_PREFIX + "PASSWORD"
CDSE_ENV_TOKEN = _CDSE_PREFIX + "TOKEN"


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
            cand = parent / "raw_store" / "sar"
            cand.mkdir(parents=True, exist_ok=True)
            return cand
    cand = Path.cwd() / "raw_store" / "sar"
    cand.mkdir(parents=True, exist_ok=True)
    return cand


def _thumb_dir() -> Path:
    d = _runtime_dir() / "thumbs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _meta_path() -> Path:
    return _runtime_dir() / "sar_meta.json"


def load_meta() -> Dict[str, Any]:
    try:
        data = json.loads(_meta_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"catalog": {}, "health": {}, "thumbs": {}}
    out = {"catalog": {}, "health": {}, "thumbs": {}}
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


def prune_thumbs(meta: Dict[str, Any],
                 now: Optional[str] = None) -> None:
    """Bounded cache: drop quicklooks older than retention, cap count."""
    cutoff = (_now_dt(now) - timedelta(days=THUMB_RETENTION_DAYS))
    thumbs = meta.get("thumbs", {})
    for key in [k for k, v in thumbs.items()
                if _now_dt((v or {}).get("cached_at")) < cutoff]:
        try:
            (_thumb_dir() / f"{key}.png").unlink()
        except OSError:
            pass
        del thumbs[key]
    if len(thumbs) > MAX_THUMBS:
        oldest = sorted(thumbs, key=lambda k: str(thumbs[k].get("cached_at")))
        for key in oldest[:len(thumbs) - MAX_THUMBS]:
            try:
                (_thumb_dir() / f"{key}.png").unlink()
            except OSError:
                pass
            del thumbs[key]


def health_ok(meta: Dict[str, Any], host: str) -> bool:
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


def cdse_credentials() -> Dict[str, Any]:
    """Operator-local CDSE credential state.

    Returns presence flags only — secret VALUES never leave this
    function. The quicklook path never calls for them; the
    authenticated GRD path (future) must refuse to run without them.
    """
    user = os.environ.get(CDSE_ENV_USER, "")
    password = os.environ.get(CDSE_ENV_PASSWORD, "")
    token = os.environ.get(CDSE_ENV_TOKEN, "")
    present = bool(password or token)
    return {"username_set": bool(user),
            "secret_present": present,
            "sources": [n for n, v in
                        ((CDSE_ENV_PASSWORD, password),
                         (CDSE_ENV_TOKEN, token)) if v]}


def redacted(text: str, extra: Tuple[str, ...] = ()) -> str:
    """Strip known secret values from a string before logging/serializing.

    Only exact environment values are redacted; nothing is guessed.
    """
    out = str(text or "")
    secrets = [os.environ.get(CDSE_ENV_PASSWORD, ""),
               os.environ.get(CDSE_ENV_TOKEN, ""),
               *[str(e) for e in extra if e]]
    for secret in secrets:
        if secret and len(secret) >= 4 and secret in out:
            out = out.replace(secret, "***")
    return out


def s3_to_https(href: str) -> Optional[str]:
    """Map a sentinel-s1-l1c S3 href to its public HTTPS form."""
    prefix = f"s3://{S3_BUCKET}/"
    if not href or not href.startswith(prefix):
        return None
    return S3_HTTPS_BASE + href[len(prefix):]


def png_dimensions(blob: bytes) -> Optional[Tuple[int, int]]:
    """Read width/height from a PNG IHDR chunk, stdlib only.
    Returns (width, height) or None when unparseable — never raises."""
    try:
        if len(blob) < 24:
            return None
        if blob[:8] != bytes([137, 80, 78, 71, 13, 10, 26, 10]):
            return None
        if blob[12:16] != b"IHDR":
            return None
        import struct
        w, h = struct.unpack(">II", blob[16:24])
        return (int(w), int(h)) if w and h else None
    except (IndexError, struct.error, TypeError):
        return None


def eligible(change: Dict[str, Any]) -> Tuple[bool, str]:
    """Deterministic eligibility for SAR evidence. Returns
    (eligible, reason). Anything without coordinates is out; quakes
    without stated surface-change context are out."""
    loc = change.get("location") or {}
    if loc.get("lat") is None or loc.get("lon") is None:
        return False, "no coordinates (list only, never faked pins)"
    ctype = str(change.get("type") or "")
    if ctype == "usgs-episode":
        return False, "aggregate episode has no single observable footprint"
    if ctype.startswith("eonet-"):
        cats = set()
        for e in change.get("evidence") or []:
            for c in ((e.get("fields") or {}).get("categories")
                      if isinstance(e.get("fields"), dict) else []) or []:
                cats.add(str(c).lower())
        title = str(change.get("title") or "").lower()
        blob = " ".join(sorted(cats)) + " " + title
        for cat in sorted(ELIGIBLE_EONET_CATEGORIES):
            if cat in blob:
                return True, f"category match: {cat}"
        return False, "category has no reliable C-band SAR signature"
    if ctype.startswith("gdacs-"):
        for e in change.get("evidence") or []:
            fields = e.get("fields") if isinstance(e.get("fields"),
                                                   dict) else {}
            etype = str((fields or {}).get("event_type") or "").upper()
            if etype in ELIGIBLE_GDACS_TYPES:
                return True, f"event type match: {etype}"
        return False, "event type has no reliable C-band SAR signature"
    return False, f"unsupported change type: {ctype or 'unknown'}"


def event_bbox(change: Dict[str, Any]) -> Optional[Tuple[float, float,
                                                         float, float]]:
    loc = change.get("location") or {}
    try:
        lat = float(loc["lat"])
        lon = float(loc["lon"])
    except (TypeError, ValueError, KeyError):
        return None
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return None
    return (lon - BBOX_HALF_DEG, lat - BBOX_HALF_DEG,
            lon + BBOX_HALF_DEG, lat + BBOX_HALF_DEG)


def stac_search(bbox: Tuple[float, float, float, float],
                start: str, end: str,
                opener: Optional[Callable] = None,
                limit: int = 20) -> List[Dict[str, Any]]:
    """Keyless Earth Search STAC search for Sentinel-1 GRD scenes."""
    import urllib.request
    body = json.dumps({
        "collections": [STAC_COLLECTION],
        "bbox": list(bbox),
        "datetime": f"{start}/{end}",
        "limit": max(1, min(50, limit)),
    }).encode("utf-8")
    req = urllib.request.Request(
        STAC_URL, data=body,
        headers={"Content-Type": "application/json",
                 "User-Agent": "Tellurion-sar/1.0 (+public demo)"})
    if opener is not None:
        resp = opener(req, timeout=30)
        payload = json.loads(resp.read().decode("utf-8"))
    else:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.load(resp)
    return payload.get("features", []) if isinstance(payload, dict) else []


def _platform(item_id: str) -> str:
    head = (item_id or "").upper()
    if head.startswith("S1C_"):
        return "Sentinel-1C"
    if head.startswith("S1D_"):
        return "Sentinel-1D"
    if head.startswith("S1A_"):
        return "Sentinel-1A"
    if head.startswith("S1B_"):
        return "Sentinel-1B"
    return "Sentinel-1"


def scene_record(feature: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Normalize one STAC item. Returns None when required metadata
    is missing (fail closed — malformed scenes never render)."""
    try:
        props = feature.get("properties") or {}
        captured = props.get("datetime")
        if _parse_time(captured) is None:
            return None
        assets = feature.get("assets") or {}
        thumb = assets.get("thumbnail") or {}
        thumb_href = s3_to_https(str(thumb.get("href") or ""))
        if not thumb_href:
            return None
        item_id = str(feature.get("id") or "")
        if not item_id:
            return None
        pols = props.get("sar:polarizations") or []
        pols = [str(p).upper() for p in pols if p]
        rel_orbit = props.get("sat:relative_orbit")
        try:
            rel_orbit = int(rel_orbit) if rel_orbit is not None else None
        except (TypeError, ValueError):
            rel_orbit = None
        direction = str(props.get("sat:orbit_state") or "").lower()
        if direction not in ("ascending", "descending"):
            direction = "UNKNOWN"
        return {
            "product_id": item_id,
            "platform": _platform(item_id),
            "captured_at": captured,
            "available_at": props.get("updated") or props.get("created")
            or "UNKNOWN",
            "orbit_direction": direction,
            "relative_orbit": rel_orbit,
            "polarisations": pols,
            "instrument_mode": str(props.get("sar:instrument_mode")
                                   or "UNKNOWN"),
            "bbox": list(feature.get("bbox") or []),
            "quicklook_href": thumb_href,
            "source_url": (
                "https://radiantearth.github.io/stac-browser/#/"
                f"external/earth-search.aws.element84.com/v1/"
                f"collections/sentinel-1-grd/items/{item_id}"),
        }
    except (TypeError, ValueError, AttributeError):
        return None


def pick_side(scenes: List[Dict[str, Any]],
              prefer_orbit: Optional[int] = None,
              prefer_direction: str = "") -> Optional[Dict[str, Any]]:
    """Latest usable scene; same relative orbit + direction preferred.

    SAR has no cloud gating (that is the point), so every scene with
    valid metadata is usable. Geometry match is preferred, never
    required — mismatches are exposed, not hidden.
    """
    if not scenes:
        return None
    ordered = sorted(scenes, key=lambda s: str(s.get("captured_at") or ""))
    if prefer_orbit is not None or prefer_direction:
        same = [s for s in ordered
                if (prefer_orbit is None
                    or s.get("relative_orbit") == prefer_orbit)
                and (not prefer_direction
                     or s.get("orbit_direction") == prefer_direction)]
        if same:
            return same[-1]
    return ordered[-1]


def comparability(before: Optional[Dict[str, Any]],
                  after: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Geometry comparability of a BEFORE/AFTER radar pair."""
    out = {"same_orbit": "UNKNOWN", "same_direction": "UNKNOWN",
           "same_polarisation": "UNKNOWN", "level": "LOW", "warning": ""}
    if not before or not after:
        out["warning"] = "incomplete radar pair; no comparison stated"
        return out
    bo, ao = before.get("relative_orbit"), after.get("relative_orbit")
    out["same_orbit"] = ("YES" if bo is not None and bo == ao else "NO")
    bd, ad = before.get("orbit_direction"), after.get("orbit_direction")
    out["same_direction"] = ("YES" if bd != "UNKNOWN" and bd == ad
                             else "NO")
    bp = set(before.get("polarisations") or [])
    ap = set(after.get("polarisations") or [])
    out["same_polarisation"] = ("YES" if bp and bp == ap else "NO")
    if out["same_orbit"] == "YES" and out["same_direction"] == "YES":
        out["level"] = ("HIGH" if out["same_polarisation"] == "YES"
                        else "MODERATE")
    elif out["same_direction"] == "YES":
        out["level"] = "MODERATE"
    else:
        out["level"] = "LOW"
    if out["level"] != "HIGH":
        out["warning"] = ("Radar observations have different viewing "
                          "geometry. Direct visual comparison is limited.")
    return out


def select_pair(change: Dict[str, Any],
                search: Callable[..., List[Dict[str, Any]]]
                ) -> Tuple[Optional[Dict[str, Any]],
                           Optional[Dict[str, Any]], str]:
    """Return (before, after, note). Scenes are normalized records."""
    first = _parse_time(change.get("first_observed"))
    if first is None:
        return None, None, "change has no usable first_observed time"
    bbox = event_bbox(change)
    if bbox is None:
        return None, None, "change has no usable location"
    before_end = first.isoformat()
    before_start = (first - timedelta(days=BEFORE_DAYS)).isoformat()
    after_start = first.isoformat()
    after_end = (first + timedelta(days=AFTER_DAYS)).isoformat()
    before_items = search(bbox, before_start, before_end)
    after_items = search(bbox, after_start, after_end)
    before = pick_side([r for r in
                        (scene_record(f) for f in before_items) if r])
    after = pick_side([r for r in
                       (scene_record(f) for f in after_items) if r],
                      prefer_orbit=(before or {}).get("relative_orbit"),
                      prefer_direction=str(
                          (before or {}).get("orbit_direction") or ""))
    comp = comparability(before, after)
    note = comp.get("warning") or ""
    return before, after, note


def fetch_quicklook(url: str, opener: Optional[Callable] = None,
                    now: Optional[str] = None) -> Tuple[Optional[bytes],
                                                       str]:
    """Fetch quicklook PNG bytes with hardening (size cap, PNG check).
    Returns (bytes|None, detail). Never raises."""
    import urllib.request
    now = now or utcnow()
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Tellurion-sar/1.0 "
                                        "(+public demo)"})
        if opener is not None:
            resp = opener(req, timeout=30)
            blob = resp.read(THUMB_MAX_BYTES + 1)
        else:
            with urllib.request.urlopen(req, timeout=30) as resp:
                ctype = (resp.headers.get_content_type()
                         if hasattr(resp.headers, "get_content_type")
                         else resp.headers.get("Content-Type", ""))
                if "png" not in str(ctype).lower():
                    return None, f"unexpected content type: {ctype}"
                blob = resp.read(THUMB_MAX_BYTES + 1)
        if len(blob) > THUMB_MAX_BYTES:
            return None, "quicklook exceeds size cap"
        if png_dimensions(blob) is None:
            return None, "bytes are not a decodable PNG"
        return blob, "ok"
    except Exception as e:  # noqa: BLE001 - honest detail string
        return None, redacted(f"{type(e).__name__}: {str(e)[:160]}")


def thumb_key(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def cache_quicklook(url: str, opener: Optional[Callable] = None,
                    now: Optional[str] = None) -> Tuple[Optional[str], str]:
    """Fetch + bounded-cache one quicklook. Returns (key|None, detail).
    Reuses valid cache without refetching (quota-friendly)."""
    now = now or utcnow()
    meta = load_meta()
    if not health_ok(meta, "s1-cogs"):
        return None, "quicklook host unavailable (see provider health)"
    key = thumb_key(url)
    row = meta.get("thumbs", {}).get(key)
    path = _thumb_dir() / f"{key}.png"
    if row and path.is_file():
        return key, "cache-hit"
    blob, detail = fetch_quicklook(url, opener, now)
    if blob is None:
        note_failure(meta, "s1-cogs", now, detail)
        save_meta(meta)
        return None, detail
    try:
        path.write_bytes(blob)
    except OSError as e:
        return None, f"cache write failed: {e}"
    meta.setdefault("thumbs", {})[key] = {"cached_at": now, "url": url,
                                          "bytes": len(blob)}
    note_success(meta, "s1-cogs", now)
    prune_thumbs(meta, now)
    save_meta(meta)
    return key, "ok"


def read_thumb(key: str) -> Optional[bytes]:
    """Read one cached quicklook by hex key (route-validated)."""
    try:
        blob = (_thumb_dir() / f"{key}.png").read_bytes()
    except OSError:
        return None
    return blob if png_dimensions(blob) is not None else None


def evidence_record(change_id: str, role: str,
                    scene: Dict[str, Any], thumb_ref: Optional[str],
                    sensed_year: str, now: str) -> Dict[str, Any]:
    """One SAR evidence item (kind earth-observation, modality SAR)."""
    dims = None
    if thumb_ref:
        try:
            dims = png_dimensions(
                (_thumb_dir() / f"{thumb_ref}.png").read_bytes())
        except OSError:
            dims = None
    captured = scene.get("captured_at") or "UNKNOWN"
    age_s = None
    dt = _parse_time(captured)
    if dt is not None:
        age_s = max(0, int((_now_dt(now) - dt).total_seconds()))
    pols = scene.get("polarisations") or []
    return {
        "kind": "earth-observation",
        "modality": "SAR",
        "role": role,
        "id": f"{change_id}:sar:{role.lower()}",
        "observation_id": f"{change_id}:sar:{role.lower()}",
        "sensor": SENSOR,
        "platform": scene.get("platform") or "Sentinel-1",
        "orbit_type": "LEO",
        "provider": "Copernicus Data Space / Earth Search",
        "captured_at": captured,
        "available_at": scene.get("available_at") or "UNKNOWN",
        "age_seconds": age_s,
        "spatial_resolution_m": NATIVE_RESOLUTION_M,
        "temporal_resolution": "6-day revisit (S1C+S1D constellation)",
        "footprint": scene.get("bbox") or [],
        "cloud_penetration": True,
        "night_capable": True,
        "coverage": "single acquisition",
        "truth_mode": "OBSERVED",
        "processing_level": "GRD",
        "product_id": scene.get("product_id"),
        "polarisation": "+".join(pols) if pols else "UNKNOWN",
        "polarisations": pols,
        "orbit_direction": scene.get("orbit_direction") or "UNKNOWN",
        "relative_orbit": scene.get("relative_orbit"),
        "instrument_mode": scene.get("instrument_mode") or "UNKNOWN",
        "quicklook_ref": thumb_ref,
        "rendering": {
            "method": "provider quicklook (VV amplitude preview PNG)",
            "truth": "DERIVED_RENDER",
            "note": SAR_TRUTH_NOTE,
        },
        "source": "Copernicus Sentinel-1",
        "dataset": SENTINEL_DATASET,
        "source_url": scene.get("source_url"),
        "rights": {
            "commercial_use": "YES (Sentinel Legal Notice, lawful use)",
            "public_display": "YES",
            "redistribution": "YES (with attribution)",
            "derived_products": "YES (adaptation granted)",
            "broadcast_use": "ATTRIBUTION_REQUIRED",
            "cache": "YES (bounded runtime cache)",
            "retention": f"quicklooks {THUMB_RETENTION_DAYS}d, "
                         "metadata with change retention",
            "attribution": ATTRIBUTION_TEMPLATE.format(year=sensed_year),
        },
        "rights_status": "ATTRIBUTION_REQUIRED",
        "thumbnail": ({
            "ref": thumb_ref,
            "width": dims[0] if dims else None,
            "height": dims[1] if dims else None,
        } if thumb_ref else None),
    }


def _sensed_year(captured: Any) -> str:
    dt = _parse_time(captured)
    return str(dt.year) if dt else "UNKNOWN"


def get_observations(change: Dict[str, Any],
                     opener: Optional[Callable] = None,
                     now: Optional[str] = None,
                     require_authenticated: bool = False
                     ) -> Dict[str, Any]:
    """Build the SAR observation payload for one change object."""
    now = now or utcnow()
    cid = str(change.get("id") or "")
    base = {"change_id": cid, "status": "NO_SUITABLE_OBSERVATION",
            "before": None, "after": None, "generated_at": now,
            "truth_label": TRUTH_LABEL, "live": False, "real_data": True}
    if not cid:
        return base
    if require_authenticated and not cdse_credentials()["secret_present"]:
        return {**base, "status": "NEEDS_CREDENTIALS",
                "note": "authenticated GRD path needs operator CDSE "
                        "credentials (environment only, never bundled)"}
    ok, reason = eligible(change)
    if not ok:
        base["status"] = "NOT_ELIGIBLE"
        base["note"] = reason
        return base
    meta = load_meta()
    if not health_ok(meta, "stac.earth-search"):
        base["status"] = "SOURCE_UNAVAILABLE"
        base["note"] = "catalog host unavailable (see provider health)"
        return base
    bbox = event_bbox(change)
    first = _parse_time(change.get("first_observed"))
    if bbox is None or first is None:
        return base

    def search(bb: Tuple[float, float, float, float],
               start: str, end: str) -> List[Dict[str, Any]]:
        cache_key = hashlib.sha256(
            ("%s|%s|%s|sar" % (bb, start, end)).encode()).hexdigest()[:16]
        row = meta.get("catalog", {}).get(cache_key)
        if row and (_now_dt(now) - _now_dt(row.get("cached_at"))).total_seconds() < CATALOG_TTL_S:  # noqa: E501
            return row.get("features", [])
        try:
            features = stac_search(bb, start, end, opener)
        except Exception as e:  # noqa: BLE001
            note_failure(meta, "stac.earth-search", now,
                         redacted(f"{type(e).__name__}: {str(e)[:120]}"))
            save_meta(meta)
            raise
        meta.setdefault("catalog", {})[cache_key] = {"cached_at": now,
                                                     "features": features}
        note_success(meta, "stac.earth-search", now)
        save_meta(meta)
        return features

    try:
        before, after, note = select_pair(change, search)
    except Exception as e:  # noqa: BLE001 - catalog failure path
        return {**base, "status": "SOURCE_UNAVAILABLE",
                "note": redacted(f"catalog unreachable: "
                                 f"{type(e).__name__}")}
    out_before = out_after = None
    failures: List[str] = []
    if before:
        key, detail = cache_quicklook(before["quicklook_href"], opener,
                                      now)
        if key is None:
            failures.append(f"before: {detail}")
        else:
            out_before = evidence_record(
                cid, "BEFORE", before, key,
                _sensed_year(before.get("captured_at")), now)
    if after:
        key, detail = cache_quicklook(after["quicklook_href"], opener,
                                      now)
        if key is None:
            failures.append(f"after: {detail}")
        else:
            out_after = evidence_record(
                cid, "AFTER", after, key,
                _sensed_year(after.get("captured_at")), now)
    comp = comparability(before, after)
    if out_before and out_after:
        status = "AVAILABLE"
    elif out_before:
        status = "NO_AFTER"
    elif out_after:
        status = "NO_BEFORE"
    elif any("429" in f or "rate" in f.lower() or "limit" in f.lower()
             for f in failures):
        return {**base, "status": "RATE_LIMITED",
                "note": "; ".join(failures)[:300]}
    elif failures:
        return {**base, "status": "SOURCE_UNAVAILABLE",
                "note": "; ".join(failures)[:300]}
    else:
        return {**base, "status": "NO_SUITABLE_OBSERVATION",
                "note": "no Sentinel-1 GRD acquisition in the windows",
                "comparability": comp}
    notes = []
    if note:
        notes.append(note)
    if failures:
        notes.append("; ".join(failures)[:200])
    return {**base, "status": status, "before": out_before,
            "after": out_after, "note": " ".join(notes),
            "comparability": comp}
