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
`docs/public/RIGHTS_POLICY.md`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

STATUSES = ("QUALIFIED", "BEST_EFFORT", "USER_KEY", "FEED_SHARE",
            "NEEDS_TERMS_REVIEW", "SYNTHETIC_ONLY")

CATEGORIES = ("AVIATION", "MARITIME", "SATELLITE", "WEATHER", "RADAR",
              "WILDFIRE", "SEISMIC", "VOLCANO", "TRAFFIC", "ROAD", "TRANSIT",
              "PUBLIC_CAMERA", "PORT", "AIRPORT", "INFRASTRUCTURE", "ENERGY",
              "GOVERNMENT", "DISASTER", "NEWS", "HUMANITARIAN", "AIR_QUALITY",
              "SPACE_WEATHER", "SPACE", "GEOCODING", "FLOOD", "TSUNAMI",
              "STORM", "LIGHTNING")


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
        status="QUALIFIED",
        plugin_potential="disaster feed (metadata leg qualified; "
                         "fixture fallback + health states)",
    ),
    SensorSource(
        source_id="adsb-lol-live", category="AVIATION",
        title="adsb.lol v2 live aircraft (point tiles + squawk/mil legs)",
        endpoint="https://api.adsb.lol/v2/",
        auth="none", https=True,
        rate_limit="dynamic by load; 4xx means back off; Tellurion polls "
                    "9 tiles/120-300 s + squawk legs/60 s + mil/120 s",
        realtime="DELAYED", coverage="regional tiles (PARTIAL by design; "
                    "oceans/Africa/polar uncovered)",
        data_rights="ODbL 1.0 (display + transient cache; attribution "
                    "mandatory; share-alike if a derived DB is conveyed)",
        commercial_use="permitted (ODbL, no non-commercial clause)",
        redistribution="permitted with attribution + share-alike on "
                       "derived DB; bulk export refused in-app",
        retention="transient TTL cache + rolling ~15 min memory trails; "
                  "no disk persistence of tracks",
        provenance="adsb.lol community receivers",
        quality="high in tiled corridors; receiver-dependent elsewhere",
        status="QUALIFIED",
        plugin_potential="WORLD NOW live aviation layer + IMPORTANT NOW",
    ),
    SensorSource(
        source_id="airplanes-live", category="AVIATION",
        title="airplanes.live REST API (non-commercial fallback)",
        endpoint="https://api.airplanes.live/v2/",
        auth="none", https=True,
        rate_limit="1 request/second; contribution expected",
        realtime="DELAYED", coverage="global (receiver-dependent)",
        data_rights="free REST API is Non-Commercial Use; no SLA",
        commercial_use="NOT permitted on free REST API",
        redistribution="per non-commercial terms; verify before any use",
        retention="per terms",
        provenance="airplanes.live community receivers",
        quality="good; unfiltered incl. military/LADD",
        status="NEEDS_TERMS_REVIEW",
        plugin_potential="standby non-commercial fallback only; never "
                         "primary for Tellurion default use",
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
        provenance="Tellurion synthetic generator (seeded, deterministic)",
        quality="deterministic; honest by construction",
        status="QUALIFIED",
        plugin_potential="default for aviation/maritime/traffic/cameras",
    ),
    # ---- WORLD COVERAGE harvest (public-safe only; see WORLD_SOURCE_MATRIX.md)
    SensorSource(
        source_id="noaa-swpc", category="SPACE_WEATHER",
        title="NOAA SWPC space-weather products (JSON)",
        endpoint="https://services.swpc.noaa.gov/products/",
        auth="none", https=True,
        rate_limit="polite polling; per-product cadence",
        realtime="DELAYED", coverage="global (solar/geomagnetic)",
        data_rights="US public domain (federal source)",
        commercial_use="permitted (public domain)",
        redistribution="permitted (public domain)",
        retention="keep product issue time; alerts expire",
        provenance="NOAA Space Weather Prediction Center",
        quality="high; Kp/Dst/flare/geomag-storm products standard",
        status="QUALIFIED",
        plugin_potential="space-weather layer live leg",
    ),
    SensorSource(
        source_id="gdacs-alerts", category="DISASTER",
        title="GDACS global disaster alerts (RSS/JSON summaries)",
        endpoint="https://www.gdacs.org/gdacsapi/api/",
        auth="none", https=True,
        rate_limit="polite polling; per-event fetch",
        realtime="DELAYED", coverage="global",
        data_rights="free humanitarian use; summary/link ok",
        commercial_use="verify commercial reuse first",
        redistribution="summary + link ok; no bulk mirror",
        retention="keep event versions + update time",
        provenance="GDACS (UN OCHA / EC JRC)",
        quality="high for major disasters; curated",
        status="QUALIFIED",
        plugin_potential="disaster corroboration leg",
    ),
    SensorSource(
        source_id="reliefweb-reports", category="HUMANITARIAN",
        title="ReliefWeb reports/jobs API (UN OCHA)",
        endpoint="https://api.reliefweb.int/v1/reports",
        auth="none", https=True,
        rate_limit="polite; paginate limit/offset",
        realtime="DELAYED", coverage="global",
        data_rights="free with attribution; source docs per origin",
        commercial_use="per terms; attribute origin",
        redistribution="API metadata ok; origin docs per terms",
        retention="keep published time + source",
        provenance="UN OCHA ReliefWeb",
        quality="high; situation reports, not ground truth",
        status="QUALIFIED",
        plugin_potential="humanitarian context leg (PUBLIC_REPORT)",
    ),
    SensorSource(
        source_id="copernicus-ems", category="DISASTER",
        title="Copernicus EMS activations (open EU)",
        endpoint="https://emergency.copernicus.eu/",
        auth="none", https=True,
        rate_limit="polite polling",
        realtime="DELAYED", coverage="global activations + Europe",
        data_rights="Copernicus free full open use",
        commercial_use="permitted with attribution",
        redistribution="permitted with attribution",
        retention="keep activation version",
        provenance="EU Copernicus Emergency Management Service",
        quality="high for activations; mapping products standard",
        status="QUALIFIED",
        plugin_potential="disaster activation leg",
    ),
    SensorSource(
        source_id="usgs-volcanoes", category="VOLCANO",
        title="USGS Volcano Hazards Program notices",
        endpoint="https://volcanoes.usgs.gov/",
        auth="none", https=True,
        rate_limit="polite polling",
        realtime="DELAYED", coverage="US + cooperating observatories",
        data_rights="US public domain (federal source)",
        commercial_use="permitted (public domain)",
        redistribution="permitted (public domain)",
        retention="keep notice time + alert level",
        provenance="USGS Volcano Hazards Program",
        quality="high; alert-level + notice vocabulary",
        status="QUALIFIED",
        plugin_potential="volcano layer live leg",
    ),
    SensorSource(
        source_id="epa-airnow", category="AIR_QUALITY",
        title="EPA AirNow observations (US)",
        endpoint="https://www.airnow.gov/",
        auth="none", https=True,
        rate_limit="polite; key tier for high-volume API",
        realtime="DELAYED", coverage="US (+partners)",
        data_rights="US public domain (federal portion)",
        commercial_use="permitted with attribution",
        redistribution="permitted with attribution",
        retention="keep observation time",
        provenance="US EPA AirNow",
        quality="high; AQI + PM2.5/O3 standard",
        status="QUALIFIED",
        plugin_potential="air-quality US leg",
    ),
    SensorSource(
        source_id="eea-airquality", category="AIR_QUALITY",
        title="EEA air-quality open data (Europe)",
        endpoint="https://www.eea.europa.eu/en/datahub",
        auth="none", https=True,
        rate_limit="polite polling",
        realtime="DELAYED", coverage="Europe",
        data_rights="EU open data reuse",
        commercial_use="permitted with attribution",
        redistribution="permitted with attribution",
        retention="keep observation time",
        provenance="European Environment Agency",
        quality="good; station observations",
        status="QUALIFIED",
        plugin_potential="air-quality EU leg",
    ),
    SensorSource(
        source_id="osm-overpass", category="INFRASTRUCTURE",
        title="OpenStreetMap / Overpass (static context)",
        endpoint="https://overpass-api.de/api/interpreter",
        auth="none", https=True,
        rate_limit="tile politely; cache; self-host for heavy use",
        realtime="STATIC", coverage="global",
        data_rights="ODbL 1.0 (share-alike on derived DB)",
        commercial_use="permitted (ODbL share-alike)",
        redistribution="permitted with attribution + share-alike",
        retention="pin planet snapshot date",
        provenance="OpenStreetMap contributors",
        quality="high for ports/airports/roads static context",
        status="QUALIFIED",
        plugin_potential="static infra context (never live tracking)",
    ),
    SensorSource(
        source_id="gtfs-static", category="TRANSIT",
        title="GTFS static timetables (per-agency)",
        endpoint="per-agency open GTFS zip",
        auth="none", https=True,
        rate_limit="per agency; cache releases",
        realtime="STATIC", coverage="per city/region",
        data_rights="per-agency open terms",
        commercial_use="per agency (usually permitted)",
        redistribution="per agency (usually permitted)",
        retention="pin feed version + date",
        provenance="transit agency (per feed)",
        quality="high for stop/route shapes",
        status="QUALIFIED",
        plugin_potential="transit static leg (Austria/EU/US packs)",
    ),
    SensorSource(
        source_id="celestrak", category="SPACE",
        title="CelesTrak orbital element sets (public catalog)",
        endpoint="https://celestrak.org/",
        auth="none", https=True,
        rate_limit="polite; no bulk automation per terms",
        realtime="DELAYED", coverage="global catalog",
        data_rights="terms-gated; review before any use",
        commercial_use="review terms first",
        redistribution="review terms first",
        retention="keep element epoch",
        provenance="CelesTrak (public element sets)",
        quality="high; TLE/OEM standard",
        status="NEEDS_TERMS_REVIEW",
        plugin_potential="satellite catalog leg only after sign-off",
    ),
    SensorSource(
        source_id="gdelt-events", category="NEWS",
        title="GDELT 2.x DOC ArtList (reported events, conservative query)",
        endpoint="https://api.gdeltproject.org/api/v2/doc/doc",
        auth="none", https=True,
        rate_limit="max 1 req / 5 s enforced (429); Tellurion polls 1x / 30 min",
        realtime="DELAYED", coverage="global",
        data_rights="open platform: unlimited use incl. commercial; redistribution with citation + link",
        commercial_use="permitted (with citation)",
        redistribution="permitted with citation + link",
        retention="keep seen time; never ground truth",
        provenance="GDELT Project",
        quality="noisy; reported events only; terms verified 2026-09-16",
        status="QUALIFIED",
        plugin_potential="news-context leg (NEWS_REPORT only; mandatory citation)",
    ),
    SensorSource(
        source_id="openaq", category="AIR_QUALITY",
        title="OpenAQ observations (global stations)",
        endpoint="https://api.openaq.org/v3/",
        auth="none", https=True,
        rate_limit="polite; key for high volume",
        realtime="DELAYED", coverage="global station-dependent",
        data_rights="terms-gated; attribution required",
        commercial_use="verify v3 terms first",
        redistribution="per terms with attribution",
        retention="keep observation time",
        provenance="OpenAQ",
        quality="good where stations exist",
        status="NEEDS_TERMS_REVIEW",
        plugin_potential="air-quality global leg after sign-off",
    ),
    SensorSource(
        source_id="gtfs-rt", category="TRANSIT",
        title="GTFS-RT vehicle positions (per-agency)",
        endpoint="per-agency GTFS-RT endpoint",
        auth="none", https=True,
        rate_limit="per agency (typically 10-30 s)",
        realtime="REALTIME", coverage="per city/region",
        data_rights="per-agency terms",
        commercial_use="per agency",
        redistribution="per agency; display ok, bulk per terms",
        retention="keep vehicle timestamps; transient",
        provenance="transit agency (per feed)",
        quality="high where published",
        status="NEEDS_TERMS_REVIEW",
        plugin_potential="transit live leg per qualified agency feed",
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
