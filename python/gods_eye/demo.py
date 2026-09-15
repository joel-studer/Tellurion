"""GOD'S EYE one-command community demo (V15/V16).

`python -m gods_eye.demo` (or `godseye demo`):
  - starts localhost-only (127.0.0.1, no 0.0.0.0 — never LAN)
  - loads safe synthetic replay data (no keys, no private alpha, no creds)
  - serves the demo console + JSON API
  - requires no network dependency (all bundled; same-origin fetch only)

Endpoints:
  /            -> demo console (bundled HTML; ?demo=hero for screenshot state)
  /api/demo    -> full synthetic dataset
  /api/health  -> ALLOW_LIVE=false, community_mode, provenance

Port behaviour (V16): the requested port is tried first. If occupied,
the server automatically selects the next available localhost port and
prints the exact URL (never binds LAN accidentally). `--strict-port`
fails closed with a clear message + alternative instead.

Hero mode (V17): `--hero` pins the deterministic screenshot state
(frozen `community-demo-v1` event, fixed camera/selection/timeline via
`?demo=hero`) so screenshots and video frames always look identical.
"""

from __future__ import annotations

import functools  # noqa: F401 (kept for backward-compatible import surface)
import http.server
import json
import socket
import webbrowser
from pathlib import Path
from typing import Any, Tuple

HOST = "127.0.0.1"
DEFAULT_PORT = 8765


class PortOccupied(Exception):
    """Raised in --strict-port mode when the requested port is taken."""


def demo_payload() -> dict:
    from gods_eye.future import demo_dataset as dd
    from gods_eye.future import venue_registry as vr
    from gods_eye.future import exec_safety as es
    ds = dd.demo_dataset()
    return {
        "demo": ds,
        "timeline": dd.timeline(),
        "venues": vr.summary(),
        "safety": es.LiveExecutionGuard().describe(),
        "community_mode": True,
        "network": "localhost-only; no external fetch",
        "credentials": "none required; none accepted",
    }


def health_payload() -> dict:
    from gods_eye.future import exec_safety as es
    from gods_eye.future import demo_dataset as dd
    return {"ok": True, "community_mode": True,
            "allow_live": es.ALLOW_LIVE,
            "provenance": dd.PROVENANCE,
            "rights": dd.RIGHTS,
            "network": "localhost-only"}


