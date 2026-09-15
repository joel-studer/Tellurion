"""Ultra density benchmark (V18, data-side, offline).

Builds the 1k scene (and scales to 5k/10k by seed sweep) and reports
payload build time + counts. Browser FPS is measured separately in the
Ultra console overlay — never fabricated here.

Usage:
  python scripts/bench_ultra_density.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))


def main() -> int:
    from gods_eye.future import ultra_demo as _u
    for label, kw in (("1k", {"n_ac": 500, "n_vs": 300}),
                      ("5k", {"n_ac": 2500, "n_vs": 1500}),
                      ("10k", {"n_ac": 5000, "n_vs": 3000}),
                      ("25k", {"n_ac": 12500, "n_vs": 7500})):
        t0 = time.perf_counter()
        ac = _u.aircraft(seed=7, n=kw["n_ac"])
        vs = _u.vessels(seed=11, n=kw["n_vs"])
        wx = _u.weather(seed=31, n_cells=50)["cells"]
        rd = _u.road_incidents(seed=61, n=100)
        dt = time.perf_counter() - t0
        total = len(ac) + len(vs) + len(wx) + len(rd)
        verdict = ("smooth" if total <= 1000 else
                   "usable" if total <= 5000 else
                   "usable-degraded" if total <= 10000 else "degraded")
        print(f"DENSITY {label}: objects={total} build_s={dt:.2f} "
              f"target={verdict}")
    print("BENCH: OK (data-side only; FPS comes from the browser overlay)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
