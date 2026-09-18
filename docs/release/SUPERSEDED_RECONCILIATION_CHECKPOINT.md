# SUPERSEDED — reconciliation checkpoint of 2026-09-16

> **Status: SUPERSEDED on 2026-09-17.** Kept for history only. It declared
> "ENGINEERING FROZEN" at 22:14, but the tree kept changing afterwards
> (`world.html`, `styles.css`, `app.js`, tests, screenshots and
> `release_manifest.py`, up to 23:37). The original file also contained a
> local absolute path, which made the source tree fail its own release check
> (`local path scan`). No hash recorded or implied here describes bytes that
> ship. See [`CURRENT_STATE_AUDIT.md`](CURRENT_STATE_AUDIT.md) for the state
> as found and the defects fixed afterwards.

The original text follows, with the machine-specific path replaced by
"this repository".

---

# TELLURION PUBLIC REPO RECONCILIATION CHECKPOINT (ENGINEERING FROZEN)

Supersedes the mixed-development-tree artifact
(`SUPERSEDED_WRONG_UI_CANDIDATE`, archive hash
680c9182f377d57f6753d29eae8738df6555e7a72566ea900cd5deab6a4ddbfb).

- Canonical public repo: this repository (branch `main`)
- Build command (run in the public repo):
  `python scripts/build_public_candidate.py --out dist/tellurion-public-candidate`
- Artifact path: `dist/tellurion-public-candidate/` (gitignored,
  reproducible from `release_manifest.public_include()`)
- File count: 262 shipped (0 missing;
  `all_included_classify_clean: True`)
- Archive: `dist/tellurion-public-candidate.zip` (deterministic:
  sorted names, fixed mtime, deflated)
- Per-file checksum manifest:
  `dist/tellurion-candidate-checksums.json` (262 entries)

## Gate results (as claimed on that artifact)

- Full Windows suite: 194/194 PASS (isolated copy, fresh venv,
  candidate pyproject install, Python 3.13.5)
- Full Linux suite: 194/194 PASS (Linux-fresh copy
  `~/tellurion-candidate`, WSL2 Ubuntu 24.04, portable Python
  3.13.15, fresh venv + pytest + pinned ccxt==4.5.46,
  candidate-only PYTHONPATH)
- Visual candidate check: 10/10 PASS on the MapLibre globe
  (Tellurion brand, REAL DATA HUD, 1,156 live aircraft, 337 real
  events, drawers, coverage row, replay contrast, zero JS errors)
- Route regression: `/ultra` serves Tellurion world surface
  (no `GOD'S EYE ULTRA`); `/ultra/classic` serves Leaflet fallback;
  world.html/app.js/MapLibre assets asserted present
- release-check: PASS fail=0 warn=0 (candidate scan 0 violations)
- verify_candidate: 9/9 PASS (ambient 8765 occupied throughout)
- WORLD NOW smoke (installed candidate): 754 real observations,
  1,158+ live aircraft, Important V2 76 items, trail deep links,
  Austria region, honest GDELT RATE_LIMITED; replay stays synthetic
- Clean install: `pip install -e . --no-deps` + `tellurion doctor`
  PASS from the candidate
- Secret scan: PASS ([]) · local-path scan: PASS ([])
  · payload scan: PASS ([]) · privacy: PASS · rights: PASS
  (7 enabled legs QUALIFIED; non-qualified refused at runtime)
- SBOM: SPDX-2.3, 13 packages, published False,
  sign-off NOT_OBTAINED (retained)
- Human/legal gates (separate, unchanged):
  EXTERNAL_PLUGIN_PILOT = NOT_RUN,
  THIRD_EYE_HUMAN_REVIEW = NOT_RUN,
  LICENSE_SIGNOFF = NOT_OBTAINED,
  ADSB_LOL_CONTACT = READY_TO_SEND (never sent, never acknowledged)

Note added on supersession: the "1,156 live aircraft" figure was a count.
The 2026-09-17 audit found that the globe drew none of them, because the
boot request (`?light=1`) carried no positions.

## Root cause (archived)

The candidate was built from the wrong source root (the mixed
development tree), whose UI lineage serves legacy Leaflet ultra.html
at /ultra and contains no world.html/MapLibre app. The public repo
owns the intended MapLibre globe UI and correct routing but predated
the WORLD NOW backend. Fixed by migrating only public-safe newer
functionality into the public repo (4 world modules, routes,
aviation engine, plugins, tests, docs, decision records) with
private research excluded by construction (manifest fail-closed +
boundary scans + suite), integrating WORLD NOW into the globe UI
without touching replay behavior, and rebuilding strictly from the
public repository.
