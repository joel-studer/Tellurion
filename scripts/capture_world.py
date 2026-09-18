"""Capture Tellurion screenshots, brand images, the hero film, and a renderer
benchmark from the real UI. Local only: nothing is uploaded.

  python scripts/capture_world.py shots   # docs/screenshots/*.png
  python scripts/capture_world.py brand   # docs/brand/*.png (favicons, social)
  python scripts/capture_world.py film    # docs/screenshots/tellurion-hero.gif + docs/media/tellurion-hero.mp4
  python scripts/capture_world.py bench   # renderer benchmark (JSON to stdout, --out to save)

Needs the optional ``capture`` extra (Playwright with Chromium). The film also
needs Pillow and an ffmpeg binary (``imageio-ffmpeg`` or ffmpeg on PATH).
``--gpu`` lets Chromium use this machine's GPU (ANGLE/D3D11 on Windows); the
default software renderer gives reproducible pixels for screenshots.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

SHOTS = (
    ("tellurion-hero", "/ultra?capture=hero", (1920, 1080)),
    ("tellurion-hero-2560", "/ultra?capture=hero", (2560, 1440)),
    ("tellurion-laptop-1440", "/ultra?capture=hero", (1440, 900)),
    ("world-globe", "/ultra?capture=world", (1920, 1080)),
    ("evidence-drawer", "/ultra?capture=evidence", (1920, 1080)),
    ("time-machine", "/ultra?capture=timemachine", (1920, 1080)),
    ("investigation", "/ultra?capture=investigation", (1920, 1080)),
    ("focus-mode", "/ultra?capture=focus", (1920, 1080)),
    ("airport-story", "/ultra?capture=airport", (1920, 1080)),
    ("earth-story", "/ultra?capture=earth", (1920, 1080)),
    ("source-health", "/ultra?capture=world&open=sources", (1920, 1080)),
    ("command-palette", "/ultra?capture=world&open=palette&q=port", (1920, 1080)),
    ("relations", "/ultra?capture=evidence&open=relations", (1920, 1080)),
    ("gallery", "/gallery", (1920, 1080)),
    ("landing", "/landing", (1920, 1080)),
)
BENCH_SCENES = (("hero", ""), ("dense1k", "&scene=dense"), ("load5k", "&scene=load5k"),
                ("load10k", "&scene=load10k"))
LEAFLET_SCENES = (("hero", ""), ("dense1k", "?scene=dense"), ("load5k", "?scene=load5k"))
GPU_ARGS = ["--use-angle=d3d11", "--enable-gpu", "--ignore-gpu-blocklist"]


def serve():
    from gods_eye import demo
    server = ThreadingHTTPServer((demo.HOST, 0), demo._Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://{demo.HOST}:{server.server_address[1]}"


def launch(playwright, gpu: bool):
    return playwright.chromium.launch(args=GPU_ARGS if gpu else [])


def wait_ready(page, timeout_ms: int = 60000) -> None:
    if "/ultra" in page.url and "classic" not in page.url:
        page.wait_for_function("document.documentElement.dataset.ready === 'true'", timeout=timeout_ms)
    else:
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
    page.wait_for_timeout(1200)


def shots(base: str, gpu: bool) -> list:
    from playwright.sync_api import sync_playwright
    out_dir = ROOT / "docs" / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    with sync_playwright() as p:
        browser = launch(p, gpu)
        for name, path, (w, h) in SHOTS:
            page = browser.new_page(viewport={"width": w, "height": h})
            page.goto(base + path)
            wait_ready(page)
            target = out_dir / f"{name}.png"
            page.screenshot(path=str(target))
            written.append(target.relative_to(ROOT).as_posix())
            page.close()
        browser.close()
    return written


def brand(base: str, gpu: bool) -> list:
    from playwright.sync_api import sync_playwright
    out_dir = ROOT / "docs" / "brand"
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    with sync_playwright() as p:
        browser = launch(p, gpu)
        for size in (16, 32, 64, 180, 512):
            svg = "favicon.svg" if size <= 32 else "tellurion-mark.svg"
            page = browser.new_page(viewport={"width": size, "height": size})
            page.set_content(f"<style>html,body{{margin:0;background:transparent}}</style>"
                             f"<img src='{base}/console/brand/{svg}' width='{size}' height='{size}'>")
            page.wait_for_timeout(300)
            target = out_dir / f"tellurion-mark-{size}.png"
            page.screenshot(path=str(target), omit_background=True)
            written.append(target.relative_to(ROOT).as_posix())
            page.close()
        for name, (w, h) in (("social-1200x630", (1200, 630)), ("social-square-1080", (1080, 1080))):
            page = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
            page.goto(f"{base}/ultra?capture=focus")
            wait_ready(page)
            target = out_dir / f"tellurion-{name}.png"
            page.screenshot(path=str(target))
            written.append(target.relative_to(ROOT).as_posix())
            page.close()
        browser.close()
    return written


def _ffmpeg() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        found = shutil.which("ffmpeg")
        if not found:
            raise SystemExit("film needs ffmpeg (pip install imageio-ffmpeg, or ffmpeg on PATH)")
        return found


def film(base: str, gpu: bool) -> list:
    """Directed 24 s hero film: world awakens, port storm, time scrub, investigation, earth story."""
    from playwright.sync_api import sync_playwright
    size = {"width": 1600, "height": 900}
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as p:
        browser = launch(p, gpu)
        context = browser.new_context(viewport=size, record_video_dir=tmp, record_video_size=size)
        page = context.new_page()
        page.goto(f"{base}/ultra?story=port")
        page.wait_for_function("document.documentElement.dataset.ready === 'true'", timeout=60000)
        page.wait_for_timeout(1500)
        for tick in range(0, 13, 2):
            page.evaluate(f"window.__tellurion.setTick({tick})")
            page.wait_for_timeout(700)
        page.keyboard.press("i")
        page.wait_for_timeout(2600)
        page.keyboard.press("Escape")
        page.wait_for_timeout(1800)
        page.evaluate("window.__tellurion.selectById('SYN-EQ00', 'earth')")
        page.wait_for_timeout(3200)
        page.keyboard.press("f")
        page.wait_for_timeout(2200)
        video = page.video.path()
        context.close()
        browser.close()
        media = ROOT / "docs" / "media"
        shots_dir = ROOT / "docs" / "screenshots"
        media.mkdir(parents=True, exist_ok=True)
        mp4 = media / "tellurion-hero.mp4"
        gif = shots_dir / "tellurion-hero.gif"
        ffmpeg = _ffmpeg()
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", video, "-ss", "1.2",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "22", "-movflags", "+faststart",
                        str(mp4)], check=True)
        palette = Path(tmp) / "palette.png"
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-ss", "1.2", "-i", str(mp4), "-vf",
                        "fps=10,scale=960:-1:flags=lanczos,palettegen=max_colors=160", str(palette)], check=True)
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-ss", "1.2", "-i", str(mp4), "-i", str(palette),
                        "-lavfi", "fps=10,scale=960:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=sierra2_4a",
                        str(gif)], check=True)
    return [mp4.relative_to(ROOT).as_posix(), gif.relative_to(ROOT).as_posix()]


def _bundle() -> dict:
    files = {
        "maplibre-gl (js)": ["console/vendor/maplibre/maplibre-gl.mjs", "console/vendor/maplibre/maplibre-gl-shared.mjs",
                             "console/vendor/maplibre/maplibre-gl-worker.mjs"],
        "maplibre-gl (css)": ["console/vendor/maplibre/maplibre-gl.css"],
        "world app (js+css+html)": ["console/world/app.js", "console/world/styles.css", "console/world.html"],
        "geography (topojson)": ["console/data/land-50m.json", "console/data/countries-50m.json"],
        "fonts (woff2)": ["console/vendor/fonts/inter-latin-wght-normal.woff2", "console/vendor/fonts/inter-latin-ext-wght-normal.woff2"],
        "leaflet (classic fallback)": ["console/vendor/leaflet.js", "console/vendor/leaflet.css", "console/ultra.html"],
    }
    out = {}
    for label, rels in files.items():
        raw = sum((ROOT / r).stat().st_size for r in rels)
        gz = sum(len(gzip.compress((ROOT / r).read_bytes(), 6)) for r in rels)
        out[label] = {"raw_kb": round(raw / 1024), "gzip_kb": round(gz / 1024)}
    return out


def _bench_globe(page, base: str, query: str) -> dict:
    started = time.perf_counter()
    page.goto(f"{base}/ultra?capture=hero&bench=1{query}")
    page.wait_for_function("document.documentElement.dataset.ready === 'true'", timeout=120000)
    ready_s = time.perf_counter() - started
    page.wait_for_function("document.documentElement.dataset.bench === 'done'", timeout=60000)
    result = page.evaluate("window.__tellurionBench")
    heap = page.evaluate("performance.memory ? Math.round(performance.memory.usedJSHeapSize / 1048576) : null")
    return {"status": "OK", **result, **_webgl_info(page), **page.evaluate(_INTERACTION),
            "ready_s": round(ready_s, 2), "js_heap_mb": heap}


_LEAFLET_BENCH = """async () => {
  if (typeof L === "undefined") return { status: "FAIL", reason: "leaflet script did not load" };
  if (typeof MAP === "undefined" || !MAP) return { status: "FAIL", reason: "map not initialised" };
  const frames = []; let last = performance.now(); const end = last + 6000; let failure = null;
  await new Promise((resolve) => {
    const stop = setTimeout(() => { failure = failure || "frame loop timed out"; resolve(); }, 20000);
    const frame = (now) => {
      try { frames.push(now - last); last = now; MAP.panBy([3, 0], { animate: false }); }
      catch (err) { failure = err.message; clearTimeout(stop); resolve(); return; }
      if (now < end) requestAnimationFrame(frame); else { clearTimeout(stop); resolve(); }
    };
    requestAnimationFrame(frame);
  });
  if (failure) return { status: "FAIL", reason: failure, frames: frames.length };
  const s = frames.slice(10).sort((a, b) => a - b);
  if (s.length < 10) return { status: "FAIL", reason: "too few frames", frames: s.length };
  const avg = s.reduce((a, b) => a + b, 0) / s.length;
  return { status: "OK", fps_avg: Math.round(10000 / avg) / 10,
    fps_p5: Math.round(10000 / s[Math.floor(s.length * 0.95)]) / 10,
    frames: s.length, dom_markers: document.querySelectorAll('.leaflet-marker-icon, path.leaflet-interactive').length };
}"""


_INTERACTION = """async () => {
  const twoFrames = () => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  const out = {};
  if (window.__tellurion && window.__tellurion.selectById) {
    const t0 = performance.now();
    window.__tellurion.selectById("SYN-EQ00", "earth");
    await twoFrames();
    out.select_ms = Math.round((performance.now() - t0) * 10) / 10;
  }
  const toggle = document.querySelector('button[role="switch"][data-key], input[type="checkbox"]');
  if (toggle) {
    const t1 = performance.now();
    toggle.click(); await twoFrames();
    out.toggle_ms = Math.round((performance.now() - t1) * 10) / 10;
    toggle.click(); await twoFrames();
  }
  return out;
}"""


def _webgl_info(page) -> dict:
    return page.evaluate("""() => {
      const c = document.createElement("canvas");
      const gl = c.getContext("webgl2") || c.getContext("webgl");
      if (!gl) return { webgl: false };
      const dbg = gl.getExtension("WEBGL_debug_renderer_info");
      return { webgl: true, gl_version: gl.getParameter(gl.VERSION),
               gl_renderer: dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : "masked" };
    }""")


def _diagnostics(page) -> dict:
    """Record page errors, console errors, and failed requests for one leg."""
    diag = {"page_errors": [], "console_errors": [], "failed_requests": []}
    page.on("pageerror", lambda e: diag["page_errors"].append(str(e)[:200]))
    page.on("console", lambda m: m.type == "error" and diag["console_errors"].append(m.text[:200]))
    page.on("requestfailed", lambda r: diag["failed_requests"].append(f"{r.url} :: {r.failure}"))
    return diag


def _leg(browser, run, *args) -> dict:
    """Run one benchmark leg. A failure is recorded honestly, never raised, so the
    other legs still produce numbers and the diagnostics reach the report."""
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    diag = _diagnostics(page)
    try:
        out = dict(run(page, *args))
    except Exception as exc:
        out = {"status": "FAIL", "error": f"{type(exc).__name__}: {str(exc).splitlines()[0][:200]}"}
    for key, hits in diag.items():
        if hits:
            out[key] = hits[:5]
    page.close()
    return out


def _bench_leaflet(page, base: str, query: str) -> dict:
    started = time.perf_counter()
    page.goto(f"{base}/ultra/classic{query}")
    page.wait_for_load_state("networkidle", timeout=120000)
    page.wait_for_timeout(1500)
    ready_s = time.perf_counter() - started
    heap = page.evaluate("performance.memory ? Math.round(performance.memory.usedJSHeapSize / 1048576) : null")
    return {**page.evaluate(_LEAFLET_BENCH), "ready_s": round(ready_s, 2), "js_heap_mb": heap}


def _write_json(path: Path, payload: dict) -> None:
    """Atomic write: a crashed run never leaves a half-written report behind."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8", newline="\n")
    tmp.replace(path)


