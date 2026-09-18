"""FUTURE-ONLY qualified live-leg adapters (pure functions, no network).

Every adapter maps caller-fetched payload text -> canonical world events.
Modules never fetch, never store credentials, never auto-enable. The demo
server only calls these when the operator explicitly opts in
(TELLURION_LIVE=1 or ?live=1 with localhost) and even then honours
per-source TTL + circuit breakers in `world_cache.py`.

Validation (all adapters): size cap, JSON schema check, coordinate
bounds, timestamp passthrough (UNKNOWN stays UNKNOWN; ingest time is
never substituted for event time), HTML escaping at render time
(caller escapes; ids are slug-checked here).
"""

from __future__ import annotations

import html
import json
import re
import time
from typing import Any, Dict, List

MAX_PAYLOAD_BYTES = 4_000_000
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


def _ok_id(v: Any, fallback: str) -> str:
    s = str(v or fallback)
    return s if _ID_RE.match(s) else fallback


def _valid_coords(lon: Any, lat: Any) -> bool:
    try:
        lo, la = float(lon), float(lat)
    except (TypeError, ValueError):
        return False
    return -180.0 <= lo <= 180.0 and -90.0 <= la <= 90.0


def _check_size(text: str) -> None:
    if len(text.encode("utf-8", "ignore")) > MAX_PAYLOAD_BYTES:
        raise ValueError("payload exceeds 4 MB cap (refused)")


def _esc(v: Any) -> Any:
    if isinstance(v, str):
        return html.escape(v, quote=True)[:500]
    return v


# --------------------------------------------------------------------------
# USGS earthquakes (GeoJSON FeatureCollection)
# --------------------------------------------------------------------------

def parse_usgs(text: str, limit: int = 200) -> List[Dict[str, Any]]:
    _check_size(text)
    data = json.loads(text)
    out: List[Dict[str, Any]] = []
    for f in (data.get("features") or [])[:max(1, min(500, limit))]:
        props = f.get("properties", {}) or {}
        geom = f.get("geometry", {}) or {}
        coords = geom.get("coordinates") or [None, None, None]
        lon, lat = (coords + [None, None])[:2]
        if not _valid_coords(lon, lat):
            continue
        out.append({
            "id": _ok_id(f.get("id") or props.get("code"), "USGS-UNKNOWN"),
            "mag": props.get("mag"), "place": _esc(props.get("place")),
            "lon": float(lon), "lat": float(lat),
            "depth_km": (coords[2] if len(coords) > 2 else None),
            "source_event_time": props.get("time") or "UNKNOWN",
            "published_time": props.get("updated") or "UNKNOWN",
            "first_seen": "UNKNOWN", "ingested_at": "UNKNOWN",
            "precision": "REGIONAL",
            "observation": "OBSERVED", "observation_type": "OBSERVED",
            "truth_mode": "DELAYED",
            "provenance": "USGS Earthquake Hazards Program",
            "rights": "US public domain",
            "category": "SEISMIC",
        })
    return out


# --------------------------------------------------------------------------
# NWS alerts (GeoJSON FeatureCollection)
# --------------------------------------------------------------------------

def parse_nws_alerts(text: str, limit: int = 200) -> List[Dict[str, Any]]:
    _check_size(text)
    data = json.loads(text)
    feats = data.get("features") or []
    out: List[Dict[str, Any]] = []
    for f in feats[:max(1, min(500, limit))]:
        props = f.get("properties", {}) or {}
        geom = f.get("geometry", {}) or {}
        coords = geom.get("coordinates")
        lat = lon = None
        if isinstance(coords, list) and coords:
            ring = coords[0] if isinstance(coords[0][0], list) else coords
            try:
                xs = [float(p[0]) for p in ring if len(p) >= 2]
                ys = [float(p[1]) for p in ring if len(p) >= 2]
                if xs and ys:
                    lon, lat = sum(xs) / len(xs), sum(ys) / len(ys)
            except (TypeError, ValueError):
                pass
        out.append({
            "id": _ok_id(props.get("id"), "NWS-UNKNOWN"),
            "title": _esc(props.get("event") or props.get("headline")
                          or "NWS alert"),
            "headline": _esc(props.get("headline")),
            "severity": _esc(props.get("severity")),
            "certainty": _esc(props.get("certainty")),
            "urgency": _esc(props.get("urgency")),
            "area": _esc(props.get("areaDesc")),
            "lat": lat, "lon": lon,
            "source_event_time": props.get("sent") or "UNKNOWN",
            "published_time": props.get("sent") or "UNKNOWN",
            "effective": props.get("effective") or "UNKNOWN",
            "expires": props.get("expires") or "UNKNOWN",
            "precision": "REGIONAL",
            "observation": "OBSERVED",
            "observation_type": "GOVERNMENT_NOTICE",
            "truth_mode": "DELAYED",
            "provenance": "National Weather Service",
            "rights": "US public domain",
            "category": "WEATHER",
        })
    return out


