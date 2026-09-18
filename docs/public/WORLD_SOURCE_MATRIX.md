# WORLD SOURCE MATRIX (Tellurion world-coverage harvest)

> Fresh harvest for the WORLD COVERAGE + DATA DENSITY pass.
> Rule: "public API" never implies redistributable. Every candidate lands
> as NEEDS_TERMS_REVIEW until qualified with terms evidence.
> Base demo stays offline/keyless; live legs are opt-in, user-key,
> rights-gated plugins. No private surveillance sources are listed.

Scoring axes (0-10, higher is better except IMPLEMENTATION_COST where
higher means cheaper/easier):

- GLOBAL_COVERAGE — how much of the world the feed covers
- FRESHNESS — update cadence / latency
- VISUAL_VALUE — how much it adds to the globe (density, polygons, tracks)
- LEGAL_CLARITY — licence/terms clarity for open-source redistribution
- AUTH_FRICTION — 10 = keyless, 0 = heavy auth / membership / paywall
- RELIABILITY — uptime / operator maturity
- DATA_VOLUME — objects per day / per poll
- COMMUNITY_VALUE — how much users care (disasters, flights, weather)
- IMPLEMENTATION_COST — 10 = trivial GeoJSON poll, 0 = WS proxy + quotas

`rights_status`: QUALIFIED | BEST_EFFORT | USER_KEY | FEED_SHARE |
NEEDS_TERMS_REVIEW | SYNTHETIC_ONLY | RESTRICTED | REJECT.

## Qualified keyless open-data (enable as fixture-backed live legs)

| source | operator | domain | coverage | latency | update | auth | rate limit | commercial | redistribution | retention | attribution | license | terms_url | GLOBAL | FRESH | VISUAL | LEGAL | AUTH | RELIAB | VOLUME | COMMUNITY | IMPL_COST | rights_status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| USGS Earthquakes | USGS Earthquake Hazards Program | SEISMIC | global | ~minutes | minute feeds | none | polite polling; 20k catalog cap | permitted (PD) | permitted (PD) | keep fetch ts | none (credit USGS) | US public domain (17 USC 105) | https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits | 10 | 9 | 9 | 10 | 10 | 10 | 8 | 10 | 10 | QUALIFIED |
| NOAA NWS Alerts + Forecast | National Weather Service | WEATHER/SEVERE/STORM | US states+territories | minutes | per-alert | none (User-Agent required) | polite polling | permitted (PD) | permitted (PD) | keep valid-time windows | credit NWS | US public domain | https://www.weather.gov/documentation/services-web-api | 4 | 9 | 9 | 10 | 10 | 10 | 8 | 10 | 9 | QUALIFIED |
| NOAA SWPC | NOAA Space Weather Prediction Center | SPACE_WEATHER | global (solar/geomag) | minutes-hours | 1-5 min products | none | polite polling of JSON products | permitted (PD) | permitted (PD) | keep product issue time | credit SWPC/NOAA | US public domain | https://www.swpc.noaa.gov/content/data-access | 10 | 8 | 7 | 10 | 10 | 9 | 5 | 7 | 9 | QUALIFIED |
| NASA EONET v3 | NASA Earth Observatory | DISASTER (wildfire/storm/volcano/flood/earthquake/landslide) | global curated | hours | daily-ish | none | paginate limit/days; intermittent 500s | metadata ok; imagery per linked source | metadata ok; imagery per source | keep open/closed + dates | credit NASA EONET | open metadata (US gov work) | https://eonet.gsfc.nasa.gov/docs/v3 | 9 | 6 | 9 | 8 | 10 | 6 | 5 | 10 | 10 | QUALIFIED (metadata leg; imagery per-source) |
| GDACS | UN OCHA / EC JRC | DISASTER (eq/flood/cyclone/volcano/drought) | global | hours | per-event | none (RSS/JSON) | polite polling | humanitarian use permitted; commercial UNKNOWN (fail closed) | link + summary ok; bulk per terms | keep event versions | credit GDACS | EU CC BY 4.0 in-band notice (credit GDACS) | https://www.gdacs.org/About/termofuse.aspx | 10 | 7 | 9 | 8 | 10 | 8 | 5 | 10 | 9 | QUALIFIED (summary/link leg; no bulk mirror) |
| ReliefWeb API | UN OCHA | HUMANITARIAN/PUBLIC NOTICE | global | hours-day | continuous | none (appid optional) | polite; paginate | permitted with attribution | API content per terms; source docs per origin | keep published time | credit ReliefWeb + origin | free, attribution | https://reliefweb.int/help/api | 10 | 6 | 6 | 8 | 10 | 9 | 7 | 8 | 9 | QUALIFIED (report metadata, not ground truth) |
| USGS Volcano Hazards (VHP notices) | USGS Volcano Hazards Program | VOLCANO | US + cooperating observatories | hours | per-notice | none | polite polling | permitted (PD) | permitted (PD) | keep notice time | credit USGS | US public domain | https://www.usgs.gov/volcanoes | 5 | 7 | 8 | 10 | 10 | 9 | 3 | 8 | 9 | QUALIFIED |
| Smithsonian GVP weekly (via EONET mirror) | Smithsonian Institution | VOLCANO | global curated | weekly | weekly | none | polite | educational; verify bulk | link/summary; no bulk mirror | keep report date | credit SI GVP | educational use | https://volcano.si.edu/ | 9 | 4 | 7 | 6 | 10 | 8 | 3 | 7 | 8 | NEEDS_TERMS_REVIEW (use via EONET, not scrape) |
| EPA AirNow | US EPA | AIR_QUALITY | US (+partners) | hourly | hourly | none (API key for API; RSS keyless) | polite; key tier for API | permitted (PD federal portion) | permitted with attribution | keep observation time | credit AirNow | US public domain (federal) | https://www.airnow.gov/ | 4 | 8 | 6 | 8 | 8 | 9 | 6 | 6 | 8 | QUALIFIED (US leg) |
| EEA Air Quality (open) | European Environment Agency | AIR_QUALITY | Europe | hourly-daily | hourly | none | polite | open reuse (EU) | open reuse with attribution | keep observation time | credit EEA | EU open data | https://www.eea.europa.eu/en/datahub | 5 | 7 | 6 | 8 | 9 | 8 | 6 | 6 | 8 | QUALIFIED (EU leg) |
| Copernicus EMS / open EU services | EU Copernicus Emergency Management | DISASTER/ENV | global (activations) + Europe | hours-day | per-activation | none | polite | full free open use | full free open with attribution | keep activation version | credit Copernicus EMS | Copernicus free full open | https://emergency.copernicus.eu/ | 8 | 6 | 8 | 9 | 9 | 8 | 4 | 9 | 7 | QUALIFIED (activation metadata leg) |
| OpenStreetMap / Overpass | OSM contributors | GEO/INFRA (static context) | global | static + minutely diffs | static snapshots | none (tile politely; heavy users self-host) | usage policy: cache, no bulk scrape | permitted (ODbL share-alike on DB) | permitted with attribution + share-alike on derived DB | pin planet snapshot date | (c) OpenStreetMap contributors | ODbL 1.0 | https://www.openstreetmap.org/copyright | 10 | 3 | 8 | 9 | 9 | 9 | 10 | 8 | 6 | QUALIFIED (static context only; respect usage policy) |
| GTFS static (per-agency) | transit agencies worldwide | TRANSIT | per-city/region | static timetable | per-release | none | per-agency; cache | per-agency (usually open) | per-agency (usually open) | pin feed version + date | per-agency | per-agency (often CC-BY / ODbL-compatible) | per-agency terms | 6 | 3 | 7 | 7 | 9 | 8 | 7 | 7 | 7 | QUALIFIED (per-feed; verify each agency) |

