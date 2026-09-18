# OPEN-SOURCE LICENSE REVIEW (V15 — recommendation, no relicensing yet)

> Descriptive comparison for the future public core. Not legal advice.
> No files are relicensed by this document.

## Candidates

### Apache-2.0

- Patent grant: YES (express patent licence + retaliation clause).
- Contributor comfort: high for infrastructure (used by LEAN, exchange_calendars,
  quantlib-adjacent stack, most Apache data tooling).
- Commercial reuse: permissive; compatible with proprietary private lane
  (open core + private edge) without copyleft spillover.
- Plugin ecosystem: Apache-2.0 core + MIT/BSD plugins compose cleanly;
  LGPL engine adapters stay behind process boundaries regardless.
- Cost: must ship LICENCE + NOTICE discipline.

### MIT

- Patent grant: NO express grant (implicit at best).
- Contributor comfort: highest familiarity, shortest text.
- Commercial reuse: permissive; same open-core/private-edge split works.
- Plugin ecosystem: maximally composable, but no patent language for a
  project that will host execution-adjacent adapters.
- Cost: minimal.

## Recommendation

**Apache-2.0 for the future public core** (`gods_eye_core`, `gods_eye_demo`).
Rationale: patent grant matters once execution-adjacent interfaces
(venue/order/fill shapes, engine boundaries) are public; contributor
comfort stays high; commercial reuse is preserved; MIT/BSD plugins remain
compatible. Keep `gods_eye_plugins` permissive per-adapter (MIT/BSD where
upstream allows) and LGPL adapters strictly behind process boundaries.

## Non-decisions (explicit)

- No relicensing of the current repo happens automatically.
- Qanat-GPL and any GPL/AGPL code are never linked (existing REJECT stands).
- Final sign-off needs counsel + contributor-licence clarity before any
  publish step. SBOM + NOTICE files ship with the preview.
