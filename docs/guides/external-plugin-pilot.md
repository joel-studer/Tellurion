# EXTERNAL PLUGIN PILOT (V16 — procedure, NOT YET RUN)

> DEVELOPER_PREVIEW closer: one external author builds a plugin unaided.
> Status: PROCEDURE DEFINED, PILOT NOT RUN. No pilot claims are made.

## Goal

Prove that a developer with only this repository can scaffold, declare,
test, and register a plugin using only the preview artifact + public docs.

## Prerequisites

- Fresh clone passes `godseye release-check` (`RELEASE CHECK: PASS`).
- Clean-machine check recorded (`docs/guides/clean-linux-check.md`).
- Participant uses only this repository: no credentials, no
  internal chat. Only the preview artifact + public docs.

## Procedure (unaided, observed)

1. Participant installs the preview artifact (`pip install -e .`) and
   runs `godseye doctor` (must reach PASS following only the `fix` hints).
2. Participant scaffolds a plugin: `godseye new-plugin --kind sensor
   --name pilot-sensor --dir pilot_sensor`.
3. Participant edits `manifest.json` (licence + data rights + schema),
   implements `poll()` over the bundled fixture, and runs the shipped
   test (`python -m pytest test_example_sensor.py -q`) until green.
4. Participant registers the declaration via the public API
   (`public_api.register_sensor`) and lists it via `godseye plugins
   --dir pilot_sensor`.
5. Observer records every question asked, every doc consulted, and wall
   time per step. No hints beyond the docs are given during the run.

## Success criteria

- Doctor PASS with no verbal help.
- Scaffold + test green with no verbal help.
- `godseye plugins --dir` shows the pilot plugin with
  production-qualified GREEN (licence + schema + non-UNKNOWN rights).
- Plugin declares no private capabilities (`declare()` refuses none —
   i.e. no refusal encountered) and imports only modules that ship in
   the `gods_eye` package (`godseye plugins validate` checks this).
- Post-run interview: participant can state the trust model in one
  paragraph (explicit install, explicit discovery, rights-first).

## Failure handling

Any criterion missed → file the friction as a docs/SDK bug against the
preview (not against the participant), fix, rebuild the artifact, and
re-run with a new participant. The pilot passes once, with one author,
end to end, unaided.

## Record

Result (when run): date, participant handle, artifact hash/build report,
per-step times, questions log, verdict PASS/FAIL, follow-up issues.
This file is updated only after a real run; until then the pilot is
OPEN.
