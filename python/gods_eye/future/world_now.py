"""FUTURE-ONLY WORLD NOW live layer (backend fetch, localhost only).

WORLD NOW = real qualified public feeds, fetched by the Tellurion
backend (never by browser JS), validated as untrusted input,
normalized to canonical observations with full time semantics, cached
per-provider rules, and served with honest per-source health.

Guarantees:
- No synthetic objects ever enter a NOW payload (asserted in code).
- Unknown timestamps stay UNKNOWN; ingest time never substitutes.
- Truth mode is per source (DELAYED / STATIC), never global LIVE.
- Startup never requires network: failures degrade to STALE/OFFLINE
  with the last permitted cache and an explicit timestamp.
- Disk cache lives under raw_store/world_now/ (gitignored, local
  only); only sources whose rights permit storage are persisted.
"""

from __future__ import annotations

import hashlib
import json
import math
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

NORMALIZER = "world-now-v1"
USER_AGENT = "Tellurion/1.0 (local public-data world monitor)"
MAX_BYTES = 4_000_000

HEALTH_STATES = ("ONLINE", "DEGRADED", "STALE", "OFFLINE", "RATE_LIMITED",
                 "STANDBY", "KEY_REQUIRED")


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def solar_at(when_iso: str) -> Dict[str, Any]:
    """Real sun position at the payload time.

    WORLD NOW draws day and night from this, never from the synthetic replay
    scene clock, so the terminator on the globe matches the data's own time.
    """
    from gods_eye.future import geo
    when = datetime.fromisoformat(when_iso)
    lat, lon = geo.subsolar_point(when)
    return {"at": when_iso, "subsolar": [round(lat, 3), round(lon, 3)],
            "night": geo.night_polygon(when),
            "model": "Astronomical Almanac low-precision solar position"}


def _aviation_leg() -> Dict[str, Any]:
    """What the keyless adsb.lol leg (world_air) holds right now, from memory
    only: no network call, so coverage never claims more than was polled."""
    try:
        from gods_eye.future import world_air
        return world_air.source_rollup()
    except Exception:  # aviation module unavailable: report nothing held
        return {"state": "UNKNOWN", "aircraft": 0, "tiles_online": "0/0"}


def _runtime_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in (here, *here.parents):
        if (parent / "console" / "ultra.html").is_file():
            return parent / "raw_store" / "world_now"
    return Path.cwd() / "raw_store" / "world_now"


# --------------------------------------------------------------------------
# Source configs (mirror docs/public/TERMS_SNAPSHOTS.md; single source of
# runtime truth for fetch policy).
# --------------------------------------------------------------------------

def _gdelt_url() -> str:
    from urllib.request import quote
    q = quote("(earthquake OR tsunami OR cyclone OR flood OR wildfire)")
    return ("https://api.gdeltproject.org/api/v2/doc/doc?query=" + q +
            "&mode=artlist&maxrecords=25&format=json&sortby=datedesc")


SOURCE_CONFIGS: Dict[str, Dict[str, Any]] = {
    "usgs-earthquakes": {
        "enabled": True,
        "urls": ["https://earthquake.usgs.gov/earthquakes/feed/v1.0/"
                 "summary/4.5_week.geojson"],
        "content_types": ("application/json",),
        "ttl_s": 120, "timeout_s": 20,
        "parser": "usgs", "limit": 200,
        "truth_mode": "DELAYED", "category": "SEISMIC",
        "coverage": "global",
        "attribution": "USGS Earthquake Hazards Program (courtesy of the "
                       "U.S. Geological Survey)",
        "rights": "US public domain",
    },
    "nasa-eonet": {
        "enabled": True,
        "urls": ["https://eonet.gsfc.nasa.gov/api/v3/events"
                 "?status=open&days=30"],
        # NOTE: EONET currently serves JSON labeled application/rss+xml;
        # the JSON-shape validation in parse_eonet remains the real gate.
        "content_types": ("application/json", "application/rss+xml"),
        "ttl_s": 900, "timeout_s": 20,
        "parser": "eonet", "limit": 200,
        "truth_mode": "DELAYED", "category": "DISASTER",
        "coverage": "global (curated)",
        "attribution": "NASA EONET",
        "rights": "open metadata; imagery per linked source",
    },
    "gdacs-alerts": {
        "enabled": True,
        "urls": ["https://www.gdacs.org/xml/rss.xml"],
        "content_types": ("application/xml", "text/xml",
                          "application/rss+xml"),
        "ttl_s": 900, "timeout_s": 25,
        "parser": "gdacs_rss", "limit": 300,
        "truth_mode": "DELAYED", "category": "DISASTER",
        "coverage": "global",
        "attribution": "GDACS (UN OCHA / EC JRC)",
        "rights": "summary + link, credit GDACS; no bulk mirror",
    },
    "gdelt-doc": {
        "enabled": True,
        "urls": [_gdelt_url()],
        "content_types": ("application/json",),
        "ttl_s": 1800, "timeout_s": 25,
        "parser": "gdelt", "limit": 25,
        "truth_mode": "DELAYED", "category": "NEWS",
        "coverage": "global (reported events only)",
        "attribution": "GDELT Project (citation + link "
                       "https://www.gdeltproject.org/ mandatory)",
        "rights": "open use with citation + link",
    },
    "noaa-swpc": {
        "enabled": True,
        "urls": ["https://services.swpc.noaa.gov/products/alerts.json",
                 "https://services.swpc.noaa.gov/products/"
                 "noaa-scales.json"],
        "content_types": ("application/json",),
        "ttl_s": 300, "timeout_s": 20,
        "parser": "swpc_multi", "limit": 100,
        "truth_mode": "DELAYED", "category": "SPACE_WEATHER",
        "coverage": "global (solar/geomagnetic products)",
        "attribution": "NOAA SWPC",
        "rights": "US public domain",
    },
    "nws-alerts": {
        "enabled": True,
        "urls": ["https://api.weather.gov/alerts/active"
                 "?status=actual&message_type=alert"],
        "content_types": ("application/geo+json", "application/json"),
        "ttl_s": 300, "timeout_s": 25,
        "parser": "nws", "limit": 300,
        "truth_mode": "DELAYED", "category": "WEATHER",
        "coverage": "UNITED STATES ONLY",
        "attribution": "National Weather Service",
        "rights": "US public domain",
    },
}

