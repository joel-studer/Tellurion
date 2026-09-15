# License sign-off

Status: NOT_OBTAINED

| Item | State |
|---|---|
| Proposed licence | Apache-2.0 (`legal/LICENSE.proposed`, unmodified upstream text) |
| NOTICE | proposed (`legal/NOTICE.proposed`); copyright holder line to confirm |
| Third-party notices | `legal/THIRD_PARTY_NOTICES.md` |
| SBOM | `legal/SBOM.spdx.json` (SPDX-2.3) |
| Asset rights | `legal/ASSET_RIGHTS.json` (every media, fixture, vendored file) |
| Contributor terms (DCO or CLA) | NOT DECIDED |
| Signed off by | (none) |
| Date | (none) |

Sign-off is a maintainer decision, with legal review where needed. No tool,
script, or AI review can set this status.

Background: `legal/LICENSE_REVIEW.md`, `legal/LICENSE_SIGNOFF_PACKET.md`.

## Checklist

- [ ] Maintainer confirms Apache-2.0 for the core
- [ ] Copyright holder line confirmed for NOTICE
- [ ] Every row in THIRD_PARTY_NOTICES verified against upstream
- [ ] `godseye release-check` rows `asset rights`, `sbom`, `secret scan` PASS
- [ ] Contributor terms chosen (DCO or CLA)
- [ ] No GPL/AGPL code linked; LGPL only across process boundaries

## After sign-off (one commit)

```bash
git mv legal/LICENSE.proposed LICENSE
git mv legal/NOTICE.proposed NOTICE
# pyproject.toml: license = "Apache-2.0", license-files = ["LICENSE", "NOTICE"]
# set Status: OBTAINED above and LICENSE_SIGNOFF in .github/RELEASE_GATES.json
```
