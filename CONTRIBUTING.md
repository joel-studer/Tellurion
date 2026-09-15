# Contributing to GOD'S EYE

Thanks for your interest. This is a local-first, rights-first project:
small honest plugins beat big opaque ones.

## 5-step first contribution (30 minutes)

1. `godseye doctor` — expect `verdict: PASS`.
2. `godseye new-plugin --kind sensor --name my-sensor --dir my_sensor`
3. Edit `my_sensor/manifest.json` (licence + data rights + schema).
4. Implement `poll()` over `fixture.json`, then
   `python -m pytest my_sensor/test_example_sensor.py -q` until green.
5. `godseye plugins validate ./my_sensor` — fix every FAIL row, then
   `godseye plugins --dir my_sensor`.

Full task: `examples/contributor_tasks/add_demo_sensor.md`.
AI-agent variant: `examples/contributor_tasks/ai_sensor_task.md`.

## Rules (fail closed)

- Stdlib only at plugin module scope; lazy-import heavies in functions.
- Synthetic or rights-cleared fixtures only. UNKNOWN stays UNKNOWN.
- Import only modules that ship in `gods_eye`; `godseye plugins validate`
  refuses non-core imports, network calls, and credential tokens.
- No secrets in code, fixtures, or logs. Localhost only.
- One plugin per PR; include licence, rights, provenance, tests,
  network/secrets needs, and a screenshot if there is UI.

## Working on the core

```bash
pip install -e ".[dev]"
python -m pytest tests plugins examples -q
godseye release-check            # read-only; never publishes
python scripts/verify_install.py
```

Boundary rules for core changes (enforced by `tests/test_boundary.py`):
every `gods_eye` import must resolve inside `python/gods_eye`; the core
must import and run with only the standard library; new media or fixture
files need an entry in `legal/ASSET_RIGHTS.json`
(`python scripts/update_asset_rights.py`).

## What happens to your PR

Maintainer checks: manifest valid, offline test green, rights honest,
no private surface, docs updated. Schema changes need a `plugin-v2`
proposal; breaking changes get one release of deprecation warning.

See `docs/GOVERNANCE.md` (lightweight) and
`docs/guides/plugin-trust-model.md`.
