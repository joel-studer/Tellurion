# LIVE MARITIME SOURCE RESEARCH (verified 2026-09-16)

> Metadata only. No terms-page content is copied into this repo.
> Review method: live documentation/API-page fetch with
> `Tellurion-terms-review/1.0` UA + search-verified community
> evidence. Re-verify before any activation.

## DECISION: NONE QUALIFIED for default live use

No public maritime source currently meets the Tellurion default-use
gate (clear licence + clear commercial/redistribution terms + keyless
or operator-key path that works without special hardware). Live
vessels therefore stay SYNTHETIC REPLAY; WORLD NOW shows an honest
NO LIVE SOURCE state for maritime. This is a product decision, not a
data failure — revisit when a source publishes citable terms.

## Candidate 1 — AISStream (standby: key + terms gap)

- endpoints: `wss://stream.aisstream.io/v0/stream` (WebSocket ONLY,
  no REST); subscription = APIKey + BoundingBoxes (+ optional MMSI /
  message-type filters); binary frames, UTF-8 JSON payloads
- docs: `https://aisstream.io/documentation.html` (verified live
  2026-09-16)
- auth: free API key via GitHub sign-in; **server-side only —
  direct browser connections are NOT permitted** (proxy required,
  which matches Tellurion's backend-only boundary)
- licence: **NONE PUBLISHED** — `/terms` returns 404, repos carry no
  data licence; open community issues ask for written storage /
  redistribution / commercial-use terms with no citable answer
  (verified 2026-09-16)
- commercial_use: UNKNOWN (asked publicly, unanswered on paper)
- redistribution: UNKNOWN (storage of messages, aggregates, derived
  DBs all unanswered on paper)
- rate_limits: per-account; subscription updates ≤ 1/s; focused
  bbox + message filters expected
- coverage: global, receiver-dependent
- latency: real-time push
- history: none public (live stream only)
- attribution: customary "vessel data via aisstream.io" (no mandate
  on paper)
- verdict: KEY_REQUIRED + NEEDS_TERMS — user-key path only with the
  operator's own key AND the operator's own terms acceptance; never
  enabled by default. A future adapter must be WebSocket-client
  based (stdlib has none — dependency question open).

## Candidate 2 — AISHub (standby: feed-share hardware gate)

- endpoints: member webservice (XML/JSON/CSV); ≥ 1/min polling
- docs: `https://www.aishub.net/api` (verified live 2026-09-16)
- auth: **members only — membership requires feeding data from your
  own AIS receiver** (FEED_SHARE); no keyless path exists
- licence/commercial/redistribution: per-membership, not a public
  open-data grant
- verdict: FEED_SHARE — only for operators who already run a shore
  receiver; never a default leg.

## Privacy boundary (binding when any maritime leg activates)

Allowed: MMSI/IMO as publicly broadcast, vessel name as broadcast,
type, course, speed, position, nav status, publicly broadcast
destination, port proximity. Forbidden: private owner identity,
crew/passenger identity, home addresses, private-person association,
VIP/yacht owner watchlists, smuggling/piracy/intent inference from
movement alone. Canonical model is specified in the movement report;
no adapter is implemented until a source qualifies.
