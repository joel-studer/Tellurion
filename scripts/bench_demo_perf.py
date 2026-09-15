"""Public-demo performance probe (V17, local only, real values).

Measures the community edition only (no private pipeline, no state DBs):
  - interpreter + gods_eye import time (cold subprocess)
  - godseye doctor wall time
  - /api/health + /api/demo latency (in-process localhost server)
  - synthetic payload scale: demo-shaped evidence rows at
    100 / 1,000 / 5,000 rows through payload-build + JSON encode
  - first-useful-UI-render via Playwright navigation timing (if available)
  - peak RSS of this process (psutil if installed, else skipped)

Prints JSON. No invented scalability claims: N rows are synthetic
evidence dicts shaped like demo_dataset evidence entries.

Usage:
  python scripts/bench_demo_perf.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
import urllib.request
from http.server import HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))


def _time_subprocess(args: list[str]) -> float:
    t0 = time.perf_counter()
    subprocess.run(args, capture_output=True, text=True, timeout=300)
    return time.perf_counter() - t0


def _serve():
    from gods_eye import demo as _demo
    server = HTTPServer((_demo.HOST, 0), _demo._Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, port


def _get(url: str) -> tuple[float, int]:
    t0 = time.perf_counter()
    with urllib.request.urlopen(url, timeout=30) as r:
        n = len(r.read())
    return time.perf_counter() - t0, n


def _scale_rows(n: int) -> dict:
    from gods_eye.future import demo_dataset as dd
    base = dd.demo_dataset()["evidence"][0]
    rows = [dict(base, id=f"perf-ev-{i:05d}",
                 ts=f"2026-09-01T09:{i % 60:02d}:00+00:00")
            for i in range(n)]
    t0 = time.perf_counter()
    blob = json.dumps({"evidence": rows})
    dt = time.perf_counter() - t0
    return {"rows": n, "json_bytes": len(blob),
            "build_encode_s": round(dt, 4),
            "rows_per_s": round(n / dt, 1) if dt > 0 else None}


def main() -> int:
    out: dict = {"note": "local-only, synthetic rows, no network"}
    out["import_s"] = round(_time_subprocess(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0,'python'); import gods_eye.demo"]), 3)
    out["doctor_s"] = round(_time_subprocess(
        [sys.executable, "-m", "gods_eye.cli", "doctor"]), 3)
    server, port = _serve()
    try:
        base = f"http://127.0.0.1:{port}"
        dt, n = _get(base + "/api/health")
        out["api_health_s"] = round(dt, 4)
        out["api_health_bytes"] = n
        dt, n = _get(base + "/api/demo")
        out["api_demo_s"] = round(dt, 4)
        out["api_demo_bytes"] = n
    finally:
        server.shutdown()
    out["scale"] = [_scale_rows(n) for n in (100, 1000, 5000)]
    try:
        from playwright.sync_api import sync_playwright
        server2, port2 = _serve()
        try:
            with sync_playwright() as p:
                b = p.chromium.launch()
                pg = b.new_page(viewport={"width": 1600, "height": 900})
                t0 = time.perf_counter()
                pg.goto(f"http://127.0.0.1:{port2}/?demo=hero",
                        wait_until="networkidle")
                pg.wait_for_timeout(400)
                out["ui_first_render_s"] = round(
                    time.perf_counter() - t0, 3)
                b.close()
        finally:
            server2.shutdown()
    except Exception as e:
        out["ui_first_render_s"] = None
        out["ui_note"] = f"playwright unavailable: {type(e).__name__}"
    try:
        import psutil
        out["peak_rss_mb"] = round(
            psutil.Process().memory_info().rss / 1e6, 1)
    except ImportError:
        out["peak_rss_mb"] = None
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
