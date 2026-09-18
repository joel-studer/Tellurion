# CONTRIBUTING (DRAFT — not yet published)

You can add a simple plugin without understanding private architecture.
The private alpha core is never required and never imported.

## Environment

```bash
python --version   # >=3.13
pip install -e .[market]   # optional: duckdb/ccxt/calendars for breadth
python -m pytest -q        # full suite must stay green
tellurion doctor             # boundary checks (no keys)
```

Base install stays lightweight (no Rust toolchain, no Torch, no
LEAN/Nautilus/skfolio). Nothing in `python/gods_eye/*` imports heavy or
private modules at module scope (tested).

## Plugin skeleton

Copy `examples/plugins/example_sensor/`:

```
examples/plugins/example_sensor/
  manifest.json   # declare() payload (license + rights + schema required)
  plugin.py       # minimal SensorPlugin subclass (no secrets, no network)
  fixture.json    # redistributable fixture (synthetic or rights-cleared)
  test_example_sensor.py  # runs offline, no keys
```

Register:

```python
from gods_eye.future import public_api as api
api.register_sensor(manifest_dict)
```

Venue / prediction-market plugins subclass `VenuePlugin` /
`PredictionMarketPlugin` and implement `describe()` with venue id, asset
classes, capabilities, required secrets, rights, rate limits, health,
schema version, licence. They must NOT expose alpha signal APIs, private
research hooks, or private strategy ranking (`declare()` refuses).

## Style

- Stdlib-only at module scope in plugins; lazy-import heavy libs inside
  functions behind availability probes.
- UNKNOWN stays UNKNOWN (never guess timestamps, rights, fees, depth).
- Timezone-aware datetimes only; naive datetimes refused.
- Amounts: integers in minor units where applicable.

## Schema compatibility

Declare `schema` (e.g. `plugin-v1`). Breaking schema changes bump the
version and are documented in the plugin's manifest + test.

## Rights declaration

Every plugin declares `data_rights` (non-UNKNOWN required for production
use). A plugin with UNKNOWN rights is discoverable but
`production_qualified()` returns False and `qualify_or_refuse()` raises.
Expose licence, data rights, network, secrets, health, capabilities in
`describe()` — the UI surfaces them.

## Provenance requirements

Every record carries source + raw hash + dataset version. No fetched row
enters a snapshot without rights + raw hash. Synthetic fixtures are
labelled CC0 with generator note.

## Security rules

- No secrets in code, fixtures, or logs. `exec_safety.assert_no_credentials`
  refuses credential keys in execution paths.
- No live execution (`ALLOW_LIVE=false`; `LiveRefused` on attempt).
- Localhost-only servers (`127.0.0.1`, never `0.0.0.0` in community code).
- No telemetry. Public/licensed/owned/authorized sources only.
- Never import modules from outside the shipped package.
  `community_check()` fails on any import that resolves outside it.
