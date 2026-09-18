# Tellurion v1.0.0-beta.2

Open-source, local-first world intelligence from public data.

SEE WHAT CHANGED. KNOW WHEN IT CHANGED. VERIFY WHY IT MATTERS.

## What Tellurion is

Tellurion fuses lawful public signals — earthquakes, weather alerts, space
weather, disasters, aviation, satellite imagery — into an evidence-first,
time-aware operational view that runs on your machine. Every object answers
the same questions in the same order: what, where, when, which sources, what
corroborates it, and what the rights are. UNKNOWN stays UNKNOWN.

## WORLD NOW

`/ultra?mode=now` — the current world over real qualified keyless public
feeds (USGS, NWS, SWPC, EONET, GDACS, GDELT, adsb.lol), each with truth mode
(DELAYED), provenance, and per-source rights shown in-app. Nothing is called
live unless it is near-live; delayed sources say so.

## CHANGE_DETECTED

First-class change objects: what changed, when, before/after state,
evidence chain, corroboration count (shared-upstream legs count once),
and confidence (never inflated past MODERATE on a single source). The first
poll seeds the baseline silently; identical reprocessing emits nothing twice.

## Satellite Evidence

Eligible changes (wildfire, flood, severe storm, volcano, landslide) gain
Sentinel-2 BEFORE/AFTER thumbnails: latest useful scene either side of first
sighting inside ±14-day windows, same MGRS tile preferred so the pair is
comparable. Every image carries capture time, cloud state, resolution and
the `Contains modified Copernicus Sentinel data [YEAR]` credit. Heavy cloud
is shown with a warning, never inferred through; missing scenes are an
honest empty state, never filler.

## LIVE EARTH

Optional NASA GIBS imagery under all overlays (toolbar globe button or `E`),
with explicit freshness on every view: VERY_FRESH (<1 h), FRESH (<6 h),
AGING (<48 h), STALE (<14 d), NO_COVERAGE (vector basemap, stated). GOES
covers the Americas at ~10-minute cadence, VIIRS/MODIS cover the world
daily. One source at a time (geo tiles are opaque off-disc; stacking would
fake coverage). Provider outages fall back to the vector globe with an
explicit chip — never a fatal dialog, never stale imagery shown as current.

## Truth / Freshness Model

REAL, DELAYED, STATIC, REPLAY and SYNTHETIC stay distinct everywhere: banner,
mode pill, timeline, drawer, feed and attribution always agree (one owner:
`state.worldMode`). Replay never loads live imagery, live feeds, or change
pins. Observation vocabulary is binding: OBSERVED / INFERRED / CORROBORATED /
UNKNOWN.

## Public Data / Rights

USGS/NWS/SWPC public domain; EONET/GDACS metadata with credit; GDELT with
citation; adsb.lol ODbL; Sentinel-2 under the Copernicus Sentinel Legal
Notice (attribution on every render); GIBS with the NASA acknowledgment;
MapLibre/Inter/Natural Earth licences vendored. Per-source rights ship in
`legal/ASSET_RIGHTS.json` (every media, fixture and vendored file).

## AI / API

Machine-readable world state, no pixel inspection required:
`/api/world/now`, `/api/world/changes?since=`, per-change
`/api/world/changes/<id>/imagery` (AVAILABLE/PARTIAL/NONE + capture times,
cloud, resolution, source), `/api/world/imagery/status` (per-layer source,
capture, age, freshness, rights + regional selection). Ask "what imagery is
available over Japan" or "which regions changed in 24 h" and get answers.

## Privacy

No facial recognition, no person tracking, no plate recognition, no owner
enrichment, no persistent private-vehicle identity, no VIP lists.
Aggregates, counts and area change only. Baselines keep counts and states
for 14 days; aircraft trails are memory-only.

## Known Limitations

- GOES gives near-real-time REGIONAL imagery (Americas), not global live
  video; VIIRS/MODIS are daily mosaics, not live.
- Asia-Pacific currently falls back to VIIRS daily: there is no qualified
  Himawari true-color path in GIBS, and the Band3 layer serves unusable
  tiles (verified live).
- Sentinel AFTER imagery appears days after a new event (revisit physics);
  fresh changes honestly show NO_AFTER until then.
- Sentinel thumbnails are granule previews (~300 m/px effective), not
  full-resolution analytical crops (source is 10 m).
- The first change poll seeds the baseline silently by design.
- Some coverage is partial or unavailable; uncovered domains say so.
- No proprietary trading, execution, market-mapping or alpha system ships;
  the public tree contains no private research identifiers.

## Install

```bash
pip install -e .
tellurion doctor       # environment + boundary checks (no keys, no network)
tellurion ultra --hero # the globe, 127.0.0.1 only
```

## Contributing

See `CONTRIBUTING.md` and `docs/GOVERNANCE.md`. Contributors sign off
commits (DCO 1.1).

## What's Next

Human gates first: external plugin pilot, third-eye human review. Then, only
by decision: Sentinel-1 processing, automatic satellite diffing, newsroom
export, commercial provider keys. No private-person tracking, ever.
