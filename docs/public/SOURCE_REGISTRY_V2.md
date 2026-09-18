# SOURCE REGISTRY V2 (lifecycle)

Statuses: DISCOVERED -> REVIEWING -> QUALIFIED -> ENABLED, with
DISABLED / REJECTED as terminal or paused states. Every transition
records a reason + evidence (terms URL + hash + date).

| status | meaning | who sets it |
|---|---|---|
| DISCOVERED | candidate from catalogs/scout; no claims | importer/scout |
| REVIEWING | terms + rate + auth + coverage being verified | maintainer |
| QUALIFIED | terms evidence archived; adapter fixture-backed | maintainer |
| ENABLED | operator explicitly enabled (opt-in / key supplied) | operator (local) |
| DISABLED | paused (quota, health, operator choice); reason kept | operator/maintainer |
| REJECTED | privacy / rights / safety block; reason kept | maintainer |

Machine view: `/api/plugins` (registry) + `/api/world/health`
(runtime: ONLINE / STANDBY / KEY REQUIRED / RIGHTS BLOCKED /
DEGRADED / STALE / OFFLINE / RATE LIMITED / AUTH REQUIRED).

Rules:

- DISCOVERED never renders. REVIEWING never renders beyond the
  registry page. Only QUALIFIED adapters ship fixtures.
- ENABLED requires explicit operator action; no auto-enable, no
  bundled keys, no shared credentials.
- REJECTED sources (private CCTV, RTSP/ONVIF scanning, credentials,
  facial/person/plate tracking, interception, paywall bypass,
  targeting) are never re-proposed without a safety review.
