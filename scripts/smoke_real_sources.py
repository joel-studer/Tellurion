"""OPT-IN live smoke for WORLD NOW sources (never run in CI).

Manually run by an operator with internet access:

    python scripts/smoke_real_sources.py [--refresh]

Fetches each enabled source once (TTL-respecting unless --refresh),
validates, and prints a health table. Exits nonzero if an ENABLED
source has no usable data (neither fresh nor cache). This script MAY
contact real public endpoints; unit tests MUST NOT (they inject
fixtures via a mock opener instead).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(prog="smoke_real_sources")
    p.add_argument("--refresh", action="store_true",
                   help="force re-fetch ignoring TTL")
    args = p.parse_args()

    from gods_eye.future import world_now as now

    payload = now.get_now(refresh=True, force=args.refresh)
    print("generated_at:", payload.get("generated_at"))
    print("total_real:", (payload.get("counts") or {}).get("total_real"))
    print("linked_pairs:", (payload.get("counts") or {}).get("linked_pairs"))
    print()
    print(f"{'source':<18}{'state':<14}{'lat(ms)':<9}detail")
    bad = []
    for h in payload.get("health", []):
        if not h.get("enabled"):
            continue
        print("%-18s%-14s%-9s%s" % (
            h["source_id"], h["state"], h.get("latency_ms"),
            (h.get("detail") or "")[:90]))
        n = (payload.get("counts") or {}).get(h["source_id"], 0)
        if h["state"] not in ("ONLINE", "STALE", "DEGRADED",
                              "RATE_LIMITED") or n == 0 and h["state"] not in (
                                  "RATE_LIMITED",):
            # RATE_LIMITED with backoff is an honest state, not a failure,
            # unless it also has no data at all.
            if h["state"] == "RATE_LIMITED":
                print("  -> rate limited (honest degradation; "
                      "retry after backoff)")
            else:
                bad.append(h["source_id"])
    print()
    print("SMOKE:", "FAIL " + ",".join(bad) if bad else "OK "
          "(%d real observations)" % (
              (payload.get("counts") or {}).get("total_real", 0)))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