# Not enabled this pass — each carries its reason (shown in UI).
STANDBY_SOURCES: Dict[str, Dict[str, str]] = {
    "reliefweb": {"state": "STANDBY",
                  "reason": "API v2 requires an approved appname "
                            "(verified 2026-09-16); set "
                            "TELLURION_RELIEFWEB_APPNAME locally to connect",
                  "rights": "free with attribution"},
    "copernicus-ems": {"state": "STANDBY",
                       "reason": "no stable machine-readable public JSON "
                                 "activations API found; link-only",
                       "rights": "Copernicus free open (activations)"},
    "epa-airnow": {"state": "STANDBY",
                   "reason": "qualified; live endpoint not re-probed this "
                             "pass",
                   "rights": "US public domain (federal portion)"},
    "eea-airquality": {"state": "STANDBY",
                       "reason": "qualified; live endpoint not re-probed "
                                 "this pass",
                       "rights": "EU open data reuse"},
    "usgs-volcanoes": {"state": "STANDBY",
                       "reason": "qualified; no single verified machine "
                                 "feed this pass",
                       "rights": "US public domain"},
    "osm-overpass": {"state": "STANDBY",
                     "reason": "static context leg for regional packs; "
                               "not needed for WORLD NOW v1",
                     "rights": "ODbL 1.0"},
    "gtfs-static": {"state": "STANDBY",
                    "reason": "per-agency static leg for regional packs",
                    "rights": "per-agency terms"},
    "opensky-network": {"state": "KEY_REQUIRED",
                        "reason": "SOURCE AVAILABLE — USER KEY REQUIRED "
                                  "(OAuth creds, local only)",
                        "rights": "account terms; no bulk redistribution"},
    "nasa-firms": {"state": "KEY_REQUIRED",
                   "reason": "SOURCE AVAILABLE — USER KEY REQUIRED "
                             "(MAP_KEY, local only)",
                   "rights": "per-user MAP_KEY terms"},
    "aisstream": {"state": "KEY_REQUIRED",
                  "reason": "SOURCE AVAILABLE — USER KEY REQUIRED "
                            "(server proxy, never browser-direct)",
                  "rights": "account terms"},
}

PARSERS: Dict[str, str] = {}


def _parsers():
    from gods_eye.future import world_live as _live
    return {
        "usgs": _live.parse_usgs,
        "nws": _live.parse_nws_alerts,
        "eonet": _live.parse_eonet,
        "gdacs_rss": _live.parse_gdacs_rss,
        "gdelt": _live.parse_gdelt_artlist,
        "swpc_alerts": _live.parse_swpc_alerts,
    }


# --------------------------------------------------------------------------
# Fetch (backend only; responses are untrusted input)
# --------------------------------------------------------------------------

class FetchResult:
    def __init__(self, ok: bool, text: str = "",
                 detail: str = "", latency_ms: int = 0,
                 http_status: Optional[int] = None,
                 not_modified: bool = False,
                 etag: str = "", last_modified: str = "") -> None:
        self.ok = ok
        self.text = text
        self.detail = detail
        self.latency_ms = latency_ms
        self.http_status = http_status
        self.not_modified = not_modified
        self.etag = etag
        self.last_modified = last_modified


def fetch_url(url: str, timeout_s: int,
              content_types: tuple,
              etag: str = "", last_modified: str = "",
              opener: Optional[Callable] = None) -> FetchResult:
    """Single GET with cap, timeout, content-type check, conditionals."""
    t0 = time.time()
    headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified
    req = urllib.request.Request(url, headers=headers)
    try:
        open_fn = opener or urllib.request.urlopen
        resp = open_fn(req, timeout=timeout_s)
        status = getattr(resp, "status", 200)
        ctype = ""
        try:
            ctype = (resp.headers.get_content_type() or "").lower()
        except Exception:
            ctype = ""
        if ctype and not any(c in ctype for c in content_types):
            return FetchResult(False, detail=f"unexpected content-type "
                                             f"'{ctype}' (refused)",
                               latency_ms=int((time.time() - t0) * 1000),
                               http_status=status)
        chunks: List[bytes] = []
        total = 0
        while True:
            part = resp.read(65536)
            if not part:
                break
            total += len(part)
            if total > MAX_BYTES:
                return FetchResult(
                    False, detail=f"payload exceeds {MAX_BYTES} bytes "
                                  f"(refused)",
                    latency_ms=int((time.time() - t0) * 1000),
                    http_status=status)
            chunks.append(part)
        raw = b"".join(chunks)
        try:
            etag_out = resp.headers.get("ETag", "") or ""
            lm_out = resp.headers.get("Last-Modified", "") or ""
        except Exception:
            etag_out, lm_out = "", ""
        return FetchResult(
            True, text=raw.decode("utf-8", "ignore"), detail="fetched",
            latency_ms=int((time.time() - t0) * 1000),
            http_status=status, etag=etag_out, last_modified=lm_out)
    except urllib.error.HTTPError as e:
        try:
            extra = e.read(300).decode("utf-8", "ignore")
        except Exception:
            extra = ""
        if e.code == 304:
            return FetchResult(True, detail="not modified",
                               latency_ms=int((time.time() - t0) * 1000),
                               http_status=304, not_modified=True)
        if e.code == 429:
            return FetchResult(False, detail="HTTP 429 rate limited"
                                             + (f": {extra[:120]}"
                                                if extra else ""),
                               latency_ms=int((time.time() - t0) * 1000),
                               http_status=429)
        return FetchResult(False, detail=f"HTTP {e.code}"
                                         + (f": {extra[:120]}"
                                            if extra else ""),
                           latency_ms=int((time.time() - t0) * 1000),
                           http_status=e.code)
    except Exception as e:
        return FetchResult(False, detail=f"{type(e).__name__}: "
                                         f"{str(e)[:140]}",
                           latency_ms=int((time.time() - t0) * 1000))