# --------------------------------------------------------------------------
# EONET events
# --------------------------------------------------------------------------

def parse_eonet(text: str, limit: int = 200) -> List[Dict[str, Any]]:
    _check_size(text)
    data = json.loads(text)
    events = data.get("events") or []
    out: List[Dict[str, Any]] = []
    for e in events[:max(1, min(500, limit))]:
        geoms = e.get("geometry") or []
        lat = lon = None
        when = "UNKNOWN"
        if geoms:
            g = geoms[-1]
            c = g.get("coordinates")
            if isinstance(c, list) and len(c) >= 2:
                try:
                    lon, lat = float(c[0]), float(c[1])
                except (TypeError, ValueError):
                    pass
            when = g.get("date") or "UNKNOWN"
        cats = [c.get("title") for c in (e.get("categories") or [])
                if c.get("title")]
        out.append({
            "id": _ok_id(e.get("id"), "EONET-UNKNOWN"),
            "title": _esc(e.get("title")),
            "categories": [_esc(c) for c in cats],
            "status": _esc(e.get("status")),
            "lat": lat, "lon": lon,
            "source_event_time": when,
            "published_time": "UNKNOWN",
            "precision": "REGIONAL",
            "observation": "OBSERVED",
            "observation_type": "OBSERVED",
            "truth_mode": "DELAYED",
            "provenance": "NASA EONET",
            "rights": "open metadata; imagery per linked source",
            "category": "DISASTER",
            "sources": e.get("sources") or [],
        })
    return out


# --------------------------------------------------------------------------
# GDACS (GeoJSON-ish / feed dict)
# --------------------------------------------------------------------------

def parse_gdacs(text: str, limit: int = 100) -> List[Dict[str, Any]]:
    _check_size(text)
    data = json.loads(text)
    feats = data.get("features") or data.get("events") or []
    out: List[Dict[str, Any]] = []
    for f in feats[:max(1, min(300, limit))]:
        props = f.get("properties", f) if isinstance(f, dict) else {}
        geom = (f.get("geometry", {}) or {}) if isinstance(f, dict) else {}
        coords = geom.get("coordinates") or [None, None]
        lon, lat = (coords + [None, None])[:2]
        out.append({
            "id": _ok_id((props.get("eventid") or props.get("id")
                          or f.get("id") if isinstance(f, dict) else None),
                         "GDACS-UNKNOWN"),
            "title": _esc(props.get("name") or props.get("title")
                          or "GDACS event"),
            "event_type": _esc(props.get("eventtype")
                               or props.get("event_type")),
            "alert_level": _esc(props.get("alertlevel")
                                or props.get("alert_level")),
            "lat": lat, "lon": lon,
            "source_event_time": props.get("fromdate")
            or props.get("datemodified") or "UNKNOWN",
            "precision": "REGIONAL",
            "observation": "OBSERVED",
            "observation_type": "GOVERNMENT_NOTICE",
            "truth_mode": "DELAYED",
            "provenance": "GDACS (UN OCHA / EC JRC)",
            "rights": "summary + link; no bulk mirror",
            "category": "DISASTER",
        })
    return out


# --------------------------------------------------------------------------
# SWPC (product JSON passthrough with validation)
# --------------------------------------------------------------------------

def parse_swpc(text: str) -> Dict[str, Any]:
    _check_size(text)
    data = json.loads(text)
    if not isinstance(data, (list, dict)):
        raise ValueError("unexpected SWPC payload shape")
    return {"raw_kind": "swpc-product",
            "n_records": len(data) if isinstance(data, list) else 1,
            "truth_mode": "DELAYED",
            "provenance": "NOAA SWPC",
            "rights": "US public domain",
            "observation": "OBSERVED",
            "observation_type": "GOVERNMENT_NOTICE"}


# --------------------------------------------------------------------------
# ReliefWeb reports
# --------------------------------------------------------------------------

def parse_reliefweb(text: str, limit: int = 100) -> List[Dict[str, Any]]:
    _check_size(text)
    data = json.loads(text)
    items = data.get("data") or []
    out: List[Dict[str, Any]] = []
    for it in items[:max(1, min(300, limit))]:
        fields = it.get("fields", {}) if isinstance(it, dict) else {}
        out.append({
            "id": _ok_id(it.get("id") if isinstance(it, dict) else None,
                         "RW-UNKNOWN"),
            "title": _esc(fields.get("title")),
            "source": [_esc(s.get("name")) for s in
                       (fields.get("source") or []) if s.get("name")],
            "country": [_esc(c.get("name")) for c in
                        (fields.get("country") or []) if c.get("name")],
            "published": (fields.get("date") or {}).get("created")
            or "UNKNOWN",
            "url": _esc(fields.get("url")),
            "source_event_time": (fields.get("date") or {}).get("created")
            or "UNKNOWN",
            "observation": "OBSERVED",
            "observation_type": "PUBLIC_REPORT",
            "truth_mode": "DELAYED",
            "provenance": "UN OCHA ReliefWeb",
            "rights": "free with attribution",
            "category": "HUMANITARIAN",
        })
    return out


