"""Local screenshot/frame capture for the community demo (V17, no publish).

Serves `gods_eye.demo` on an ephemeral localhost port in-process, then
drives it with Playwright (Chromium) in deterministic hero state
(`?demo=hero`: frozen dataset, fixed selection, fixed timeline).

Captures (default out: docs/screenshots):
  hero-world.png      world + event pulse
  event-evidence.png  evidence drawer open (hero auto-inspects event 0)
  entity-graph.png    entity neighbourhood (drawer scrolled to relations)
  time-machine.png    as-of applied in HISTORICAL BELIEF mode
  source-health.png   source health + blind spots column
  plugin-system.png   real `tellurion plugins list` output rendered as text

With --frames-only, captures numbered demo frames for the 30-second
video pipeline (see docs/SCREENSHOTS.md for the ffmpeg command).

Fails closed: if Playwright browsers are missing, exits non-zero with
the exact manual capture plan instead of fake images. Nothing uploads.

Usage:
  python scripts/capture_screenshots.py [--out docs/screenshots]
  python scripts/capture_screenshots.py --frames-only --out preview-assets/frames
"""

from __future__ import annotations

import argparse
import html
import json
import sys
import threading
from http.server import HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

SHOTS = ("hero-world", "event-evidence", "entity-graph",
         "time-machine", "source-health", "plugin-system")


# Chromium refuses navigation to these ports (ERR_UNSAFE_PORT); skip
# them when picking the ephemeral capture server port (localhost only).
_UNSAFE_PORTS = frozenset({
    1, 7, 9, 11, 13, 15, 17, 19, 20, 21, 22, 23, 25, 37, 42, 43, 53,
    77, 79, 87, 95, 101, 102, 103, 104, 109, 110, 111, 113, 115, 117,
    119, 123, 135, 139, 143, 179, 389, 465, 512, 513, 514, 515, 526,
    530, 531, 532, 540, 556, 563, 587, 601, 636, 993, 995, 2049, 3659,
    4045, 6000, 6665, 6666, 6667, 6668, 6669, 6697,
})


def _serve() -> tuple[HTTPServer, int]:
    from gods_eye import demo as _demo
    assert _demo.HOST == "127.0.0.1", _demo.HOST
    for _ in range(50):
        server = HTTPServer((_demo.HOST, 0), _demo._Handler)
        port = server.server_address[1]
        if port not in _UNSAFE_PORTS:
            break
        server.server_close()
    else:
        raise RuntimeError("no browser-safe ephemeral localhost port found")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, port


def _plugin_html() -> str:
    from gods_eye.cli import cmd_plugins
    rep = cmd_plugins(None)
    body = html.escape(json.dumps(rep, indent=1))[:6000]
    return ("<!doctype html><meta charset=utf-8>"
            "<title>tellurion plugins</title>"
            "<body style='background:#0b0e14;color:#e8edf5;"
            "font:13px/1.5 monospace;padding:24px'>"
            "<h1 style='font-size:15px'>tellurion plugins list "
            "(explicit discovery only)</h1>"
            f"<pre>{body}</pre>")


def capture(out_dir: Path, frames_only: bool = False) -> dict:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        return {"ok": False,
                "error": f"playwright not installed: {e}",
                "manual": "pip install playwright && "
                          "python -m playwright install chromium, then re-run"}
    out_dir.mkdir(parents=True, exist_ok=True)
    server, port = _serve()
    base = f"http://127.0.0.1:{port}"
    hero = f"{base}/?demo=hero"
    shots: list[str] = []
    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch()
            except Exception as e:
                return {"ok": False,
                        "error": f"browser launch failed: "
                                 f"{type(e).__name__}: {e}",
                        "manual": "python -m playwright install chromium "
                                  "(needs network once), then re-run; or "
                                  "capture manually per docs/SCREENSHOTS.md"}
            page = browser.new_page(viewport={"width": 1600, "height": 900})
            if frames_only:
                # 30s flow at ~0.5fps idea: 6 staged frames (see
                # docs/guides/demo-script-30s.md for the narration).
                stages = [
                    ("frame-00", hero, None),
                    ("frame-01", hero, "inspect(0)"),
                    ("frame-02", hero,
                     "document.getElementById('right').scrollIntoView()"),
                    ("frame-03", hero,
                     "document.getElementById('timeline').scrollIntoView()"),
                    ("frame-04", hero,
                     "document.getElementById('left').scrollIntoView()"),
                    ("frame-05", hero, None),
                ]
                for name, url, js in stages:
                    page.goto(url, wait_until="networkidle")
                    page.wait_for_timeout(600)
                    if js:
                        page.evaluate(js)
                        page.wait_for_timeout(400)
                    page.screenshot(path=str(out_dir / f"{name}.png"))
                    shots.append(f"{name}.png")
            else:
                page.goto(hero, wait_until="networkidle")
                page.wait_for_timeout(800)
                page.screenshot(path=str(out_dir / "hero-world.png"))
                shots.append("hero-world.png")
                page.evaluate("inspect(0)")
                page.wait_for_timeout(400)
                page.screenshot(path=str(out_dir / "event-evidence.png"))
                shots.append("event-evidence.png")
                page.evaluate("document.getElementById('right')"
                              ".scrollIntoView()")
                page.wait_for_timeout(300)
                page.screenshot(path=str(out_dir / "entity-graph.png"))
                shots.append("entity-graph.png")
                page.evaluate(
                    "document.getElementById('asof').value='2026-09-01T09:30';"
                    "document.getElementById('apply').click()")
                page.wait_for_timeout(400)
                page.evaluate("document.getElementById('timeline')"
                              ".scrollIntoView({block:'center'})")
                page.screenshot(path=str(out_dir / "time-machine.png"))
                shots.append("time-machine.png")
                page.evaluate("document.getElementById('left')"
                              ".scrollIntoView()")
                page.wait_for_timeout(300)
                page.screenshot(path=str(out_dir / "source-health.png"))
                shots.append("source-health.png")
                page.set_content(_plugin_html())
                page.wait_for_timeout(300)
                page.screenshot(path=str(out_dir / "plugin-system.png"))
                shots.append("plugin-system.png")
            browser.close()
    finally:
        server.shutdown()
    return {"ok": True, "shots": shots, "out_dir": str(out_dir),
            "published": False,
            "note": "local captures only; hero state (?demo=hero)"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "docs" / "screenshots"))
    ap.add_argument("--frames-only", action="store_true")
    args = ap.parse_args()
    rep = capture(Path(args.out), frames_only=args.frames_only)
    print(json.dumps(rep, indent=1))
    if not rep.get("ok"):
        print("CAPTURE: FAIL (see manual fallback above)",
              file=sys.stderr)
        return 1
    print(f"CAPTURE: OK ({len(rep['shots'])} images, NOT published)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
