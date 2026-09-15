# Third-party notices (PROPOSED, sign-off NOT_OBTAINED)

Software licences and data rights are tracked separately. Media, fixture,
and vendored-file rights: `legal/ASSET_RIGHTS.json`. Component inventory:
`legal/SBOM.spdx.json`. Versions below were read from installed package
metadata on the build machine on 2026-09-15; verify upstream at sign-off.

## Shipped in this repository

| Component | Version | Licence | Where |
|---|---|---|---|
| Leaflet | 1.9.4 | BSD-2-Clause | `console/vendor/leaflet.js`, `console/vendor/leaflet.css`; licence text `console/vendor/LEAFLET_LICENSE.txt` |

No other third-party code, web fonts, or icon sets are vendored. The core
package has no runtime dependencies.

## Optional extras (installed only on request, never distributed)

| Extra | Package | Version checked | Licence (installed metadata) |
|---|---|---|---|
| `market` | duckdb | 1.5.1 | MIT |
| `market` | ccxt | 4.5.46 | MIT |
| `market` | exchange_calendars | 4.13.2 | Apache-2.0 |
| `market` | pandas | 3.0.1 | BSD-3-Clause |
| `market` | pandas_market_calendars | 5.4.0 | MIT |
| `capture` | playwright | 1.58.0 | Apache-2.0 |
| `dev` | pytest | 9.0.2 | MIT |
| build | setuptools | 82.0.0 | MIT |

Correction to the earlier preview notice: installed metadata for
pandas_market_calendars 5.4.0 declares MIT (the preview listed BSD).

## Referenced by name, never installed or distributed

`gods_eye.future.optional_deps` probes for these engines so `godseye doctor`
can report them. None is a dependency; verify each licence before any
future integration: LEAN (Apache-2.0), hftbacktest (MIT), skfolio
(BSD-3-Clause), PyPortfolioOpt (MIT), PyTorch (BSD-3-Clause), sktime
(BSD-3-Clause), darts (Apache-2.0), statsforecast (Apache-2.0), Kronos (MIT).

## Copyleft boundary

- NautilusTrader (LGPL-3.0-only): never imported in-process
  (`optional_deps` reports it BLOCKED); separate process only.
- GPL/AGPL code is never linked or vendored.

## Data sources named in docs

USGS, NOAA/NWS, NASA FIRMS/EONET, OpenSky, Open-Meteo, and similar public
sources appear only as documented, opt-in plugin targets. No data from them
is bundled; each live plugin must declare its own terms.
