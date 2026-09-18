# LICENSE SIGNOFF PACKET (prepared — sign-off NOT_OBTAINED, do not claim)

> One bundle for maintainer and legal review, refreshed 2026-09-17 against the
> exact files that ship in the public candidate. Everything below can be
> verified in-tree. Nothing here is legal advice, and no tool, script or AI
> review can set `LICENSE_SIGNOFF` — only a human maintainer can.

Status: **NOT_OBTAINED** (see `legal/LICENSE_SIGNOFF.md`).

## Correction to the previous packet (resolved here)

The previous version of this packet said *"MapLibre GL 4.7.1 — NO (prototype
only, excluded from manifest)"*. That was wrong for the current product.
**MapLibre GL JS 6.10.0 ships** and is the primary renderer of the Tellurion
globe. The version was verified three independent ways on 2026-09-17:

1. at runtime, from the shipped bundle itself: `maplibregl.getVersion()` →
   `6.10.0`;
2. in `legal/THIRD_PARTY_NOTICES.md` and `legal/SBOM.spdx.json`
   (`maplibre-gl 6.10.0`, BSD-3-Clause);
3. in the per-file rights basis in `legal/ASSET_RIGHTS.json`.

The 4.7.1 figure survives only in `docs/design/maplibre-vs-leaflet.md`, which
is explicitly marked SUPERSEDED and describes a historical prototype.

## Intended licence

- Code: Apache-2.0 (`legal/LICENSE.proposed`, unmodified upstream text; the
  copyright holder line is confirmed at sign-off).
- Project documentation and screenshots: same MIT bundle. Synthetic
  fixtures are CC0 where marked.
- `legal/NOTICE.proposed`, `legal/THIRD_PARTY_NOTICES.md`, SBOM
  (`legal/SBOM.spdx.json`, SPDX-2.3, `signOff: NOT_OBTAINED`).

## Third-party code, fonts and data that ship

| Item | Version | Licence | Where | Attribution in tree |
|---|---|---|---|---|
| MapLibre GL JS (primary globe renderer) | **6.10.0** | BSD-3-Clause | `console/vendor/maplibre/` | `MAPLIBRE_LICENSE.txt` |
| Leaflet (`/ultra/classic` fallback) | 1.9.4 | BSD-2-Clause | `console/vendor/leaflet.*` | `LEAFLET_LICENSE.txt` |
| Inter variable font (Fontsource packaging) | 5.3.0 | SIL OFL 1.1 | `console/vendor/fonts/` | `INTER_OFL_LICENSE.txt` |
| world-atlas TopoJSON (Natural Earth 1:50m) | 2.0.2 | ISC (build); Natural Earth data public domain | `console/data/` | `WORLD_ATLAS_LICENSE.txt` |
| Icons | — | original inline SVG geometry | `console/world/app.js`, `console/brand/` | none needed |
| Synthetic fixtures and generators | — | CC0 (in-repo) | `plugins/*/fixture.json`, `python/gods_eye/future/*demo*` | per file / manifest |

No GPL or AGPL code is vendored or linked. NautilusTrader (LGPL-3.0-only) is
referenced by name only and never imported in-process.

## Real public data shown at runtime (not bundled)

WORLD NOW fetches these at run time; only a transient local cache is kept
(`raw_store/`, gitignored, never shipped). Terms evidence per source:
`docs/public/TERMS_SNAPSHOTS.md` (retrieved 2026-09-16).

| Source | Rights as recorded | Attribution shown |
|---|---|---|
| USGS earthquakes | US public domain | USGS Earthquake Hazards Program |
| NASA EONET | open metadata; imagery per linked source | NASA EONET |
| GDACS | summary + link, credit GDACS; no bulk mirror | GDACS |
| GDELT DOC | open use with citation + link | The GDELT Project |
| NOAA SWPC | US public domain | NOAA SWPC |
| NWS alerts (US only) | US public domain | National Weather Service |
| adsb.lol v2 (live aviation) | **ODbL 1.0** — display + transient cache; attribution mandatory | adsb.lol contributors (ODbL) |

Runtime rights gate (verified 2026-09-17): only these 7 enabled legs fetch.
STANDBY and KEY_REQUIRED sources (ReliefWeb, OpenSky, NASA FIRMS, AISStream,
OSM Overpass, and others) and unknown source IDs are refused with
`not enabled`, with zero network calls.

**ODbL question for the reviewer:** Tellurion displays adsb.lol data and holds
at most ~15 minutes of positions in memory, never on disk, and the public
server has no bulk export endpoint at all (`/api/world/export` returns
HTTP 404, verified 2026-09-17). Confirm this is display plus a transient
cache and not a conveyed derivative database.

## Open items for sign-off (human decisions)

1. DONE (2026-09-18): MIT text and copyright holder line; NOTICE content.
2. Contributor terms: DCO or CLA (currently NOT DECIDED).
3. ODbL treatment of the adsb.lol display and cache (above).
4. GDACS "no bulk mirror" and GDELT citation duties confirmed against the UI.
5. Every row of `legal/THIRD_PARTY_NOTICES.md` checked against upstream.
6. adsb.lol courtesy contact sent by a human
   (`docs/public/ADSB_LOL_PRODUCTION_CONTACT.md`, currently READY_TO_SEND).