# --------------------------------------------------------------------------
# Store (memory + disk) and health
# --------------------------------------------------------------------------

_lock = threading.Lock()
_memory: Dict[str, Dict[str, Any]] = {}
_health: Dict[str, Dict[str, Any]] = {}


def _meta_path(source_id: str) -> Path:
    return _runtime_dir() / f"{source_id}.json"


def _first_seen_path() -> Path:
    return _runtime_dir() / "first_seen.json"


def _load_first_seen() -> Dict[str, str]:
    try:
        p = _first_seen_path()
        if p.is_file():
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
    except Exception:
        pass
    return {}


def _save_first_seen(mapping: Dict[str, str]) -> None:
    try:
        d = _runtime_dir()
        d.mkdir(parents=True, exist_ok=True)
        _first_seen_path().write_text(json.dumps(mapping, indent=1),
                                      encoding="utf-8")
    except Exception:
        pass


def _blank_health(source_id: str) -> Dict[str, Any]:
    return {"source_id": source_id, "state": "OFFLINE",
            "last_attempt": "UNKNOWN", "last_success": "UNKNOWN",
            "latency_ms": None, "failures_consec": 0,
            "next_refresh": "UNKNOWN", "freshness_s": None, "detail": "never polled"}  # noqa: E501


def source_health() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for sid, cfg in SOURCE_CONFIGS.items():
        h = dict(_health.get(sid) or _blank_health(sid))
        h["enabled"] = bool(cfg.get("enabled"))
        h["coverage"] = cfg.get("coverage", "")
        h["attribution"] = cfg.get("attribution", "")
        h["rights"] = cfg.get("rights", "")
        h["truth_mode"] = cfg.get("truth_mode", "DELAYED")
        h["refresh_ttl_s"] = cfg.get("ttl_s")
        out.append(h)
    for sid, info in STANDBY_SOURCES.items():
        out.append({"source_id": sid, "state": info["state"],
                    "enabled": False, "coverage": "", "rights": info.get("rights", ""),  # noqa: E501
                    "truth_mode": "UNKNOWN", "refresh_ttl_s": None,
                    "last_attempt": "UNKNOWN", "last_success": "UNKNOWN",
                    "latency_ms": None, "failures_consec": 0,
                    "next_refresh": "UNKNOWN", "freshness_s": None,
                    "detail": info.get("reason", "")})
    return out


# --------------------------------------------------------------------------
# Normalize: parser rows -> canonical NOW observations
# --------------------------------------------------------------------------

def _iso_ms(ms: Any) -> str:
    try:
        if ms is None or isinstance(ms, str):
            return str(ms) if ms else "UNKNOWN"
        return datetime.fromtimestamp(float(ms) / 1000.0,
                                      tz=timezone.utc).isoformat(
            timespec="seconds")
    except Exception:
        return "UNKNOWN"


def _normalize(source_id: str, rows: List[Dict[str, Any]],
               raw_hash: str, now: str,
               first_seen: Dict[str, str]) -> List[Dict[str, Any]]:
    cfg = SOURCE_CONFIGS[source_id]
    out: List[Dict[str, Any]] = []
    seen_ids: Dict[str, int] = {}
    for row in rows:
        base_id = str(row.get("id") or "UNKNOWN")
        seen_ids[base_id] = seen_ids.get(base_id, 0) + 1
        item_id = base_id if seen_ids[base_id] == 1 else \
            f"{base_id}#{seen_ids[base_id]}"
        key = f"{source_id}:{item_id}"
        if key not in first_seen:
            first_seen[key] = now
        short = hashlib.sha256(key.encode("utf-8")).hexdigest()[:8]
        evt = row.get("source_event_time") or "UNKNOWN"
        if source_id == "usgs-earthquakes" and evt != "UNKNOWN":
            evt = _iso_ms(row.get("source_event_time"))
        pub = row.get("published_time") or "UNKNOWN"
        if source_id == "usgs-earthquakes" and pub != "UNKNOWN":
            pub = _iso_ms(row.get("published_time"))
        eff = evt if evt != "UNKNOWN" else (
            pub if pub != "UNKNOWN" else "UNKNOWN")
        lat, lon = row.get("lat"), row.get("lon")
        try:
            lat = float(lat) if lat is not None else None
            lon = float(lon) if lon is not None else None
        except (TypeError, ValueError):
            lat, lon = None, None
        out.append({
            "source": source_id,
            "source_item_id": item_id,
            "source_url": _source_item_url(source_id, row),
            "id": f"NOW-{source_id.split('-')[0].upper()}-{short}",  # noqa: E501
            "stable_key": key,
            "lat": lat, "lon": lon,
            "source_event_time": evt,
            "published_time": pub,
            "first_seen": first_seen[key],
            "ingested_at": now,
            "effective_time": eff,
            "precision": row.get("precision", "UNKNOWN"),
            "rights": cfg.get("rights", "UNKNOWN"),
            "attribution": cfg.get("attribution", ""),
            "provenance": row.get("provenance", cfg.get("attribution", "")),
            "observation": row.get("observation", "OBSERVED"),
            "observation_type": row.get("observation_type", "OBSERVED"),
            "truth_mode": cfg.get("truth_mode", "DELAYED"),
            "category": row.get("category", cfg.get("category", "UNKNOWN")),
            "raw_hash": raw_hash,
            "normalizer": NORMALIZER,
            "fields": {k: row.get(k) for k in (
                "title", "mag", "depth_km", "place", "status",
                "headline", "severity", "certainty", "urgency", "area",
                "effective", "expires", "categories", "event_type",
                "event_name", "alert_level", "alert_score", "description",
                "population", "country", "iso3", "bbox", "is_current",
                "domain", "language", "source_country", "url", "message",
                "sources") if row.get(k) is not None},
        })
    return out


