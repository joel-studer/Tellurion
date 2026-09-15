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
   UI / APIs  (/api/demo, /api/health, demo console)
        |
 generic optional: MARKET CONTEXT / EXECUTION REPLAY / PORTFOLIO
   (venue contracts over synthetic replay data; no live execution)
```

Cross-cutting: source health + blind spots (coverage honesty),
rights-first gating (UNKNOWN never qualifies), localhost-only demo,
`ALLOW_LIVE=false` enforced in code.

What is NOT here: trading strategies, ranking or allocation policy, and
credentials. Downstream layers plug in through the plugin SDK and
extension slots (see `docs/OPEN_CORE_BOUNDARY.md`).
