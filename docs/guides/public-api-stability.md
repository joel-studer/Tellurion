# PUBLIC API STABILITY (V16 — preview classifications)

> Minimized surface. Anything not listed here is INTERNAL and may change
> without notice. Versioned: plugin schema, public API, demo dataset,
> market contracts.

## STABLE_PREVIEW (will not break without a major preview bump)

- `gods_eye.future.public_api`: `register_sensor`,
  `register_market_data_provider`, `register_entity_resolver`,
  `register_visualization`, `register_model_challenger`, `register_venue`,
  `list_registered`, `api_surface` (schema `public-api-v1`).
- `gods_eye.future.plugins`: `declare`, `production_qualified`,
  `qualify_or_refuse`, `rights_declared`, `KINDS`, `REQUIRED_KEYS`;
  plugin base classes `SensorPlugin`, `MarketDataPlugin`,
  `EntityResolverPlugin`, `VisualizationPlugin`, `ModelChallengerPlugin`,
  `VenuePlugin`, `PredictionMarketPlugin` (schema `plugin-v1`).
- `gods_eye.future.demo_dataset`: `demo_dataset`, `timeline`,
  `validate_no_holdout_refs`, `DATASET_ID` (`community-demo-v1`),
  CC0 provenance constants.
- CLI: `godseye doctor|demo|serve|plugins|sources|new-plugin` flags as in
  `--help` (JSON keys of `doctor` may gain new checks, never lose `verdict`,
  `ok`, `checks[].name/status/detail/fix`).
- Demo HTTP: `/api/demo`, `/api/health` shapes (additive only).

## EXPERIMENTAL (may change; labelled in code/docs)

- `gods_eye.future.discovery` (`explicit-dirs` + `entry-points` mechanisms,
  group `gods_eye.plugins`).
- `gods_eye.future.venue_registry` row fields (additive), `ccxt_meta`
  normalization output (additive), `nautilus_polymarket` shapes.
- `gods_eye.future.venues` / `prediction_markets` dataclass fields
  (additive; `UNKNOWN` defaults guaranteed).
- `gods_eye.future.optional_deps` catalog + statuses.
- `gods_eye.future.extensions` slot names + contracts (additive);
  `gods_eye.future.boundary` scan helpers; `gods_eye.future.isolation`
  profile API (`configure`, `reset`).

## INTERNAL (no compatibility promise)

- Everything else under `gods_eye.*` (fixture engines, validators,
  catalog internals, `community.community_check` return extras,
  `demo.run_demo` signature beyond `(port, open_browser, strict_port)`).

## Compatibility policy

- Preview series `0.x`: STABLE_PREVIEW breaks only with a minor bump +
  CHANGELOG-equivalent note in `docs/` + one-release deprecation
  warning where feasible.
- `UNKNOWN`-valued fields never become required; new enum members are
  additive; `declare()` required keys only grow with a `plugin-v2` schema.
- Demo dataset `community-demo-v1` is frozen; a new dataset gets a new id.
- Pre-release note (V17, nothing published yet): `community-demo-v1`
  gained a second corroborating synthetic source
  (`synthetic-timetable-feed`, additive `source_health` row) before any
  public tag. Content freezes at the first public tag; after that, any
  content change ships as a new dataset id.