def ultra_payload(tick: int = 0, scene: str = "") -> dict:
    """Ultra world payload (V18, synthetic replay, localhost only)."""
    from gods_eye.future import ultra_demo as _u
    try:
        t = max(0, min(12, int(tick)))
    except (TypeError, ValueError):
        t = 0
    if scene == "dense":
        return _u.ultra_payload(tick=t, n_ac=500, n_vs=300)
    if scene in ("load5k", "load10k"):
        n = 2500 if scene == "load5k" else 5000
        return _u.ultra_payload(tick=t, n_ac=n, n_vs=n * 3 // 5)
    return _u.ultra_payload(tick=t)


def repo_root() -> Path:
    """Portable repo-root resolution (pathlib only; no drive assumptions).

    Works for a checkout (python/gods_eye/demo.py -> root) and for an
    installed package (falls back to CWD).
    """
    here = Path(__file__).resolve()
    for parent in (here, *here.parents):
        if (parent / "console" / "demo.html").is_file():
            return parent
        if parent.name == "gods_eye" and (parent.parent / "console").is_dir():
            maybe = parent.parent
            if (maybe / "console" / "demo.html").is_file():
                return maybe
    return Path.cwd()


def _demo_html() -> bytes:
    cand = repo_root() / "console" / "demo.html"
    try:
        if cand.is_file():
            return cand.read_bytes()
    except OSError:
        pass
    return (b"<!doctype html><meta charset=utf-8><title>GOD'S EYE demo</title>"
            b"<body><h1>GOD'S EYE community demo</h1>"
            b"<p>demo.html not found; /api/demo serves the dataset.</p>")


def _landing_html() -> bytes:
    cand = repo_root() / "console" / "landing.html"
    try:
        if cand.is_file():
            return cand.read_bytes()
    except OSError:
        pass
    return b"<!doctype html><meta charset=utf-8><title>GOD'S EYE</title>"


def _ultra_html() -> bytes:
    cand = repo_root() / "console" / "ultra.html"
    try:
        if cand.is_file():
            return cand.read_bytes()
    except OSError:
        pass
    return (b"<!doctype html><meta charset=utf-8><title>GOD'S EYE ultra</title>"
            b"<body><h1>Ultra view missing</h1>"
            b"<p>ultra.html not found; /api/ultra serves the dataset.</p>")


class _Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a: Any) -> None:  # quieter than default
        pass

    def _send(self, body: bytes, ctype: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        from urllib.parse import parse_qs, urlparse
        path = self.path.split("?", 1)[0]
        query = parse_qs(urlparse(self.path).query)
        if path in ("/", "/demo"):
            self._send(_demo_html(), "text/html; charset=utf-8")
        elif path == "/ultra":
            self._send(_ultra_html(), "text/html; charset=utf-8")
        elif path == "/ultra-gl":
            cand = repo_root() / "console" / "ultra-gl.html"
            try:
                body = (cand.read_bytes() if cand.is_file()
                        else b"gl prototype missing")
            except OSError:
                body = b"gl prototype missing"
            self._send(body, "text/html; charset=utf-8")
        elif path == "/gallery":
            cand = repo_root() / "console" / "gallery.html"
            try:
                body = cand.read_bytes() if cand.is_file() else b"gallery missing"
            except OSError:
                body = b"gallery missing"
            self._send(body, "text/html; charset=utf-8")
        elif path in ("/landing", "/about"):
            self._send(_landing_html(), "text/html; charset=utf-8")
        elif path == "/api/demo":
            self._send(json.dumps(demo_payload(), indent=1).encode(),
                       "application/json")
        elif path == "/api/ultra":
            tick = (query.get("tick") or ["0"])[0]
            scene = (query.get("scene") or [""])[0]
            if scene not in ("", "dense", "load5k", "load10k"):
                scene = ""
            self._send(json.dumps(ultra_payload(tick, scene),
                                  indent=1).encode(),
                       "application/json")
        elif path == "/api/ultra/dense":
            from gods_eye.future import ultra_demo as _u
            self._send(json.dumps(
                {"counts": _u.density_scene()["counts"],
                 "dataset_id": _u.DATASET_ID, "license": _u.LICENSE,
                 "community_mode": True, "live": False},
                indent=1).encode(), "application/json")
        elif path == "/api/ultra/evidence":
            from gods_eye.future import ultra_demo as _u
            obj_id = (query.get("id") or [""])[0]
            kind = (query.get("kind") or ["object"])[0]
            self._send(json.dumps(
                _u.evidence_for(kind, obj_id), indent=1).encode(),
                "application/json")
        elif path == "/api/ultra/context":
            from gods_eye.future import ultra_demo as _u
            try:
                lat = float((query.get("lat") or ["51.42"])[0])
                lon = float((query.get("lon") or ["-3.18"])[0])
            except ValueError:
                lat, lon = 51.42, -3.18
            self._send(json.dumps(
                _u.context_for(lat, lon), indent=1).encode(),
                "application/json")
        elif path == "/api/plugins":
            from gods_eye.future import sensor_sources as _ss
            self._send(json.dumps(
                {"sources": [s.__dict__ for s in _ss.list_sources()],
                 "ranking": _ss.scout_rank(),
                 "summary": _ss.summary(),
                 "community_mode": True, "live": False},
                indent=1).encode(), "application/json")
        elif path == "/api/health":
            self._send(json.dumps(health_payload(), indent=1).encode(),
                       "application/json")
        elif path.startswith("/vendor/") or path.startswith("/console/"):
            self._serve_static(path)
        else:
            self.send_response(404)
            self.end_headers()

    def _serve_static(self, path: str) -> None:
        """Serve vendored console assets (localhost only, traversal-safe).

        Only .js/.css/.png under console/ (the vendored UI libs). No
        dotfiles, no directory listing, no Range games.
        """
        from urllib.parse import unquote
        ctype = (".js", "application/javascript"), (".css", "text/css"), (
            ".png", "image/png")
        name = unquote(path.split("?", 1)[0])
        if "/." in name.replace("\\", "/") or ".." in name:
            self.send_response(404)
            self.end_headers()
            return
        sub = name[len("/vendor/"):] if name.startswith("/vendor/") else \
            name[len("/console/"):]
        cand = (repo_root() / "console" / "vendor" / sub
                if name.startswith("/vendor/")
                else repo_root() / "console" / sub)
        try:
            resolved = cand.resolve()
            if repo_root().resolve() not in resolved.parents:
                raise OSError("outside root")
            suffix = resolved.suffix.lower()
            mime = dict(ctype).get(suffix, "")
            if not mime or not resolved.is_file():
                raise OSError("not a servable asset")
            body = resolved.read_bytes()
        except OSError:
            self.send_response(404)
            self.end_headers()
            return
        self._send(body, mime + ("; charset=utf-8" if suffix != ".png"
                                 else ""))


def port_available(port: int, host: str = HOST) -> bool:
    """True if nothing serves `port` on localhost (socket closed after)."""
    # Connect probe first: a listening server means occupied even where
    # a REUSEADDR bind would still succeed (Windows semantics).
    try:
        with socket.create_connection((host, port), timeout=0.25):
            return False
    except OSError:
        pass
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def select_port(requested: int, host: str = HOST,
                strict: bool = False) -> Tuple[int, bool]:
    """Return (port_to_use, fell_back). Fail closed in strict mode."""
    if not (1 <= requested <= 65535):
        raise ValueError(
            f"invalid port {requested}: use 1-65535 "
            f"(e.g. --port {DEFAULT_PORT})")
    if port_available(requested, host):
        return requested, False
    if strict:
        raise PortOccupied(
            f"port {requested} on {host} is already in use. "
            f"Stop the other program, or run: godseye demo --port "
            f"{requested + 1} (or omit --strict-port to auto-select).")
    probe = requested + 1
    while probe <= 65535 and not port_available(probe, host):
        probe += 1
    if probe > 65535:
        raise PortOccupied(
            f"no free localhost port found from {requested} upward.")
    return probe, True


def run_demo(port: int = DEFAULT_PORT, open_browser: bool = False,
             strict_port: bool = False, hero: bool = False,
             ultra: bool = False) -> int:
    """Start the demo server. Returns the bound port. Never binds LAN."""
    from gods_eye.future import demo_dataset as dd
    from gods_eye.future import sensor_sources as _ss
    from gods_eye.future import ultra_demo as _u
    use_port, fell_back = select_port(port, HOST, strict_port)
    if fell_back:
        print(f"port {port} on {HOST} is occupied — using {use_port} instead "
              f"(localhost-only; pass --strict-port to fail instead).")
    if ultra:
        suffix = "?demo=hero" if hero else ""
        url = f"http://{HOST}:{use_port}/ultra{suffix}"
        n_layers = len(_u.ultra_payload(tick=0))
        print("GOD'S EYE ULTRA")
        print("Mode: LOCAL / REPLAY"
              f"{' / HERO (deterministic)' if hero else ''}")
        print("Live execution: DISABLED")
        print(f"Data: SYNTHETIC + REDISTRIBUTABLE DEMO "
              f"({_u.DATASET_ID}, {_u.LICENSE})")
        print(f"Sources: {_ss.summary()['n_sources']} "
              f"(registry; demo runs on synthetic replay)")
        print(f"Layers: {n_layers} payload sections")
        print(f"Open: {url}")
    else:
        suffix = "?demo=hero" if hero else ""
        url = f"http://{HOST}:{use_port}/{suffix}"
        print("GOD'S EYE Community Demo")
        print(f"Status: LOCAL / REPLAY"
              f"{' / HERO (deterministic)' if hero else ''}")
        print("Live execution: DISABLED")
        print(f"Dataset: {dd.DATASET_ID} ({dd.LICENSE})")
        print(f"Open: {url}")
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            print("could not open a browser automatically; "
                  f"visit {url} manually.")
    print("(localhost-only, no keys, Ctrl-C to stop)")
    with http.server.HTTPServer((HOST, use_port), _Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\ndemo stopped.")
    return use_port


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(prog="python -m gods_eye.demo")
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--no-browser", action="store_true")
    p.add_argument("--strict-port", action="store_true",
                   help="fail with a clear message if --port is occupied")
    p.add_argument("--hero", action="store_true",
                   help="deterministic hero state (?demo=hero) for "
                   "screenshots/video")
    p.add_argument("--ultra", action="store_true",
                   help="open the Ultra world surface (/ultra)")
    a = p.parse_args()
    try:
        run_demo(port=a.port, open_browser=not a.no_browser,
                 strict_port=a.strict_port, hero=a.hero, ultra=a.ultra)
    except PortOccupied as e:
        print(f"error: {e}")
        raise SystemExit(2) from None
    except ValueError as e:
        print(f"error: {e}")
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
