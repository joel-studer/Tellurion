# Contributing to Tellurion

Thanks for your interest. This is a local-first, rights-first project:
small honest plugins beat big opaque ones.

## 5-step first contribution (30 minutes)

1. `tellurion doctor` — expect `verdict: PASS`.
2. `tellurion new-plugin --kind sensor --name my-sensor --dir my_sensor`
3. Edit `my_sensor/manifest.json` (licence + data rights + schema).
4. Implement `poll()` over `fixture.json`, then
   `python -m pytest my_sensor/test_example_sensor.py -q` until green.
5. `tellurion plugins validate ./my_sensor` — fix every FAIL row, then
   `tellurion plugins --dir my_sensor`.

Full task: `examples/contributor_tasks/add_demo_sensor.md`.
AI-agent variant: `examples/contributor_tasks/ai_sensor_task.md`.

## Rules (fail closed)

- Stdlib only at plugin module scope; lazy-import heavies in functions.
- Synthetic or rights-cleared fixtures only. UNKNOWN stays UNKNOWN.
- Import only modules that ship in `gods_eye`; `tellurion plugins validate`
  refuses non-core imports, network calls, and credential tokens.
- No secrets in code, fixtures, or logs. Localhost only.
- One plugin per PR; include licence, rights, provenance, tests,
  network/secrets needs, and a screenshot if there is UI.

## Working on the core

```bash
pip install -e ".[dev]"
python -m pytest tests plugins examples -q
tellurion release-check            # read-only; never publishes
python scripts/verify_install.py
```

Boundary rules for core changes (enforced by `tests/test_boundary.py`):
every `gods_eye` import must resolve inside `python/gods_eye`; the core
must import and run with only the standard library; new media or fixture
files need an entry in `legal/ASSET_RIGHTS.json`
(`python scripts/update_asset_rights.py`).

## Signing your work (DCO)

Tellurion uses the [Developer Certificate of Origin 1.1](https://developercertificate.org/):
by signing off, you state that you wrote the contribution, or have the right
to submit it under the project's licence. There is no CLA to sign and no
paperwork — one flag does it:

```bash
git commit -s -m "feat(sensor): add my-sensor plugin"
```

That appends a line to your commit message:

```
Signed-off-by: Your Name <your.email@example.com>
```

Contributions are accepted under the MIT License (`LICENSE`). You keep the
copyright to what you write.

## What happens to your PR

Maintainer checks: manifest valid, offline test green, rights honest,
no private surface, docs updated. Schema changes need a `plugin-v2`
proposal; breaking changes get one release of deprecation warning.

See `docs/GOVERNANCE.md` (lightweight) and
`docs/guides/plugin-trust-model.md`.
