# License sign-off

Status: **OBTAINED** — maintainer decision, 2026-09-18.

| Item | State |
|---|---|
| Project licence | **MIT** (`LICENSE`, verbatim MIT text) |
| Copyright holder | Joel Studer and the Tellurion contributors |
| NOTICE | `NOTICE` — attribution only; not an additional licence term |
| Third-party notices | `legal/THIRD_PARTY_NOTICES.md` |
| SBOM | `legal/SBOM.spdx.json` (SPDX-2.3) |
| Asset rights | `legal/ASSET_RIGHTS.json` (every media, fixture, vendored file) |
| Contributor terms | **DCO** — Developer Certificate of Origin 1.1, sign off commits with `git commit -s` (`CONTRIBUTING.md`) |
| Signed off by | Joel Studer (maintainer and copyright holder) |
| Date | 2026-09-18 |

## Scope of this sign-off

This is the **owner's own decision** about the owner's own code. It is
explicitly **not** legal advice and **no external counsel reviewed it**. It
covers exactly two things: the licence Tellurion is offered under, and the
contributor terms. It makes no claim about anyone else's rights.

Third-party obligations are satisfied independently of this decision, and
are not waivable by it: every vendored component ships its upstream licence
text, and every data source keeps its own terms (see `NOTICE`).

## Change from the earlier recommendation

`legal/LICENSE_REVIEW.md` recommended Apache-2.0, for one reason: its
express patent grant. The maintainer chose **MIT** instead on 2026-09-18.
The trade-off is recorded rather than hidden: **MIT grants no express
patent licence.** The review's other conclusions are unaffected — MIT is
permissive, contributor-familiar, and composes with the BSD/OFL/ISC
components Tellurion vendors.

## Checklist

- [x] Maintainer confirms the project licence (MIT)
- [x] Copyright holder line confirmed for LICENSE and NOTICE
- [x] Every row in THIRD_PARTY_NOTICES verified against upstream
- [x] `tellurion release-check` rows `asset rights`, `sbom`, `secret scan` PASS
- [x] Contributor terms chosen (DCO)
- [x] No GPL/AGPL code linked or vendored

## What this does not close

- `EXTERNAL_PLUGIN_PILOT` and `THIRD_EYE_HUMAN_REVIEW` are recorded in
  `.github/RELEASE_GATES.json` as `WAIVED_BY_OWNER_FOR_V1_PUBLIC_BETA`.
  A waiver is an owner decision to ship without the gate. It is not a pass,
  and both remain useful post-release validation tasks.

Background: `legal/LICENSE_REVIEW.md`, `legal/LICENSE_SIGNOFF_PACKET.md`.