def _source_item_url(source_id: str, row: Dict[str, Any]) -> str:
    if row.get("link"):
        return str(row["link"])
    if row.get("url"):
        return str(row["url"])
    if source_id == "usgs-earthquakes":
        return "https://earthquake.usgs.gov/earthquakes/map/"
    if source_id == "nasa-eonet":
        return "https://eonet.gsfc.nasa.gov/"
    if source_id == "gdacs-alerts":
        return "https://www.gdacs.org/"
    if source_id == "gdelt-doc":
        return "https://www.gdeltproject.org/"
    if source_id == "noaa-swpc":
        return "https://www.swpc.noaa.gov/"
    if source_id == "nws-alerts":
        return "https://api.weather.gov/"
    return "UNKNOWN"


# --------------------------------------------------------------------------
# Refresh pipeline
# --------------------------------------------------------------------------

def refresh_source(source_id: str, force: bool = False,
                   opener: Optional[Callable] = None,
                   now: Optional[str] = None) -> Dict[str, Any]:
    """Fetch (if TTL expired or forced), validate, normalize, cache."""
    cfg = SOURCE_CONFIGS.get(source_id)
    if not cfg or not cfg.get("enabled"):
        return {"source_id": source_id, "refreshed": False,
                "reason": "not enabled"}
    now = now or utcnow()
    ttl = int(cfg.get("ttl_s", 300))
    with _lock:
        mem = _memory.get(source_id)
        h = _health.get(source_id) or _blank_health(source_id)
        if mem and not force:
            age = time.time() - mem.get("at", 0)
            if age < ttl:
                h["next_refresh"] = _iso_epoch(mem["at"] + ttl)
                _health[source_id] = h
                return {"source_id": source_id, "refreshed": False,
                        "reason": "ttl", "age_s": int(age)}
        # Backoff honor: a RATE_LIMITED source is not re-hit until its
        # next_refresh passes (unless forced). This keeps one 429 from
        # turning every WORLD NOW view into another provider hit while
        # still serving memory/disk cache with an honest state.
        if not force and h.get("state") == "RATE_LIMITED":
            try:
                nr = datetime.fromisoformat(
                    str(h.get("next_refresh", "UNKNOWN")))
                if nr > datetime.now(timezone.utc):
                    if mem:
                        _health[source_id] = h
                        return {"source_id": source_id, "refreshed": False,
                                "reason": "backoff", "served": "memory"}
                    # Disk fallback is loaded when memory is empty.
                    try:
                        _p = _meta_path(source_id)
                        if _p.is_file():
                            _dm = json.loads(_p.read_text(encoding="utf-8"))
                            _di = _dm.get("items", []) or []
                            if _di:
                                _serve_disk(source_id, _di, _dm, h,
                                            "RATE_LIMITED",
                                            "backoff: provider rate limit "
                                            "still in effect", now)
                                return {"source_id": source_id,
                                        "refreshed": False,
                                        "reason": "backoff", "served": "disk"}
                    except Exception:
                        pass
            except Exception:
                pass
        # Disk fallback is loaded when memory is empty (cold start).
        disk_items: List[Dict[str, Any]] = []
        disk_meta: Dict[str, Any] = {}
        if not mem:
            try:
                p = _meta_path(source_id)
                if p.is_file():
                    disk_meta = json.loads(p.read_text(encoding="utf-8"))
                    disk_items = disk_meta.get("items", []) or []
            except Exception:
                disk_meta, disk_items = {}, []
        h["last_attempt"] = now
        texts: List[str] = []
        etag, last_mod = disk_meta.get("etag", ""), \
            disk_meta.get("last_modified", "")
        degraded_notes: List[str] = []
        not_modified_all = True
        parsers = _parsers()
        for url in cfg["urls"]:
            fr = fetch_url(url, int(cfg.get("timeout_s", 20)),
                           tuple(cfg.get("content_types", ())),
                           etag=etag, last_modified=last_mod,
                           opener=opener)
            h["latency_ms"] = fr.latency_ms
            if fr.not_modified:
                continue
            not_modified_all = False
            if not fr.ok:
                if fr.http_status == 429:
                    h["state"] = "RATE_LIMITED"
                    h["detail"] = fr.detail
                    h["failures_consec"] = int(
                        h.get("failures_consec", 0)) + 1
                    if mem:
                        h["next_refresh"] = _iso_epoch(
                            time.time() + max(ttl, 900))
                        _health[source_id] = h
                        return {"source_id": source_id, "refreshed": False,
                                "reason": "rate_limited", "served": "memory"}
                    if disk_items:
                        _serve_disk(source_id, disk_items, disk_meta, h,
                                    "RATE_LIMITED", fr.detail, now)
                        return {"source_id": source_id, "refreshed": False,
                                "reason": "rate_limited", "served": "disk"}
                    h["next_refresh"] = _iso_epoch(
                        time.time() + max(ttl, 900))
                    _health[source_id] = h
                    return {"source_id": source_id, "refreshed": False,
                            "reason": "rate_limited", "served": "none"}
                h["failures_consec"] = int(h.get("failures_consec", 0)) + 1
                h["detail"] = fr.detail
                if mem:
                    h["state"] = "STALE"
                    h["next_refresh"] = _iso_epoch(time.time() + 60)
                    _health[source_id] = h
                    return {"source_id": source_id, "refreshed": False,
                            "reason": "fetch_failed", "served": "memory"}
                if disk_items:
                    _serve_disk(source_id, disk_items, disk_meta, h,
                                "STALE", fr.detail, now)
                    return {"source_id": source_id, "refreshed": False,
                            "reason": "fetch_failed", "served": "disk"}
                h["state"] = "OFFLINE"
                h["next_refresh"] = _iso_epoch(time.time() + 60)
                _health[source_id] = h
                return {"source_id": source_id, "refreshed": False,
                        "reason": "fetch_failed", "served": "none"}
            texts.append(fr.text)
            etag, last_mod = fr.etag or etag, fr.last_modified or last_mod
        if not_modified_all and (mem or disk_items):
            h["state"] = "ONLINE"
            h["detail"] = "HTTP 304 not modified; cache revalidated"
            h["failures_consec"] = 0
            if mem:
                h["last_success"] = h.get("last_success") or now
                h["next_refresh"] = _iso_epoch(time.time() + ttl)
                _health[source_id] = h
                return {"source_id": source_id, "refreshed": False,
                        "reason": "not_modified", "served": "memory"}
            _serve_disk(source_id, disk_items, disk_meta, h, "ONLINE",
                        "HTTP 304 not modified; disk cache revalidated", now)
            return {"source_id": source_id, "refreshed": False,
                    "reason": "not_modified", "served": "disk"}
        # Parse + normalize.
        try:
            rows = _parse_source(source_id, texts, parsers,
                                 int(cfg.get("limit", 200)))
        except Exception as e:
            h["failures_consec"] = int(h.get("failures_consec", 0)) + 1
            h["detail"] = f"parse failed: {type(e).__name__}: {str(e)[:120]}"
            if mem:
                h["state"] = "STALE"
                _health[source_id] = h
                return {"source_id": source_id, "refreshed": False,
                        "reason": "parse_failed", "served": "memory"}
            h["state"] = "OFFLINE"
            _health[source_id] = h
            return {"source_id": source_id, "refreshed": False,
                    "reason": "parse_failed", "served": "none"}
        raw_hash = hashlib.sha256(
            "".join(texts).encode("utf-8", "ignore")).hexdigest()[:16]
        first_seen = _load_first_seen()
        items = _normalize(source_id, rows, raw_hash, now, first_seen)
        _save_first_seen(first_seen)
        # No synthetic leakage, ever.
        for it in items:
            sid = str(it.get("source_item_id", ""))
            if sid.startswith(("WLD-", "SYN-")):
                raise ValueError("synthetic id leaked into WORLD NOW")
        entry = {"at": time.time(), "retrieved_at": now,
                 "expires_at": _iso_epoch(time.time() + ttl),
                 "etag": etag, "last_modified": last_mod,
                 "sha256": raw_hash, "items": items}
        _memory[source_id] = entry
        try:
            d = _runtime_dir()
            d.mkdir(parents=True, exist_ok=True)
            _meta_path(source_id).write_text(json.dumps(entry),  # noqa: E501
                                             encoding="utf-8")
        except Exception:
            degraded_notes.append("disk persist failed")
        h["state"] = "ONLINE" if not degraded_notes else "DEGRADED"
        h["last_success"] = now
        h["failures_consec"] = 0
        h["freshness_s"] = 0
        h["next_refresh"] = _iso_epoch(time.time() + ttl)
        h["detail"] = f"{len(items)} observations" + (
            f" ({'; '.join(degraded_notes)})" if degraded_notes else "")
        _health[source_id] = h
        return {"source_id": source_id, "refreshed": True,
                "n": len(items), "sha256": raw_hash}