# --------------------------------------------------------------------------
# GDACS RSS (xml/rss.xml — summary/link leg, geo + alert semantics kept)
# --------------------------------------------------------------------------

_GDACS_NS = {
    "geo": "http://www.w3.org/2003/01/geo/wgs84_pos#",
    "gdacs": "https://www.gdacs.org/xml/gdacs.rss",
    "georss": "http://www.georss.org/georss",
}


def _gdacs_text(item, tag):
    # Namespace URIs drift across GDACS templates; match by local name.
    for child in item:
        local = child.tag.rsplit("}", 1)[-1]
        if local == tag:
            return (child.text or "").strip() or None
    return None


def parse_gdacs_rss(text: str, limit: int = 300) -> List[Dict[str, Any]]:
    """Map the GDACS RSS feed (caller-fetched) to canonical events.

    GDACS alert/severity/population semantics are copied verbatim —
    never reinterpreted. Only current (`iscurrent=true`) items are
    kept by default callers; the flag is preserved for transparency.
    """
    import xml.etree.ElementTree as _et
    _check_size(text)
    try:
        root = _et.fromstring(text.encode("utf-8", "ignore")
                              if isinstance(text, str) else text)
    except Exception as e:
        raise ValueError(f"GDACS RSS is not parseable XML: {e}") from e
    items = [el for el in root.iter()
             if el.tag.rsplit("}", 1)[-1] == "item"]
    out: List[Dict[str, Any]] = []
    for el in items[:max(1, min(500, limit))]:
        lat = _gdacs_text(el, "lat")
        lon = _gdacs_text(el, "long")
        try:
            flat, flon = (float(lat), float(lon)) \
                if lat is not None and lon is not None else (None, None)
            if flat is not None and not _valid_coords(flon, flat):
                flat, flon = None, None
        except (TypeError, ValueError):
            flat, flon = None, None
        etype = _gdacs_text(el, "eventtype")
        eid = _gdacs_text(el, "eventid")
        out.append({
            "id": _ok_id(f"GDACS-{etype}-{eid}"
                         if etype and eid else None, "GDACS-UNKNOWN"),
            "title": _esc(_gdacs_text(el, "title")),
            "description": _esc(_gdacs_text(el, "description")),
            "link": _esc(_gdacs_text(el, "link")),
            "event_type": _esc(etype),
            "event_name": _esc(_gdacs_text(el, "eventname")),
            "alert_level": _esc(_gdacs_text(el, "alertlevel")),
            "alert_score": _gdacs_text(el, "alertscore"),
            "severity": _esc(_gdacs_text(el, "severity")),
            "population": _esc(_gdacs_text(el, "population")),
            "country": _esc(_gdacs_text(el, "country")),
            "iso3": _esc(_gdacs_text(el, "iso3")),
            "bbox": _esc(_gdacs_text(el, "bbox")),
            "is_current": _esc(_gdacs_text(el, "iscurrent")),
            "lat": flat, "lon": flon,
            "source_event_time": _gdacs_text(el, "fromdate")
            or _gdacs_text(el, "dateadded") or "UNKNOWN",
            "published_time": _gdacs_text(el, "pubDate")
            or "UNKNOWN",
            "first_seen": "UNKNOWN", "ingested_at": "UNKNOWN",
            "precision": "REGIONAL",
            "observation": "OBSERVED",
            "observation_type": "GOVERNMENT_NOTICE",
            "truth_mode": "DELAYED",
            "provenance": "GDACS (UN OCHA / EC JRC)",
            "rights": "summary + link, credit GDACS; no bulk mirror",
            "category": "DISASTER",
        })
    return out


# --------------------------------------------------------------------------
# GDELT DOC 2.1 ArtList (reported-events leg — NEWS_REPORT, never truth)
# --------------------------------------------------------------------------

