# OSS LAUNCH READINESS (V15 — honest scores, 0-10 each)

> Scored 2026-09-14 against the V15 evidence in this repo. No faked scores.

| Axis | Score | Evidence / gap |
|---|---|---|
| INSTALL | 5 | `pyproject` base stays light + extras; no published wheel yet, no lockfile/SBOM publish step. |
| DEMO | 7 | `tellurion demo` + `python -m gods_eye.demo` localhost-only on synthetic CC0; needs real screenshot/GIF + Windows/macOS/Linux smoke. |
| UI | 5 | New `console/demo.html` (dark console, event pulse -> evidence -> entities -> time machine) + `landing.html`; ops views preserved; needs polish + mobile pass. |
| README | 6 | `docs/public/README_DRAFT.md` complete as draft; needs screenshots + quickstart verified on clean machine. |
| PLUGIN_SDK | 6 | `plugins.py` Venue/PredictionMarket kinds + rights-first gates + `public_api.register_*`; needs one external author to succeed unaided. |
| DOCS | 6 | Boundary, package map, rights, security, license review, visual flow present; needs mkdocs/gh-pages shape. |
| TESTS | 7 | 526 pre-existing green + new `test_future_venues_v15.py` boundary tests; needs CI badge + cross-platform run. |
| LICENSE | 3 | Recommendation (Apache-2.0 core) documented; NO final decision, NO relicensing, NO NOTICE/SBOM publish yet. |
| SECURITY | 7 | Localhost-only, ALLOW_LIVE=false enforced, no-creds enforced, community import boundary tested; needs third-eye review. |
| CROSS_PLATFORM | 4 | Stdlib-first new code (portable); console is plain HTML; not yet verified on macOS/Linux CI. |
| CONTRIBUTOR_ONBOARDING | 5 | Template plugin + CONTRIBUTING draft; not yet tested with a real new contributor. |
| SCREENSHOT_VIDEO_HOOK | 2 | Placeholders only; no captures, no 30-second video. Highest virality leverage, currently missing. |

Total: 63/120.

## Gates

- **DEVELOPER_PREVIEW** needs: LICENSE decision signed + NOTICE stub,
  screenshot/GIF captures, clean-machine quickstart log, one external
  plugin built unaided, CI green on 2 OSes. Current blockers: LICENSE (3),
  SCREENSHOT_VIDEO_HOOK (2), CROSS_PLATFORM proof (4).
- **PUBLIC_BETA** needs: all axes >= 6, stable `public-api-v1` + schema
  versioning, published SBOM, security review closed.
- **1.0** needs: all axes >= 8, API stability window, versioned schemas,
  reproducible builds.

## Recommendation

Ship INTERNAL_PREVIEW now; do the four DEVELOPER_PREVIEW closers in V16
(licence sign-off, captures, clean-machine log, external-plugin pilot)
before any public URL.

---

# V17 ADDENDUM (2026-09-14 — scored against V17 evidence, conservative)

V17 axes (0–10). Evidence is runnable/screenshots in this tree; the
three procedural gates stay NOT_RUN/NOT_OBTAINED (see bottom).

