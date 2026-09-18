# adsb.lol PRODUCTION CONTACT PACKAGE (READY — NOT SENT)

> adsb.lol asks production users to get in touch so API changes don't break
> them by accident. This package is prepared for that courtesy contact.
> DO NOT send it automatically: a human operator sends it and records the
> acknowledgement below.

CONTACT_STATUS = READY_TO_SEND

> Refreshed 2026-09-17 with request rates **measured** against the real API
> from the release candidate code (method below). Still NOT SENT.

## What Tellurion is

Tellurion is an open-source, local-first public-data world monitor. WORLD NOW
shows real qualified public feeds (earthquakes, disasters, weather alerts,
space weather, news context, live ADS-B) with per-source attribution,
freshness, rights and health. No accounts, no tracking, no bundled
credentials. It runs on the user's own machine and serves only
`127.0.0.1`. Repository: <GitHub URL placeholder — operator fills before
sending>.

## Measured request rate (2026-09-17)

Method: every outbound request to adsb.lol was counted at the single fetch
function the aviation leg uses, while a real Chromium page loaded WORLD NOW.

| Scenario | Window | Page loads | adsb.lol requests | Average | Peak in any 60 s |
|---|---|---|---|---|---|
| One cold WORLD NOW page load | 28 s | 1 | 4 | — | 4 |
| Page reloaded every 15 s (deliberate worst case) | 600 s | 35 | 50 | **0.083 req/s** | **11** |

What the numbers show:

- The UI does not poll. A page left open makes no further requests; only a
  new page load or an explicit scrub asks the server to refresh.
- Per-leg time-to-live caps the load even under constant reloading: 35 page
  loads in 10 minutes produced 50 requests, not 35 × 13.
- Legs used: 9 regional point tiles (`/v2/lat/{lat}/lon/{lon}/dist/250`),
  each fetched 2–5 times in the 10 minutes, and 3 squawk legs
  (`/v2/squawk/7500|7600|7700`, small responses), each fetched at most 5 times.
- The military leg (`/v2/mil`) was not called at all: it is off unless the
  operator explicitly enables the display-only military layer.
- A 429 response puts that leg into a 300 s cooldown; there is no retry storm
  and no burst on cold start.

## Cache policy

Transient cache in process memory, plus a rolling ~15-minute position history
held in memory only (capped). No disk persistence of tracks, no long-term
archive, no derived database conveyed to anyone.

## Attribution

Every aircraft view shows `adsb.lol contributors (ODbL)`, and the dataset is
labelled `tellurion-aviation-v1`.

## Commitments

- No bulk redistribution: the public server has no export endpoint for
  aviation data at all.
- No commercial resale of the data; no API key sharing (none is needed).
- No private-person tracking: flight state is displayed only, with no owner,
  passenger or VIP enrichment of any kind. Military contacts, when the
  operator enables that layer, are shown as generic movement only.
- Misuse contact: <operator contact placeholder — operator fills before
  sending>.

## Suggested message (operator sends manually)

> Hello adsb.lol team — we run Tellurion, an open-source, local-first
> public-data monitor that uses your v2 API for a live aviation layer. Each
> installation runs on the user's own machine. Measured load per running
> instance: 4 requests on a cold start and about 0.08 requests per second
> (peak 11 per minute) even when the page is reloaded every 15 seconds, across
> 9 regional point tiles and the three squawk endpoints, with a 300-second
> cooldown after any 429. We show ODbL attribution in the app and do not
> redistribute or store tracks. Please tell us if this pattern causes trouble,
> or if you'd prefer we contribute a feed in return.
> Code: <repo URL>. Contact: <operator contact>.

## Acknowledgement log

- (none yet — record the date and a summary of the reply here)
