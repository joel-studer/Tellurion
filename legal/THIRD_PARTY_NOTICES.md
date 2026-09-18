# Third-party notices

Tellurion itself is MIT (`LICENSE`). The components below keep their own
licences, which this file records.

Software licences and data rights are tracked separately. Media, fixture,
and vendored-file rights: `legal/ASSET_RIGHTS.json`. Component inventory:
`legal/SBOM.spdx.json`. Versions below were read from installed package
metadata on the build machine and verified against upstream on
2026-09-18.

## Shipped in this repository

| Component | Version | Licence | Where |
|---|---|---|---|
| MapLibre GL JS | 6.10.0 | BSD-3-Clause | `console/vendor/maplibre/maplibre-gl.mjs`, `-shared.mjs`, `-worker.mjs`, `maplibre-gl.css`; licence text `console/vendor/maplibre/MAPLIBRE_LICENSE.txt` |
| Leaflet | 1.9.4 | BSD-2-Clause | `console/vendor/leaflet.js`, `console/vendor/leaflet.css`; licence text `console/vendor/LEAFLET_LICENSE.txt` |
| Inter (variable) | 5.3.0 (Fontsource packaging) | SIL OFL 1.1 | `console/vendor/fonts/inter-latin-wght-normal.woff2`, `inter-latin-ext-wght-normal.woff2`; licence text `console/vendor/fonts/INTER_OFL_LICENSE.txt` |
| world-atlas (TopoJSON build of Natural Earth 1:50m) | 2.0.2 | ISC (build scripts); the underlying Natural Earth data is public domain | `console/data/land-50m.json`, `console/data/countries-50m.json`; licence text `console/data/WORLD_ATLAS_LICENSE.txt` |

These four are the only third-party web assets vendored, and each ships with
its licence text beside it. No icon set is vendored: every icon in the console
is drawn as inline SVG geometry for this project. No map tiles, basemap
imagery, or satellite imagery are bundled or fetched — the globe is drawn from
the TopoJSON above. The core Python package has no runtime dependencies.

Per-file rights basis and content hashes: `legal/ASSET_RIGHTS.json`.

## Optional extras (installed only on request, never distributed)

| Extra | Package | Version checked | Licence (installed metadata) |
|---|---|---|---|
| `capture` | playwright | 1.58.0 | Apache-2.0 |
| `dev` | pytest | 9.0.2 | MIT |
| build | setuptools | 82.0.0 | MIT |

The `market` extra and its packages were removed with the trading surface
before the v1.0.0-beta.1 release; only `capture` and `dev` remain.

## Referenced by name, never installed or distributed

None. V1 removed the modules that named third-party engines, and
`gods_eye.future.optional_deps` now probes only `playwright` and `pytest`.

## Copyleft boundary

GPL/AGPL code is never linked or vendored.

## Public data sources fetched at run time

WORLD NOW fetches live public data at run time from USGS, NASA EONET,
GDACS, GDELT, NOAA SWPC, NWS and adsb.lol. **No data from them is bundled
with this repository**; each response is fetched by the person running the
software, and the attribution each source requires is shown in the
application next to the data it produced. Full list and terms: `NOTICE`
and `python/gods_eye/rights/registry.py`. Sources that are not enabled —
including those needing a user's own key — make no network request at all.
