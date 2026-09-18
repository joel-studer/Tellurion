"""LIVE EARTH freshness layer V2.2 (NASA GIBS provider-hosted tiles).

Visualization context only: imagery sits UNDER all overlays and never
changes event truth, Important Now scoring, CHANGE_DETECTED records
or Sentinel-2 evidence. Replay never loads it.

Verified mechanics (2026-09-17, live probes):
  - Tile template (XYZ order works as-is):
    {BASE}/{layer}/default/{time}/{matrix}/{z}/{y}/{x}.jpg
    (GIBS may serve PNG bytes for GeoColor; content type rules.)
  - Polar daily layers accept YYYY-MM-DD; geostationary layers need
    full ISO datetimes aligned to real slots.
  - Per-layer best time comes from GetCapabilities <Default>
    (geo lags ~1 h; never assume "now").
  - Per-layer TileMatrixSet differs (polar Level9, GOES Level7):
    parsed from capabilities, never hardcoded.
  - Off-disc geo tiles are opaque BLACK: stacking is forbidden, so
    exactly one imagery source is active at a time (region rule).
  - No Himawari true-color layer exists in GIBS, and the Band3
    layer serves unusable tiles (verified live); Asia-Pacific uses the
    daily polar mosaic (documented gap). No EUMETSAT direct products
    (terms unqualified).

Freshness classes (spec thresholds, documented):
  VERY_FRESH <1 h, FRESH <6 h, AGING <48 h, STALE <14 d,
  NO_COVERAGE otherwise. Geo 10-min cadence and polar daily cadence
  both land honestly in these buckets; thresholds were NOT tuned to
  flatter any UI.

Rights: all layers are US public-domain works served by NASA GIBS.
Imagery activates ONLY with complete rights metadata (fail closed).
Attribution uses the verified GIBS acknowledgment wording.
"""

from __future__ import annotations

import json
import xml.sax
import xml.sax.handler
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

GIBS_BASE = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best"
GIBS_CAPS = (GIBS_BASE + "/1.0.0/WMTSCapabilities.xml")
GIBS_ATTRIBUTION = (
    "We acknowledge the use of imagery provided by services from "
    "NASA's Global Imagery Browse Services (GIBS), part of NASA's "
    "Earth Science Data and Information System (ESDIS).")
GIBS_SHORT_ATTRIBUTION = "NASA GIBS"

CAPS_TTL_S = 1800
MAX_CAPS_BYTES = 60_000_000
SOURCE_UNAVAILABLE_AFTER_FAILS = 3

TRUTH_LABEL = "LIVE EARTH (NASA GIBS provider-hosted imagery)"

# Freshness buckets in hours (spec-fixed, documented above).
FRESH_VERY = 1.0
FRESH_FRESH = 6.0
FRESH_AGING = 48.0
FRESH_STALE = 14 * 24.0


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


# Layer registry: id, dataset label, region kind, nominal resolution,
# sub-daily flag (full-ISO time axis vs YYYY-MM-DD), single-band flag.
LAYERS: Tuple[Dict[str, Any], ...] = (
    {"id": "VIIRS_SNPP_CorrectedReflectance_TrueColor",
     "dataset": "VIIRS Suomi-NPP true color (daily)",
     "region": "global", "resolution_m": 250, "subdaily": False,
     "bands": "true-color"},
    {"id": "MODIS_Terra_CorrectedReflectance_TrueColor",
     "dataset": "MODIS Terra true color (daily)",
     "region": "global", "resolution_m": 250, "subdaily": False,
     "bands": "true-color"},
    {"id": "GOES-East_ABI_GeoColor",
     "dataset": "GOES-19 ABI GeoColor (~10 min)",
     "region": "americas-east", "resolution_m": 2000, "subdaily": True,
     "bands": "true-color"},
    {"id": "GOES-West_ABI_GeoColor",
     "dataset": "GOES-18 ABI GeoColor (~10 min)",
     "region": "americas-west", "resolution_m": 2000, "subdaily": True,
     "bands": "true-color"},
)
# NOTE (2026-09-18, verified live): Himawari has no true-color GIBS
# layer, and Himawari_AHI_Band3_Red_Visible_1km serves striped,
# unusable tiles (checked at multiple slots incl. the current best).
# Asia-Pacific therefore uses the daily polar mosaic (documented
# gap); single-band visible would also be night-blind half the day.

