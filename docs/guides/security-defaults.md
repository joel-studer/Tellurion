# SECURITY FOR COMMUNITY EDITION (V15 — safe defaults)

Community defaults (enforced in code where possible, documented everywhere):

- **Localhost only.** Demo/serve bind `127.0.0.1`, never `0.0.0.0`
  (`python/gods_eye/demo.py::HOST`, `cli.py` serve path).
- **No live execution.** `ALLOW_LIVE=false`, `ALLOW_PAPER_SANDBOX=false`;
  `exec_safety.assert_mode_allowed()` raises `LiveRefused` for LIVE
  (and for PAPER_SANDBOX until separately enabled). Tested.
- **No credentials required; none accepted.** `assert_no_credentials()`
  refuses credential keys in execution paths. Demo/CLI never read env keys.
- **No telemetry.** No outbound calls in community paths; ccxt layer is
  offline `describe()` only (no `load_markets()`); calendars are local.
- **Core-only imports.** Community mode never loads modules from outside
  the `gods_eye` package (`community.assert_no_private_imports`, tested).
- **No protected communications.** No relay, mempool, broker, or key-bearing
  paths exist in open-core modules (scan-tested: no credential values or
  key material anywhere in the tree).
- **Public/licensed/owned/authorized sources only.** Rights-first plugin
  policy: UNKNOWN rights never production-qualify. Demo data is synthetic
  CC0 with provenance stamped.

## Operator checklist (community install)

1. `godseye doctor` green (imports, demo provenance, live-disabled, matrix).
2. `python -m pytest -q` green (or at least the `test_future_venues_v15.py`
   + `test_future_oss_v14.py` subset for plugin authors).
3. Serve only on loopback; do not proxy the demo to the public internet
   without adding auth/TLS yourself (out of scope for the preview).
4. Report credential-looking strings in issues with redaction (never paste keys).