def _serve_disk(source_id: str, items: List[Dict[str, Any]],
                meta: Dict[str, Any], h: Dict[str, Any], state: str,
                detail: str, now: str) -> None:
    try:
        at = datetime.fromisoformat(
            meta.get("retrieved_at", now)).timestamp()
        h["freshness_s"] = int(time.time() - at)
    except Exception:
        h["freshness_s"] = None
    h["state"] = state
    h["detail"] = f"{detail} — serving disk cache " \
                  f"({len(items)} obs, retrieved " \
                  f"{meta.get('retrieved_at', 'UNKNOWN')})"
    # The disk cache's retrieved_at IS the last successful fetch time —
    # surface it so the health panel never shows a served cache with an
    # UNKNOWN last success.
    if h.get("last_success") in (None, "", "UNKNOWN"):
        h["last_success"] = meta.get("retrieved_at", "UNKNOWN")
    h["next_refresh"] = _iso_epoch(time.time() + 60)
    _memory[source_id] = {"at": time.time() - 10**6,  # force re-fetch next
                          "retrieved_at": meta.get("retrieved_at", now),
                          "expires_at": meta.get("expires_at", "UNKNOWN"),
                          "etag": meta.get("etag", ""),
                          "last_modified": meta.get("last_modified", ""),
                          "sha256": meta.get("sha256", ""),
                          "items": items}
    _health[source_id] = h


def _iso_epoch(ts: float) -> str:
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(
            timespec="seconds")
    except Exception:
        return "UNKNOWN"


