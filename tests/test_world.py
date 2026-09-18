"""World surface: geodesy truth, synthetic world scene, routes, UI contract."""

from __future__ import annotations

import json
import re
import sys
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from gods_eye.future import geo, world_scene as ws  # noqa: E402

UTC = timezone.utc
BRAND = "Tellurion"


# ---------------------------------------------------------------- geodesy ---

def test_land_mask_knows_real_geography():
    mask = geo.land_mask()
    assert mask is not None and len(mask) > 1000
    assert mask.is_land(51.507, -0.128)      # London
    assert mask.is_land(38.90, -77.04)       # Washington
    assert not mask.is_land(45.0, -30.0)     # North Atlantic
    assert not mask.is_land(-30.0, -120.0)   # South Pacific


def test_subsolar_point_matches_known_geometry():
    lat, lon = geo.subsolar_point(datetime(2026, 6, 21, 12, 0, tzinfo=UTC))
    assert abs(lat - 23.44) < 0.1 and abs(lon) < 1.5
    lat, _ = geo.subsolar_point(datetime(2026, 12, 21, 12, 0, tzinfo=UTC))
    assert abs(lat + 23.44) < 0.1
    lat, _ = geo.subsolar_point(datetime(2026, 3, 20, 14, 46, tzinfo=UTC))
    assert abs(lat) < 0.1
    with pytest.raises(ValueError):
        geo.subsolar_point(datetime(2026, 1, 1))


def test_night_polygon_covers_antisolar_point_only():
    when = ws.SCENE_EPOCH
    dec, lon = geo.subsolar_point(when)
    ring = geo.night_polygon(when)
    assert ring[0] == ring[-1]
    antisolar_lon = (lon + 360.0) % 360.0 - 180.0
    assert geo.ring_contains(ring, -dec, antisolar_lon)
    assert not geo.ring_contains(ring, dec, lon)


def test_great_circle_geometry():
    lhr, jfk = (51.470, -0.454), (40.641, -73.778)
    distance = geo.distance_km(lhr, jfk)
    assert 5500 < distance < 5600
    assert 51.5 < geo.interpolate(lhr, jfk, 0.5)[0] < 54.0  # bows north
    end = geo.destination(lhr, geo.bearing_deg(lhr, jfk), distance)
    assert geo.distance_km(end, jfk) < 25.0


# ------------------------------------------------------------ world scene ---

def test_world_scene_is_deterministic_synthetic_and_labelled():
    a, b = ws.scene(3), ws.scene(3)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert a["live"] is False and a["synthetic"] is True
    assert a["license"].startswith("CC0")
    assert a["world_time"] == "2026-09-15T16:43:00Z"
    assert ws.scene(99)["tick"] == ws.MAX_TICK and ws.scene("x")["tick"] == 0
    for key in ("aircraft", "vessels"):
        assert a[key], key
        for obj in a[key]:
            assert obj["synthetic"] is True and obj["id"].startswith("SYN-")
            assert obj["provenance"] and obj["rights"]
    assert ws.scene(4)["aircraft"] != ws.scene(5)["aircraft"]
    assert "not a forecast" in a["storm"]["label"]


def test_every_sea_lane_and_vessel_is_on_water():
    mask = geo.land_mask()
    for lane in ws.lanes():
        for lat, lon in lane["path"]:
            assert not mask.is_land(lat, lon), (lane["id"], lat, lon)
    for tick in (0, 6, 12):
        for v in ws.vessels(tick):
            assert not mask.is_land(v["lat"], v["lon"]), v["id"]


def test_regional_replay_respects_real_coastlines():
    from gods_eye.future import ultra_demo as u
    mask = geo.land_mask()
    for v in u.vessels():
        assert not mask.is_land(v["lat"], v["lon"]), v["id"]
    for obj in u.road_incidents() + u.cameras() + u.wildfires():
        assert mask.is_land(obj["lat"], obj["lon"]), obj["id"]


def test_satellite_track_is_orbit_consistent():
    sat = ws.satellite(ws.PASS_TICK)
    assert geo.distance_km(tuple(sat["position"]), ws.PASS_POINT) < 5.0
    assert max(abs(p[0]) for p in sat["track"]) <= 180.0 - 98.2 + 1e-6
    assert 97.0 < sat["orbit"]["period_min"] < 100.0
    steps = [geo.distance_km(tuple(sat["track"][i]), tuple(sat["track"][i + 1]))
             for i in range(len(sat["track"]) - 1)]
    assert all(380.0 < d < 440.0 for d in steps), (min(steps), max(steps))


def test_polygons_are_closed():
    w = ws.scene(0)
    for band in w["storm"]["bands"]:
        assert band["polygon"][0] == band["polygon"][-1]
    assert w["satellite"]["swath"][0] == w["satellite"]["swath"][-1]
    assert w["solar"]["night"][0] == w["solar"]["night"][-1]


# ------------------------------------------------------------ server/UI ---

