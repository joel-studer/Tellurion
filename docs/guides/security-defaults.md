# SECURITY FOR COMMUNITY EDITION (V15 — safe defaults)

Community defaults (enforced in code where possible, documented everywhere):

- **Localhost only.** Demo/serve bind `127.0.0.1`, never `0.0.0.0`
  (`python/gods_eye/demo.py::HOST`, `cli.py` serve path).
- **No execution surface at all.** V1 ships no order, venue, portfolio or
  backtest module. `boundary.trading_surface_hits()` fails `tellurion
  doctor` and `release-check` if one reappears. Tested.
- **No credentials required; none accepted.** Demo and CLI never read
  credential environment variables.
- **No telemetry.** Nothing reports back. The only outbound calls are the
  public data feeds you can see in the coverage view, each with its rights
  recorded.
- **Core-only imports.** Community mode never loads modules from outside
  the `gods_eye` package (`community.assert_no_private_imports`, tested).
- **No protected communications.** No relay, mempool, broker, or key-bearing
  paths exist in open-core modules (scan-tested: no credential values or
  key material anywhere in the tree).
- **Public/licensed/owned/authorized sources only.** Rights-first plugin
  policy: UNKNOWN rights never production-qualify. Demo data is synthetic
  CC0 with provenance stamped.

## Operator checklist (community install)

1. `tellurion doctor` green (imports, demo provenance, no execution
   surface, rights matrix).
2. `python -m pytest -q` green.
3. Serve only on loopback; do not proxy the demo to the public internet
   without adding auth/TLS yourself (out of scope for the preview).
4. Report credential-looking strings in issues with redaction (never paste keys).
