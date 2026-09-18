# COMMUNITY PACKAGE MAP (V15 — design only, no migration yet)

> Target publishable structure vs current files. Nothing moves in V15.
> Classification per file: PUBLIC | PRIVATE | DATA_DEPENDENT | INTERNAL_ONLY.

## Target

```
gods_eye_core/        # pip-installable community edition
gods_eye_plugins/     # optional permissive-licence adapters (isolated)
gods_eye_demo/        # synthetic CC0 demo + replay driver
(private edge)        # separate repository, never published
```

## Map (current -> target)

### PUBLIC -> gods_eye_core

- `python/gods_eye/future/venues.py` — multi-venue canonical contracts
- `python/gods_eye/future/prediction_markets.py` — generic prediction-market contracts
- `python/gods_eye/future/venue_registry.py` — capability matrix
- `python/gods_eye/future/ccxt_meta.py` + `crypto_data.py` — ccxt metadata layer (offline)
- `python/gods_eye/future/nautilus_polymarket.py` — fixture mapping layer (docs + shapes)
- `python/gods_eye/future/market.py` — bars/quotes/trades/book contracts
- `python/gods_eye/future/providers.py` — provider adapter contract
- `python/gods_eye/future/execution.py` + `exec_engine.py` (fixture part) — generic execution contracts
- `python/gods_eye/future/portfolio.py` + `portfolio_optimizer.py` (fixture part) — generic portfolio contracts
- `python/gods_eye/future/plugins.py` + `public_api.py` — plugin SDK + public API
- `python/gods_eye/future/demo_dataset.py` — synthetic demo dataset
- `python/gods_eye/future/community.py` — community-mode boundary
- `python/gods_eye/future/session_calendar.py`, `market_catalog.py` — calendars + catalog
- `python/gods_eye/future/oss.py`, `forecast.py`, `tca.py` — registry + challenger/TCA contracts
- `python/gods_eye/cli.py`, `demo.py` — CLI + one-command demo
- `python/gods_eye/rights/registry.py`, `future/rights.py` — rights models
- `console/demo.html`, `console/landing.html` — public demo/landing (new; ops console stays)
- `docs/public/*` — README/CONTRIBUTING/readiness drafts

### PUBLIC (plugin lane) -> gods_eye_plugins

- `python/gods_eye/future/lean_engine.py`, `nautilus_engine.py`, `hft_validator.py`,
  `skfolio_engine.py`, `pypfopt_validator.py` — engine wrappers (boundary only,
  Apache-2.0/MIT/BSD in-process; Nautilus LGPL behind process boundary)
- `examples/plugins/example_sensor/` — template plugin

### PUBLIC (demo) -> gods_eye_demo

- `python/gods_eye/future/demo_dataset.py` + fixture JSON (when vendored)
- replay driver (thin; to be extracted from fixture engines in V16)

### PRIVATE (separate repository, never published)

Research, strategy and operational code lives in a separate private
repository that depends on this public core, never the other way round. It
is deliberately not named, listed or described here: the public tree ships
no private module names, file names or research identifiers. The boundary is
enforced by tests and scans (see `docs/OPEN_CORE_BOUNDARY.md`), not by this
document.

### DATA_DEPENDENT (gated per dataset, never assumed)

- LSE trial artefacts (redistribution banned)
- Yahoo-derived bars (transient/personal-use only)
- Paid-vendor data (contract-gated), hosted PIT datasets (keyed, procurement-gated)
- Per-venue crypto data (UNKNOWN until licensed)
- Public-domain defaults only: SEC EDGAR, FRED (with attribution)

### INTERNAL_ONLY (ops, not shipped)

- Operational run-books with hostnames, local runtime state (`state/`,
  `raw_store/`, `logs/`), and any frozen research artefacts beyond the
  public boundary document

## Migration rule

No destructive repo migration until DEVELOPER_PREVIEW criteria (see
`docs/public/OSS_LAUNCH_READINESS.md`) are met. Migration itself is a
separate reviewed PR with a release-manifest update and a green full suite.