@pytest.fixture(scope="module")
def base_url():
    from gods_eye import demo as _demo
    server = HTTPServer((_demo.HOST, 0), _demo._Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://{_demo.HOST}:{server.server_address[1]}"
    server.shutdown()


def _get(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return r.read(), r.headers.get("Content-Type", "")


def test_world_routes_and_static_assets(base_url):
    body, _ = _get(base_url + "/ultra")
    assert b"ULTRA" in body and BRAND.encode() in body
    classic, _ = _get(base_url + "/ultra/classic")
    assert b"leaflet" in classic.lower()
    world, ctype = _get(base_url + "/api/world?tick=2")
    assert "json" in ctype and json.loads(world)["tick"] == 2
    for path, expected in (("/vendor/maplibre/maplibre-gl.mjs", "javascript"),
                           ("/vendor/maplibre/maplibre-gl-worker.mjs", "javascript"),
                           ("/console/data/land-50m.json", "json"),
                           ("/vendor/fonts/inter-latin-wght-normal.woff2", "woff2"),
                           ("/console/brand/tellurion-mark.svg", "svg"),
                           ("/console/world/app.js", "javascript")):
        _, ctype = _get(base_url + path)
        assert expected in ctype, (path, ctype)
    for bad in ("/console/../pyproject.toml", "/vendor/..%2f..%2fpyproject.toml",
                "/console/world.html"):
        with pytest.raises(urllib.error.HTTPError):
            _get(base_url + bad)


def test_classic_fallback_resolves_its_assets_from_its_own_route(base_url):
    """Regression: relative asset paths under /ultra/classic resolved to
    /ultra/vendor/* and 404'd, so Leaflet never loaded and MAP stayed null."""
    page = (ROOT / "console" / "ultra.html").read_text(encoding="utf-8")
    for relative in ('href="./vendor/', 'src="./vendor/'):
        assert relative not in page, relative
    body, _ = _get(base_url + "/ultra/classic")
    for asset in ("/vendor/leaflet.js", "/vendor/leaflet.css"):
        assert asset in body.decode(), asset
        payload, _ = _get(base_url + asset)
        assert payload, asset


def test_gallery_binds_to_the_real_plugins_api(base_url):
    """The gallery may only render fields /api/plugins actually supplies."""
    page = (ROOT / "console" / "gallery.html").read_text(encoding="utf-8")
    data = json.loads(_get(base_url + "/api/plugins")[0])
    assert data["sources"], "no sources served"
    for field in ("source_id", "category", "realtime", "coverage",
                  "data_rights", "auth", "plugin_potential"):
        assert field in data["sources"][0], field
        assert f"s.{field}" in page, field
    assert "health" not in data["sources"][0]        # never invented in the UI
    assert "s.health" not in page and "s.status" not in page


def _ui_sources() -> str:
    return ((ROOT / "console" / "world.html").read_text(encoding="utf-8")
            + (ROOT / "console" / "world" / "app.js").read_text(encoding="utf-8"))


def test_world_ui_contract_truth_fallback_and_motion():
    src = _ui_sources()
    for needle in ("SYNTHETIC", "prefers-reduced-motion", "webgl2", "/ultra/classic",
                   "capture", "focus", "investigation", "palette", "globe",
                   "aria-live"):
        assert needle in src, needle
    for preset in ("world", "hero", "port", "airport", "earth"):
        assert re.search(rf"\b{preset}\s*:\s*\{{", src), preset
    external = re.findall(r"https?://[^\s\"'`)]+", src)
    assert external == [], external  # offline: no remote assets or calls


def test_public_brand_is_consistent():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert readme.startswith(f"# {BRAND}")
    assert "GOD'S EYE" not in "\n".join(readme.splitlines()[:25])
    for page in ("world.html", "ultra.html", "landing.html", "gallery.html", "demo.html"):
        html = (ROOT / "console" / page).read_text(encoding="utf-8")
        title = re.search(r"<title>(.*?)</title>", html, re.S).group(1)
        assert BRAND in title, (page, title)
    for asset in ("tellurion-mark.svg", "tellurion-wordmark.svg", "favicon.svg"):
        assert (ROOT / "console" / "brand" / asset).is_file(), asset


def test_ultra_default_is_tellurion_world_surface():
    """Release-defect regression: /ultra must serve the Tellurion globe
    surface (world.html), never the legacy GOD'S EYE UI. Fails on any
    candidate built without console/world.* (e.g. the superseded artifact
    built from the mixed development tree)."""
    for rel in ("console/world.html", "console/world/app.js",
                "console/vendor/maplibre/maplibre-gl.mjs",
                "console/vendor/maplibre/MAPLIBRE_LICENSE.txt"):
        assert (ROOT / rel).is_file(), rel
    from gods_eye import demo as _demo
    server = HTTPServer((_demo.HOST, 0), _demo._Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        base = f"http://{_demo.HOST}:{server.server_address[1]}"
        body, ctype = _get(base + "/ultra")
        assert "text/html" in ctype
        assert BRAND.encode() in body, "Tellurion brand missing on /ultra"
        assert b"GOD'S EYE ULTRA" not in body, \
            "legacy GOD'S EYE UI served as /ultra default"
        classic, _ = _get(base + "/ultra/classic")
        assert b"leaflet" in classic.lower(), \
            "classic fallback must serve the Leaflet view"
    finally:
        server.shutdown()
