# USER KEYS (local-only, never bundled)

Some legs need a per-user key (FIRMS MAP_KEY, OpenSky OAuth, AISStream
key, GTFS-RT agency key, high-volume AirNow/OpenAQ tiers).

Rules:

- The UI shows `SOURCE AVAILABLE — KEY REQUIRED` and never prompts
  for a key to be sent anywhere except the operator's own localhost
  config / env.
- Keys live in local env (`TELLURION_<SOURCE>_KEY`) or the operator's
  server proxy. They are never committed, never logged, never embedded
  in URLs shared via `?` state (share URLs carry view/layers/region/
  selection/time only).
- Browser-direct streaming (AISStream WS) is forbidden: key holders
  run their own server proxy; the console only talks to localhost.
- Quota handling: cache first (per-source TTL), backoff + jitter,
  circuit breaker, `RATE LIMITED` health state. See
  `python/gods_eye/future/world_live.py::SourceCache`.
