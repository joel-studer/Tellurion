# WORLD SURFACE TECHNOLOGY DECISION V2 (V18 — evidence, 2026-09-15)

> Target is no longer one synthetic point: moving aircraft + vessels,
> satellite footprints, event pulses, heat/raster overlays, road
> segments, polygons, camera points, 1k–10k objects, time playback,
> selection, clustering. Zero keys, offline base demo, no build step.

## Candidates (measured upstream figures, Sept 2026)

| | Leaflet | MapLibre GL JS v6 | CesiumJS |
|---|---|---|---|
| Licence | BSD-2-Clause | BSD-3-Clause | Apache-2.0 |
| Bundle | ~42 kB min (~15 kB gzip) | ~972 kB min (~251 kB gzip) | multi-MB |
| Rendering | DOM/SVG markers (+ canvas plugins) | WebGL vector, 60fps, globe + 3D | WebGL 3D, 3D-Tiles king |
| 1k objects | OK with clustering | smooth | smooth |
| 5–10k objects | DOM choke without canvas work | usable (GeoJSON + clustering) | smooth |
| Offline/keyless | yes | yes (empty style + local GeoJSON, no tile server) | yes but heavy |
| Contributor curve | trivial | moderate (style spec) | steep |
| Key required | no | no (self-hosted; tiles optional) | no (ion optional) |

FOSS4G-2025 benchmark direction: CesiumJS wins 3D-Tiles point
clouds; MapLibre wins lightweight vector FCP/stability. Our scene is
lightweight vector → MapLibre's strength.

## Decision

- **Default: MapLibre GL JS (pinned build, vendored or pinned CDN
  with local fallback), empty offline style + local GeoJSON
  sources.** No tile server, no key, works from `file://`-adjacent
  localhost demo. Clustering via GeoJSON `cluster` sources; heat via
  heatmap layers; footprints via fill layers; trails via line layers.
- **Fallback: Leaflet** (ops pages keep it; Ultra ships a
  `?renderer=leaflet` path reusing the same `/api/ultra` payload with
  canvas markers + clustering). Keeps low-power machines in.
- **Rejected as default: CesiumJS.** True-3D/orbit strengths do not
  justify multi-MB + steep curve for a 2D ops surface. Documented
  future option for an orbit/terrain view only.

## Evidence gates (binding)

- `scripts/bench_ultra_density.py` asserts payload build time and
  counts for 1k/5k/10k scenes (data-side; renderer FPS measured in
  the browser console overlay and recorded in DEMO_PERFORMANCE V18
  addendum — never fabricated).
- Public target: smooth at 1k, usable at 5k, degraded-but-functional
  at 10k+. If MapLibre misses on the maintainers' hardware, the
  Leaflet-canvas fallback becomes default and this file is updated —
  the decision follows evidence, not preference.
