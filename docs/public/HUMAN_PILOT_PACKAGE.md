# HUMAN PILOT PACKAGE — external contributor task (NOT_RUN)

Status: **NOT_RUN.** Do not mark PASS or FAIL until a real person performs
this with the public candidate only: no private repository, and no help beyond
the documents named here. AI dry runs do not count toward this gate.

## Operator setup

1. Take the release candidate archive `tellurion-public-candidate.zip` and its
   SHA-256 from the maintainer's final release checkpoint (kept in the
   repository's release folder, not shipped inside the candidate). Verify the
   checksum before handing anything over:

   ```bash
   sha256sum tellurion-public-candidate.zip
   ```

2. Unzip into a clean directory that contains nothing else (never add
   `.venv*/`, `raw_store/`, `state*/`, `logs/`, `dist/`).
3. Create a fresh virtual environment in that directory:

   ```bash
   python -m venv .venv
   ```

   then activate it, run `pip install -e .`, and run `tellurion doctor`
   (expect `verdict: PASS`).
4. Hand the person ONLY the unzipped directory and this file.
5. Start a timer when they begin. Do not coach.

## Human task (read aloud exactly)

> "Add a new public data source plugin to Tellurion. Pick any open JSON
> endpoint you like, for example a city open-data feed. Your plugin must have
> a fixture-backed poll, a rights declaration in its manifest, and at least
> one passing test, and it must be listed by `tellurion plugins --dir`
> pointing at your plugin folder. Use README.md and CONTRIBUTING.md only."

## Known limitation (do not reveal during the task)

The `/gallery` page is a static showcase of the bundled plugins plus the
static source registry. It does **not** discover new plugins in this beta, so
"appears in the gallery" is not part of the pass bar. If the person expects it
to, record that under confusion points — it is real product feedback.

## Record (operator fills)

- completion_time:
- questions_asked (verbatim):
- failures / confusion points:
- final_result (PASS / FAIL, and what was delivered):
- listed by `tellurion plugins --dir` (yes / no):
- `tellurion plugins validate <dir>` verdict:
- notes:

## Pass bar (competent developer)

Scaffold → fixture → rights → test → listed, in under 15 minutes, using only
the two documents.

For calibration only: an AI dry run of the same task on 2026-09-16 scaffolded,
validated and passed 3 plugin tests in under a minute. That is **not** human
evidence and does not count toward `EXTERNAL_PLUGIN_PILOT`.
