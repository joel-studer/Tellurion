"""Import the public-apis catalog into candidate rows (V18, offline).

Reads a local checkout of public-apis/public-apis README (table rows)
and emits raw candidate rows. Rights are NEVER inferred here — every
row lands as NEEDS_TERMS_REVIEW for manual qualification against the
registry schema in `gods_eye.future.sensor_sources`.

Usage:
  python scripts/import_public_apis.py --in README.md --out candidates.json
  (no network; point --in at a file you already have)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROW = re.compile(r"^\|\s*\[([^]]+)\]\(([^)]+)\)\s*\|\s*([^|]+?)\s*\|\s*"
                 r"([^|]+?)\s*\|\s*([^|]+?)\s*\|")


def parse(text: str) -> list[dict]:
    out = []
    for line in text.splitlines():
        m = ROW.match(line.strip())
        if not m:
            continue
        name, link, desc, auth, https = (g.strip() for g in m.groups())
        out.append({"name": name, "link": link, "description": desc,
                    "auth": auth, "https": https,
                    "rights": "NEEDS_TERMS_REVIEW (never inferred)",
                    "status": "NEEDS_TERMS_REVIEW"})
    return out


def main() -> int:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="inp", required=True)
    p.add_argument("--out", dest="out", required=True)
    args = p.parse_args()
    rows = parse(Path(args.inp).read_text(encoding="utf-8", errors="ignore"))
    Path(args.out).write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print(f"IMPORT: OK ({len(rows)} raw rows -> {args.out}; "
          f"rights still NEEDS_TERMS_REVIEW)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
