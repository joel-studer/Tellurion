# Tellurion final release checkpoint (2026-09-17)

Status: **TECHNICAL_PUBLIC_BETA_CANDIDATE = YES** · **ENGINEERING_FROZEN = YES**
· **PUBLIC_RELEASE = NO** · **PUBLISHED = NO**

Every result below was produced on the exact archive identified here, in fresh
extractions, never inside the canonical candidate folder. The canonical folder
was re-hashed after all gates: 266 files, 0 extra, 0 missing, 0 changed.

## Identity

| Field | Value |
|---|---|
| Source repository | public repository, branch `main` |
| HEAD | `618c5738507adce2ee96a36056d31c1ed096dbd6` — **working tree not committed**; the candidate is built from the working tree |
| Build command | `python scripts/build_public_candidate.py` |
| Build timestamp (UTC) | 2026-09-17T14:17:35+00:00 |
| Files in candidate | 266 (260 from the release manifest + 6 builder-generated alias/layout files) |
| Archive | `dist/tellurion-public-candidate.zip`, 47,592,240 bytes |
| **CANDIDATE_ARCHIVE_HASH** (SHA-256) | `0602d8bca7f67e3e455f0d1892d0e5c37f442434d611bceab843d64e16521a12` |
| **CHECKSUM_MANIFEST** (SHA-256 of `dist/tellurion-candidate-checksums.json`) | `373cb180622acda4f7685a68af843d50cb6d86e2831e180906399b01ee88ee04` |
| **TECHNICAL_CHECKPOINT_HASH** (SHA-256 over sorted `sha256  path` lines) | `67b41f4cd62c4d4d5468487059dd88da67d77024ed6ce2b833eeaaab2974db4e` |

Determinism: two clean builds produced byte-identical archives. The technical
checkpoint hash was recomputed independently on Linux from the extracted
archive and matched. It depends on file contents only; the archive hash also
depends on the Python/zlib used to compress.

## Gate results (on the archive above)

| Gate | Result | Evidence |
|---|---|---|
| Full Windows suite | **PASS** | 240 passed, 0 skipped; Python 3.13.5; fresh venv; `gods_eye.__file__` inside the extraction |
| Full Linux suite | **PASS** | 240 passed, 0 skipped; WSL Ubuntu 24.04, Python 3.13.15; fresh venv |
| Clean install | **PASS** | `pip install -e .` from the candidate in fresh venvs; `tellurion --help` → `usage: tellurion`; no global entrypoint used |
| `tellurion doctor` | **PASS** | Linux all green; Windows one environment-only warning (localhost port 8765 busy at that moment) |
| `verify_candidate.py` | **9/9 PASS** | imports, doctor, demo smoke, plugin validate, dataset, example test, release-check, no private paths, no private payload dirs |
| Public release-check | **PASS** | fail 0, warn 0, publishable false |
| Secret scan | **PASS** | 0 findings in the candidate |
| Private leakage (private-side scan V2) | **PASS** | 0 findings; release-check with the private denylist PASS; private research freeze verified intact |
| Archive byte audit | **PASS** | no bytecode, runtime state, venv, keys, databases, local absolute paths, wallets or secret-looking literals |
| Routes and assets | **PASS** | 26/26 |
| Browser QA (real Chromium) | **PASS** | 7 scenarios, 0 wrong-mode paints, 0 console/page/network errors |
| Privacy audit | **PASS** | aviation shows flight state only, no owner/person enrichment; privacy tests in the suite |
| Rights audit | **PASS** | only 7 enabled legs fetch; non-enabled and unknown source IDs refused with 0 network calls |
| Asset rights | **PASS** | 66 entries, no drift |
| SBOM | **PASS** | SPDX-2.3, 13 packages, MapLibre GL JS 6.10.0 confirmed at runtime |
| Accessibility (practical gate) | **PASS_WITH_RISK** | 0 unnamed controls; visible focus on 100% of Tab stops; contrast floor 5.44:1; Escape closes dialogs; reduced motion stops animations. Risk: map canvas content is not available to screen readers. Not a WCAG certification |
| Performance (real browser) | **PASS** | WORLD NOW global 59.9 FPS p95; regional movement 59.9; replay 1k 59.5; replay 10k (8,094 objects) 59.5 |
| Real-network smoke | **PASS** | 682 real observations; GDELT rate-limited and degraded honestly |
| Aviation smoke | **PASS** | 2,224 real aircraft, all positioned; flags phrased as observations |

## Defects fixed in this pass

Found in a real browser or by a real scan, each pinned by a regression test
where it is code:

1. WORLD NOW showed the synthetic replay clock and drew day/night from it.
2. Coverage and blind spots claimed aviation needs an OpenSky key while the
   keyless adsb.lol leg served thousands of aircraft.
3. Replay wording painted for 50–110 ms on every WORLD NOW load.
4. Replay subtitles were frozen onto real layers (navigation built before data).
5. Timeline in WORLD NOW used replay labels and clock.
6. The globe drew **none** of the counted aircraft: the boot request carried no
   positions. Deep links, search and clicks for unflagged aircraft also failed.
7. Real earthquakes, wildfires and notices were hidden at globe zoom.
8. Overlapping text, raw ISO timestamps, 15-decimal coordinates.
9. The default "now" item was days old or had no coordinates.
10. `?open=sources` did nothing in WORLD NOW.
11. Search offered synthetic replay objects and demo stories in WORLD NOW.
12. Region "Austria" reported the worldwide aircraft total as regional.
13. Important Now reasoning existed only in the API; now shown in the drawer.
14. Public media, captions, commands and provenance still carried the legacy
    internal codename; 25 stale pre-rebrand or pre-fix media files removed.
15. Dangling documentation links in shipped pages; a legal packet that said
    MapLibre 4.7.1 did not ship.
16. **Boundary breach:** migrated public files named private modules, frozen
    artefacts, research identifiers and private credential variable names.
    Removed without weakening protection (fail-closed manifest; markers now
    injected at run time by the private side).
17. The release-critical WORLD NOW UI test suite was not in the candidate.
18. The build was not reproducible across operating systems.

## Human and legal gates (not closable by engineering)

| Gate | Status |
|---|---|
| EXTERNAL_PLUGIN_PILOT | **NOT_RUN** — package ready: `docs/public/HUMAN_PILOT_PACKAGE.md` |
| THIRD_EYE_HUMAN_REVIEW | **NOT_RUN** — package ready: `docs/public/HUMAN_REVIEW_PACKAGE.md` |
| LICENSE_SIGNOFF | **NOT_OBTAINED** — packet ready: `legal/LICENSE_SIGNOFF_PACKET.md` |
| adsb.lol courtesy contact | **READY_TO_SEND** — never sent: `docs/public/ADSB_LOL_PRODUCTION_CONTACT.md` |

## Engineering freeze

No further development before the human gates, unless a human reviewer exposes
a release-blocking defect. Any change to a shipped file invalidates all three
hashes above and requires a full rebuild and a re-run of every gate.