## User-key / gated (adapter exists; never bundled; user supplies own key locally)

| source | operator | domain | coverage | latency | auth | rate limit | commercial | redistribution | rights_status | terms_url | scores (G/F/V/L/A/R/Vol/C/I) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| NASA FIRMS | NASA LANCE | WILDFIRE hotspots | global (MODIS/VIIRS/Landsat/GOES) | NRT ~3h | user MAP_KEY | 5,000 tx / 10 min / key | per FIRMS terms | derived display ok; key never redistributed | USER_KEY | https://firms.modaps.eosdis.nasa.gov/api/ | 10/9/10/7/5/9/10/10/8 |
| OpenSky Network | OpenSky Network association | AVIATION states | global receiver-dependent | ~10 s (+delay tiers) | OAuth2 user creds | 400/day anon, 4,000/day acct, bbox pricing | per tier; non-commercial default | NO bulk redistribution | USER_KEY (non-commercial default; agreement needed for product use) | https://opensky-network.org/about/terms-of-use | 9/9/10/5/4/8/10/10/6 |
| AISStream | AISStream | MARITIME stream | global receiver-dependent | real-time | user key, WS-only, server proxy | per-account; bbox subscription | per account | NO raw redistribution | USER_KEY | https://aisstream.io/ | 9/10/9/4/3/8/9/9/4 |
| AISHub | AISHub | MARITIME | member-dependent 1,500+ stations | real-time | feed-share (own receiver) | max 1/min | per membership | per membership | FEED_SHARE | https://data.aishub.net/ | 7/10/8/4/1/8/8/7/4 |
| GTFS-RT (per-agency) | transit agencies | TRANSIT realtime | per-city | seconds-min | user or keyless per agency | per-agency | per-agency | per-agency | USER_KEY or QUALIFIED per feed | per-agency | 5/9/8/6/6/8/7/7/5 |
| OpenAQ | OpenAQ | AIR_QUALITY | global (station-dependent) | hourly | none/key tier v3 | polite; key for high volume | per terms (verify commercial) | attribution required | NEEDS_TERMS_REVIEW (verify v3 terms before live) | https://openAQ.org/ | 9/8/6/6/8/7/7/6/8 |
| adsb.lol / public ADS-B aggregators | community | AVIATION | receiver-dependent | seconds | none/user key | polite; quota | ODbL share-alike where stated | share-alike on derived DB | NEEDS_TERMS_REVIEW (verify per-endpoint before use) | https://adsb.lol/ | 8/10/10/5/7/7/10/9/7 |

