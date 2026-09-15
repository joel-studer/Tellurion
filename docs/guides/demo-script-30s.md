# 30-SECOND DEMO SCRIPT (V16 — preview)

> Spoken script for `godseye demo` → http://127.0.0.1:8765/ (localhost
> only, synthetic CC0 data, no keys, no trading logic). Timings are
> cumulative wall-clock targets for a rehearsed run.

## Setup (before the clock)

`godseye doctor` PASS. Terminal + browser side by side. No other tabs.

## Script

**0:00–0:05 — Open.** Run `godseye demo`. Say: "One command, localhost
only, no keys." Browser shows the dark console with one pulsing event.

**0:05–0:10 — Event pulse.** Click the pulse. Say: "One synthetic event
— Harborview bridge inspection announcement. Timestamp, family, label."

**0:10–0:15 — Evidence trace.** Open the evidence drawer. Say: "Two
sourced quotes, every record with source, timestamp, and hash.
Fact versus inference is labelled."

**0:15–0:20 — Entity relationships.** Show the OPERATES edge (Transit
Authority → Bridge 7). Say: "Entities resolve with method and model
version on the edge — never a bare name."

**0:20–0:25 — Time machine.** Change the as-of input; toggle
belief/replay. Say: "Replay the same evidence as of any date. The
drawer relabels; history is never rewritten."

**0:25–0:30 — Market context + safety bar.** Scroll to the synthetic
replay bars (DEMO:XHB on the demo venue, YES 0.62 / NO 0.38) and the
system bar (dataset, licence, venues, live=disabled). Say: "Market
context is generic venue contracts over synthetic data. Live execution
is disabled in code."

## Close (after the clock)

"Useful on its own: map, evidence, time machine, venue
contracts, replay, plugin SDK. `godseye new-plugin` scaffolds your
first sensor in a minute."

## Notes for the presenter

- All numbers are synthetic and labelled as such. Never imply live
  data, never claim market-beating results.
- If the default port is busy, the demo prints the fallback URL
  (localhost-only); or re-run with `--strict-port` for a clean error.
