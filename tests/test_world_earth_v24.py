"""V2.2 LIVE EARTH tests (offline only — capabilities are fixtures).

Covers: status API schema / source selection / all five freshness
classes / rights propagation + fail-closed / provider fallback /
cached true age / replay isolation / overlays + pins + Sentinel
evidence untouched / attribution / source drawer contract /
no-synthetic / leak gate / no trading fields / route contract /
browser visual state / provider health.
"""

from __future__ import annotations

import json
import sys
import threading
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from gods_eye.future import world_earth as earth  # noqa: E402

UTC = timezone.utc
NOW = datetime(2026, 9, 18, 9, 0, tzinfo=UTC)
NOW_ISO = NOW.replace(microsecond=0).isoformat()


def _iso(dt):
    return dt.replace(microsecond=0).isoformat()


CAPS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Capabilities xmlns="http://www.opengis.net/wmts/1.0">
<Contents>
<Layer><ows:Title xmlns:ows="http://www.opengis.net/ows/1.1">VIIRS</ows:Title>
<ows:Identifier xmlns:ows="http://www.opengis.net/ows/1.1">VIIRS_SNPP_CorrectedReflectance_TrueColor</ows:Identifier>
<Dimension><ows:Identifier xmlns:ows="http://www.opengis.net/ows/1.1">Time</ows:Identifier><ows:UOM>ISO8601</ows:UOM><Default>2026-09-17T00:00:00Z</Default></Dimension>
<TileMatrixSetLink><TileMatrixSet>GoogleMapsCompatible_Level9</TileMatrixSet></TileMatrixSetLink>
</Layer>
<Layer><ows:Title xmlns:ows="http://www.opengis.net/ows/1.1">MODIS</ows:Title>
<ows:Identifier xmlns:ows="http://www.opengis.net/ows/1.1">MODIS_Terra_CorrectedReflectance_TrueColor</ows:Identifier>
<Dimension><ows:Identifier xmlns:ows="http://www.opengis.net/ows/1.1">Time</ows:Identifier><ows:UOM>ISO8601</ows:UOM><Default>2026-09-16T00:00:00Z</Default></Dimension>
<TileMatrixSetLink><TileMatrixSet>GoogleMapsCompatible_Level9</TileMatrixSet></TileMatrixSetLink>
</Layer>
<Layer><ows:Title xmlns:ows="http://www.opengis.net/ows/1.1">East</ows:Title>
<ows:Identifier xmlns:ows="http://www.opengis.net/ows/1.1">GOES-East_ABI_GeoColor</ows:Identifier>
<Dimension><ows:Identifier xmlns:ows="http://www.opengis.net/ows/1.1">Time</ows:Identifier><ows:UOM>ISO8601</ows:UOM><Default>2026-09-18T08:20:00Z</Default></Dimension>
<TileMatrixSetLink><TileMatrixSet>GoogleMapsCompatible_Level7</TileMatrixSet></TileMatrixSetLink>
</Layer>
<Layer><ows:Title xmlns:ows="http://www.opengis.net/ows/1.1">West</ows:Title>
<ows:Identifier xmlns:ows="http://www.opengis.net/ows/1.1">GOES-West_ABI_GeoColor</ows:Identifier>
<Dimension><ows:Identifier xmlns:ows="http://www.opengis.net/ows/1.1">Time</ows:Identifier><ows:UOM>ISO8601</ows:UOM><Default>2026-09-18T08:20:00Z</Default></Dimension>
<TileMatrixSetLink><TileMatrixSet>GoogleMapsCompatible_Level7</TileMatrixSet></TileMatrixSetLink>
</Layer>
</Contents>
</Capabilities>
"""


class FakeResp:
    def __init__(self, body):
        self._b = body if isinstance(body, bytes) else body.encode()

    def read(self, n=-1):
        out, self._b = self._b, b""
        return out


@pytest.fixture()
def iso_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(earth, "_runtime_dir", lambda: tmp_path)
    yield tmp_path


def _opener(body=CAPS_XML.encode(), calls=None):
    def opener(req, timeout=None):
        if calls is not None:
            calls.append(req.full_url
                         if hasattr(req, "full_url") else str(req))
        return FakeResp(body)
    return opener


def _status(**kw):
    return earth.get_status(opener=kw.pop("opener", _opener()),
                            now=kw.pop("now", NOW_ISO), **kw)


def _by_id(payload):
    return {item["layer"]: item for item in payload["layers"]}


# -------------------------------------------------------- schema ---


def test_status_api_schema(iso_dirs):
    payload = _status(lat=40.0, lon=-98.0)
    assert set(payload) >= {"generated_at", "live", "real_data",
                            "truth_label", "layers",
                            "current_source_by_region", "selected",
                            "freshness_summary"}
    assert payload["live"] is False and payload["real_data"] is True
    assert len(payload["layers"]) == 4
    for item in payload["layers"]:
        assert set(item) >= {"source", "dataset", "captured_at",
                             "age_seconds", "freshness_class",
                             "truth_mode", "source_url", "attribution",
                             "rights_status", "resolution_m",
                             "tile_url", "coverage_quality",
                             "cloud_cover_pct_or_unknown"}
        assert item["source"] == "NASA GIBS"
        assert item["truth_mode"] == "OBSERVED"


# ------------------------------------------------------ selection ---


def test_source_selection_logic(iso_dirs):
    payload = _status()
    by_id = _by_id(payload)
    assert earth.select_layer(-75.0, by_id) == "GOES-East_ABI_GeoColor"
    assert earth.select_layer(-122.0, by_id) == "GOES-West_ABI_GeoColor"
    # Asia-Pacific has no qualified geostationary layer: VIIRS daily.
    assert earth.select_layer(139.0, by_id) == \
        "VIIRS_SNPP_CorrectedReflectance_TrueColor"
    assert earth.select_layer(10.0, by_id) == \
        "VIIRS_SNPP_CorrectedReflectance_TrueColor"
    assert earth.select_layer(-150.0, by_id) == "GOES-West_ABI_GeoColor"
    assert earth.select_layer("bogus", by_id) is None
    # Stale geo falls through to daily polar (never fake-fresh geo).
    stale = dict(by_id)
    stale["GOES-East_ABI_GeoColor"] = dict(
        stale["GOES-East_ABI_GeoColor"], status="AVAILABLE",
        freshness_class="STALE")
    assert earth.select_layer(-75.0, stale) == \
        "VIIRS_SNPP_CorrectedReflectance_TrueColor"


def test_no_himawari_layer_ships(iso_dirs):
    # Himawari Band3 tiles verified striped/unusable live, and GIBS
    # carries no Himawari true-color: the layer must not exist in
    # the registry, and the Pacific selects VIIRS daily.
    assert all("Himawari" not in layer["id"] for layer in earth.LAYERS)
    payload = _status()
    assert earth.select_layer(150.0, _by_id(payload)) == \
        "VIIRS_SNPP_CorrectedReflectance_TrueColor"


# ------------------------------------------------------ freshness ---


def test_freshness_thresholds():
    assert earth.freshness_class(0.5) == "VERY_FRESH"
    assert earth.freshness_class(0.99) == "VERY_FRESH"
    assert earth.freshness_class(1.0) == "FRESH"
    assert earth.freshness_class(5.9) == "FRESH"
    assert earth.freshness_class(6.0) == "AGING"
    assert earth.freshness_class(47.9) == "AGING"
    assert earth.freshness_class(48.0) == "STALE"
    assert earth.freshness_class(13 * 24.0) == "STALE"
    assert earth.freshness_class(14 * 24.0) == "NO_COVERAGE"
    assert earth.freshness_class(None) == "NO_COVERAGE"


def test_very_fresh_classification(iso_dirs):
    payload = _status()
    east = _by_id(payload)["GOES-East_ABI_GeoColor"]
    assert east["freshness_class"] == "VERY_FRESH"
    assert east["captured_at"] == "2026-09-18T08:20:00Z"
    assert east["age_seconds"] == pytest.approx(40 * 60, abs=120)


def test_fresh_and_aging_and_stale(iso_dirs):
    assert earth.freshness_class(3.0) == "FRESH"
    assert earth.freshness_class(30.0) == "AGING"
    assert earth.freshness_class(9 * 24.0) == "STALE"
    payload = _status()
    viirs = _by_id(payload)["VIIRS_SNPP_CorrectedReflectance_TrueColor"]
    assert viirs["freshness_class"] == "AGING"  # ~33 h old
    assert viirs["tile_url"].endswith(".jpg")
    assert "2026-09-17" in viirs["tile_url"]  # date-only axis


def test_no_coverage(iso_dirs):
    assert earth.freshness_class(30 * 24.0) == "NO_COVERAGE"
    rec = earth.layer_status(
        {"id": "X", "dataset": "d", "region": "global",
         "resolution_m": 1, "subdaily": False}, {}, NOW_ISO)
    assert rec["freshness_class"] == "NO_COVERAGE"
    assert rec["rights_status"] == "RIGHTS_UNVERIFIED"
    assert rec["tile_url"] == ""


# --------------------------------------------------------- rights ---


def test_rights_propagation(iso_dirs):
    payload = _status()
    for item in payload["layers"]:
        assert item["rights_status"] == "ATTRIBUTION_REQUIRED"
        assert set(item["rights"]) == {
            "public_display", "redistribution", "commercial_use",
            "broadcast_use", "cache", "retention", "attribution",
        }
        assert "Global Imagery Browse Services" in \
            item["rights"]["attribution"]
        assert "NASA GIBS" in item["attribution"]


def test_missing_rights_fail_closed():
    rec = earth.layer_status(
        {"id": "X", "dataset": "d", "region": "global",
         "resolution_m": 1, "subdaily": False}, {}, NOW_ISO)
    assert rec["tile_url"] == ""
    assert rec["rights_status"] == "RIGHTS_UNVERIFIED"


# ------------------------------------------------------- provider ---


def test_provider_unavailable_fallback(iso_dirs):
    def boom(req, timeout=None):
        raise TimeoutError("gibs down")

    first = earth.get_status(opener=boom, now=NOW_ISO)
    assert first["capabilities"] != "ok"
    assert first["selected"] is None
    assert all(item["freshness_class"] == "NO_COVERAGE"
               for item in first["layers"])
    assert "unreachable" in first["capabilities"]
    # ... but a cached capabilities file still serves true ages.
    second = earth.get_status(
        opener=_opener(), now=_iso(NOW + timedelta(hours=1)))
    assert second["selected"] is not None


def test_cached_imagery_retains_true_age(iso_dirs):
    first = _status()
    later = earth.get_status(
        opener=_opener(), now=_iso(NOW + timedelta(hours=5)))
    a = _by_id(first)["GOES-East_ABI_GeoColor"]["age_seconds"]
    b = _by_id(later)["GOES-East_ABI_GeoColor"]["age_seconds"]
    assert b - a == pytest.approx(5 * 3600, abs=120)
    assert _by_id(later)["GOES-East_ABI_GeoColor"]["captured_at"] == \
        "2026-09-18T08:20:00Z"


def test_provider_health_behavior(iso_dirs):
    meta = earth.load_meta()
    assert meta == {"health": {}}
    earth.get_status(opener=_opener(), now=NOW_ISO)
    meta = earth.load_meta()
    assert meta["health"]["gibs.caps"]["state"] == "ONLINE"

    def boom(req, timeout=None):
        raise TimeoutError("x")

    # No cached file: every attempt hits the (dead) provider.
    earth._caps_path().unlink()
    for _ in range(3):
        earth.get_status(opener=boom, now=NOW_ISO)
    meta = earth.load_meta()
    assert meta["health"]["gibs.caps"]["state"] == "SOURCE_UNAVAILABLE"
    # ... and while unavailable, status short-circuits honestly.
    out = earth.get_status(opener=boom, now=NOW_ISO)
    assert out["capabilities"] != "ok"
    assert out["selected"] is None


# ------------------------------------------- isolation & purity ---


def test_replay_loads_no_live_earth():
    from gods_eye import demo as _demo
    server = HTTPServer((_demo.HOST, 0), _demo._Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        base = f"http://{_demo.HOST}:{server.server_address[1]}"
        with urllib.request.urlopen(base + "/api/ultra?tick=0",
                                    timeout=60) as r:
            blob = r.read().decode("utf-8")
    finally:
        server.shutdown()
    assert "gibs.earthdata.nasa.gov" not in blob
    src = (ROOT / "console" / "world" / "app.js").read_text(encoding="utf-8")
    # Full offline guarantee: NO remote tile endpoint literal anywhere
    # in UI sources. Tile URLs arrive exclusively from our own backend
    # (/api/world/imagery/status) with verified dates and rights.
    assert "gibs.earthdata.nasa.gov" not in src
    assert "earthdata.nasa.gov/wmts" not in src
    # ... while the NOW-guarded live-earth path itself exists.
    start = src.index("function loadLiveEarth")
    end = src.index("function wireLiveEarth")
    end = src.index("\nfunction ", end + 10)
    section = src[start:end]
    assert "MODE_NOW" in section
    assert "/api/world/imagery/status" in section


def test_overlays_pins_sentinel_unaffected(iso_dirs):
    payload = _status()
    blob = json.dumps(payload).lower()
    assert "synthetic" not in blob
    for token in ("ultra", "replay", "important-v2", "trail"):
        assert token not in blob
    assert "sentinel" not in blob and "change_detected" not in blob


def test_attribution_rendered():
    src = (ROOT / "console" / "world" / "app.js").read_text(encoding="utf-8")
    assert "liveEarth" in src or "live-earth" in src
    low = src.lower()
    assert "nasa gibs" in low
    assert "freshness" in low


def test_source_metadata_drawer():
    src = (ROOT / "console" / "world" / "app.js").read_text(encoding="utf-8")
    for needle in ("earthInfo", "captured", "age_seconds", "rights_status"):
        assert needle in src, needle


def test_no_synthetic_fallback(iso_dirs):
    payload = _status()
    blob = json.dumps(payload).lower()
    assert "synthetic" not in blob
    assert payload["real_data"] is True and payload["live"] is False
    for item in payload["layers"]:
        assert "synthetic" not in json.dumps(item).lower()


# ------------------------------------------------ boundaries ---


def test_public_leak_gate():
    import re
    for rel in ("python/gods_eye/future/world_earth.py",
                "tests/test_world_earth_v24.py"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        from gods_eye.future import world_change as chg
        word = lambda tok: re.search(r"(?<![a-z_])" + re.escape(tok)
                                     + r"(?![a-z_])", text.lower())
        hits = sorted({t for t in chg.FORBIDDEN_FIELDS if word(t)})
        assert not hits, (rel, hits)
        from gods_eye.future import boundary
        assert boundary.secret_hits_text(text) == [], rel
        kinds = {k for k, rx in boundary._LOCAL_RES if rx.search(text)}
        assert kinds == set(), (rel, kinds)


def test_no_trading_fields(iso_dirs):
    from gods_eye.future import world_change as chg
    blob = json.dumps(_status()).lower()
    for field in chg.FORBIDDEN_FIELDS:
        assert f'"{field}"' not in blob, field


def test_route_contract():
    from gods_eye import demo as _demo
    server = HTTPServer((_demo.HOST, 0), _demo._Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        base = f"http://{_demo.HOST}:{server.server_address[1]}"
        with urllib.request.urlopen(
                base + "/api/world/imagery/status?norefresh=1",
                timeout=60) as r:
            payload = json.load(r)
    finally:
        server.shutdown()
    assert payload["truth_label"] == earth.TRUTH_LABEL
    assert set(payload) >= {"layers", "selected",
                            "current_source_by_region",
                            "freshness_summary", "generated_at"}


def test_tile_errors_degrade_instead_of_fatal():
    # A dead tile host must fall back to the vector basemap, never to
    # the fatal "world surface could not start" dialog.
    src = (ROOT / "console" / "world" / "app.js").read_text(encoding="utf-8")
    assert "noteEarthTileError" in src
    assert 'sourceId === "liveearth"' in src
    assert "imagery source unavailable" in src


def test_raster_saturation_never_boosts():
    # MapLibre raster-saturation is an OFFSET (-1..1, 0 = unchanged).
    # A value of 1 renders neon false color; normal imagery is 0.
    src = (ROOT / "console" / "world" / "app.js").read_text(encoding="utf-8")
    assert '"raster-saturation": 0' in src
    assert '"raster-saturation": 1' not in src


def test_browser_visual_state():
    src = (ROOT / "console" / "world" / "app.js").read_text(encoding="utf-8")
    for needle in ("liveEarth", "LIVE EARTH", "STANDARD",
                   "raster-saturation", "earthInfo"):
        assert needle in src, needle
    css = (ROOT / "console" / "world" / "styles.css").read_text(
        encoding="utf-8")
    assert "earth" in css.lower()
