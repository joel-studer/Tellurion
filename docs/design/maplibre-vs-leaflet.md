# MAPLIBRE VS LEAFLET (V18.5 — measured 2026-09-15, decision: KEEP_LEAFLET)

> Non-destructive prototype: `console/ultra-gl.html` (same
> deterministic `/api/ultra` dataset, offline style, no tiles) vs the
> Leaflet Ultra. Same box, same headless Chromium 1600×900,
> in-page FPS overlays. Nothing replaced; prototype ships nowhere
> (not in the preview manifest).

## Numbers (observed, not modeled)

| | Leaflet (vendored 1.9.x) | MapLibre GL (vendored 4.7.1) |
|---|---|---|
| Bundle (vendored) | 147,552 + 14,806 B (~162 KB) | 803,086 + 65,534 B (~868 KB, 5.4×) |
| Licence | BSD-2-Clause (file ships) | BSD-3-Clause (file ships) |
| 1k scene FPS | 60 | 60 |
| Dense 1k FPS | 60 | 60 |
| Offline | yes (graticule, zero tiles) | yes (empty style, zero tiles) |
| Clustering | hand-rolled grid (<9 zoom) | built-in GeoJSON cluster |
| Heat | n/a (opacity fills) | built-in heatmap layer |
| Trails / glyphs / selection / drawer | shipped, tested | NOT built in prototype |
| Time slider | tick reload | tick reload |

## Qualitative

- MapLibre GPU circles + heat glow look modern with zero effort;
  cluster styling needed work (dark dots in prototype).
- Leaflet Ultra carries the whole product (evidence, relations,
  palette, belief modes); re-platforming means rebuilding all of it
  for zero FPS gain at our scales.

## Decision: KEEP_LEAFLET

Migrate only if a measured gate fails: <50 fps at 5k, or a feature
we cannot build on canvas (true 3D, vector tiles). Re-run
`scripts/compare_renderers.py` + `scripts/bench_ultra_browser.py`
before reopening. HYBRID (MapLibre heat/globe view alongside)
remains the likely future, not a rewrite.

## Reproduce

`python scripts/compare_renderers.py` (bundle + FPS + matching
screenshots into `preview-assets/frames-thirdeye/render-*.png`).
