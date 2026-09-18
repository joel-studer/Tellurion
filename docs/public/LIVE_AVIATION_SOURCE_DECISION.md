# LIVE AVIATION SOURCE DECISION (verified 2026-09-16)

> Metadata only. No terms-page content is copied into this repo.
> Review method: live HTTP fetch of terms/docs/API pages with
> `Tellurion-terms-review/1.0` UA plus small representative API
> queries (1 point tile, 1 squawk query, 1 mil query). Re-verify
> before release if older than 90 days or if health checks fail.

## DECISION

- PRIMARY: **adsb.lol** — QUALIFIED (ODbL 1.0 open-data leg).
- SECONDARY: **airplanes.live** — STANDBY (REST API is non-commercial;
  fails the Tellurion default-use gate; documented fallback only).
- **OpenSky: DO NOT enable operationally without written licence**
  (verbatim terms fetched 2026-09-16; stays USER_KEY/standby).

## PRIMARY — adsb.lol (v2 API)

- operator: adsb.lol community (aggregated volunteer receivers)
- endpoints (verified live 2026-09-16, all HTTP 200):
  `https://api.adsb.lol/v2/lat/{lat}/lon/{lon}/dist/{nm}` (point tile;
  probe `lat/50.03/lon/8.56/dist/100` → 197 positioned aircraft),
  `/v2/squawk/7700` (empty when no current emergency — normal),
  `/v2/mil` (probe → 241 tagged aircraft),
  `/v2/icao/{hex}` per API docs (ADSBExchange-compatible shape)
- docs: `https://api.adsb.lol/docs` (interactive; JS app)
- terms_url: `https://api.adsb.lol/docs` ("Terms of Service" + "License"
  sections); rate-limit text: `https://github.com/adsblol/api`
  (`README.md`, retrieved 2026-09-16, sha `37ddb5660c91eb75`)
- retrieved_at: 2026-09-16
- license: **ODbL 1.0** ("same license OpenStreetMap uses") for the API
  and all public data
- commercial_use: permitted (ODbL; no non-commercial clause)
- redistribution: permitted with attribution + share-alike on a derived
  database; Tellurion displays + keeps a transient TTL cache only and
  conveys no derived database (working interpretation; re-verify on
  any change to storage semantics)
- attribution: `adsb.lol contributors (ODbL)` — shown in UI + payloads
- rate_limit: dynamic by server load; 4xx means back off; no published
  hard limit; community guidance 30–60 s between periodic requests;
  Tellurion strategy stays far inside that (tiles staggered ~2 min,
  squawk/mil legs ~60 s)
- production_use: maintainer asks production users to make contact so
  app changes don't break them — courtesy contact recommended before
  any wide release; NOT YET SENT (recorded as pre-release task)
- auth: none currently; feeder key may be required in the future
  (then this leg degrades to STANDBY until re-qualified)
- coverage: global, receiver-dependent (dense EU/US, sparse ocean/remote)
- API shape: ADSBExchange-compatible JSON (`ac[]` with hex/flight/r/t/
  lat/lon/alt_baro/alt_geom/gs/track/baro_rate/squawk/seen/seen_pos/
  mlat/nav_modes/emergency flags)
- global_access: yes, keyless, documented point-tile API (no scraping)
- historical_access: none public (live positions only)
- operational_product_restriction: none stated beyond ODbL + politeness
- refresh_ttl: tiles 120 s (Oceania 300 s), squawk legs 60 s,
  mil leg 120 s
- coverage detail (2026-09-16 probes): 9 tiles polled; africa-west
  (6.5,3.4/250 nm) and central-asia (41.5,64/250 nm) returned 0
  aircraft and are deliberately NOT polled (no receiver coverage —
  polling them would spend provider budget for zero value); Oceania
  tile verified live (17 aircraft near Sydney)
- privacy: broadcast positions only; no owner/passenger fields exist in
  the API; Tellurion performs no identity enrichment (see IMPORTANT NOW
  boundary section in the aviation report)

## SECONDARY — airplanes.live (STANDBY, not enabled)

- operator: airplanes.live community
- endpoints: `https://api.airplanes.live/v2/` (`/point`, `/squawk`,
  `/mil`, `/icao`, `/reg`, `/type` per API guide)
- terms_url: `https://airplanes.live/terms-of-use/` (JS-rendered;
  page shell fetched 2026-09-16, sha `3ddd6481bb6aae7b`)
- api_guide: `https://airplanes.live/api-guide` (indexed 2026-07-13)
- retrieved_at: 2026-09-16
- license/finding: REST API is explicitly **Non-Commercial Use**, no SLA,
  no uptime guarantee; contribution (feeding) expected of API users
- commercial_use: NOT permitted on the free REST API → fails the
  Tellurion default-use gate → standby fallback only, never primary
- rate_limit: 1 request/second
- coverage: global, receiver-dependent, unfiltered (incl. military/LADD)
- decision: STANDBY. May be wired later as an operator-selected
  non-commercial fallback with its own clear labeling; needs no code
  changes beyond a second tile fetcher (same canonical model).

## NOT ENABLED — OpenSky Network (written licence required)

- terms_url: `https://opensky-network.org/about/terms-of-use`
  (full General Terms of Use & Data License Agreement read verbatim
  2026-09-16; direct curl returned 403, content verified via document
  fetch the same day)
- retrieved_at: 2026-09-16
- license: non-profit research/education only; **any commercial-entity
  use requires a written licence; operational REST API use in any live
  product/service/automated system requires a previous written
  agreement — even for non-profits and governments**
- decision: DO NOT enable operationally without written licence from
  contact[at]opensky-network.org. Stays KEY_REQUIRED/user-key standby;
  user-key path only with the operator's own licence, keys local-only.
