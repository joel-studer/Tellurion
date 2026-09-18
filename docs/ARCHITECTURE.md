# Architecture

```
PUBLIC / LICENSED SOURCES
        |
     PLUGINS  (explicit install, explicit discovery, declared rights)
        |
 CANONICAL EVENTS  (one shape per family: id, ts, geo, entities)
        |
 EVIDENCE / ENTITY / WORLD STATE
   - evidence trail: WHAT / WHO says so / WHEN visible /
     RAW vs NORMALIZED / OBSERVATION vs INFERENCE / confidence / rights
   - entity neighbourhoods: A --relation--> B + supporting evidence +
     effective time + uncertainty (bounded, never hairballs)
        |
   TIME MACHINE  (HISTORICAL BELIEF vs CURRENT REPLAY, as-of any date)
        |
   CHANGE DETECTION  (what is different from the last observation:
     EONET lifecycle, GDACS transitions, USGS seismic episodes)
        |
   UI / APIs  (/api/world/now, /api/world/changes, /api/demo, consoles)
```

Cross-cutting: source health + blind spots (coverage honesty),
rights-first gating (UNKNOWN never qualifies), localhost-only serving.

What is NOT here: any trading, execution, venue, portfolio or market
surface, and credentials. `tellurion doctor` and `release-check` both fail
if such a module reappears (`boundary.trading_surface_hits`). Downstream
layers plug in through the plugin SDK (see `docs/OPEN_CORE_BOUNDARY.md`).
