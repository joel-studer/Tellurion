# Open-core boundary

GOD'S EYE is the platform. This repository must run, test, and demo on its
own, and it must never need code that lives anywhere else.

## Dependency direction

```
downstream extensions  --depend on-->     gods-eye (this repository)
gods-eye               --never imports--> anything downstream
```

| Guarantee | Enforced by |
|---|---|
| Every `gods_eye` import (any scope) resolves inside `python/gods_eye` | `boundary.unresolved_internal_imports`, `tests/test_boundary.py`, `godseye release-check` |
| The core imports and runs with only the standard library on `sys.path` | `tests/test_boundary.py::test_core_runs_with_standard_library_only`, `scripts/verify_install.py` |
| Community imports load nothing from outside the package | `community.community_check`, `godseye doctor` |
| Plugins import only shipped modules | `godseye plugins validate` |
| No credentials, machine paths, runtime state, or databases in the tree | `boundary` scans in `godseye release-check` |
| Every media, fixture, and vendored file has a declared, allowed licence | `legal/ASSET_RIGHTS.json`, `godseye release-check` |

Downstream CI can add its own term list without publishing it:
`GODS_EYE_DENYLIST=/path/to/terms.txt godseye release-check`. Matches fail
the check; the terms are never printed.

## What belongs here

Canonical event and layer models, plugin SDK, sensor plugins (synthetic or
rights-cleared data), the Ultra world view, evidence drawer, entity graph,
time machine, source health and blind spots, gallery, sensor scout, API
catalog importer, replay and demo, generic market / execution / portfolio
*contracts* over fixtures, CLI, doctor, release-check, and docs.

## What never belongs here

Trading strategies or signals, event-to-market mappings, timing or
source-ranking logic, settlement logic, capital allocation policy,
execution edge, research outcomes, evaluation holdouts, credentials,
wallets, machine-specific paths, runtime state, and any data without a
redistribution right.

## Extension points

- **Plugins** (`gods_eye.plugins`, `gods_eye.future.public_api`): sensors,
  market data, entity resolvers, visualizations, venues.
- **Extension slots** (`gods_eye.future.extensions`): capabilities the core
  defines but does not implement, for example `portfolio.eligibility`.
  An unfilled slot raises `ExtensionUnavailable` with a fix hint.
- **Isolation profiles** (`gods_eye.future.isolation.configure`): a
  downstream project declares paths that future code may never write or
  read. The core ships no profile.

## Licences

Apache-2.0 / MIT / BSD code only in-process. LGPL engines (NautilusTrader)
only behind a separate process. GPL/AGPL code is never linked.
