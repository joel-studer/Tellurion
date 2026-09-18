# CONTRIBUTOR TASK: add a demo sensor (V16)

> First-sensor walkthrough for a new contributor. Timebox: 30 minutes.
> You need only this repository and its docs. No keys, no
> network beyond localhost.

## Goal

Ship one working demo sensor plugin: scaffold → declare rights →
implement `poll()` over a fixture → offline test green → register via
the public API.

## Steps

### 1. Check the environment (5 min)

```bash
tellurion doctor
```

Expect `verdict: PASS`. If a check reports WARN/FAIL, follow its `fix`
hint and re-run. Do not continue on FAIL.

### 2. Scaffold from the template (5 min)

```bash
tellurion new-plugin --kind sensor --name my-sensor --dir my_sensor
```

This copies `manifest.json`, `plugin.py`, `fixture.json`, and the
offline test into `my_sensor/`. Read all four files before editing.

### 3. Declare identity + rights (5 min)

Edit `my_sensor/manifest.json`:

- `name`: your sensor name (keep it lowercase with dashes).
- `license`: your licence identifier (e.g. `MIT`).
- `data_rights`: honest rights basis for your fixture (e.g.
  `public-domain (synthetic CC0 fixture)`). UNKNOWN rights stay
  discoverable but never production-qualified.
- `capabilities`: what the plugin does (e.g. `["poll"]`). Capability
  tokens that imply ranking/allocation hooks are refused at declaration.
- `provenance`, `health`, `schema` (`plugin-v1`): fill in truthfully.

Validate any time with:

```bash
tellurion plugins validate ./my_sensor
```

FAIL rows name the file, the rule, and the fix. The same check backs
`examples/contributor_tasks/ai_sensor_task.md` (machine-verifiable).

### 4. Implement `poll()` + test offline (10 min)

Edit `my_sensor/plugin.py`: implement `poll()` over your
`fixture.json` (synthetic or rights-cleared data only — no scraped
rows, no credentials, no network calls). Then run the shipped test:

```bash
python -m pytest my_sensor/test_example_sensor.py -q
```

Green means: declaration valid, `poll()` returns fixture items with
provenance + rights attached, no secrets, no outbound calls.

### 5. Register + list (5 min)

```python
from gods_eye.future import public_api as api
import json
manifest = json.load(open("my_sensor/manifest.json"))
print(api.register_sensor(manifest))
print(api.list_registered())
```

```bash
tellurion plugins --dir my_sensor
```

Your sensor appears with its licence, rights, health, and the
production-qualified flag (GREEN only with licence + schema +
non-UNKNOWN rights).

## Rules (fail closed)

- Stdlib only at module scope; lazy-import heavies inside functions.
- UNKNOWN stays UNKNOWN (never guess timestamps, rights, fees, depth).
- Import only modules that ship in the `gods_eye` package — community
  checks fail on anything else.
- No secrets in code, fixtures, or logs. Localhost only.

## Done when

- [ ] `tellurion doctor` PASS (paste the verdict).
- [ ] Offline test green (paste the pytest line).
- [ ] `tellurion plugins --dir my_sensor` lists your sensor as expected.
- [ ] You can state the trust model in one paragraph (explicit install,
      explicit discovery, rights-first). See
      `docs/guides/plugin-trust-model.md`.
