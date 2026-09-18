# Tellurion (DRAFT — not yet published)

> An open-source world-intelligence platform for lawful public/licensed data.

<!-- Screenshot/GIF placeholders (to capture from console/demo.html):
  ![demo world + event pulse](../screenshots/tellurion-hero.png)
  ![evidence drawer](../screenshots/evidence-drawer.png)
  ![time machine](../screenshots/tellurion-hero.gif)
-->

## What it is

Tellurion turns lawful public sources into canonical world events with
provenance on every record: sensors poll, fusion links, the evidence graph
traces fact-vs-inference, the time machine replays belief, entities resolve
with method labels, and generic market/venue contracts describe context.
The community edition runs fully offline on synthetic demo data — no keys,
no live execution, no telemetry.

Possible capabilities: world events, sensors, evidence graph, time machine,
entity relationships, source health, plugin adapters, replay/demo.

No proprietary alpha is included. No market-beating claims are made.

## 5-minute quickstart

```bash
pip install gods-eye-core
tellurion doctor     # environment + boundary checks (no keys)
tellurion demo       # localhost-only demo -> http://127.0.0.1:8765/
tellurion plugins    # plugin SDK kinds + registry
tellurion sources    # source/rights summary
```

Or without install:

```bash
python -m gods_eye.demo --port 8765
```

## Architecture

```
sensors (plugins) -> canonical events -> fusion -> evidence graph
  -> entities -> time machine -> market/venue context (generic contracts)
  -> demo/replay console (localhost)
```

- `gods_eye_core/` — events, graph, evidence, time machine, generic
  market/execution/portfolio contracts, venue matrix, capability registry.
- `gods_eye_plugins/` — optional adapters (ccxt metadata, calendars,
  engine boundaries) behind isolated interfaces.
- `gods_eye_demo/` — synthetic CC0 dataset + replay driver.
- a separate private repository — never published; it depends on this
  public core and nothing here depends on it.

See `docs/public/COMMUNITY_PACKAGE_MAP.md` and `docs/OPEN_CORE_BOUNDARY.md`.

## Plugin example

```python
from gods_eye.future import public_api as api

declaration = dict(
    name="example-sensor", version="0.1.0", kind="Sensor",
    license="MIT", data_rights="public-domain (synthetic CC0)",
    capabilities=["poll"], network="none", secrets="none",
    provenance="examples/plugins/example_sensor", health="ok",
    schema="plugin-v1",
)
print(api.register_sensor(declaration))
```

Full skeleton: `examples/plugins/example_sensor/`.

## Lawful-use boundary

Public/licensed/owned/authorized sources only. Software licences and data
rights are separate; UNKNOWN rights never qualify for production
(`production_qualified()` refuses). See `docs/public/RIGHTS_POLICY.md` and
`docs/public/SECURITY_DEFAULTS.md`.

## Open-core explanation

OPEN THE INFRASTRUCTURE. KEEP THE EDGE PRIVATE. The community edition is
useful without the proprietary alpha core: world map, evidence, time
machine, venue/market contracts, replay, plugin SDK. Proprietary
research, strategy and operational code, secrets and evaluation data stay
private (see `docs/OPEN_CORE_BOUNDARY.md`).

## Roadmap

- DEVELOPER_PREVIEW: one-command demo, plugin template, README/CONTRIBUTING,
  license decision, readiness scores honest.
- PUBLIC_BETA: cross-platform CI, screenshots/video hook, external plugin.
- 1.0: stable public API, versioned schemas, published SBOM.

See `docs/public/OSS_LAUNCH_READINESS.md`.

## Contributing

See `docs/public/CONTRIBUTING_DRAFT.md`. New contributors can add a plugin
without understanding private architecture. `tellurion doctor` must stay green.
