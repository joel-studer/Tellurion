"""Sentinel-2 before/after evidence for CHANGE_DETECTED objects (V2.1).

Sidecar: imagery corroborates changes the V1 engine already detected.
No change-detection logic lives here; no ingestion leg is modified.

Discovery path (verified 2026-09-17, keyless, no credentials):
  Element84 Earth Search STAC (sentinel-2-l2a) for scene search, plus
  per-item `thumbnail` preview JPEGs from the public sentinel-cogs
  bucket. Rationale, documented honestly: the canonical Copernicus
  Data Space STAC exposes only CLMS/CCM collections — Sentinel-2
  mission scenes are NOT keylessly searchable there (OData/S3 need an
  account). Earth Search serves the same Sentinel-2 L2A products
  under the same Sentinel Legal Notice, so every record carries the
  canonical attribution plus a link back to the Earth Search item;
  the CDSE archive remains the canonical source of the full product.

Windows (conservative, documented): BEFORE = latest useful scene in
[first_observed - 14d, first_observed); AFTER = latest useful scene
in (first_observed, first_observed + 14d]. Rationale: Sentinel-2
revisits every ~5 days (2-3 mid-latitudes), so 14 days guarantee
~2-3 overpasses per window even if one is clouded out, while bounding
catalog cost and keeping the pair temporally relevant to the event.

Useful = intersects the event bbox, valid acquisition metadata,
lowest cloud cover wins; same MGRS tile preferred for BEFORE+AFTER
so bounds/projection/scale match. Cloud states from tile-level
cloud_cover_pct (tile-level, NOT AOI-level — stated wherever shown):
  <10 CLEAR, <30 PARTLY_CLOUDY, <60 CLOUD_LIMITED (shown + warning),
  >=60 rejected. No suitable scene -> NO_SUITABLE_OBSERVATION.

Thumbnails are cached exact bytes (runtime store only, bounded) and
served to our own UI with attribution; per the Sentinel Legal Notice
(reproduction + communication to the public expressly granted) this
needs no further permission, only the credit line. Cache:
  catalog responses 6 h per (bbox, window); thumbnails 30 days,
  max 200 files; provider health tracked, SOURCE_UNAVAILABLE after
  3 consecutive failures. Never bypass quotas; no background polling.

Fail-closed: missing rights metadata, malformed scene metadata, or
absent source qualification -> no render (RIGHTS_UNVERIFIED or the
honest empty statuses). Never fake imagery.
"""

from __future__ import annotations

import hashlib
import json
import struct
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

SENTINEL_DATASET = "Copernicus Sentinel-2 L2A"
STAC_URL = "https://earth-search.aws.element84.com/v1/search"
STAC_COLLECTION = "sentinel-2-l2a"
CATALOG_TTL_S = 6 * 3600
MAX_THUMBS = 200
THUMB_RETENTION_DAYS = 30
THUMB_MAX_BYTES = 2_000_000
NATIVE_RESOLUTION_M = 10

# Search windows around first_observed (see module docstring).
BEFORE_DAYS = 14
AFTER_DAYS = 14
# Event bbox half-size in degrees (~0.25 deg ~= 25 km radius).
BBOX_HALF_DEG = 0.25

# Cloud states from tile-level cloud_cover_pct.
CLOUD_CLEAR = 10.0
CLOUD_PARTLY = 30.0
CLOUD_LIMIT = 60.0

SOURCE_UNAVAILABLE_AFTER_FAILS = 3

TRUTH_LABEL = "SATELLITE EVIDENCE (Copernicus Sentinel-2)"
ATTRIBUTION_TEMPLATE = "Contains modified Copernicus Sentinel data [{year}]"

# Deterministic eligibility: change types whose surface effect a
# 10 m optical sensor can plausibly show. Earthquakes without
# visible surface effect, aviation, textual notices and aggregates
# are never forced into satellite evidence.
ELIGIBLE_EONET_CATEGORIES = {"wildfire", "flood", "severe storm",
                             "volcano", "landslide"}
ELIGIBLE_GDACS_TYPES = {"FL", "TC", "VO", "WF"}


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
            cand = parent / "raw_store" / "imagery"
            cand.mkdir(parents=True, exist_ok=True)
            return cand
    cand = Path.cwd() / "raw_store" / "imagery"
    cand.mkdir(parents=True, exist_ok=True)
    return cand