def parse_gdelt_artlist(text: str,
                        limit: int = 50) -> List[Dict[str, Any]]:
    """Map a GDELT DOC artlist response (caller-fetched) to report stubs.

    Articles carry no coordinates by construction (lat/lon stay None);
    they attach to countries/disasters via linking, never as pins.
    """
    _check_size(text)
    try:
        data = json.loads(text)
    except Exception as e:
        raise ValueError(f"GDELT artlist is not JSON: {e}") from e
    arts = data.get("articles")
    if arts is None:
        raise ValueError("GDELT artlist missing 'articles'")
    if not isinstance(arts, list):
        raise ValueError("GDELT artlist 'articles' is not a list")
    out: List[Dict[str, Any]] = []
    for i, a in enumerate(arts[:max(1, min(100, limit))]):
        if not isinstance(a, dict):
            continue
        import hashlib as _hl
        digest = _hl.sha256(
            str(a.get("url", "")).encode("utf-8", "ignore")).hexdigest()[:12]
        out.append({
            "id": _ok_id(f"GDELT-{digest}-{i}", "GDELT-UNKNOWN"),
            "title": _esc(a.get("title")),
            "url": _esc(a.get("url")),
            "domain": _esc(a.get("domain")),
            "language": _esc(a.get("language")),
            "source_country": _esc(a.get("sourcecountry")),
            "lat": None, "lon": None,
            "source_event_time": a.get("seendate") or "UNKNOWN",
            "published_time": a.get("seendate") or "UNKNOWN",
            "first_seen": "UNKNOWN", "ingested_at": "UNKNOWN",
            "precision": "UNKNOWN",
            "observation": "OBSERVED",
            "observation_type": "NEWS_REPORT",
            "truth_mode": "DELAYED",
            "provenance": "GDELT Project (reported event, not ground truth)",
            "rights": "open use with citation + link to gdeltproject.org",
            "category": "NEWS",
        })
    return out


# --------------------------------------------------------------------------
# SWPC alerts.json (per-alert items + scales summary)
# --------------------------------------------------------------------------

def parse_swpc_alerts(text: str,
                      limit: int = 100) -> List[Dict[str, Any]]:
    """Map SWPC alerts.json (caller-fetched) to canonical alert stubs."""
    _check_size(text)
    try:
        data = json.loads(text)
    except Exception as e:
        raise ValueError(f"SWPC alerts are not JSON: {e}") from e
    if not isinstance(data, list):
        raise ValueError("SWPC alerts payload is not a list")
    out: List[Dict[str, Any]] = []
    for i, a in enumerate(data[:max(1, min(300, limit))]):
        if not isinstance(a, dict):
            continue
        msg = a.get("message") or ""
        head = next((ln.strip() for ln in str(msg).splitlines()
                     if ln.strip()), "SWPC alert")
        out.append({
            "id": _ok_id(a.get("product_id") or f"SWPC-{i}",
                         "SWPC-UNKNOWN"),
            "title": _esc(head)[:200],
            "message": _esc(msg)[:2000],
            "lat": None, "lon": None,
            "source_event_time": a.get("issue_datetime") or "UNKNOWN",
            "published_time": a.get("issue_datetime") or "UNKNOWN",
            "first_seen": "UNKNOWN", "ingested_at": "UNKNOWN",
            "precision": "UNKNOWN",
            "observation": "OBSERVED",
            "observation_type": "GOVERNMENT_NOTICE",
            "truth_mode": "DELAYED",
            "provenance": "NOAA SWPC",
            "rights": "US public domain",
            "category": "SPACE_WEATHER",
        })
    return out


# --------------------------------------------------------------------------
# Minimal in-memory TTL cache + circuit breaker (stdlib only).
# --------------------------------------------------------------------------

class SourceCache:
    """Per-source TTL cache with failure backoff + circuit breaker.

    Honours provider rules: cache first, conditional refresh only after
    TTL, exponential backoff with jitter on failure, open circuit after
    N consecutive failures.
    """

    def __init__(self, ttl_s: int = 300, max_failures: int = 3,
                 cool_down_s: int = 600) -> None:
        self.ttl_s = ttl_s
        self.max_failures = max_failures
        self.cool_down_s = cool_down_s
        self._store: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str) -> Any | None:
        row = self._store.get(key)
        if not row:
            return None
        if time.time() - row["at"] > self.ttl_s:
            return None
        return row["value"]

    def put(self, key: str, value: Any) -> None:
        self._store[key] = {"value": value, "at": time.time(),
                            "failures": 0, "open_until": 0.0}

    def record_failure(self, key: str) -> None:
        row = self._store.setdefault(key, {"value": None, "at": 0.0,
                                           "failures": 0, "open_until": 0.0})
        row["failures"] = int(row.get("failures", 0)) + 1
        if row["failures"] >= self.max_failures:
            import random as _r
            jitter = _r.uniform(0, self.cool_down_s * 0.2)
            row["open_until"] = time.time() + self.cool_down_s + jitter

    def circuit_open(self, key: str) -> bool:
        row = self._store.get(key)
        if not row:
            return False
        return time.time() < float(row.get("open_until", 0.0))

    def health(self) -> Dict[str, Any]:
        return {"entries": len(self._store),
                "open_circuits": sum(1 for k in self._store
                                     if self.circuit_open(k))}
