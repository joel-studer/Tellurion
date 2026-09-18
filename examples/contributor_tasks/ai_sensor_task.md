# AI-AGENT CONTRIBUTOR TASK: build a sensor plugin from public docs only (V17)

> For Claude Code / Codex / OpenCode / Cursor / human developers.
> Context budget: this file + linked public docs. No keys,
> no network beyond localhost and the package index.

## Mission

Ship one working sensor plugin (`weather-sensor-demo`) using ONLY:

- `README.md`, `CONTRIBUTING.md`
- `docs/guides/plugin-trust-model.md`
- `examples/plugins/example_sensor/` (manifest, plugin, fixture, test)
- `tellurion --help` / `tellurion plugins validate --help` equivalents

## Steps

1. `tellurion doctor` → PASS. 2. `tellurion new-plugin --kind sensor
   --name weather-sensor-demo --dir weather_sensor_demo`.
3. Write `fixture.json`: 3+ synthetic weather observations (no real
   persons, no scraped rows).
4. Implement `poll()` returning `{items, provenance, rights}`.
5. `python -m pytest weather_sensor_demo/test_example_sensor.py -q` → green.
   NOTE: the scaffolded `test_poll_offline` asserts `len(items) == 2`
   (the template fixture size). With 3+ fixture items, update that
   assertion to `>= 3` (or your exact count) — the test is yours now.
6. `tellurion plugins validate ./weather_sensor_demo` → no FAIL rows.
7. `tellurion plugins --dir weather_sensor_demo` → listed, qualified.

## Acceptance (machine-verifiable)

```bash
tellurion doctor | grep -q '"failed": 0'   # WARN rows (e.g. a busy port) are fine
python -m pytest weather_sensor_demo/test_example_sensor.py -q
tellurion plugins validate ./weather_sensor_demo | grep -q '"verdict": "PASS"'
python scripts/check_ai_task.py ./weather_sensor_demo
```

PowerShell: run each command and read the JSON (`failed: 0`, `verdict: PASS`),
or pipe into `Select-String '"failed": 0'`.

`scripts/check_ai_task.py` asserts: manifest schema `plugin-v1`,
licence + non-UNKNOWN rights, `poll()` returns fixture items with
provenance/rights, no non-core imports, no network tokens, no
credential tokens, offline test present.

## Report back

Time/steps taken, every blocker + which doc fixed it, missing doc
section (file + heading), and the validate JSON. Findings improve the
docs, never the agent's score.