def bench(base: str, gpu: bool) -> dict:
    from playwright.sync_api import sync_playwright
    report = {"measured_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
              "gpu_flag": gpu, "viewport": "1920x1080", "method":
              "6 s of continuous camera motion; frame intervals from requestAnimationFrame (first 10 dropped)",
              "bundle": _bundle(), "globe": {}, "leaflet_classic": {}}
    with sync_playwright() as p:
        browser = launch(p, gpu)
        for label, query in BENCH_SCENES:
            report["globe"][label] = _leg(browser, _bench_globe, base, query)
        for label, query in LEAFLET_SCENES:
            report["leaflet_classic"][label] = _leg(browser, _bench_leaflet, base, query)
        browser.close()
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("what", choices=("shots", "brand", "film", "bench"))
    ap.add_argument("--gpu", action="store_true", help="use the machine GPU instead of the software renderer")
    ap.add_argument("--out", default="", help="bench: also write the JSON report here")
    args = ap.parse_args()
    server, base = serve()
    try:
        if args.what == "bench":
            report = bench(base, args.gpu)
            print(json.dumps(report, indent=1))
            if args.out:
                _write_json(Path(args.out), report)
            failed = [f"{section}/{label}" for section in ("globe", "leaflet_classic")
                      for label, leg in report[section].items() if leg.get("status") != "OK"]
            if failed:
                print("FAILED LEGS: " + ", ".join(failed), file=sys.stderr)
                return 1
        else:
            for rel in {"shots": shots, "brand": brand, "film": film}[args.what](base, args.gpu):
                print("wrote", rel)
    finally:
        server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