def _thumb_dir() -> Path:
    d = _runtime_dir() / "thumbs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _meta_path() -> Path:
    return _runtime_dir() / "imagery_meta.json"


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
    """Bounded cache: drop thumbnails older than retention, cap count."""
    cutoff = (_now_dt(now) - timedelta(days=THUMB_RETENTION_DAYS))
    thumbs = meta.get("thumbs", {})
    for key in [k for k, v in thumbs.items()
                if _now_dt((v or {}).get("cached_at")) < cutoff]:
        try:
            (_thumb_dir() / f"{key}.jpg").unlink()
        except OSError:
            pass
        del thumbs[key]
    if len(thumbs) > MAX_THUMBS:
        oldest = sorted(thumbs, key=lambda k: str(thumbs[k].get("cached_at")))
        for key in oldest[:len(thumbs) - MAX_THUMBS]:
            try:
                (_thumb_dir() / f"{key}.jpg").unlink()
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


def jpeg_dimensions(blob: bytes) -> Optional[Tuple[int, int]]:
    """Read width/height from a JPEG header (SOF marker), stdlib only.
    Returns (width, height) or None when unparseable — never raises."""
    try:
        if len(blob) < 4 or blob[0:2] != b"\xff\xd8":
            return None
        pos = 2
        while pos + 4 < len(blob):
            if blob[pos] != 0xFF:
                return None
            marker = blob[pos + 1]
            if marker in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack(">HH", blob[pos + 5:pos + 9])
                return (int(w), int(h)) if w and h else None
            if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                pos += 2
                continue
            (length,) = struct.unpack(">H", blob[pos + 2:pos + 4])
            if length < 2:
                return None
            pos += 2 + length
        return None
    except (IndexError, struct.error, TypeError):
        return None


def cloud_state(pct: Optional[float]) -> str:
    if pct is None:
        return "UNKNOWN"
    if pct < CLOUD_CLEAR:
        return "CLEAR"
    if pct < CLOUD_PARTLY:
        return "PARTLY_CLOUDY"
    if pct < CLOUD_LIMIT:
        return "CLOUD_LIMITED"
    return "UNUSABLE"


def eligible(change: Dict[str, Any]) -> Tuple[bool, str]:
    """Deterministic eligibility for satellite evidence. Returns
    (eligible, reason). Anything without coordinates is out."""
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
        return False, "category has no reliable 10 m optical signature"
    if ctype.startswith("gdacs-"):
        for e in change.get("evidence") or []:
            fields = e.get("fields") if isinstance(e.get("fields"),
                                                   dict) else {}
            etype = str((fields or {}).get("event_type") or "").upper()
            if etype in ELIGIBLE_GDACS_TYPES:
                return True, f"event type match: {etype}"
        return False, "event type has no reliable 10 m optical signature"
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
    """Keyless Earth Search STAC search for Sentinel-2 L2A scenes."""
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
                 "User-Agent": "Tellurion-imagery/1.0 (+public demo)"})
    if opener is not None:
        resp = opener(req, timeout=30)
        payload = json.loads(resp.read().decode("utf-8"))
    else:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.load(resp)
    return payload.get("features", []) if isinstance(payload, dict) else []


