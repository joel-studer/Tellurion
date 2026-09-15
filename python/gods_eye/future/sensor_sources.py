"""FUTURE-ONLY public sensor-source registry (V18, offline, no network).

Machine-readable candidate catalog for lawful public data feeds.
Every entry records rights explicitly; nothing here is fetched —
adapters fetch only after rights qualification (see
`public_api.register_*` + validator gates).

Qualification states:
  QUALIFIED          — keyless open data, usable in demo with attribution
  BEST_EFFORT        — keyless but intermittent; fixture fallback required
  USER_KEY           — needs a per-user credential; never bundled, never shared
  FEED_SHARE         — needs a user-operated feed (e.g. own receiver)
  NEEDS_TERMS_REVIEW — public endpoint, but redistribution/terms need
                       counsel or maintainer review before any use
  SYNTHETIC_ONLY     — no lawful live source; demo stays fixture/replay

"Public API" never implies redistributable. See
`docs/guides/rights-policy.md`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

STATUSES = ("QUALIFIED", "BEST_EFFORT", "USER_KEY", "FEED_SHARE",
            "NEEDS_TERMS_REVIEW", "SYNTHETIC_ONLY")

CATEGORIES = ("AVIATION", "MARITIME", "SATELLITE", "WEATHER", "RADAR",
              "WILDFIRE", "SEISMIC", "TRAFFIC", "ROAD", "PUBLIC_CAMERA",
              "PORT", "AIRPORT", "INFRASTRUCTURE", "ENERGY", "GOVERNMENT",
              "DISASTER", "NEWS", "GEOCODING", "SPACE")


@dataclass(frozen=True)
class SensorSource:
    source_id: str
    category: str
    title: str
    endpoint: str
    auth: str           # none | user-key | feed-share
    https: bool
    rate_limit: str
    realtime: str       # REALTIME | DELAYED | STATIC
    coverage: str
    data_rights: str
    commercial_use: str
    redistribution: str
    retention: str
    provenance: str
    quality: str
    status: str
    plugin_potential: str


SOURCES: List[SensorSource] = [
    SensorSource(
        source_id="usgs-earthquakes", category="SEISMIC",
        title="USGS Earthquake Hazards (GeoJSON feeds + FDSN catalog)",
        endpoint="https://earthquake.usgs.gov/earthquakes/feed/v1.0/",
        auth="none", https=True,
        rate_limit="polite polling; minute-refresh feeds; 20k catalog cap",
        realtime="REALTIME", coverage="global",
        data_rights="US public domain (federal source)",
        commercial_use="permitted (public domain)",
        redistribution="permitted (public domain)",
        retention="operator feed lifecycle; keep fetch timestamps",
        provenance="USGS Earthquake Hazards Program",
        quality="high; minute updates; magnitude/depth/place standard",
        status="QUALIFIED",
        plugin_potential="seismic layer live leg (fixture fallback kept)",
    ),
    SensorSource(
        source_id="noaa-weather-alerts", category="WEATHER",
        title="NOAA weather.gov alerts + forecast (US)",
        endpoint="https://api.weather.gov/",
        auth="none", https=True,
        rate_limit="polite polling; quantify before shipping",
        realtime="REALTIME", coverage="US states/territories",
        data_rights="US public domain (federal source)",
        commercial_use="permitted (public domain)",
        redistribution="permitted (public domain)",
        retention="alerts expire; keep valid-time windows",
        provenance="National Weather Service",
        quality="high for US; no global coverage",
        status="QUALIFIED",
        plugin_potential="weather alert polygons + storm tracks (US leg)",
    ),
    SensorSource(
        source_id="nasa-eonet", category="DISASTER",
        title="NASA EONET natural-event tracker (v3)",
        endpoint="https://eonet.gsfc.nasa.gov/api/v3/events",
        auth="none", https=True,
        rate_limit="polite polling; paginate with limit/days",
        realtime="DELAYED", coverage="global (curated)",
        data_rights="open metadata; imagery via linked sources per terms",
        commercial_use="review linked-source terms first",
        redistribution="metadata ok; imagery per source",
        retention="open/closed lifecycle; keep status + closed date",
        provenance="NASA Earth Observatory pipeline",
        quality="medium; intermittent 500s observed spring 2026",
        status="BEST_EFFORT",
        plugin_potential="disaster feed with fixture fallback + health states",
    ),
    SensorSource(
        source_id="opensky-network", category="AVIATION",
        title="OpenSky Network state vectors (OAuth2 client credentials)",
        endpoint="https://opensky-network.org/api/states/all",
        auth="user-key", https=True,
        rate_limit="credit quotas: anon 400/day, account 4,000/day, "
                   "per-endpoint; bbox-area pricing",
        realtime="DELAYED", coverage="global (receiver-dependent)",
        data_rights="account terms; no redistribution of bulk feed",
        commercial_use="per account tier",
        redistribution="not permitted for bulk states",
        retention="keep fetch time; 1h history only for accounts",
        provenance="OpenSky Network community receivers",
        quality="high where covered; quota exhausts fast",
        status="USER_KEY",
        plugin_potential="optional aviation live leg (quota-aware, cached)",
    ),
    SensorSource(
        source_id="nasa-firms", category="WILDFIRE",
        title="NASA FIRMS active-fire hotspots (per-user MAP_KEY)",
        endpoint="https://firms.modaps.eosdis.nasa.gov/api/",
        auth="user-key", https=True,
        rate_limit="5,000 transactions per 10 minutes per key",
        realtime="DELAYED", coverage="global (MODIS/VIIRS/Landsat/GOES)",
        data_rights="per-user key terms; key never shared or bundled",
        commercial_use="per FIRMS terms",
        redistribution="derived display ok; key never redistributed",
        retention="NRT vs standard-processing windows differ; keep sensor id",
        provenance="NASA LANCE FIRMS",
        quality="high; sensor + confidence per hotspot",
        status="USER_KEY",
        plugin_potential="optional wildfire live leg (key holder only)",
    ),
    SensorSource(
        source_id="aisstream", category="MARITIME",
        title="AISStream vessel stream (registration key, WebSocket-only)",
        endpoint="wss://stream.aisstream.io/v0/stream",
        auth="user-key", https=True,
        rate_limit="per-account stream limits; bbox subscription required",
        realtime="REALTIME", coverage="global (receiver-dependent)",
        data_rights="account terms; server-side key handling only",
        commercial_use="per account terms",
        redistribution="not permitted for raw stream",
        retention="keep receipt time; tracks are user-side only",
        provenance="AISStream community feed",
        quality="high where covered; needs server proxy, never browser-direct",
        status="USER_KEY",
        plugin_potential="optional maritime live leg via user server proxy",
    ),
    SensorSource(
        source_id="aishub", category="MARITIME",
        title="AISHub cooperative feed (own receiver required)",
        endpoint="https://data.aishub.net/",
        auth="feed-share", https=True,
        rate_limit="max once per minute; quality thresholds apply",
        realtime="REALTIME", coverage="member-dependent (1,500+ stations)",
        data_rights="membership terms; access earned by sharing a feed",
        commercial_use="per membership terms",
        redistribution="per membership terms",
        retention="keep receipt time",
        provenance="AISHub member stations",
        quality="high for members; inaccessible without a receiver",
        status="FEED_SHARE",
        plugin_potential="receiver-owner maritime leg only",
    ),
    SensorSource(
        source_id="open-meteo", category="WEATHER",
        title="Open-Meteo forecast (keyless, attribution terms)",
        endpoint="https://api.open-meteo.com/v1/forecast",
        auth="none", https=True,
        rate_limit="generous free tier; commercial tier separate",
        realtime="DELAYED", coverage="global grids",
        data_rights="terms-gated: attribution required; non-commercial default",
        commercial_use="requires commercial subscription",
        redistribution="per terms; attribute + link back",
        retention="forecast valid-time windows; keep model run time",
        provenance="Open-Meteo (DWD/GFS blends)",
        quality="good for demo overlays outside the US",
        status="NEEDS_TERMS_REVIEW",
        plugin_potential="weather overlay leg after terms sign-off",
    ),
    SensorSource(
        source_id="stac-public-catalogs", category="SATELLITE",
        title="Public STAC catalogs (earth-search / planetary computer patterns)",
        endpoint="per-catalog STAC API root",
        auth="none", https=True,
        rate_limit="per catalog; tile politely",
        realtime="DELAYED", coverage="global archives + NRT collections",
        data_rights="per-collection licenses (mostly CC-BY / CDLA variants)",
        commercial_use="per collection",
        redistribution="preview assets per collection terms",
        retention="acquisition time + collection version pinned",
        provenance="catalog operator + mission owner",
        quality="high; footprint + preview + cloud-cover standard",
        status="NEEDS_TERMS_REVIEW",
        plugin_potential="satellite scene/footprint leg (pinned collections)",
    ),
    SensorSource(
        source_id="dot-public-cameras", category="PUBLIC_CAMERA",
        title="DOT public traffic cameras (operator snapshot feeds)",
        endpoint="per-operator open feed",
        auth="none", https=True,
        rate_limit="per operator; snapshots only, never streams",
        realtime="DELAYED", coverage="per operator region",
        data_rights="per-operator terms; snapshots only",
        commercial_use="per operator",
        redistribution="thumbnails per operator terms",
        retention="keep last-update timestamp; no archival",
        provenance="road operator (TfL/WSDOT/Caltrans-style)",
        quality="medium; availability varies",
        status="NEEDS_TERMS_REVIEW",
        plugin_potential="camera-point leg after per-operator sign-off",
    ),
    SensorSource(
        source_id="synthetic-replay", category="NEWS",
        title="Bundled synthetic replay (all movement layers in base demo)",
        endpoint="local fixture (no network)",
        auth="none", https=True,
        rate_limit="none (local)",
        realtime="STATIC", coverage="demo region (synthetic)",
        data_rights="CC0 synthetic, generated in-repo",
        commercial_use="permitted",
        redistribution="permitted",
        retention="versioned with the demo dataset",
        provenance="GOD'S EYE synthetic generator (seeded, deterministic)",
        quality="deterministic; honest by construction",
        status="QUALIFIED",
        plugin_potential="default for aviation/maritime/traffic/cameras",
    ),
]

_BY_ID: Dict[str, SensorSource] = {s.source_id: s for s in SOURCES}


def list_sources(status: str | None = None,
                 category: str | None = None) -> List[SensorSource]:
    out = list(SOURCES)
    if status:
        out = [s for s in out if s.status == status]
    if category:
        out = [s for s in out if s.category == category]
    return out


def get(source_id: str) -> SensorSource:
    return _BY_ID[source_id]


def scout_rank() -> List[Dict[str, Any]]:
    """Discovery-only ranking: relevance first, friction second.

    Score favours keyless + open-rights + realtime; never connects.
    """
    status_rank = {"QUALIFIED": 0, "BEST_EFFORT": 1,
                   "NEEDS_TERMS_REVIEW": 2, "USER_KEY": 3, "FEED_SHARE": 4,
                   "SYNTHETIC_ONLY": 5}
    rows = []
    for s in SOURCES:
        friction = status_rank.get(s.status, 9)
        fresh = {"REALTIME": 0, "DELAYED": 1, "STATIC": 2}.get(s.realtime, 3)
        rows.append({"source_id": s.source_id, "category": s.category,
                     "status": s.status, "realtime": s.realtime,
                     "score": friction * 10 + fresh,
                     "note": s.plugin_potential})
    return sorted(rows, key=lambda r: (r["score"], r["source_id"]))


def summary() -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    for s in SOURCES:
        counts[s.status] = counts.get(s.status, 0) + 1
    return {"schema": "sensor-sources-v1", "n_sources": len(SOURCES),
            "statuses": counts,
            "rule": "public endpoint is never assumed redistributable"}
