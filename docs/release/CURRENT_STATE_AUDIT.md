# Current state audit (before final release fixes)

Audited 2026-09-17 from the public repository only. This records the tree
**as found**, before any change in the final release pass. Every "defect"
below was observed in a real Chromium browser or a real command, not inferred
from source.

## CURRENT_HEAD

`618c5738507adce2ee96a36056d31c1ed096dbd6` on `main` (2026-09-15,
"fix(sdk): list a plugin folder passed to plugins --dir").

No commit has been made since. All OpenCode work (WORLD NOW backend, live
aviation, candidate tooling) and the earlier brand/globe pass exist **only in
the working tree**.

## DIRTY_TREE

YES — 26 modified, 1 deleted, 73 untracked paths.

## CHANGED_FILES (tracked, modified)

`.gitignore`, `README.md`, `console/{demo,gallery,landing,ultra}.html`,
`docs/README.md`, `docs/design/{maplibre-vs-leaflet,world-renderer-decision}.md`,
`docs/screenshots/{source-health,time-machine}.png`,
`legal/{ASSET_RIGHTS.json,NOTICE.proposed,SBOM.spdx.json,THIRD_PARTY_NOTICES.md}`,
`pyproject.toml`, `python/gods_eye/{cli,demo}.py`,
`python/gods_eye/future/{boundary,layers,release_check,sensor_sources,ultra_demo}.py`,
`python/gods_eye/rights/registry.py`, `scripts/update_asset_rights.py`,
`tests/test_venues.py`. Deleted: `docs/screenshots/gods-eye-ultra-hero.png`.

## NEW_FILES (untracked, grouped)

- WORLD NOW backend: `python/gods_eye/future/{world_now,world_air,world_live,world_demo,world_scene,geo,release_manifest}.py`, `python/gods_eye/rights/__init__.py`
- Globe UI: `console/world.html`, `console/world/{app.js,styles.css}`, `console/{brand,data,media}/`, `console/vendor/{maplibre,fonts}/`
- Live-leg plugins: `plugins/{weather_nws,disaster_eonet,space_swpc,austria_pack}/`
- Tooling: `scripts/{build_public_candidate,verify_candidate,smoke_real_sources,smoke_aviation,capture_world}.py`
- Tests: `tests/{test_world,test_world_now_ui,test_world_now_v20,test_world_coverage_v19,test_aviation_v21,test_future_venues_v15,test_future_preview_v16,test_future_ultra_v18}.py`
- Docs/media: `docs/public/`, `docs/brand/`, `docs/design/PRODUCT_DESIGN_AUDIT.md`, 36 new screenshots, `docs/media/tellurion-hero.mp4`
- **Not for publication:** `raw_store/` (live feed cache — **not gitignored**), `FINAL_RECONCILIATION_CHECKPOINT.md` (contains a local absolute path — **not gitignored**)

## CURRENT_UI_STATE (real browser, real network, 2026-09-17)

What holds:

- `/ultra?mode=now` boots with every chrome surface agreeing after sync:
  pill `WORLD NOW · real data`, banner `REAL WORLD NOW · real public feeds
  (delayed, never global LIVE)`, attribution `real public feeds, delayed`,
  sources `5 online · REAL DATA`, `state.worldMode = now`.
- `/ultra` and `/ultra?story=none` stay `Replay · synthetic` with no
  WORLD NOW wording anywhere visible.
- Zero console errors, zero page errors, zero failed requests across seven
  scenarios.

Defects observed:

| # | Surface | Defect | Class |
|---|---|---|---|
| D1 | Top bar, timeline, day/night layer | WORLD NOW shows **World time 2026-09-15 16:40 UTC** (the synthetic replay epoch) while data was fetched 2026-09-17; the day/night terminator is computed from that same synthetic clock | TRUTH |
| D2 | Coverage | `real_coverage()` hard-codes aviation as `KEY_REQUIRED (OpenSky)` while adsb.lol serves ~2,000 real aircraft | TRUTH |
| D3 | First paint | pill and banner read `Replay · synthetic` / `SYNTHETIC SCENARIO` for 50–110 ms before sync in every NOW load | TRUTH (flash) |
| D4 | Left nav in NOW | replay subtitles on real rows: Aircraft "Corridors and regional replay", Storm "Rain bands and track", Wildfire "Satellite detections" | TRUTH (labels) |
| D5 | Timeline in NOW | mode button reads "Current replay"; ticks and clock are the replay scale | CLARITY |
| D6 | Global view | 90 quakes, 81 wildfires, 145 notices hidden below zoom 4–6 (replay minzooms); aircraft clusters at 20% opacity — globe looks empty beside "Aircraft 1,963" | DENSITY |
| D7 | Left nav | "Public cameras" title and "NO QUALIFIED SOURCE" render on top of each other | LAYOUT |
| D8 | Drawer | raw ISO timestamps break mid-string (`2026-09-` / `11T21:23…`) | READABILITY |
| D9 | Default selection | auto-selected "now" event is 135 h old | CLARITY |
| D10 | Deep link | `?open=sources` does nothing in WORLD NOW (handled only in the replay path) | DEEP LINK |

Cold first WORLD NOW load: 32 s to ready (feeds fetched on request);
warm loads 3.5 s.

## CURRENT_BACKEND_STATE

Real network probe: `/api/world/now` 13.8 s cold — 6 feeds configured,
5 online, 16 health rows, 10 coverage rows, 5 blind spots, 1 cross-source
link. `/api/world/now/aviation` 13.3 s — 838–1,963 aircraft depending on the
poll. `/api/world/now/important-v2` — 50–52 items with
observed/inferred, source count, freshness and score components.

## CURRENT_TEST_STATE

Source tree (`PYTHONPATH=python`): **228 passed, 2 failed** in 105 s.
Both failures are `local path scan`: `FINAL_RECONCILIATION_CHECKPOINT.md`
contains a Windows user path. The file that declared the tree frozen is the
file that breaks the tree's release check.

## OLD_HASH_STATUS

| Artifact | Hash | Status |
|---|---|---|
| Candidate built from the mixed development tree | `680c9182f377d57f6753d29eae8738df6555e7a72566ea900cd5deab6a4ddbfb` | SUPERSEDED (wrong UI lineage, recorded by the earlier checkpoint) |
| `dist/tellurion-public-candidate.zip` built 2026-09-16 23:38 | `2cf6ca042855b03dbe09ac9c94b9c74e8f3e6e46be1fb03b2fdc5d6ed110febb` | SUPERSEDED — built before defects D1–D10 were fixed; the extracted folder has since been polluted with `__pycache__` by in-place test runs |
| `dist/tellurion-candidate-checksums.json` (271 entries) | `4ec22b4a063b784102c6ad836fb36525cee3f8767415f5665751b426f6a2a218` | SUPERSEDED |
| `FINAL_RECONCILIATION_CHECKPOINT.md` "ENGINEERING FROZEN" | — | SUPERSEDED — OpenCode edited `world.html`, `styles.css`, `app.js`, tests, screenshots and `release_manifest.py` after it (22:14 → 23:37), and the file fails the local-path gate |

No previous hash matches bytes that will ship from this pass.