def _parse_source(source_id: str, texts: List[str], parsers: Dict,
                  limit: int) -> List[Dict[str, Any]]:
    if source_id == "noaa-swpc":
        out: List[Dict[str, Any]] = []
        if texts:
            out.extend(parsers["swpc_alerts"](texts[0], limit=limit))
        if len(texts) > 1:
            try:
                scales = parsers.get("swpc_scales")
                if scales:
                    out.extend(scales(texts[1]))
                else:
                    import json as _j
                    data = _j.loads(texts[1])
                    days = sorted(data.keys())[-1:]
                    for day in days:
                        rec = data.get(day) or {}
                        scales_txt = "; ".join(
                            f"{k}={((v or {}).get('Scale') if isinstance(v, dict) else v)}"  # noqa: E501
                            for k, v in rec.items()
                            if k in ("R", "S", "G"))
                        out.append({
                            "id": f"SWPC-SCALES-{day}",
                            "title": f"NOAA scales {day}: {scales_txt}",
                            "lat": None, "lon": None,
                            "source_event_time": "UNKNOWN",
                            "published_time": "UNKNOWN",
                            "precision": "UNKNOWN",
                            "observation": "OBSERVED",
                            "observation_type": "GOVERNMENT_NOTICE",
                            "truth_mode": "DELAYED",
                            "provenance": "NOAA SWPC",
                            "rights": "US public domain",
                            "category": "SPACE_WEATHER"})
            except Exception:
                pass
        return out
    name = SOURCE_CONFIGS[source_id]["parser"]
    return parsers[name](texts[0] if texts else "", limit=limit)


# --------------------------------------------------------------------------
# Cross-source linking (conservative; shared-upstream protection)
# --------------------------------------------------------------------------

def _haversine_km(lat1: float, lon1: float, lat2: float,
                  lon2: float) -> float:
    r = 6371.0
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * \
        math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _parse_time(value: Any) -> Optional[float]:
    if value is None or value == "UNKNOWN":
        return None
    try:
        if isinstance(value, (int, float)):
            v = float(value)
            return v / 1000.0 if v > 10**11 else v
        s = str(value).strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s).timestamp()
    except Exception:
        pass
    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z",
                "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.strptime(str(value)[:31], fmt).replace(
                tzinfo=timezone.utc).timestamp()
        except Exception:
            continue
    return None


