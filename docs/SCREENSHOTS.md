# Screenshots and media (local only, never published by a script)

Every image here was rendered locally from this repository. Two kinds exist,
and they are never mixed:

- **DEMO REPLAY** captures are deterministic: synthetic CC0 data, a fixed
  clock (2026-09-15 16:40 UTC), motion off. Re-running reproduces them.
- **WORLD NOW** captures show real public feeds at the moment of capture.
  They are not reproducible pixel-for-pixel: aircraft, alerts and rate limits
  change. Each records its data time in the top bar.

Rights and content hashes for every file: `legal/ASSET_RIGHTS.json`.

## WORLD NOW (real public feeds, captured 2026-09-17)

| File | View | URL |
|---|---|---|
| `hero-world-now.png` | 2560×1440 first screen: globe, HUD, default Important item | `/ultra?mode=now` |
| `world-now-global.png` | globe with the drawer closed: aircraft clusters, earthquakes, coverage chip | `/ultra?mode=now` |
| `world-now-event.png` | deep-linked real event with UTC times and freshness | `/ultra?mode=now&event=<key>` |
| `world-now-important.png` | the same event scrolled to **Why flagged** (rank, certainty, reasons, score) | `/ultra?mode=now&event=<key>` |
| `world-now-aircraft.png` | aircraft drawer: flags with WHY and evidence, no owner enrichment | `/ultra?mode=now&aircraft=<icao24>` |
| `world-now-time-machine.png` | recorded real track played back (memory only, not live) | aircraft deep link → **Play recorded track** |
| `world-now-coverage.png` | source health: state, latency, next refresh, rights per source | `/ultra?mode=now&open=sources` |
| `world-now-region.png` | region intelligence and blind spots for Austria | `/ultra?mode=now&region=Austria` |

## CHANGE_DETECTED (real public feeds)

| File | View | URL |
|---|---|---|
| `world-now-change-global.png` | globe with lime change rings among event rings | `/ultra?mode=now` |
| `world-now-change-drawer.png` | change drawer: before/after, why flagged, evidence | `/ultra?mode=now&event=<chg-key>` |
| `change-before-after.png` | regional framing of a selected change | `/ultra?mode=now&event=<chg-key>` |
| `change-satellite-before-after.png` | Sentinel-2 BEFORE/AFTER pair with capture times, cloud, rights | change drawer → Satellite evidence |
| `change-satellite-cloud-limited.png` | cloud-limited pair with honesty banner | change drawer → Satellite evidence |
| `change-satellite-no-observation.png` | honest empty state (no suitable scene) | change drawer → Satellite evidence |

## LIVE EARTH (NASA GIBS, captured 2026-09-18)

| File | View | URL |
|---|---|---|
| `live-earth-global.png` | GOES true color over the Americas + LIVE EARTH freshness chip | `/ultra?mode=now`, then LIVE EARTH toggle |
| `live-earth-goes-americas.png` | regional GOES view | `/ultra?mode=now&lat=30&lon=-95&zoom=2.5` |
| `live-earth-himawari-pacific.png` | Pacific region (VIIRS fallback; no qualified Himawari true-color path) | `/ultra?mode=now&lat=20&lon=150&zoom=2.5` |
| `live-earth-daily-global.png` | VIIRS daily mosaic over Europe/Africa, AGING chip | `/ultra?mode=now&lat=25&lon=15&zoom=2` |
| `live-earth-stale-fallback.png` | provider outage: vector basemap + outage chip, no fatal dialog | LIVE EARTH with tile host blocked |
| `live-earth-with-change-pins.png` | change rings and events over live imagery | `/ultra?mode=now` |
| `replay-no-live-earth.png` | replay has no imagery mode (button hidden) | `/ultra?capture=world` |

## DEMO REPLAY (synthetic, deterministic)

| File | View |
|---|---|
| `replay-global.png` | replay globe, synthetic banner, event list (`/ultra?story=none`) |
| `tellurion-hero.png`, `tellurion-hero-2560.png`, `tellurion-laptop-1440.png` | replay hero at three sizes |
| `world-globe.png`, `evidence-drawer.png`, `time-machine.png`, `investigation.png`, `focus-mode.png`, `airport-story.png`, `earth-story.png`, `source-health.png`, `command-palette.png`, `relations.png` | replay surfaces |
| `tellurion-hero.gif`, `../media/tellurion-hero.mp4` | replay hero film |
| `landing.png`, `gallery.png` | landing page and plugin gallery |

Brand rasters and social cards live in `docs/brand/`.

## How to re-render

DEMO REPLAY screenshots, brand images, the film and the renderer benchmark:

```bash
python scripts/capture_world.py shots
python scripts/capture_world.py brand
python scripts/capture_world.py film
python scripts/capture_world.py bench --gpu --out bench.json
```

WORLD NOW captures need internet access and a running local server:

```bash
tellurion ultra
```

then open the URLs in the WORLD NOW table. Never commit a capture that shows a
synthetic label in WORLD NOW, a replay clock on real data, or the legacy
internal codename; the release review rejects all three.
