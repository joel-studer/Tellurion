# LICENSE SIGNOFF PACKET (prepared — signoff NOT_OBTAINED, do not claim)

> One bundle for maintainer/legal review. Everything below is
> verifiable in-tree; nothing here constitutes legal advice.

## Intended licence

- Code: Apache-2.0 (`legal/LICENSE.proposed` — preview stub,
  final text + copyright line on sign-off).
- Docs/captures: same Apache-2.0 bundle (CC0 only for synthetic
  fixtures where marked).
- `legal/NOTICE.proposed` + `legal/THIRD_PARTY_NOTICES.md` + SBOM
  (`legal/SBOM.spdx.json`, SPDX-2.3, `signOff: NOT_OBTAINED`).

## Copied / vendored code inventory

| Item | Licence | Ships? | Attribution |
|---|---|---|---|
| Leaflet 1.9.x (`console/vendor/`) | BSD-2-Clause | yes (+ LICENCE file) | `LEAFLET_LICENSE.txt` in place |
| MapLibre GL 4.7.1 (`console/vendor/`) | BSD-3-Clause | NO (prototype only, excluded from manifest) | `MAPLIBRE_LICENSE.txt` in place |
| Ultra icons (inline SVG) | original | yes | none needed (design-system doc) |
| Synthetic fixtures/generators | CC0 (in-repo) | yes | marked per file/manifest |
| USGS-shape mapping code | original (data: US public domain) | yes | provenance strings in code |

## Data-rights notes

- 11-source registry with per-source rights/commercial/
  redistribution (`sensor_sources.py`); only QUALIFIED legs are
  live-capable and none are bundled with credentials.
- No GPL/AGPL code vendored (AIS-catcher, shiptracker, OTC are
  REFERENCE_ONLY; harvest doc states the rule).
- Camera/OSINT guards tested (`test_camera_safety_surface`,
  `test_osint_classification_discipline`).

## Open items for sign-off

Final Apache-2.0 text + copyright holder line; NOTICE content;
third-eye licence review of STAC-vocabulary use; Open-Meteo and
STAC-catalog terms before any live leg ships.
