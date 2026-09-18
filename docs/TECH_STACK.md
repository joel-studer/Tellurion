# Tech stack

Hybrid by measurement, not by fashion.

## Python — integration / research / data / plugins

All world-state contracts, the plugin SDK, discovery, the demo and
WORLD NOW servers, the change engine, and the synthetic replay live here
(`python/gods_eye/`). Rationale: fastest review loop, largest geospatial
and data ecosystem, zero build toolchain for contributors
(`pip install -e .` is enough).

## Rust — only where measured need exists

No Rust in the community preview. A native extension is justified only
for a proven hot path (e.g. high-throughput message parsing) with
benchmarks before/after. Until such a need is measured in the public
tree, Python + documented interfaces win.

## Web — community UI

Dependency-free HTML/CSS/JS for the demo console (`console/demo.html`):
no build step, no bundler, works from a `file://`-adjacent localhost
server. Map libraries are evaluated in
`docs/design/world-viz-decision.md`; the demo ships a zero-dependency
SVG world grid because it is offline-capable and reviewable.

## External OSS

The core needs only the Python standard library. Everything else is an
optional extra, imported lazily inside functions:

- `capture` extra: Playwright (screenshot and QA capture scripts).
- `dev` extra: pytest.
- Vendored: MapLibre GL JS 6.10.0 (BSD-3-Clause), Leaflet 1.9.4
  (BSD-2-Clause), Inter 5.3.0 (OFL-1.1), world-atlas 2.0.2 (ISC).

GPL/AGPL code is never linked. Full list: `legal/THIRD_PARTY_NOTICES.md`;
inventory: `legal/SBOM.spdx.json`.
