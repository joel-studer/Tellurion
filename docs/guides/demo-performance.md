# COMMUNITY DEMO PERFORMANCE (V17 — measured, not claimed)

> Measured 2026-09-14 on a Windows laptop (Python 3.13.5, localhost
> only, synthetic data). Rerun anytime:
> `python scripts/bench_demo_perf.py` (dev-side probe; the community
> tree carries no benchmark dependency).

| Probe | Value |
|---|---|
| `import gods_eye.demo` (cold interpreter) | 0.133 s |
| `tellurion doctor` (11 checks) | 0.568 s |
| `GET /api/health` (285 B) | 0.044 s |
| `GET /api/demo` (4,636 B) | 0.002 s |
| Evidence payload build + JSON encode, 100 rows | 0.0001 s (~1.0M rows/s) |
| Evidence payload build + JSON encode, 1,000 rows | 0.0008 s (~1.2M rows/s) |
| Evidence payload build + JSON encode, 5,000 rows | 0.0041 s (~1.2M rows/s) |
| First useful UI render (Chromium, `?demo=hero`, network-idle) | 0.961 s |
| Probe process peak RSS | 41.9 MB |

## Honest scope

- The scale rows are synthetic evidence dicts shaped like
  `demo_dataset` entries, measured through payload-build + JSON
  encode only. They prove the serving path is not the bottleneck;
  they are **not** a claim about DOM rendering of 5,000 cards (the
  shipped demo renders its 2-row synthetic dataset).
- UI render time is one local Chromium run, not a percentile.
- No network is involved anywhere in the demo path (localhost only).
- No scalability claim beyond these rows is made.

---

# ULTRA PERFORMANCE ADDENDUM (V18 — measured 2026-09-15)

> Same machine (Windows, Python 3.13.5, headless Chromium 1600×900,
> localhost only). Data-side via `python scripts/bench_ultra_density.py`;
> browser FPS via `python scripts/measure_ultra_fps.py` (in-page
> requestAnimationFrame overlay, 2 s window — observed, not modeled).

| Scene | Payload build | Browser FPS (observed) | Verdict |
|---|---|---|---|
| normal (~83 objects) | < 0.01 s | 60 fps | smooth (target met) |
| dense 1k (826 objects) | < 0.01 s | 60 fps | smooth (target met) |
| 5k (4,150 objects) | 0.02 s | not yet measured | usable (data-side only) |
| 10k (8,150 objects) | 0.05 s | not yet measured | usable-degraded (data-side only) |
| 25k (20,150 objects) | 0.10 s | not yet measured | degraded (data-side only) |

Notes:

- Serving path is never the bottleneck (20k objects serialize in
  0.10 s). Rendering risk sits in the DOM: dense mode therefore uses
  circle markers + grid clustering below zoom 9, glyphs only under
  ~150 markers.
- 5k/10k/25k browser FPS is explicitly NOT claimed until the overlay
  records it; the renderer decision stays evidence-led (see
  `WORLD_RENDERER_DECISION_V2.md`). If Leaflet-canvas misses at 5k on
  reference hardware, the MapLibre prototype becomes default.

---

# V18.5 BROWSER BENCH (measured 2026-09-15 — real clicks, real FPS)

> `python scripts/bench_ultra_browser.py` (headless Chromium,
> 1600×900, localhost). Load scenes via `/ultra?scene=dense|load5k|
> load10k`. Selection = feed-card click → drawer headline change.
> Toggle = aircraft layer off+on (includes ~0.8 s scripted waits, so
> true render is ≈0.1 s). Load includes a fixed 6 s settle wait.

| Scene | Objects | FPS | Select | Toggle | JS heap |
|---|---|---|---|---|---|
| 1k | 826 | 60 | 0.027 s | 0.92 s | 6 MB |
| 5k | 4,026 | 60 | 0.026 s | 0.90 s | 8 MB |
| 10k | 8,026 | 60 | 0.026 s | 0.91 s | 13 MB |

Verdict: smooth at 1k AND 5k, usable-plus at 10k (60 fps, 13 MB
heap, 26 ms selection). No bottleneck found — no fix needed, no
renderer migration triggered. MapLibre comparison:
`MAPLIBRE_VS_LEAFLET_V18_5.md` → KEEP_LEAFLET.
