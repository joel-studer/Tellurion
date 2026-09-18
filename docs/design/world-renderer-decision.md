# WORLD SURFACE TECHNOLOGY DECISION V3 (measured 2026-09-16)

Measured, not argued. Every number comes from
`python scripts/capture_world.py bench --gpu` on this machine. Nothing is
extrapolated, and the candidate that was not built is marked as not measured.
This supersedes the V2 estimates and the stale `KEEP_LEAFLET` verdict in
[`maplibre-vs-leaflet.md`](maplibre-vs-leaflet.md), which was written against a
MapLibre 4.7.1 prototype that had no globe, no selection, and no evidence
drawer.

| | |
|---|---|
| Machine | Windows 11, AMD Radeon(TM) Graphics, Chromium via Playwright |
| GL | WebGL 2.0, `ANGLE (AMD, … Direct3D11 vs_5_0 ps_5_0)` |
| Viewport | 1920×1080 |
| Method | 6 s of continuous camera motion; frame intervals from `requestAnimationFrame`, first 10 dropped |

Two frame-rate figures are reported because they say different things:

- **FPS (p95 frame)** — the rate at the 95th-percentile frame interval, i.e.
  what is sustained for all but the slowest 5% of frames.
- **FPS (mean)** — from the mean frame interval, so a handful of long frames
  drags it down. The gap between the two *is* the finding.

## Candidate A — MapLibre GL JS 6.10.0 globe (current primary)

| Scene | Objects | FPS (p95 frame) | FPS (mean) | Startup | Select | Toggle | JS heap |
|---|---|---|---|---|---|---|---|
| hero | 136 | 59.5 | 49.6 | 2.37 s | 38.9 ms | 26.5 ms | 54 MB |
| 1k (`dense`) | 894 | 59.5 | 49.7 | 1.63 s | 38.8 ms | 28.1 ms | 104 MB |
| 5k (`load5k`) | 4 094 | 59.9 | 49.9 | 3.61 s | 38.3 ms | 33.0 ms | 43 MB |
| 10k (`load10k`) | 8 094 | 59.5 | 49.4 | 4.09 s | 42.4 ms | 30.7 ms | 117 MB |

Status: **PASS** on all four scenes — no page errors, no failed requests.

The striking result is how flat it is: object count barely moves the frame
rate, because the work happens on the GPU and in clustering, not per object in
the DOM. What does move is **startup** (2.4 s → 4.1 s from hero to 10k) and
selection (38.9 → 42.4 ms), which scale with the data rather than the drawing.

The mean/p95 gap (≈49 vs ≈59.5 in every scene) means the globe holds 59–60 FPS
for 95% of frames and then spends roughly 60–80 ms on a few frames, consistent
with label/icon rasterisation and GC during continuous motion. It reads as an
occasional hitch while dragging, not as a low frame rate. It is a real defect,
it is **not** fixed here, and it is carried into the audit rather than smoothed
over.

## Candidate B — Leaflet 1.9.4 classic (fallback, `/ultra/classic`)

| Scene | DOM markers drawn | FPS (p95 frame) | FPS (mean) | Startup | JS heap |
|---|---|---|---|---|---|
| hero | 90 | 59.9 | 60.0 | 2.30 s | 10 MB |
| 1k (`dense`) | 121 | 59.9 | 60.0 | 2.67 s | 10 MB |
| 5k (`load5k`) | 128 | 59.9 | 60.0 | 3.96 s | 10 MB |

Status: **PASS**, with the caveat that makes the numbers possible: the page
aggregates above 120 markers below zoom 9 (`console/ultra.html`, the
`items.length>120&&z<9` branch), so it draws 90–128 DOM elements however much
data arrives — and `/api/ultra?scene=load5k` really does return 4 058 objects
(verified independently). **Leaflet's 60 FPS at "5k" is not the globe's
workload at 4 094 objects.** It is fast partly because it declines to draw the
scene. Its genuine advantages remain: one tenth of the memory (10 MB vs
43–117 MB) and no WebGL requirement at all.

`load10k` was not run against Leaflet: the same cap applies, so the result
would only restate it.

## Candidate C — CesiumJS

**Not benchmarked.** Assessed from published metadata only and rejected before
implementation, on two grounds that do not need a benchmark: its default
experience assumes network terrain/imagery assets, and this product is offline
and local-first by rule; and its bundle is several times the MapLibre build we
already ship. Recorded as *not measured* rather than given an invented number.

## Bundle cost (as shipped)

| Component | Raw | Gzip |
|---|---|---|
| maplibre-gl js | 1 091 KB | 294 KB |
| maplibre-gl css | 81 KB | 10 KB |
| world app (js+css+html) | 120 KB | 34 KB |
| geography (TopoJSON 1:50m) | 1 271 KB | 400 KB |
| fonts (Inter woff2, 2 files) | 130 KB | 130 KB |
| leaflet fallback (js+css+html) | 193 KB | 57 KB |

The globe path costs about **868 KB gzipped**; the fallback costs **57 KB**.
Geography, not the renderer, is the largest single item — a deliberate trade
for working with no network at all.

## Decision: KEEP CURRENT (MapLibre globe primary, Leaflet fallback)

| Criterion | Verdict |
|---|---|
| Visual wow | Globe. A real sphere with a day/night terminator is the first impression; a flat map is not. |
| True globe UX | Globe only. Leaflet cannot do it. |
| 5k performance | Globe draws 4 094 objects at 59.9 FPS (p95). Leaflet "passes" by drawing 128. |
| 10k usability | Globe: 59.5 FPS, 4.1 s startup, 117 MB heap — usable; startup is the weak point. Leaflet: not comparable. |
| Offline / local-first | Both pass: vendored library, local TopoJSON, no tile server, no network calls. |
| Bundle size | Leaflet wins decisively (57 KB vs 868 KB). Accepted — offline geography is most of the difference. |
| Fallback | Required and kept: no WebGL, or simple preference, lands on `/ultra/classic`. |
| Maintenance | Two surfaces is a real cost, accepted because the fallback is the no-GPU and accessibility story, not a second product. |

No migration is forced: the globe was already primary and the measurements
support leaving it there.

## What this benchmark cost us to learn

The first run did not fail honestly. It died with `Execution context was
destroyed`, which pointed at the wrong thing entirely. The real cause:
`/ultra/classic` requested `./vendor/leaflet.js`, which resolves to
`/ultra/vendor/leaflet.js` and 404s, so Leaflet never loaded, `MAP` stayed
`null`, and `MAP.panBy` threw inside a `requestAnimationFrame` loop whose
promise then never resolved. The harness had no timeout, captured no console or
page errors, and discarded four passing globe legs when the fifth threw.

Both are fixed: the page uses absolute asset paths, and the harness guards the
globals, bounds the frame loop, records `status: FAIL` per leg instead of
raising, attaches page/console/request diagnostics, writes its report
atomically, and exits non-zero only when a leg actually failed.

## Reproduce

```bash
python scripts/capture_world.py bench --gpu --out bench.json
```
