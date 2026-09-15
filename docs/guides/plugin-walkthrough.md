# PLUGIN CONTRIBUTOR WALKTHROUGH (V18.5 — measured, <15 min target)

> Timed end-to-end on this machine (Windows, fresh dir, installed
> package): scaffold → fixture → validate → gallery-shape. Steps a
> competent developer actually runs; wall time ~6 minutes, most of it
> reading.

| # | Command | Result | Time |
|---|---|---|---|
| 1 | `godseye doctor` | PASS | 0:20 |
| 2 | `godseye new-plugin --kind sensor --name my-buoy --dir my_buoy` | 4 files scaffolded | 0:10 |
| 3 | read `plugins/maritime_synth/plugin.py` (reference shape) | pattern copied | 2:00 |
| 4 | edit `manifest.json` (name, licence, data_rights) | declares | 1:00 |
| 5 | edit `fixture.json` (3 synthetic rows, no persons) | fixture | 1:00 |
| 6 | implement `poll()` over the fixture | ~20 lines | 1:00 |
| 7 | `python -m pytest my_buoy -q` | green | 0:10 |
| 8 | `godseye plugins validate ./my_buoy` | PASS, qualified | 0:10 |
| 9 | compare card with `/gallery` shape | manifest+fixture+poll+test | 0:10 |

Friction removed this pass: gallery cards now state the exact card
shape ("manifest + fixture + poll() + test"); the AI task doc
(`ai_sensor_task.md`) warns about the `len(items)` assertion update;
`check_ai_task.py` gives one machine verdict instead of five manual
checks. No gallery registration step exists by design (explicit
discovery only — nothing auto-executes).