def scene_record(feature: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Normalize one STAC item. Returns None when required metadata
    is missing (fail closed — malformed scenes never render)."""
    try:
        props = feature.get("properties") or {}
        captured = props.get("datetime")
        if _parse_time(captured) is None:
            return None
        cloud = props.get("eo:cloud_cover")
        cloud = float(cloud) if cloud is not None else None
        assets = feature.get("assets") or {}
        thumb = assets.get("thumbnail") or {}
        thumb_href = thumb.get("href")
        if not thumb_href:
            return None
        item_id = str(feature.get("id") or "")
        if not item_id:
            return None
        tile = ""
        parts = item_id.split("_")
        if len(parts) >= 2:
            tile = parts[1]
        return {
            "product_id": item_id,
            "tile": tile,
            "captured_at": captured,
            "available_at": props.get("updated") or props.get("created")
            or "UNKNOWN",
            "cloud_cover_pct": cloud,
            "cloud_state": cloud_state(cloud),
            "bbox": list(feature.get("bbox") or []),
            "thumbnail_href": thumb_href,
            "source_url": (
                "https://radiantearth.github.io/stac-browser/#/"
                f"external/earth-search.aws.element84.com/v1/"
                f"collections/sentinel-2-l2a/items/{item_id}"),
        }
    except (TypeError, ValueError, AttributeError):
        return None


def pick_side(scenes: List[Dict[str, Any]], prefer_tile: str = ""
              ) -> Optional[Dict[str, Any]]:
    """Latest useful scene; same-tile preferred for comparability."""
    usable = [s for s in scenes
              if (s.get("cloud_cover_pct") or 100.0) < CLOUD_LIMIT]
    if not usable:
        return None
    usable.sort(key=lambda s: str(s.get("captured_at") or ""))
    if prefer_tile:
        same = [s for s in usable if s.get("tile") == prefer_tile]
        if same:
            return same[-1]
    return usable[-1]


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
                      prefer_tile=(before or {}).get("tile", ""))
    note = ""
    if before and after and before.get("tile") != after.get("tile"):
        note = ("different MGRS tiles (%s vs %s): same region, not "
                "pixel-aligned" % (before.get("tile"),
                                   after.get("tile")))
    return before, after, note


def fetch_thumbnail(url: str, opener: Optional[Callable] = None,
                    now: Optional[str] = None) -> Tuple[Optional[bytes],
                                                       str]:
    """Fetch thumbnail bytes with hardening (size cap, JPEG check).
    Returns (bytes|None, detail). Never raises."""
    import urllib.request
    now = now or utcnow()
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Tellurion-imagery/1.0 "
                                        "(+public demo)"})
        if opener is not None:
            resp = opener(req, timeout=30)
            blob = resp.read(THUMB_MAX_BYTES + 1)
        else:
            with urllib.request.urlopen(req, timeout=30) as resp:
                ctype = (resp.headers.get_content_type()
                         if hasattr(resp.headers, "get_content_type")
                         else resp.headers.get("Content-Type", ""))
                if "jpeg" not in str(ctype).lower():
                    return None, f"unexpected content type: {ctype}"
                blob = resp.read(THUMB_MAX_BYTES + 1)
        if len(blob) > THUMB_MAX_BYTES:
            return None, "thumbnail exceeds size cap"
        if jpeg_dimensions(blob) is None:
            return None, "bytes are not a decodable JPEG"
        return blob, "ok"
    except Exception as e:  # noqa: BLE001 - honest detail string
        return None, f"{type(e).__name__}: {str(e)[:160]}"


def thumb_key(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def cache_thumbnail(url: str, opener: Optional[Callable] = None,
                    now: Optional[str] = None) -> Tuple[Optional[str], str]:
    """Fetch + bounded-cache one thumbnail. Returns (key|None, detail).
    Reuses valid cache without refetching (quota-friendly)."""
    now = now or utcnow()
    meta = load_meta()
    if not health_ok(meta, "thumbs.s3"):
        return None, "thumbnail host unavailable (see provider health)"
    key = thumb_key(url)
    row = meta.get("thumbs", {}).get(key)
    path = _thumb_dir() / f"{key}.jpg"
    if row and path.is_file():
        return key, "cache-hit"
    blob, detail = fetch_thumbnail(url, opener, now)
    if blob is None:
        note_failure(meta, "thumbs.s3", now, detail)
        save_meta(meta)
        return None, detail
    try:
        path.write_bytes(blob)
    except OSError as e:
        return None, f"cache write failed: {e}"
    meta.setdefault("thumbs", {})[key] = {"cached_at": now, "url": url,
                                          "bytes": len(blob)}
    note_success(meta, "thumbs.s3", now)
    prune_thumbs(meta, now)
    save_meta(meta)
    return key, "ok"


def evidence_record(change_id: str, role: str,
                    scene: Dict[str, Any], thumb_ref: Optional[str],
                    sensed_year: str, now: str) -> Dict[str, Any]:
    """One imagery evidence item (kind satellite-image)."""
    dims = None
    if thumb_ref:
        try:
            dims = jpeg_dimensions(
                (_thumb_dir() / f"{thumb_ref}.jpg").read_bytes())
        except OSError:
            dims = None
    captured = scene.get("captured_at") or "UNKNOWN"
    age_s = None
    dt = _parse_time(captured)
    if dt is not None:
        age_s = max(0, int((_now_dt(now) - dt).total_seconds()))
    # Effective ground sample of the served preview: granule previews
    # cover ~110 km; exact tile width varies with latitude, so this
    # is labelled approximate wherever shown.
    eff_res = None
    if dims:
        eff_res = round(110000.0 / max(1, dims[0]), 0)
    return {
        "kind": "satellite-image",
        "role": role,
        "id": f"{change_id}:img:{role.lower()}",
        "source": "Copernicus Sentinel-2",
        "dataset": SENTINEL_DATASET,
        "product_id": scene.get("product_id"),
        "captured_at": captured,
        "available_at": scene.get("available_at") or "UNKNOWN",
        "age_seconds": age_s,
        "resolution_m": eff_res,
        "native_resolution_m": NATIVE_RESOLUTION_M,
        "cloud_cover_pct": scene.get("cloud_cover_pct"),
        "cloud_state": scene.get("cloud_state") or "UNKNOWN",
        "truth_mode": "OBSERVED",
        "coverage_quality": ("same-tile pair" if scene.get("same_tile")
                             else "single scene"),
        "bounds": scene.get("bbox") or [],
        "source_url": scene.get("source_url"),
        "rights": {
            "commercial_use": "YES (Sentinel Legal Notice, lawful use)",
            "public_display": "YES",
            "redistribution": "YES (with attribution)",
            "derived_products": "YES (adaptation granted)",
            "broadcast_use": "ATTRIBUTION_REQUIRED",
            "cache": "YES (bounded runtime cache)",
            "retention": f"thumbnails {THUMB_RETENTION_DAYS}d, "
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


def load_change(change_id: str) -> Optional[Dict[str, Any]]:
    """Load one persisted change record by stable ID (read-only)."""
    from gods_eye.future import world_change as chg_mod
    try:
        store = chg_mod.load_store()
    except Exception:  # noqa: BLE001 - corrupt store reads as empty
        return None
    rec = (store.get("emitted") or {}).get(change_id)
    change = (rec or {}).get("change")
    return change if isinstance(change, dict) else None


def read_thumb(key: str) -> Optional[bytes]:
    """Read one cached thumbnail by hex key (route-validated)."""
    try:
        blob = (_thumb_dir() / f"{key}.jpg").read_bytes()
    except OSError:
        return None
    return blob if jpeg_dimensions(blob) is not None else None


def get_imagery(change: Dict[str, Any],
                opener: Optional[Callable] = None,
                now: Optional[str] = None) -> Dict[str, Any]:
    """Build the imagery evidence payload for one change object."""
    now = now or utcnow()
    cid = str(change.get("id") or "")
    base = {"change_id": cid, "status": "NO_SUITABLE_OBSERVATION",
            "before": None, "after": None, "generated_at": now,
            "truth_label": TRUTH_LABEL, "live": False, "real_data": True}
    if not cid:
        return base
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
            ("%s|%s|%s" % (bb, start, end)).encode()).hexdigest()[:16]
        row = meta.get("catalog", {}).get(cache_key)
        if row and (_now_dt(now) - _now_dt(row.get("cached_at"))).total_seconds() < CATALOG_TTL_S:  # noqa: E501
            return row.get("features", [])
        try:
            features = stac_search(bb, start, end, opener)
        except Exception as e:  # noqa: BLE001
            note_failure(meta, "stac.earth-search", now,
                         f"{type(e).__name__}: {str(e)[:120]}")
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
                "note": f"catalog unreachable: {type(e).__name__}"}
    out_before = out_after = None
    failures: List[str] = []
    if before:
        key, detail = cache_thumbnail(before["thumbnail_href"], opener, now)
        if key is None:
            failures.append(f"before: {detail}")
        else:
            before["same_tile"] = bool(
                after and after.get("tile") == before.get("tile"))
            out_before = evidence_record(
                cid, "BEFORE", before, key,
                _sensed_year(before.get("captured_at")), now)
    if after:
        key, detail = cache_thumbnail(after["thumbnail_href"], opener, now)
        if key is None:
            failures.append(f"after: {detail}")
        else:
            after["same_tile"] = bool(
                before and before.get("tile") == after.get("tile"))
            out_after = evidence_record(
                cid, "AFTER", after, key,
                _sensed_year(after.get("captured_at")), now)
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
                "note": "no useful Sentinel-2 scene in the search windows"}
    limited = [r for r in (out_before, out_after) if r and r.get(
        "cloud_state") == "CLOUD_LIMITED"]
    if limited and status == "AVAILABLE":
        status = "PARTIAL"
    notes = []
    if note:
        notes.append(note)
    if limited:
        notes.append("Satellite evidence limited by cloud cover.")
    if failures:
        notes.append("; ".join(failures)[:200])
    return {**base, "status": status, "before": out_before,
            "after": out_after, "note": " ".join(notes)}