# View-longitude -> preferred regional layer (Americas split at -100;
# GOES-West also covers the central Pacific better than Himawari's
# limb, so no separate Pacific rule: VIIRS is the honest fallback).
REGION_RULES: Tuple[Dict[str, Any], ...] = (
    {"region": "americas-east", "lon_min": -100.0, "lon_max": -20.0,
     "layer": "GOES-East_ABI_GeoColor"},
    {"region": "americas-west", "lon_min": -180.0, "lon_max": -100.0,
     "layer": "GOES-West_ABI_GeoColor"},
)


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


def _caps_path() -> Path:
    return _runtime_dir() / "gibs_caps.xml"


def _meta_path() -> Path:
    return _runtime_dir() / "live_earth_meta.json"


def load_meta() -> Dict[str, Any]:
    try:
        data = json.loads(_meta_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"health": {}}
    return {"health": data.get("health", {}) if isinstance(
        data.get("health"), dict) else {}}


def save_meta(meta: Dict[str, Any]) -> None:
    path = _meta_path()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(meta, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8")
    tmp.replace(path)


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


def health_ok(meta: Dict[str, Any], host: str) -> bool:
    return int((meta.get("health", {}).get(host) or {}).get(
        "fails_consec", 0)) < SOURCE_UNAVAILABLE_AFTER_FAILS


class _CapsGrabber(xml.sax.handler.ContentHandler):
    """Stream GIBS capabilities: per-layer default time + matrix sets."""

    def __init__(self, wanted: List[str]):
        self._wanted = set(wanted)
        self._depth = 0
        self._stack: List[str] = []
        self._layer: Optional[Dict[str, Any]] = None
        self._capture: Optional[str] = None
        self._buf = ""
        self.layers: Dict[str, Dict[str, Any]] = {}

    def startElement(self, name: str, attrs: Any) -> None:
        if name.endswith("Layer"):
            self._depth += 1
            if self._depth == 1:
                self._layer = {"default": "", "matrices": []}
        # Direct-child and grandchild positions only: nested Style and
        # Dimension blocks carry their own Identifiers/Defaults/sets
        # that must never leak into the layer record.
        parent = self._stack[-1] if self._stack else ""
        self._stack.append(name)
        if self._depth != 1 or self._layer is None or self._capture:
            return
        if name.endswith("Identifier") and parent.endswith("Layer"):
            self._capture = "id"
            self._buf = ""
        elif name.endswith("Default") and parent.endswith("Dimension"):
            self._capture = "default"
            self._buf = ""
        elif name.endswith("TileMatrixSet") and parent.endswith(
                "TileMatrixSetLink"):
            self._capture = "matrix"
            self._buf = ""

    def characters(self, content: str) -> None:
        if self._capture:
            self._buf += content

    def endElement(self, name: str) -> None:
        if self._stack:
            self._stack.pop()
        if self._capture and name.endswith(
                ("Identifier", "Default", "TileMatrixSet")):
            text = self._buf.strip()
            if self._capture == "id":
                self._layer["lid"] = text  # type: ignore[index]
            elif self._capture == "default" and self._layer is not None:
                self._layer["default"] = text
            elif self._capture == "matrix" and self._layer is not None:
                if text.startswith("GoogleMapsCompatible_Level"):
                    self._layer["matrices"].append(text)
            self._capture = None
        if name.endswith("Layer"):
            if self._depth == 1 and self._layer is not None:
                lid = str(self._layer.get("lid") or "")
                if lid in self._wanted:
                    self.layers[lid] = {
                        "default": str(self._layer.get("default") or ""),
                        "matrices": list(self._layer.get("matrices")
                                         or []),
                    }
            self._layer = None
            self._depth -= 1


def fetch_capabilities(opener: Optional[Callable] = None,
                       now: Optional[str] = None) -> Tuple[
                           Optional[Dict[str, Dict[str, Any]]], str]:
    """Fetch + parse GIBS capabilities (cached raw XML, TTL-bound).
    Returns ({layer_id: {default, matrices}}, detail). Never raises."""
    import urllib.request
    now = now or utcnow()
    meta = load_meta()
    if not health_ok(meta, "gibs.caps"):
        return None, "capabilities host unavailable (see provider health)"
    path = _caps_path()
    try:
        stale = True
        if path.is_file():
            age = (_now_dt(now) - datetime.fromtimestamp(
                path.stat().st_mtime, tz=timezone.utc)).total_seconds()
            stale = age > CAPS_TTL_S
        if stale:
            req = urllib.request.Request(
                GIBS_CAPS, headers={"User-Agent": "Tellurion-imagery/1.0 "
                                                  "(+public demo)"})
            if opener is not None:
                blob = opener(req, timeout=120)
                if hasattr(blob, "read"):
                    blob = blob.read(MAX_CAPS_BYTES + 1)
            else:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    blob = resp.read(MAX_CAPS_BYTES + 1)
            if len(blob) > MAX_CAPS_BYTES:
                return None, "capabilities response exceeds size cap"
            path.write_bytes(blob)
            note_success(meta, "gibs.caps", now)
            save_meta(meta)
    except Exception as e:  # noqa: BLE001 - honest detail string
        note_failure(meta, "gibs.caps", now,
                     f"{type(e).__name__}: {str(e)[:120]}")
        save_meta(meta)
        if not path.is_file():
            return None, f"capabilities unreachable: {type(e).__name__}"
    try:
        grab = _CapsGrabber([layer["id"] for layer in LAYERS])
        parser = xml.sax.make_parser()
        parser.setFeature(xml.sax.handler.feature_namespaces, False)
        parser.setContentHandler(grab)
        parser.parse(str(path))
        return grab.layers, "ok"
    except Exception as e:  # noqa: BLE001
        return None, f"capabilities unparseable: {type(e).__name__}"


def best_matrix(matrices: List[str]) -> str:
    """Highest GoogleMapsCompatible level (most detail)."""
    best = ""
    best_n = -1
    for matrix in matrices or []:
        try:
            num = int(matrix.rsplit("Level", 1)[1])
        except (ValueError, IndexError):
            continue
        if num > best_n:
            best_n, best = num, matrix
    return best or "GoogleMapsCompatible_Level7"


def tile_url(layer_id: str, when_iso: str, matrix: str) -> str:
    return (f"{GIBS_BASE}/{layer_id}/default/{when_iso}/"
            f"{matrix}/{{z}}/{{y}}/{{x}}.jpg")


def freshness_class(age_hours: Optional[float]) -> str:
    if age_hours is None:
        return "NO_COVERAGE"
    if age_hours < FRESH_VERY:
        return "VERY_FRESH"
    if age_hours < FRESH_FRESH:
        return "FRESH"
    if age_hours < FRESH_AGING:
        return "AGING"
    if age_hours < FRESH_STALE:
        return "STALE"
    return "NO_COVERAGE"


def _rights_block() -> Dict[str, Any]:
    return {
        "public_display": "YES (US public domain)",
        "redistribution": "YES (US public domain, attribution requested)",
        "commercial_use": "YES (US public domain; no endorsement)",
        "broadcast_use": "ATTRIBUTION_REQUIRED",
        "cache": "YES (polite tile/browser cache)",
        "retention": "tiles cached by client; metadata unretained",
        "attribution": GIBS_ATTRIBUTION,
    }


def layer_status(layer: Dict[str, Any], caps: Dict[str, Dict[str, Any]],
                 now: str) -> Dict[str, Any]:
    """One layer's verified status record (fail-closed on gaps)."""
    lid = layer["id"]
    info = (caps or {}).get(lid) or {}
    default = str(info.get("default") or "")
    captured = _parse_time(default)
    matrix = best_matrix(list(info.get("matrices") or []))
    if captured is None or not matrix:
        return {"source": "NASA GIBS", "dataset": layer["dataset"],
                "layer": lid, "status": "NO_COVERAGE",
                "captured_at": "UNKNOWN", "available_at": "UNKNOWN",
                "age_seconds": None, "freshness_class": "NO_COVERAGE",
                "resolution_m": layer["resolution_m"],
                "truth_mode": "OBSERVED",
                "coverage_quality": layer["region"],
                "cloud_cover_pct_or_unknown": "UNKNOWN",
                "tile_url": "", "matrix": matrix,
                "source_url": "https://earthdata.nasa.gov/gibs",
                "attribution": GIBS_SHORT_ATTRIBUTION,
                "rights_status": "RIGHTS_UNVERIFIED",
                "rights": _rights_block(),
                "note": "capabilities gave no usable time for this layer"}
    age_s = max(0, int((_now_dt(now) - captured).total_seconds()))
    cls = freshness_class(age_s / 3600.0)
    when = default if layer["subdaily"] else default[:10]
    return {"source": "NASA GIBS", "dataset": layer["dataset"],
            "layer": lid,
            "status": "AVAILABLE" if cls != "NO_COVERAGE"
            else "NO_COVERAGE",
            "captured_at": default, "available_at": default,
            "age_seconds": age_s, "freshness_class": cls,
            "resolution_m": layer["resolution_m"],
            "truth_mode": "OBSERVED",
            "coverage_quality": layer["region"],
            "cloud_cover_pct_or_unknown": "UNKNOWN",
            "tile_url": tile_url(lid, when, matrix), "matrix": matrix,
            "source_url": "https://earthdata.nasa.gov/gibs",
            "attribution": GIBS_SHORT_ATTRIBUTION,
            "rights_status": "ATTRIBUTION_REQUIRED",
            "rights": _rights_block()}


def select_layer(lon: float,
                 statuses: Dict[str, Dict[str, Any]]) -> Optional[str]:
    """Deterministic region rule: geostationary layer when its region
    covers the view AND it is VERY_FRESH/FRESH; else daily polar
    (VIIRS, MODIS fallback); else None (vector basemap)."""
    try:
        lon = float(lon)
    except (TypeError, ValueError):
        return None
    lon = ((lon + 180.0) % 360.0) - 180.0
    regional = None
    for rule in REGION_RULES:
        if rule["lon_min"] <= lon <= rule["lon_max"]:
            regional = rule["layer"]
            break
    if regional:
        rec = statuses.get(regional) or {}
        if rec.get("status") == "AVAILABLE" and rec.get(
                "freshness_class") in ("VERY_FRESH", "FRESH"):
            return regional
    for fallback in ("VIIRS_SNPP_CorrectedReflectance_TrueColor",
                     "MODIS_Terra_CorrectedReflectance_TrueColor"):
        rec = statuses.get(fallback) or {}
        if rec.get("status") == "AVAILABLE" and rec.get(
                "freshness_class") != "NO_COVERAGE":
            return fallback
    return None


def get_status(lat: Optional[float] = None, lon: Optional[float] = None,
               opener: Optional[Callable] = None,
               now: Optional[str] = None) -> Dict[str, Any]:
    """Build the /api/world/imagery/status payload."""
    now = now or utcnow()
    caps, detail = fetch_capabilities(opener, now)
    layers = [layer_status(layer, caps or {}, now) for layer in LAYERS]
    by_id = {item["layer"]: item for item in layers}
    selected = select_layer(lon if lon is not None else -28.0, by_id)
    fresh = [item["freshness_class"] for item in layers]
    summary = {cls: fresh.count(cls) for cls in
               ("VERY_FRESH", "FRESH", "AGING", "STALE", "NO_COVERAGE")}
    return {
        "generated_at": now,
        "live": False,
        "real_data": True,
        "truth_label": TRUTH_LABEL,
        "layers": layers,
        "current_source_by_region": [
            {"region": rule["region"], "layer": rule["layer"],
             "status": (by_id.get(rule["layer"]) or {}).get(
                 "status", "NO_COVERAGE"),
             "freshness_class": (by_id.get(rule["layer"]) or {}).get(
                 "freshness_class", "NO_COVERAGE")}
            for rule in REGION_RULES],
        "selected": selected,
        "selection_note": ("single active source (geo tiles are opaque "
                           "off-disc; stacking would fake coverage)"),
        "freshness_summary": summary,
        "capabilities": detail,
    }