| Axis | Score | Evidence / gap |
|---|---|---|
| INSTALL | 7 | `pip install -e . --no-deps --no-build-isolation` verified + `tellurion` entry (alias `godseye`) + `tellurion doctor` PASS, no PYTHONPATH. Gap: no published wheel, no clean-machine log. |
| DEMO | 8 | Localhost demo + `--hero` deterministic + smoke green + port fallback/strict verified + 30 s script + real frames. Gap: clean-machine run pending. |
| UI | 7 | Dark console (stream/map/drawer/time-machine/health/blind), first-seen row, reduced-motion, responsive fallback, no hype. Gap: single-event dataset, no real-user test. |
| README | 8 | First screen answers WHAT/WHY/LOOK/RUN, 3-command quickstart, real screenshots shipped, disclaimers test-enforced. Gap: clean-machine unverified. |
| PLUGIN_SDK | 8 | Scaffold→test→validate verified end-to-end; rights-first gates; internal blind pilot PASS. Gap: external human pilot pending. |
| DOCS | 7 | Boundary, package map, rights, security+lawful scope, API stability, tech stack, perf (measured), leak audit, map decision. Gap: no docs site. |
| TESTS | 8 | 562 green + V16 15/15 + smoke + candidate 9/9 + release-check. Gap: GH CI matrix not yet observed green. |
| LICENSE | 3 | Preview stubs only; sign-off NOT_OBTAINED. Unchanged. |
| SECURITY | 8 | ALLOW_LIVE/PAPER false in code + CI gate, scans, SECURITY.md (reporting placeholder, trust, lawful scope). Gap: no third-eye review. |
| CROSS_PLATFORM | 5 | Portable stdlib-first code; CI matrix (win+ubuntu × 3.13/3.14) defined. Gap: executed on Windows only; Linux NOT_RUN. |
| CONTRIBUTOR_ONBOARDING | 7 | AI task + `check_ai_task` + blind pilot PASS (0 avoidable questions). Gap: human pilot pending. |
| VISUAL_HOOK | 7 | 6 real hero captures + 6 video frames + ffmpeg command documented. Gap: no encoded MP4/GIF (no ffmpeg here). |
| REPO_CLEANLINESS | 8 | Manifest-enforced 96 files, gitignores, artifact 0 violations, no caches shipped. Gap: local-only captures/frames untracked by design. |
| RELEASE_AUTOMATION | 6 | Build + verify + release-check + SBOM sanity in CI; dependency-review on PRs. Gap: no tags/releases (publishing forbidden). |
| PLUGIN_EASE | 8 | One-command scaffold; blind pilot finished in ~12 steps unaided. Gap: human confirmation pending. |
| PRIVATE_ISOLATION | 9 | Fail-closed manifest + scans + candidate isolation + semantic leak audit (no leaks). Gap: no third-party audit. |

## V17 gate check (PUBLIC_BETA_CANDIDATE needs all of)

- Standalone candidate PASS — YES (9/9, candidate-only PYTHONPATH).
- INSTALL ≥ 8 — NO (7: clean-machine log missing).
- DEMO ≥ 8 — YES (8). UI ≥ 7 — YES (7). README ≥ 8 — YES (8).
- PLUGIN_SDK ≥ 8 — YES (8). TESTS ≥ 8 — YES (8). SECURITY ≥ 8 — YES (8).
- REPO_CLEANLINESS ≥ 8 — YES (8). PRIVATE_ISOLATION ≥ 9 — YES (9).
- VISUAL_HOOK ≥ 7 — YES (7).
- Procedural: REAL_LINUX_RUN NOT_RUN, EXTERNAL_PLUGIN_PILOT NOT_RUN,
  LICENSE_SIGNOFF NOT_OBTAINED.

## V17 recommendation

Stage stays INTERNAL_PREVIEW. Engineering gates are met except
INSTALL (blocked on the clean-machine run); the three procedural
gates are external by nature and must not be fabricated. Next: real
Linux run → external pilot → licence sign-off, in that order.

---

# V18 ADDENDUM (2026-09-15 — Ultra engineering complete)

Engineering state: DEVELOPER_PREVIEW_READY. Evidence: clean-Linux
re-verification PASS (157-file artifact), candidate 9/9, preview
release-check 27/27, full suite green, 60 fps @1k measured,
reviewed captures, hero-first README, 9-plugin pack, 11-source
registry, leakage re-audit with NO LEAKS.

Still procedural (never fabricated): EXTERNAL_PLUGIN_PILOT NOT_RUN,
LICENSE_SIGNOFF NOT_OBTAINED, no third-eye review, no GIF render.
PUBLIC_BETA_CANDIDATE is NOT claimed. Nothing published.