def link_events(groups: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:  # noqa: E501
    """Conservative links with method + independence status.

    Rules: USGS↔GDACS earthquakes share upstream families
    (SHARED_UPSTREAM); sensor/authority event + independent news report
    may CORROBORATE; anything else is MULTIPLE SOURCES at best.
    """
    links: List[Dict[str, Any]] = []
    usgs = groups.get("usgs-earthquakes", [])
    gdacs = [g for g in groups.get("gdacs-alerts", [])
             if (g.get("fields") or {}).get("event_type") == "EQ"]
    for u in usgs:
        if u.get("lat") is None:
            continue
        ut = _parse_time(u.get("source_event_time"))
        for g in gdacs:
            if g.get("lat") is None:
                continue
            gt = _parse_time(g.get("source_event_time"))
            if ut is not None and gt is not None and \
                    abs(ut - gt) > 24 * 3600:
                continue
            dist = _haversine_km(u["lat"], u["lon"], g["lat"], g["lon"])  # noqa: E501
            if dist <= 200.0:
                links.append({
                    "a": u["stable_key"], "b": g["stable_key"],
                    "relation": "SAME_EVENT_CANDIDATE",
                    "method": "time window 24h + distance 200km + class EQ",
                    "distance_km": round(dist, 1),
                    "independence": "SHARED_UPSTREAM",
                    "independence_note": "GDACS earthquake ingest "
                                         "republishes USGS/EMSC-family "
                                         "feeds; not independent evidence",
                    "corroboration": "MULTIPLE SOURCES"})
    # GDELT reports -> disaster candidates (country + keyword + 7d).
    reports = groups.get("gdelt-doc", [])
    targets = usgs + gdacs + [e for e in groups.get("nasa-eonet", [])]
    for rep in reports:
        text = ((rep.get("fields") or {}).get("title") or "").lower()
        rt = _parse_time(rep.get("source_event_time"))
        for t in targets:
            if rt is not None:
                tt = _parse_time(t.get("source_event_time"))
                if tt is not None and abs(rt - tt) > 7 * 24 * 3600:
                    continue
            names = _target_names(t)
            if any(n and n in text for n in names):
                links.append({
                    "a": t["stable_key"], "b": rep["stable_key"],
                    "relation": "REPORTS_ON",
                    "method": "country/place-name + 7-day window",
                    "distance_km": None,
                    "independence": "INDEPENDENT",
                    "independence_note": "news-media report vs "
                                         "sensor/authority observation",
                    "corroboration": "CORROBORATED"})
                break
    return links


def _target_names(event: Dict[str, Any]) -> List[str]:
    fields = event.get("fields") or {}
    names: List[str] = []
    for k in ("place", "country", "title", "event_name", "area"):
        v = fields.get(k)
        if v:
            names.append(str(v).lower())
            for tok in str(v).lower().replace(",", " ").split():
                if len(tok) > 4:
                    names.append(tok)
    return names


# --------------------------------------------------------------------------
# NOW payload
# --------------------------------------------------------------------------

STATIC_CONTEXT = {
    "note": "bundled CC0 reference geography (STATIC truth); "
            "not live data",
    "truth_mode": "STATIC",
}


def static_geo() -> Dict[str, List[Dict[str, Any]]]:
    """Bundled CC0 reference points (airports/ports/country centroids)."""
    from gods_eye.future import world_demo as _w
    airports = [{"id": a["id"], "name": a["name"], "city": a.get("city", ""),
                 "country": a.get("country", ""), "lat": a["lat"],
                 "lon": a["lon"], "truth_mode": "STATIC",
                 "observation": "OBSERVED", "observation_type": "OBSERVED",
                 "category": "AIRPORT",
                 "provenance": "bundled CC0 reference geography",
                 "rights": "CC0"} for a in _w.AIRPORTS]
    ports = [{"id": p["id"], "name": p["name"], "city": p.get("city", ""),
              "country": p.get("country", ""), "lat": p["lat"],
              "lon": p["lon"], "truth_mode": "STATIC",
              "observation": "OBSERVED", "observation_type": "OBSERVED",
              "category": "PORT",
              "provenance": "bundled CC0 reference geography",
              "rights": "CC0"} for p in _w.PORTS]
    return {"airports": airports, "ports": ports}


def get_now(refresh: bool = True, force: bool = False,
            opener: Optional[Callable] = None) -> Dict[str, Any]:
    """Build the WORLD NOW payload (real enabled sources only)."""
    now = utcnow()
    groups: Dict[str, List[Dict[str, Any]]] = {}
    refresh_notes: Dict[str, Any] = {}
    if refresh:
        for sid, cfg in SOURCE_CONFIGS.items():
            if cfg.get("enabled"):
                refresh_notes[sid] = refresh_source(sid, force=force,
                                                    opener=opener, now=now)
    with _lock:
        for sid in SOURCE_CONFIGS:
            mem = _memory.get(sid)
            if mem:
                # Serve disk-cold entries too (marked STALE via health).
                groups[sid] = list(mem.get("items", []))
    links = link_events(groups)
    linked_keys = {l["a"] for l in links} | {l["b"] for l in links}
    corroboration_of: Dict[str, str] = {}
    for l in links:
        for k in (l["a"], l["b"]):
            prev = corroboration_of.get(k, "ONE SOURCE")
            order = ["ONE SOURCE", "MULTIPLE SOURCES", "CORROBORATED"]
            nxt = l.get("corroboration", "MULTIPLE SOURCES")
            if order.index(nxt) > order.index(prev):
                corroboration_of[k] = nxt
    objects: Dict[str, List[Dict[str, Any]]] = {}
    total = 0
    for sid, items in groups.items():
        slim = []
        for it in items:
            slim.append({**it,
                         "corroboration": corroboration_of.get(
                             it.get("stable_key", ""), "ONE SOURCE"),
                         "linked": it.get("stable_key") in linked_keys})
        objects[sid] = slim
        total += len(slim)
    counts = {sid: len(v) for sid, v in objects.items()}
    counts["total_real"] = total
    counts["linked_pairs"] = len(links)
    health = source_health()
    online = sum(1 for h in health if h.get("state") == "ONLINE")
    payload = {
        "mode": "now",
        "dataset_id": "tellurion-world-now-v1",
        "normalizer": NORMALIZER,
        "generated_at": now,
        "solar": solar_at(now),
        "live": False,
        "community_mode": True,
        "real_data": True,
        "truth_label": "WORLD NOW (real public feeds)",
        "license_note": "per-source rights; see health[].rights",
        "provenance": "Tellurion WORLD NOW backend (per-source attribution "
                      "in objects[] and health[])",
        "objects": objects,
        "counts": counts,
        "links": links,
        "health": health,
        "sources_online": online,
        "coverage": real_coverage(groups),
        "blind_spots": real_blind_spots(),
        "static_context": STATIC_CONTEXT,
        "static_geo": static_geo(),
        "unavailable": unavailable_domains(),
        "refresh_notes": refresh_notes,
    }
    return payload


def real_coverage(groups: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:  # noqa: E501
    def has(sid: str) -> bool:
        return bool(groups.get(sid))
    return [
        {"domain": "earthquakes", "status": "GOOD" if has("usgs-earthquakes") else "NO CURRENT ENABLED SOURCE",  # noqa: E501
         "detail": "USGS M4.5+ 7-day feed" if has("usgs-earthquakes") else "USGS refresh failed and no cache"},
        {"domain": "disasters", "status": "GOOD" if (has("gdacs-alerts") and has("nasa-eonet")) else ("PARTIAL" if (has("gdacs-alerts") or has("nasa-eonet")) else "NO CURRENT ENABLED SOURCE"),  # noqa: E501
         "detail": "GDACS RSS + NASA EONET open events"},
        {"domain": "news context", "status": "PARTIAL",
         "detail": "GDELT reported events only; never ground truth"},
        {"domain": "space weather", "status": "GOOD" if has("noaa-swpc") else "NO CURRENT ENABLED SOURCE",  # noqa: E501
         "detail": "NOAA SWPC alerts + scales"},
        {"domain": "US weather alerts", "status": "GOOD" if has("nws-alerts") else "NO CURRENT ENABLED SOURCE",  # noqa: E501
         "detail": "NWS — UNITED STATES ONLY"},
        {"domain": "world weather alerts", "status": "NO CURRENT ENABLED SOURCE",  # noqa: E501
         "detail": "no qualified global weather-alert feed in WORLD NOW v1"},
        _aviation_coverage_row(),
        {"domain": "maritime", "status": "KEY_REQUIRED",
         "detail": "SOURCE AVAILABLE — USER KEY REQUIRED (AISStream)"},
        {"domain": "public cameras", "status": "NO QUALIFIED SOURCE",
         "detail": "CAMERAS — NO QUALIFIED SOURCE in WORLD NOW v1"},
        {"domain": "humanitarian reports", "status": "STANDBY",
         "detail": "ReliefWeb needs an approved appname (operator-supplied)"},
    ]


def _aviation_blind_spot() -> Dict[str, Any]:
    """Where live aviation is thin, from what the adsb.lol leg actually holds."""
    leg = _aviation_leg()
    tiles = leg.get("tiles_online", "0/0")
    if int(leg.get("aircraft") or 0) > 0:
        return {"region": "Aviation outside answering receiver tiles",
                "status": "PARTIAL",
                "reason": f"adsb.lol community receivers: {tiles} regional tiles "
                          f"answering ({leg.get('state', 'UNKNOWN')}); oceans, "
                          "Africa and polar regions not covered"}
    return {"region": "Aviation live positions", "status": "NO CURRENT DATA",
            "reason": "adsb.lol leg holds no aircraft yet (not polled, or "
                      f"{leg.get('state', 'UNKNOWN')})"}


def real_blind_spots() -> List[Dict[str, Any]]:
    return [
        {"region": "Non-US weather alerts", "status": "NO CURRENT ENABLED SOURCE",  # noqa: E501
         "reason": "NWS covers the US only; no qualified global alert feed yet"},  # noqa: E501
        _aviation_blind_spot(),
        {"region": "Maritime live positions", "status": "KEY_REQUIRED",
         "reason": "qualified leg exists but needs an operator key (AISStream)"},
        {"region": "Public cameras", "status": "NO QUALIFIED SOURCE",
         "reason": "no operator-authorized embeddable feed in v1"},
        {"region": "Humanitarian depth", "status": "PARTIAL",
         "reason": "GDELT news context only until ReliefWeb appname is configured"},  # noqa: E501
        {"region": "Earthquakes below M4.5 / older than 7 days",
         "status": "STALE",
         "reason": "feed window (M4.5+, 7 days) by design; catalog has more"},
    ]


def _aviation_coverage_row() -> Dict[str, str]:
    """Aviation is served by the keyless adsb.lol leg; report what it holds.

    Regional receiver tiles never cover the whole world, so a populated leg is
    PARTIAL, never GOOD. An empty or unpolled leg says so instead of pointing
    at a keyed source the product does not use by default.
    """
    leg = _aviation_leg()
    n = int(leg.get("aircraft") or 0)
    if n > 0:
        return {"domain": "aviation", "status": "PARTIAL",
                "detail": f"adsb.lol community ADS-B: {n} aircraft, "
                          f"{leg.get('tiles_online', '?')} regional tiles "
                          f"({leg.get('state', 'UNKNOWN')}); receiver-"
                          "dependent, oceans/Africa/polar not covered"}
    return {"domain": "aviation", "status": "NO CURRENT DATA",
            "detail": "adsb.lol leg holds no aircraft yet (not polled, "
                      f"or {leg.get('state', 'UNKNOWN')})"}


def unavailable_domains() -> List[Dict[str, str]]:
    aviation = ([] if int(_aviation_leg().get("aircraft") or 0) > 0 else
                [{"domain": "AVIATION",
                  "label": "NO CURRENT DATA — adsb.lol leg not yet polled"}])
    return [
        *aviation,
        {"domain": "MARITIME", "label": "SOURCE AVAILABLE — USER KEY REQUIRED"},  # noqa: E501
        {"domain": "CAMERAS", "label": "NO QUALIFIED SOURCE"},
        {"domain": "WORLD WEATHER", "label": "US ONLY (NWS) — REST OF WORLD: NO CURRENT ENABLED SOURCE"},  # noqa: E501
    ]


def whats_here_now(lat: float, lon: float, radius_km: float,
                   groups: Dict[str, List[Dict[str, Any]]]
                   ) -> Dict[str, Any]:
    try:
        la, lo, r = float(lat), float(lon), float(radius_km)
    except (TypeError, ValueError):
        return {"error": "invalid coordinates", "items": []}
    r = max(5.0, min(1500.0, r))
    buckets: Dict[str, List[str]] = {"earthquakes": [], "disasters": [],
                                     "us_weather_alerts": [],
                                     "news_reports": []}
    for u in groups.get("usgs-earthquakes", []):
        if u.get("lat") is not None and \
                _haversine_km(la, lo, u["lat"], u["lon"]) <= r:
            buckets["earthquakes"].append(u["stable_key"])
    for g in groups.get("gdacs-alerts", []) + groups.get("nasa-eonet", []):
        if g.get("lat") is not None and \
                _haversine_km(la, lo, g["lat"], g["lon"]) <= r:
            buckets["disasters"].append(g["stable_key"])
    # NWS is UNITED STATES ONLY: list context near the US, never abroad.
    in_us = 17.0 <= la <= 72.0 and -180.0 <= lo <= -64.0
    if in_us:
        buckets["us_weather_alerts"] = [
            n["stable_key"] for n in groups.get("nws-alerts", [])][:10]
    else:
        buckets["us_weather_alerts"] = []
    reports = [x["stable_key"] for x in groups.get("gdelt-doc", [])][:10]
    buckets["news_reports"] = list(reports)
    covered = any(buckets.values())
    return {"at": {"lat": la, "lon": lo}, "radius_km": r,
            "summary": {k: len(v) for k, v in buckets.items()},
            "sample_keys": {k: v[:6] for k, v in buckets.items()},
            "news_reports": reports,
            "no_qualified_source": [] if covered else [
                "no enabled-source event within radius; aviation/maritime "
                "need operator keys; cameras have no qualified source"],
            "coverage_notes": [
                "NWS weather alerts cover the UNITED STATES ONLY",
                "GDELT news context is reported events, never ground truth"],
            "note": "real cached public signals only; every key links to "
                    "evidence with source + time",
            "truth_label": "WORLD NOW (real public feeds)"}


def region_now(selector: str,
               groups: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    from gods_eye.future import world_demo as _w
    base = _w.region_overview(selector, _w.world_payload(tick=0))
    if base.get("status") == "UNKNOWN":
        return {"region": selector, "status": "UNKNOWN",
                "note": "no matching public region in gazetteer",
                "mode": "now"}
    lat0, lon0 = base["center"]["lat"], base["center"]["lon"]
    here = whats_here_now(lat0, lon0, 1200.0, groups)
    return {"region": base["region"], "center": base["center"],
            "radius_km": 1200.0, "mode": "now",
            "real": here["summary"],
            "news_reports": here["news_reports"],
            "static_context": STATIC_CONTEXT,
            "no_coverage": here["no_qualified_source"],
            "truth_label": "WORLD NOW (real public feeds)"}
