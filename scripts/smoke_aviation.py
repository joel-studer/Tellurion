"""OPT-IN live smoke for the aviation leg (never run in CI).

Manually run by an operator with internet access:

    python scripts/smoke_aviation.py [--mil]

Refreshes all 8 tiles + 3 squawk legs against the real adsb.lol API
(polite cadence inside the script), prints the REALITY TEST counts.
Unit tests MUST NOT touch the network (they inject fixtures instead).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(prog="smoke_aviation")
    p.add_argument("--mil", action="store_true",
                   help="also poll the provider-tagged military leg")
    args = p.parse_args()

    from gods_eye.future import world_air as air

    import time as _t
    # Sweep in polite rounds (round-robin budget inside refresh) until
    # every leg is fresh or 5 rounds pass — never one burst.
    rep = {}
    for rnd in range(5):
        rep = air.refresh_aviation(force=False, include_mil=args.mil)
        print(f"round {rnd}: fetched={rep.get('fetched_legs')} "
              f"pending={rep.get('pending_legs')} "
              f"errors={len(rep.get('errors', []))}")
        if not rep.get("pending_legs"):
            break
        _t.sleep(25)
    snap = air.get_aviation(refresh=False)
    c = snap.get("counts", {})
    print("generated_at:", snap.get("generated_at"))
    print("legs fetched:", rep.get("fetched_legs"),
          "errors:", json.dumps(rep.get("errors")))
    print()
    print("REALITY (actual counts only):")
    print("  TOTAL_AIRCRAFT      ", c.get("total"))
    print("  POSITIONED_AIRCRAFT ", c.get("total"),
          "(non-positioned contacts are counted, never rendered)")
    print("  signals             ", json.dumps(c.get("signals")))
    print("  ON_GROUND           ", c.get("on_ground"))
    print("  AIRBORNE            ", c.get("airborne"))
    print("  FLAGGED_IMPORTANT   ", c.get("important"))
    print("  EMERGENCY_SQUAWKS   ", c.get("emergency_squawks"))
    print("  HOLDING_CANDIDATES  ", c.get("holding"))
    print("  WEATHER_CONFLICTS   ", c.get("weather_conflicts"))
    print("  STALE_TRACKS        ", c.get("stale"))
    print("  tracks_held         ", snap.get("tracks_held"))
    print("  airport_events      ", len(snap.get("airport_events", [])))
    for e in snap.get("airport_events", [])[:5]:
        print("   -", e.get("label"), e.get("level"))
    for f in snap.get("important", [])[:10]:
        first = (f.get("flags") or [{}])[0].get("label")
        print(f"   ! {f.get('callsign')} {f.get('icao24')} "
              f"[{f.get('interest')}] {first}")
    print()
    bad = [h for h in snap.get("health", [])
           if h.get("state") not in ("ONLINE",)]
    print("SMOKE:", "OK (%d real aircraft)" % (c.get("total", 0))
          if c.get("total") else "FAIL (no aircraft)")
    return 0 if c.get("total") else 1


if __name__ == "__main__":
    raise SystemExit(main())
