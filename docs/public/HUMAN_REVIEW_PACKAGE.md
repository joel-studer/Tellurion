# HUMAN PRODUCT REVIEW PACKAGE (NOT_RUN)

Status: **NOT_RUN.** Fill in only from a real, uncoached session with a person
who has not worked on Tellurion. An AI review does not count toward this gate.

Every URL below was opened in a real browser on 2026-09-17 against the
release candidate and showed what the step describes.

## Operator setup (5 minutes)

1. Install the public candidate in a fresh environment (see
   `HUMAN_PILOT_PACKAGE.md`, "Operator setup", steps 1–3), then run
   `tellurion ultra`.
2. Use a normal desktop browser at 1440 px width or larger, with internet
   access (WORLD NOW fetches real public feeds; the first load can take
   20–40 s while feeds answer).
3. Share only the browser window. Do not explain the product first.

## What to show (in this order, no commentary)

| # | Step | URL or action |
|---|---|---|
| 1 | WORLD NOW first screen | `http://127.0.0.1:8765/ultra?mode=now` |
| 2 | Important Now reasoning | in the right drawer, scroll to **Why flagged · Important #n** |
| 3 | One aircraft | click any aircraft cluster and zoom, or open `/ultra?mode=now&aircraft=<icao24>` |
| 4 | Recorded movement | in the aircraft drawer press **Play recorded track** |
| 5 | Region | `/ultra?mode=now&region=Austria` |
| 6 | Coverage and source health | `/ultra?mode=now&open=sources`, then the **Coverage** row in the left panel |
| 7 | Demo replay contrast | `/ultra` (synthetic scenario, clearly labelled) |
| 8 | Plugin gallery | `/gallery` |

## Questionnaire (ask exactly, record verbatim)

1. What is Tellurion, in your own words, after 10 seconds on step 1?
2. Is the data on step 1 real or simulated? How can you tell?
3. What does the product claim it does *not* cover?
4. Would you star it? Why or why not?
5. Would you clone it? Why or why not?
6. What looks unfinished?
7. What looks fake or overclaimed?
8. What is confusing?

## Rules

- No coaching, no leading, no defending.
- Record answers verbatim before any discussion.
- Ask before taking screenshots of their screen.

## Known limitations to observe, not explain

- WORLD NOW is delayed public data, never globally live; aviation covers the
  regional receiver tiles that answered (shown as "Aircraft coverage n/9").
- The first WORLD NOW load waits on real feeds; later loads are fast.
- `view=` and `sky=` URL parameters are accepted but have no effect.

## Results (operator fills)

- reviewer_profile (non-identifying, e.g. "backend dev, maps hobbyist"):
- date:
- answers_1_to_8 (verbatim):
- observed_friction (where did they hesitate or click wrong?):
- anything they believed was fake that is actually real, or the reverse:
- verdict_notes:
- gate result for `.github/RELEASE_GATES.json` → `THIRD_EYE_HUMAN_REVIEW`
  (PASS / FAIL, set by the maintainer, not by this form):
