"""Ultra capture (V18, local only, never published).

Serves the demo in-process, screenshots /ultra (+hero), /gallery,
and density-mode frames into preview-assets/frames-ultra/.

Usage:
  python scripts/capture_ultra.py [--out preview-assets/frames-ultra]
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
from http.server import HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))


def _serve() -> tuple[HTTPServer, int]:
    from gods_eye import demo as _demo
    assert _demo.HOST == "127.0.0.1", _demo.HOST
    server = HTTPServer((_demo.HOST, 0), _demo._Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, port


def capture(out_dir: Path) -> dict:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        return {"ok": False, "error": f"playwright missing: {e}"}
    out_dir.mkdir(parents=True, exist_ok=True)
    server, port = _serve()
    base = f"http://127.0.0.1:{port}"
    shots = [("ultra-world", f"{base}/ultra", None),
             ("ultra-hero", f"{base}/ultra?demo=hero", None),
             ("ultra-evidence", f"{base}/ultra?demo=hero",
              "document.querySelector('#feed .ev').click()"),
             ("ultra-gallery", f"{base}/gallery", None),
             ("ultra-dense", f"{base}/ultra?demo=dense", None)]
    taken: list[str] = []
    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch()
            except Exception as e:
                return {"ok": False,
                        "error": f"browser launch failed: {e}"}
            page = browser.new_page(viewport={"width": 1600,
                                              "height": 900})
            for name, url, js in shots:
                page.goto(url, wait_until="networkidle")
                page.wait_for_timeout(900)
                if js:
                    page.evaluate(js)
                    page.wait_for_timeout(500)
                page.screenshot(path=str(out_dir / f"{name}.png"))
                taken.append(f"{name}.png")
            browser.close()
    finally:
        server.shutdown()
    return {"ok": True, "shots": taken, "out_dir": str(out_dir),
            "published": False}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "preview-assets"
                                        / "frames-ultra"))
    args = ap.parse_args()
    rep = capture(Path(args.out))
    print(json.dumps(rep, indent=1))
    if not rep.get("ok"):
        return 1
    print(f"CAPTURE: OK ({len(rep['shots'])} images, NOT published)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