## Terms-review / restricted / rejected

| source | verdict | reason |
|---|---|---|
| CelesTrak (TLE/OEM) | NEEDS_TERMS_REVIEW | Public element sets are widely mirrored, but CelesTrak terms restrict automated bulk use and require review; use only after counsel/maintainer sign-off. Never for targeting. Terms: https://celestrak.org/ |
| Public STAC catalogs (earth-search / Planetary Computer) | NEEDS_TERMS_REVIEW per collection | Metadata + footprints generally fine; preview assets per-collection (CC-BY/CDLA). Pin collection + version. |
| Open-Meteo | NEEDS_TERMS_REVIEW | Keyless but terms-gated: attribution required, non-commercial default; commercial tier separate. https://open-meteo.com/en/terms |
| DOT / operator public cameras | NEEDS_TERMS_REVIEW per operator | Only snapshots from operators whose terms explicitly allow embedding; per-operator sign-off; snapshot time + operator + rights shown; no streams; no analytics. |
| GDELT 2.x DOC ArtList | QUALIFIED (reported-events leg, verified 2026-09-16) | Unlimited academic/commercial/governmental use + redistribution with citation + link; DOC API max 1 req/5 s (429 enforced) — Tellurion polls 1x/30 min. Noisy; OBSERVED=never — always NEWS_REPORT; never ground truth. https://www.gdeltproject.org/about.html#termsofuse |
| OpenSky bulk / commercial resale | RESTRICTED | Non-commercial default; bulk redistribution not permitted without agreement. Adapter is user-key display-only. |
| Commercial AIS resale feeds | RESTRICTED | No commercial/restricted feed without written permission. |
| Private CCTV / RTSP / ONVIF scanning / home cameras / facial recognition / person tracking / plate recognition / Wi-Fi-BT interception / phone tracking / deanonymization / covert personnel tracking / paywall bypass / credential access | REJECT | Never listed, never integrated. See safety boundary. |
| Military targeting / strike guidance | REJECT | Situational-awareness shapes only (published NOTAM/exercise-area polygons); never targeting. |

## Selected for this pass (highest value x lowest rights risk)

1. USGS Earthquakes — QUALIFIED — seismic live leg (fixture fallback).
2. NOAA NWS Alerts — QUALIFIED — US weather-alert live leg.
3. NOAA SWPC — QUALIFIED — space-weather live leg.
4. NASA EONET — QUALIFIED (metadata) — global disaster feed.
5. GDACS — QUALIFIED (summary/link) — global disaster corroboration.
6. ReliefWeb — QUALIFIED — humanitarian context (PUBLIC_REPORT).
7. Copernicus EMS — QUALIFIED — activation metadata.
8. EPA AirNow + EEA AQ — QUALIFIED — air-quality legs (US + EU).
9. OSM/Overpass static + GTFS static per-agency — QUALIFIED — geographic + transit context.
10. FIRMS / OpenSky / AISStream / AISHub — USER_KEY/FEED_SHARE adapters (user opt-in, quota-aware, cached, never bundled).
11. CelesTrak / STAC / Open-Meteo / OpenAQ / operator cameras — NEEDS_TERMS_REVIEW; adapters are parse-only + fixture-backed, disabled until sign-off.
    GDELT DOC ArtList upgraded to QUALIFIED (reported-events leg) after the 2026-09-16 terms review — see `TERMS_SNAPSHOTS.md`.

## Freshness contract (truth model)

Every observation carries: source, source_event_time, published_time?,
first_seen, ingested_at, effective_time, precision, rights, provenance,
observation_type (OBSERVED / PUBLIC_REPORT / GOVERNMENT_NOTICE /
NEWS_REPORT / INFERRED / UNKNOWN). Unknown timestamps stay UNKNOWN.
Ingest time is never substituted for event time. Live / delayed / static /
replay / synthetic is declared per source and per object.
