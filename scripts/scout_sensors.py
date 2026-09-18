"""Sensor scout for future developers (V18, discovery only, offline).

`tellurion scout` ranks the registry in `gods_eye.future.sensor_sources`
by relevance vs auth friction. It never connects anywhere.

Usage:
  tellurion scout [--category AVIATION] [--status QUALIFIED]
  python scripts/scout_sensors.py [--category AVIATION]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(prog="tellurion scout")
    p.add_argument("--category", default=None)
    p.add_argument("--status", default=None)
    args = p.parse_args()
    from gods_eye.future import sensor_sources as ss
    rows = ss.scout_rank()
    if args.category:
        rows = [r for r in rows if r["category"] == args.category.upper()]
    if args.status:
        rows = [r for r in rows if r["status"] == args.status.upper()]
    print(json.dumps({"summary": ss.summary(), "candidates": rows},
                     indent=1))
    print(f"SCOUT: OK ({len(rows)} candidates, discovery only, "
          f"nothing connected)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
