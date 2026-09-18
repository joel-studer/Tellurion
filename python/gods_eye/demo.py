"""Tellurion one-command community demo.

`python -m gods_eye.demo` (or `tellurion demo`):
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
    ds = dd.demo_dataset()
    return {
        "demo": ds,
        "timeline": dd.timeline(),
        "community_mode": True,
        "network": "localhost-only; no external fetch",
        "credentials": "none required; none accepted",
        "safety": {"ALLOW_LIVE": False,
                   "mode": "local replay only; no live execution"},
    }


def health_payload() -> dict:
    from gods_eye.future import demo_dataset as dd
    return {"ok": True, "community_mode": True,
            "trading": "none: this build has no execution surface",
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


def _console_page(name: str, fallback: bytes) -> bytes:
    """A console HTML page from the checkout, or ``fallback`` when absent."""
    cand = repo_root() / "console" / name
    try:
        return cand.read_bytes() if cand.is_file() else fallback
    except OSError:
        return fallback


def _demo_html() -> bytes:
    cand = repo_root() / "console" / "demo.html"
    try:
        if cand.is_file():
            return cand.read_bytes()
    except OSError:
        pass
    return (b"<!doctype html><meta charset=utf-8><title>Tellurion demo</title>"
            b"<body><h1>Tellurion community demo</h1>"
            b"<p>demo.html not found; /api/demo serves the dataset.</p>")


def _landing_html() -> bytes:
    cand = repo_root() / "console" / "landing.html"
    try:
        if cand.is_file():
            return cand.read_bytes()
    except OSError:
        pass
    return b"<!doctype html><meta charset=utf-8><title>Tellurion</title>"


def _ultra_html() -> bytes:
    cand = repo_root() / "console" / "ultra.html"
    try:
        if cand.is_file():
            return cand.read_bytes()
    except OSError:
        pass
    return (b"<!doctype html><meta charset=utf-8><title>Tellurion ultra</title>"
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
            # Globe-first world surface; the page itself falls back to
            # /ultra/classic when WebGL2 is unavailable.
            self._send(_console_page("world.html", _ultra_html()),
                       "text/html; charset=utf-8")
        elif path == "/ultra/classic":
            self._send(_ultra_html(), "text/html; charset=utf-8")
        elif path == "/api/world":
            from gods_eye.future import world_scene as _ws
            tick = (query.get("tick") or ["0"])[0]
            self._send(json.dumps(_ws.scene(tick)).encode(), "application/json")
        elif path == "/ultra-gl":
            # Historical local prototype; not shipped. Serve it only when a
            # developer has the file, otherwise an honest 404 (never a 200
            # placeholder that looks like a working page).
            cand = repo_root() / "console" / "ultra-gl.html"
            try:
                body = cand.read_bytes() if cand.is_file() else None
            except OSError:
                body = None
            if body is None:
                self.send_response(404)
                self.end_headers()
            else:
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
        elif path == "/api/world/now":
            from gods_eye.future import world_now as _now
            force = (query.get("refresh") or [""])[0] == "1"
            serve_only = (query.get("norefresh") or [""])[0] == "1"
            try:
                payload = _now.get_now(refresh=not serve_only,
                                       force=force)
            except Exception as e:
                payload = {"mode": "now", "error": f"{type(e).__name__}: "
                                                  f"{str(e)[:200]}",
                           "real_data": False, "live": False,
                           "truth_label": "WORLD NOW (unavailable)",
                           "objects": {}, "counts": {"total_real": 0},
                           "links": [], "health": _now.source_health()}
            self._send(json.dumps(payload, indent=1).encode(),
                       "application/json")
        elif path == "/api/world/now/evidence":
            from gods_eye.future import world_now as _now
            key = (query.get("key") or [""])[0][:200]
            payload = _now.get_now(refresh=False)
            found = None
            for items in payload.get("objects", {}).values():
                for it in items:
                    if it.get("stable_key") == key or it.get("id") == key:
                        found = it
                        break
                if found:
                    break
            related = [l for l in payload.get("links", [])
                       if l.get("a") == (found or {}).get("stable_key")
                       or l.get("b") == (found or {}).get("stable_key")]
            self._send(json.dumps(
                {"evidence": found, "related": related,
                 "truth_label": "WORLD NOW (real public feeds)",
                 "live": False}, indent=1).encode(), "application/json")
        elif path == "/api/world/now/whatshere":
            from gods_eye.future import world_now as _now
            try:
                lat = float((query.get("lat") or ["48.2"])[0])
                lon = float((query.get("lon") or ["16.4"])[0])
                radius = float((query.get("radius_km") or
                                query.get("radius") or ["250"])[0])
            except ValueError:
                lat, lon, radius = 48.2, 16.4, 250.0
            payload = _now.get_now(refresh=False)
            here = _now.whats_here_now(lat, lon, radius,
                                       payload.get("objects", {}))
            # Movement V2: nearby live aircraft from the aviation
            # snapshot (same process memory; absent when never polled).
            try:
                from gods_eye.future import world_air as _air
                snap = _air.get_aviation(refresh=False)
                near = [o["icao24"] for o in snap.get("states", [])
                        if o.get("lat") is not None and _air._haversine_km(
                            lat, lon, o["lat"], o["lon"]) <= radius]
                here["movement"] = {
                    "aircraft_nearby": len(near),
                    "sample": near[:12],
                    "vessels": "NO LIVE SOURCE (synthetic replay only)",
                    "satellites": "NO LIVE SOURCE (synthetic replay only)",
                    "trails": "recorded past positions (RECORDED truth); "
                              "never a long-term archive"}
            except Exception:
                here["movement"] = {"aircraft_nearby": "UNKNOWN"}
            self._send(json.dumps(here, indent=1).encode(),
                       "application/json")
        elif path == "/api/world/now/region":
            from gods_eye.future import world_now as _now
            region = (query.get("region") or ["Austria"])[0][:120]
            payload = _now.get_now(refresh=False)
            reg = _now.region_now(region, payload.get("objects", {}))
            # Region intelligence: movement counts merged read-only.
            try:
                from gods_eye.future import world_air as _air
                snap = _air.get_aviation(refresh=False)
                c = snap.get("counts", {})
                center = reg.get("center") or {}
                radius = float(reg.get("radius_km") or 0.0)

                def _inside(o: dict) -> bool:
                    return (bool(center) and o.get("lat") is not None
                            and o.get("lon") is not None
                            and _air._haversine_km(center["lat"], center["lon"],
                                                   o["lat"], o["lon"]) <= radius)
                reg["movement"] = {
                    # Aircraft inside THIS region's radius, never the
                    # worldwide total presented as regional.
                    "aircraft_tracked": sum(1 for s in snap.get("states", []) if _inside(s)),
                    "radius_km": radius,
                    "aircraft_all_tiles": c.get("total", 0),
                    "important": sum(1 for f in snap.get("important", []) if _inside(f)),
                    "vessels": "NO LIVE SOURCE",
                    "satellites": "NO LIVE SOURCE",
                    "generated_at": snap.get("generated_at", "UNKNOWN")}
            except Exception:
                reg["movement"] = {"aircraft_tracked": "UNKNOWN"}
            try:
                reg["blind_spots"] = _now.real_blind_spots()
            except Exception:
                reg["blind_spots"] = []
            self._send(json.dumps(reg, indent=1).encode(),
                       "application/json")
        elif path == "/api/world/now/aviation":
            from gods_eye.future import world_air as _air
            include_mil = (query.get("mil") or [""])[0] == "1"
            serve_only = (query.get("norefresh") or [""])[0] == "1"
            viewport = None
            try:
                if "lat" in query and "lon" in query:
                    viewport = {"lat": float(query["lat"][0]),
                                "lon": float(query["lon"][0])}
            except (ValueError, TypeError, IndexError):
                viewport = None
            try:
                if serve_only:
                    payload = _air.get_aviation(refresh=False)
                else:
                    _air.refresh_aviation(include_mil=include_mil,
                                          viewport=viewport)
                    payload = _air.get_aviation(refresh=False)
                payload["source_rollup"] = _air.source_rollup()
            except Exception as e:
                payload = {"mode": "aviation", "error": f"{type(e).__name__}: "
                           f"{str(e)[:200]}", "real_data": False,
                           "live": False, "counts": {"total": 0},
                           "states": [], "important": []}
            if (query.get("light") or [""])[0] == "1":
                slim = {k: payload.get(k) for k in (
                    "mode", "dataset", "normalizer", "generated_at", "live",
                    "real_data", "truth_label", "license_note",
                    "attribution", "counts", "tracks_held", "capped",
                    "health", "coverage", "errors", "source_rollup")
                    if k in payload}
                slim["important"] = payload.get("important", [])
                slim["airport_events"] = payload.get("airport_events", [])
                # Map positions only: exactly what the globe draws, nothing
                # more (no registration, squawk or history). Keeps the light
                # payload small while every counted aircraft stays visible.
                fields = ("icao24", "lat", "lon", "track_deg", "callsign",
                          "type", "baro_alt_ft", "gs_kt")
                slim["positions"] = [
                    {k: s.get(k) for k in fields}
                    for s in payload.get("states", [])
                    if s.get("lat") is not None and s.get("lon") is not None]
                payload = slim
            self._send(json.dumps(payload, indent=1).encode(),
                       "application/json")
        elif path == "/api/world/now/important":
            from gods_eye.future import world_air as _air
            payload = _air.get_aviation(refresh=False)
            self._send(json.dumps(
                {"important": payload.get("important", []),
                 "airport_events": payload.get("airport_events", []),
                 "counts": payload.get("counts", {}),
                 "generated_at": payload.get("generated_at", "UNKNOWN"),
                 "truth_label": "IMPORTANT NOW (transparent rules only)",
                 "live": False}, indent=1).encode(), "application/json")
        elif path == "/api/world/now/important-v2":
            from gods_eye.future import world_air as _air
            try:
                payload = _air.important_v2()
            except Exception as e:
                payload = {"mode": "important-v2",
                           "error": f"{type(e).__name__}: "
                                    f"{str(e)[:200]}",
                           "items": [], "n": 0, "live": False}
            self._send(json.dumps(payload, indent=1).encode(),
                       "application/json")
        elif path == "/api/world/now/trail":
            from gods_eye.future import world_air as _air
            hx = (query.get("hex") or [""])[0][:6].lower()
            snap = _air.get_aviation(refresh=False)
            ac = next((o for o in snap.get("states", [])
                       if o.get("icao24") == hx), None)
            flagged = next((f for f in snap.get("flagged", [])
                            if f.get("icao24") == hx), None)
            self._send(json.dumps(
                {"icao24": hx, "aircraft": ac, "flags": flagged,
                 "trail": _air.get_trail(hx),
                 "truth_label": "short rolling trail (memory only)",
                 "live": False}, indent=1).encode(), "application/json")
        elif path == "/api/world/changes":
            from gods_eye.future import world_change as _chg
            since = (query.get("since") or [""])[0][:64] or None
            serve_only = (query.get("norefresh") or [""])[0] == "1"
            try:
                limit = max(1, min(500, int(
                    (query.get("limit") or ["100"])[0])))
            except ValueError:
                limit = 100
            try:
                payload = _chg.get_changes(refresh=not serve_only,
                                           since=since, limit=limit)
            except Exception as e:
                payload = {"mode": "changes",
                           "error": f"{type(e).__name__}: "
                                    f"{str(e)[:200]}",
                           "real_data": False, "live": False,
                           "truth_label": "WORLD CHANGE (unavailable)",
                           "changes": [], "cursor": "", "counts": {},
                           "sources": {}}
            self._send(json.dumps(payload, indent=1).encode(),
                       "application/json")
        elif path.startswith("/api/world/changes/") and path.endswith(
                "/imagery"):
            from urllib.parse import unquote
            from gods_eye.future import world_imagery as _img
            cid = unquote(path[len("/api/world/changes/"):-len("/imagery")],
                          errors="replace")[:200]
            change = _img.load_change(cid)
            if change is None:
                payload = {"change_id": cid,
                           "status": "NO_SUITABLE_OBSERVATION",
                           "before": None, "after": None,
                           "generated_at": _img.utcnow(),
                           "truth_label": _img.TRUTH_LABEL,
                           "live": False, "real_data": True,
                           "note": f"unknown change id: {cid}"}
            else:
                try:
                    payload = _img.get_imagery(change)
                except Exception as e:
                    payload = {"change_id": cid,
                               "status": "SOURCE_UNAVAILABLE",
                               "before": None, "after": None,
                               "generated_at": _img.utcnow(),
                               "truth_label": _img.TRUTH_LABEL,
                               "live": False, "real_data": True,
                               "error": f"{type(e).__name__}: "
                                        f"{str(e)[:200]}"}
            self._send(json.dumps(payload, indent=1).encode(),
                       "application/json")
        elif path.startswith("/api/world/imagery/thumb/"):
            from gods_eye.future import world_imagery as _img
            key = path[len("/api/world/imagery/thumb/"):]
            if key.endswith(".jpg"):
                key = key[:-4]
            blob = _img.read_thumb(key) if len(key) == 16 and key.isalnum() \
                else None
            if blob is None:
                self._send(json.dumps(
                    {"error": "unknown thumbnail",
                     "truth_label": _img.TRUTH_LABEL}).encode(),
                    "application/json")
            else:
                self._send(blob, "image/jpeg")
        elif path == "/api/world/imagery/status":
            from gods_eye.future import world_earth as _earth
            try:
                lat = float((query.get("lat") or [""])[0])
            except ValueError:
                lat = None
            try:
                lon = float((query.get("lon") or [""])[0])
            except ValueError:
                lon = None
            try:
                payload = _earth.get_status(lat=lat, lon=lon)
            except Exception as e:
                payload = {"generated_at": _earth.utcnow(),
                           "live": False, "real_data": False,
                           "truth_label": "LIVE EARTH (unavailable)",
                           "error": f"{type(e).__name__}: "
                                    f"{str(e)[:200]}",
                           "layers": [], "selected": None,
                           "current_source_by_region": [],
                           "freshness_summary": {}}
            self._send(json.dumps(payload, indent=1).encode(),
                       "application/json")
        elif path == "/api/world/presets":
            self._send(json.dumps(
                {"presets": [
                    {"id": "world-now", "label": "WORLD NOW",
                     "view": "world", "density": "standard",
                     "layers": ["aircraft", "vessels", "weather",
                                "seismic", "disasters"]},
                    {"id": "aviation", "label": "GLOBAL AVIATION",
                     "view": "world", "density": "dense",
                     "layers": ["aircraft", "airports"]},
                    {"id": "aviation-live", "label": "GLOBAL AVIATION (LIVE)",
                     "view": "world", "mode": "now", "sky": "aviation"},
                    {"id": "important-now", "label": "IMPORTANT NOW",
                     "view": "world", "mode": "now", "sky": "important"},
                    {"id": "movement-live", "label": "LIVE MOVEMENT",
                     "view": "world", "mode": "now", "sky": "movement"},
                    {"id": "shipping", "label": "GLOBAL SHIPPING",
                     "view": "world", "density": "dense",
                     "layers": ["vessels", "ports"]},
                    {"id": "earth", "label": "EARTH LIVE (replay)",
                     "view": "world", "density": "standard",
                     "layers": ["seismic", "wildfire", "volcanoes",
                                "disasters"]},
                    {"id": "severe", "label": "SEVERE WEATHER",
                     "view": "world", "density": "standard",
                     "layers": ["weather", "disasters"]},
                    {"id": "disaster", "label": "DISASTER WATCH",
                     "view": "world", "density": "standard",
                     "layers": ["disasters", "seismic", "wildfire",
                                "notices"]},
                    {"id": "satellites", "label": "SATELLITES",
                     "view": "world", "density": "standard",
                     "layers": ["satellites"]},
                    {"id": "austria", "label": "AUSTRIA",
                     "view": "region", "region": "Austria"},
                    {"id": "europe", "label": "EUROPE",
                     "view": "region", "region": "Germany"},
                    {"id": "atlantic", "label": "NORTH ATLANTIC",
                     "view": "world", "density": "standard",
                     "layers": ["vessels", "aircraft", "weather"]},
                ], "truth_mode": "SYNTHETIC"}, indent=1).encode(),
                "application/json")
        elif path.startswith("/vendor/") or path.startswith("/console/"):
            self._serve_static(path)
        else:
            self.send_response(404)
            self.end_headers()

    def _serve_static(self, path: str) -> None:
        """Serve vendored console assets (localhost only, traversal-safe).

        Only static asset types under console/ (scripts, styles, images,
        fonts, data). No
        dotfiles, no directory listing, no Range games.
        """
        from urllib.parse import unquote
        ctype = ((".js", "application/javascript"),
                 (".mjs", "application/javascript"), (".css", "text/css"),
                 (".png", "image/png"), (".svg", "image/svg+xml"),
                 (".json", "application/json"), (".woff2", "font/woff2"),
                 (".txt", "text/plain"))
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
        binary = suffix in (".png", ".woff2")
        self._send(body, mime + ("" if binary else "; charset=utf-8"))


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
            f"Stop the other program, or run: tellurion demo --port "
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
        print("TELLURION ULTRA")
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
        print("Tellurion community demo")
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
