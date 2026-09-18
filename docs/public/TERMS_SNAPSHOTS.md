# TERMS SNAPSHOTS — Real World Activation (verified 2026-09-16)

> Metadata only. No terms-page content is copied into this repo.
> `terms_hash` = sha256 (first 16 hex) of the live terms page bytes as
> fetched once on the retrieval date. Re-verify before release if older
> than 90 days or if a source's health checks start failing.
>
> Review method: live HTTP fetch of terms + endpoint, single polite
> requests, `Tellurion-terms-review/1.0` UA. Endpoint checks used
> small representative queries only.

## ENABLED — usgs-earthquakes

- operator: USGS Earthquake Hazards Program
- endpoint: `https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.geojson`
- endpoint check: HTTP 200, `application/json`, 59,691 bytes, 85 events
- terms_url: `https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits`
- retrieved_at: 2026-09-16
- terms_hash: `858b88657db20444`
- license: US public domain (USGS-authored data; 17 U.S.C. Sec. 105)
- attribution: `... courtesy of the U.S. Geological Survey`
- redistribution: permitted (public domain)
- commercial_use: permitted (public domain)
- retention: keep fetch timestamps; feed lifecycle (events age out)
- rate_limit: polite polling; minute-refresh feeds; no key
- refresh_ttl: 120 s
- notes: previous registry URL (`.../copyright-and-credit`) now 404;
  canonical page is `.../copyrights-and-credits`. Truth mode DELAYED.

## ENABLED — nws-alerts (US ONLY)

- operator: National Weather Service
- endpoint: `https://api.weather.gov/alerts/active?status=actual&message_type=alert`
- endpoint check: HTTP 200, `application/geo+json`, ~951 KB, 247 features
- terms_url: `https://www.weather.gov/documentation/services-web-api`
- retrieved_at: 2026-09-16
- terms_hash: `b42a2befae076b34`
- license: US public domain
- attribution: credit National Weather Service
- redistribution: permitted (public domain)
- commercial_use: permitted (public domain)
- retention: alerts expire; keep valid-time windows
- rate_limit: polite polling; descriptive `User-Agent` required
- refresh_ttl: 300 s
- notes: coverage is UNITED STATES ONLY — UI must say so. Many alerts
  are zone-based (`geometry: null`); those render list-only, never
  faked onto the map. Truth mode DELAYED.

## ENABLED — noaa-swpc

- operator: NOAA Space Weather Prediction Center
- endpoints:
  `https://services.swpc.noaa.gov/products/alerts.json` (200, live),
  `https://services.swpc.noaa.gov/products/noaa-scales.json` (200, live)
- terms_url: `https://www.swpc.noaa.gov/content/data-access`
- retrieved_at: 2026-09-16
- terms_hash: `b3d7343bcec7bdee`
- license: US public domain
- attribution: credit NOAA SWPC
- redistribution: permitted (public domain)
- commercial_use: permitted (public domain)
- retention: keep product issue time; alerts expire
- rate_limit: polite polling; per-product cadence
- refresh_ttl: 300 s
- notes: global solar/geomagnetic products. Optional layer. DELAYED.

## ENABLED — nasa-eonet (metadata leg)

- operator: NASA Earth Observatory / EONET
- endpoint: `https://eonet.gsfc.nasa.gov/api/v3/events?status=open&days=30`
- endpoint check: HTTP 200, 5 open events returned for `limit=5` probe
- terms_url: `https://eonet.gsfc.nasa.gov/docs/v3`
- retrieved_at: 2026-09-16
- terms_hash: `94d36e80c59a397a`
- license: open metadata (US government work); linked imagery per source
- attribution: credit NASA EONET
- redistribution: metadata ok; imagery per linked-source terms
- commercial_use: metadata ok; imagery per linked source
- retention: keep open/closed lifecycle + dates
- rate_limit: polite polling; paginate with limit/days
- refresh_ttl: 900 s
- notes: categories kept as-provided; severity never inferred. DELAYED.

## ENABLED — gdacs-alerts (summary/link leg)

- operator: GDACS (UN OCHA / EC JRC)
- endpoint: `https://www.gdacs.org/xml/rss.xml`
- endpoint check: HTTP 200, `application/xml`, ~756 KB, 247 items with
  `geo:lat`/`geo:long`, `gdacs:bbox`, eventtype/eventid/alertlevel,
  severity, population, country/iso3, from/to dates, report links
- terms_url: `https://www.gdacs.org/About/termofuse.aspx`
- retrieved_at: 2026-09-16
- terms_hash: `b0e3b0156d6e9105`
- license: EU/JRC content; in-band RSS notice states European Union
  (CC BY 4.0) reuse allowed with credit to GDACS
- attribution: credit GDACS
- redistribution: summary + link ok; no bulk mirror
- commercial_use: UNKNOWN (not explicitly granted — fail closed)
- retention: keep event versions + update time
- rate_limit: polite polling
- refresh_ttl: 900 s
- notes: previous registry URL (`/About/terms.aspx`) now 404;
  canonical page is `/About/termofuse.aspx`. GDACS alert/severity
  semantics are displayed verbatim, never reinterpreted. DELAYED.

## ENABLED — gdelt-doc (reported-events leg)

- operator: The GDELT Project
- endpoint: `https://api.gdeltproject.org/api/v2/doc/doc`
  (`mode=artlist&format=json`, single conservative query,
  `maxrecords=25`)
- endpoint check: HTTP 200 observed; HTTP 429 under burst probing with
  body `Please limit requests to one every 5 seconds...`
- terms_url: `https://www.gdeltproject.org/about.html#termsofuse`
- retrieved_at: 2026-09-16
- terms_hash: `384754b514042255`
- license: open platform — unlimited use for academic/commercial/
  governmental use without fee
- attribution: citation to the GDELT Project + link (mandatory)
- redistribution: permitted (rehost/republish/mirror) with citation
- commercial_use: permitted
- retention: keep seen time; articles are reports, never ground truth
- rate_limit: max 1 request per 5 s; Tellurion polls once per 30 min
  with jitter + backoff; 429 → RATE LIMITED health, never retry-storm
- refresh_ttl: 1800 s
- notes: observation type is always NEWS_REPORT / PUBLIC_REPORT.
  Verdict upgraded NEEDS_TERMS_REVIEW → QUALIFIED (reported-events
  leg only) on the basis of this review.

## STANDBY — reliefweb (appname registration required)

- operator: UN OCHA ReliefWeb
- finding: API v1 decommissioned (`410: use v2`); v2 requires an
  **approved appname** (verified HTTP 400 without appname, 403 with
  unapproved appname)
- terms/apidoc: `https://apidoc.reliefweb.int/parameters`
  (retrieved 2026-09-16, sha `7c58c2feadece4be`)
- decision: STANDBY. Adapter accepts an operator-supplied appname via
  local env (`TELLURION_RELIEFWEB_APPNAME`); UI shows CONNECT SOURCE.
  Zero-friction principle kept: nothing ships that needs registration.

## STANDBY — others (unchanged, not probed this pass)

- copernicus-ems: no stable machine-readable public JSON activations
  API found; link-only. STANDBY.
- epa-airnow / eea-airquality / usgs-volcanoes / osm-overpass /
  gtfs-static: qualified last pass; live endpoints not re-probed in
  this pass — stay STANDBY until their activation pass. Never enabled
  merely for being in the registry.
