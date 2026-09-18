# OPEN-SOURCE LICENSE REVIEW (recommendation; superseded by the owner's decision)

> Descriptive comparison for the future public core. Not legal advice.
> No files are relicensed by this document.

## Candidates

### Apache-2.0

- Patent grant: YES (express patent licence + retaliation clause).
- Contributor comfort: high for infrastructure (used by LEAN, exchange_calendars,
  quantlib-adjacent stack, most Apache data tooling).
- Commercial reuse: permissive; compatible with proprietary downstream
  extensions without copyleft spillover.
- Plugin ecosystem: Apache-2.0 core + MIT/BSD plugins compose cleanly;
  LGPL engine adapters stay behind process boundaries regardless.
- Cost: must ship LICENCE + NOTICE discipline.

### MIT

- Patent grant: NO express grant (implicit at best).
- Contributor comfort: highest familiarity, shortest text.
- Commercial reuse: permissive; proprietary downstream extensions stay possible.
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

## Decision (2026-09-18) — supersedes the recommendation above

The maintainer chose **MIT**, not Apache-2.0. The review above is kept
unedited so the trade-off stays visible: **MIT carries no express patent
grant**, which was the single reason Apache-2.0 was recommended. Every
other conclusion still holds, and the removal of all execution-adjacent
code from V1 narrows the patent exposure the recommendation was written
against.

Recorded in `legal/LICENSE_SIGNOFF.md` (status OBTAINED, maintainer
decision, no external counsel review).
