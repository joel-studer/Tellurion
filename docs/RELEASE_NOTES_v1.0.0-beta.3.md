# Tellurion v1.0.0-beta.3

Open-source, local-first world intelligence from public data.

This is a dependency-hygiene release. The product is unchanged from
v1.0.0-beta.2 (same WORLD NOW, CHANGE_DETECTED, Sentinel-2 evidence,
LIVE EARTH, Replay, AI APIs, rights model, and known limitations —
see `docs/RELEASE_NOTES_v1.0.0-beta.2.md`).

## What changed since beta.2

- `capture` extra: `playwright>=1.50` → `>=1.63.0` (screenshot/bench
  tooling only; verified with Chromium 1243 / HeadlessChrome 153:
  WORLD NOW and Replay render with no console errors).
- `build-system`: `setuptools>=61` → `>=84.0.0` (verified: wheel +
  sdist build, clean install, editable install, PEP 639
  `license = "MIT"` + `license-files` untouched).
- CI fix: the standalone install probe no longer imports the removed
  `gods_eye.market / .execution / .portfolio` alias packages
  (they left with the trading surface; the probe was the only
  remaining reference and failed every branch).
- Boundary rule anchored in the public suite: the dependency direction
  is enforced by test (private may import public, never the reverse).

No product behavior, sources, rights, or UI changed.

## CI note (environmental, not a product issue)

The PR-only `dependency-review` job fails with "Dependency review is
not supported on this repository" because the GitHub Dependency graph
is disabled in repo settings. Core CI (ubuntu/windows × 3.13/3.14:
tests, doctor, demo smoke, install verification, asset-rights check,
release-check) is fully green. Do not read the dependency-review
failure as a vulnerability finding.

## Install

```bash
pip install -e .
tellurion doctor       # environment + boundary checks (no keys, no network)
tellurion ultra --hero # the globe, 127.0.0.1 only
```

## What Tellurion does not claim

No global high-resolution real-time video, no complete global
coverage, no person tracking, no military targeting, no financial
prediction, no proprietary trading capability.
