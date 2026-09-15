# Public layout (candidate-first, V17)

Canonical modules live under `gods_eye.future.*` (stable import paths,
see `docs/guides/public-api-stability.md`). The alias packages in this
directory are thin re-exports for the friendlier layout:

- `gods_eye.core` — canonical event/world surface
- `gods_eye.plugins` — SDK + discovery + validator + public API
- `gods_eye.demo` — canonical demo server module (`gods_eye/demo.py`) +
- synthetic dataset via `gods_eye.future.demo_dataset`
- `gods_eye.market` — venues, prediction markets, catalog
- `gods_eye.execution` — execution contracts + safety gate
- `gods_eye.portfolio` — portfolio contracts + optimizer

New code should import from the alias packages; canonical paths keep
working (STABLE_PREVIEW promise).
