# Open-core boundary

Tellurion is the platform. This repository must run, test, and demo on its
own, and it must never need code that lives anywhere else.

## Dependency direction

```
downstream extensions  --depend on-->     gods-eye (this repository)
gods-eye               --never imports--> anything downstream
```

| Guarantee | Enforced by |
|---|---|
| Every `gods_eye` import (any scope) resolves inside `python/gods_eye` | `boundary.unresolved_internal_imports`, `tests/test_boundary.py`, `tellurion release-check` |
| The core imports and runs with only the standard library on `sys.path` | `tests/test_boundary.py::test_core_runs_with_standard_library_only`, `scripts/verify_install.py` |
| Community imports load nothing from outside the package | `community.community_check`, `tellurion doctor` |
| Plugins import only shipped modules | `tellurion plugins validate` |
| No credentials, machine paths, runtime state, or databases in the tree | `boundary` scans in `tellurion release-check` |
| Every media, fixture, and vendored file has a declared, allowed licence | `legal/ASSET_RIGHTS.json`, `tellurion release-check` |

Downstream CI can add its own term list without publishing it:
`GODS_EYE_DENYLIST=/path/to/terms.txt tellurion release-check`. Matches fail
the check; the terms are never printed.

## What belongs here

Canonical event and layer models, plugin SDK, sensor plugins (synthetic or
rights-cleared data), the Ultra world view, evidence drawer, entity graph,
time machine, source health and blind spots, change detection, gallery,
sensor scout, API catalog importer, replay and demo, CLI, doctor,
release-check, and docs.

## What never belongs here

Any trading surface at all: strategies, signals, order or execution
logic, venue and market-data adapters, prediction-market mechanics,
portfolio or capital allocation, backtest engines, transaction-cost
models. Also: event-to-market mappings, source-ranking edge, settlement
logic, research outcomes, evaluation holdouts, credentials, wallets,
machine-specific paths, runtime state, and any data without a
redistribution right.

This is enforced, not just documented: `boundary.trading_surface_hits`
fails `tellurion doctor` and `release-check` if any of those module names
reappears under `python/gods_eye/`.

## Extension points

- **Plugins** (`gods_eye.plugins`, `gods_eye.future.public_api`): sensors,
  entity resolvers, visualizations.
- **Isolation profiles** (`gods_eye.future.isolation.configure`): a
  downstream project declares paths that future code may never write or
  read. The core ships no profile.

## Licences

MIT / Apache-2.0 / BSD code only in-process. GPL/AGPL code is never
linked. Tellurion itself is MIT (see `LICENSE`).
