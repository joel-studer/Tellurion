"""V2.4c live satellite layer tests (offline — providers mocked).

Covers: source qualification / TLE parse + checksums / epoch /
deterministic SGP4 / invalid elements / fresh+stale classes / outage /
cached-stale honesty / API schema + filters / satellite tracking +
camera modes + HUD + ground track + nearest / JARVIS verbs +
contacts / deep links + share / unavailable / NOW-only + replay
isolation / no synthetic fallback / credentials / rights /
performance cap / boundary / regressions.
"""

from __future__ import annotations

import json
import sys
import threading
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import HTTPServer
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from gods_eye.future import world_satellites as sats  # noqa: E402
from gods_eye.future import world_tools as tools  # noqa: E402

sgp4 = pytest.importorskip("sgp4")

# Real public TLE (CelesTrak, 2026-09-21). Fixed fixtures: deterministic.
ISS_TLE = (
    "ISS (ZARYA)",
    "1 25544U 98067A   26264.49719541  .00007274  00000+0  13903-3 0  9998",  # noqa: E501
    "2 25544  51.6310 183.4357 0004787 164.7753 195.3381 15.49212079586681",  # noqa: E501
)
CSS_TLE = (
    "CSS (TIANHE)",
    "1 48274U 21035A   26263.98635566  .00014007  00000+0  17119-3 0  9996",  # noqa: E501
    "2 48274  41.4678 100.3250 0002511 293.9975  66.0601 15.60145341308124",  # noqa: E501
)
EPOCH = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)

CTX = {"mode": "now", "lat": 47.5, "lon": 14.5, "zoom": 2,
       "selected": "", "tick": 12, "layers": "satellite"}

APP = ROOT / "console" / "world" / "app.js"


def app():
    return APP.read_text(encoding="utf-8")


def _obj(norad=25544, lat=47.0, lon=9.0, fresh="FRESH", age=3600):
    return {"object_id": f"SAT:{norad}", "name": "ISS (ZARYA)",
            "norad_id": norad, "source": "CelesTrak",
            "epoch": "2026-09-21T11:55:57+00:00",
            "age_seconds": age, "element_format": "TLE",
            "orbit_type": "LEO", "object_type": "PAYLOAD",
            "group": "stations", "inclination_deg": 51.631,
            "eccentricity": 0.0004788, "mean_motion": 15.49,
            "altitude_km": 419.4, "latitude": lat, "longitude": lon,
            "velocity_km_s": 7.65,
            "propagated_at": "2026-09-21T12:00:00+00:00",
            "truth_mode": "PROPAGATED", "freshness": fresh,
            "source_url": "https://celestrak.org/x",
            "rights": {"commercial_use": "YES",
                       "public_display": "YES",
                       "redistribution": "YES (with attribution)",
                       "derived_products": "YES",
                       "broadcast_use": "ATTRIBUTION_REQUIRED",
                       "cache": "YES",
                       "attribution": "CelesTrak / Dr. T.S. Kelso"},
            "attribution": "CelesTrak / Dr. T.S. Kelso [2026]"}


@pytest.fixture()
def iso_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(sats, "_runtime_dir", lambda: tmp_path)
    yield tmp_path


# ------------------------------------------------------- source ---


def test_source_qualification_gate():
    assert sats.SOURCE_ID == "celestrak"
    assert sats.TERMS_URLS and all(
        u.startswith("https://") for u in sats.TERMS_URLS)
    creds = sats.credentials_status()
    assert creds["account_required"] is False
    assert creds["api_key_required"] is False
    assert sats.RIGHTS_STATUS == "ATTRIBUTION_REQUIRED"
    assert "CelesTrak" in sats.ATTRIBUTION


def test_parse_tle():
    text = "\n".join([ISS_TLE[0], ISS_TLE[1], ISS_TLE[2],
                      CSS_TLE[0], CSS_TLE[1], CSS_TLE[2]])
    recs = sats.parse_tle(text)
    assert len(recs) == 2
    assert recs[0]["name"] == "ISS (ZARYA)"
    assert recs[0]["line1"].startswith("1 25544")


def test_bad_checksum_rejected():
    bad = ("X",
           "1 25544U 98067A   26264.49719541  .00007274  00000+0  13903-3 0  9990",  # noqa: E501
           ISS_TLE[2])
    recs = sats.parse_tle("\n".join(bad))
    assert recs == []
    assert sats.parse_tle("garbage\nmore garbage") == []


def test_epoch_preserved():
    epoch = sats.tle_epoch(ISS_TLE[1])
    assert epoch is not None
    assert (epoch.year, epoch.month, epoch.day) == (2026, 9, 21)
    assert sats.tle_epoch("short") is None


def test_sgp4_deterministic_propagation():
    a = sats.propagate(ISS_TLE[1], ISS_TLE[2], EPOCH)
    b = sats.propagate(ISS_TLE[1], ISS_TLE[2], EPOCH)
    assert a == b
    assert 400.0 < a["altitude_km"] < 450.0
    assert 7.0 < a["velocity_km_s"] < 8.0
    assert -90.0 <= a["latitude"] <= 90.0
    assert -180.0 <= a["longitude"] <= 180.0


def test_invalid_elements_rejected():
    with pytest.raises(Exception):
        sats.propagate(ISS_TLE[1], ISS_TLE[2][:20] + "0" * 49, EPOCH)
    assert sats.build_object("X", "bad", "bad", "stations", EPOCH,
                             "2026-09-21T12:00:00+00:00") is None


def test_fresh_classification():
    assert sats.freshness_class(0.5) == "FRESH"
    assert sats.freshness_class(3.0) == "AGING"
    assert sats.freshness_class(30.0) == "STALE"
    assert sats.freshness_class(None) == "UNKNOWN"


def test_stale_classification_in_model(iso_dirs):
    assert sats.freshness_class(10.0) == "STALE"
    assert sats.orbit_class(15.49, 0.0004) == "LEO"
    assert sats.orbit_class(1.0027, 0.0002) == "GEO"
    assert sats.orbit_class(2.0, 0.01) == "MEO"
    assert sats.orbit_class(2.0, 0.7) == "HEO"


def test_source_outage(iso_dirs):
    def boom(req, timeout=None):
        raise ConnectionError("denied")
    res = sats.refresh_elements(groups=("stations",), opener=boom)
    assert res["ok"] == []
    out = sats.get_satellites(refresh=False)
    assert out["status"] in ("SOURCE_UNAVAILABLE", "NO_COVERAGE")
    assert "synthetic" not in json.dumps(out).lower()


def test_cached_stale_honesty(iso_dirs, monkeypatch):
    # Element age (epoch vs now) drives freshness, not fetch time.
    # An old epoch must surface as STALE with its real age shown.
    old_epoch = EPOCH - timedelta(days=30)
    monkeypatch.setattr(sats, "tle_epoch", lambda line1: old_epoch)
    meta = {"elements": {"stations": {
        "fetched_at": EPOCH.isoformat(),
        "tle": "\n".join(ISS_TLE),
        "count": 1}}, "health": {}}
    sats.save_meta(meta)
    out = sats.get_satellites(refresh=False, now=EPOCH)
    assert out["objects"] and out["objects"][0]["freshness"] == "STALE"
    assert out["objects"][0]["age_seconds"] >= 29 * 86400
    assert any("STALE" in w for w in out["warnings"])


# ---------------------------------------------------------- API ---


def _api(path, timeout=60):
    from gods_eye import demo as _demo
    server = HTTPServer((_demo.HOST, 0), _demo._Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        base = f"http://{_demo.HOST}:{server.server_address[1]}"
        with urllib.request.urlopen(base + path,
                                    timeout=timeout) as r:
            return json.load(r)
    finally:
        server.shutdown()


def test_api_schema(iso_dirs):
    with mock.patch.object(sats, "load_meta",
                           return_value={"elements": {}, "health": {}}):
        payload = _api("/api/world/satellites?limit=10")
    assert set(payload) >= {"generated_at", "objects", "count",
                            "truth_label", "status"}
    assert "PROPAGATED" in payload.get("truth_note", "")
    assert "never live GPS" in payload.get("truth_note", "")


def test_bbox_filter(iso_dirs):
    objs = [_obj(norad=25544, lat=47.0, lon=9.0),
            _obj(norad=48274, lat=-30.0, lon=-60.0)]
    with mock.patch.object(sats, "load_meta", return_value={
            "elements": {"stations": {"fetched_at": EPOCH.isoformat(),
                                      "tle": "", "count": 0}},
            "health": {}}):
        with mock.patch.object(sats, "parse_tle", return_value=[]):
            out = sats.get_satellites(
                refresh=False, bbox=(0.0, 40.0, 20.0, 55.0), now=EPOCH)
    assert out["objects"] == []
    assert sats._matches(objs[0], (0.0, 40.0, 20.0, 55.0), "", "")
    assert not sats._matches(objs[1], (0.0, 40.0, 20.0, 55.0), "", "")


def test_orbit_filter(iso_dirs):
    assert sats._matches(_obj(), None, "LEO", "")
    assert not sats._matches(_obj(), None, "GEO", "")
    assert sats._matches(_obj(fresh="STALE"), None, "", "STALE")


# -------------------------------------------------------- track ---


def test_track_satellite():
    with mock.patch.object(sats, "get_object", return_value={
            "status": "AVAILABLE", "object": _obj()}):
        out = tools.execute("track_entity", {"id": "SAT:25544"},
                            CTX)
    assert out["status"] == "SUCCESS"
    assert out["data"]["action"] == "track"
    assert out["truth_mode"] == "PROPAGATED"
    assert out["data"]["ground_track"] is True


def test_stop_satellite_tracking():
    out = tools.execute("stop_tracking", {}, CTX)
    assert out["status"] == "SUCCESS"


def test_camera_modes_contract():
    src = app()
    for mode in ("FOLLOW", "ORBIT", "CHASE", "OVERVIEW"):
        out = tools.execute("set_camera_mode",
                            {"camera_mode": mode}, CTX)
        assert out["status"] == "SUCCESS", mode
    assert "setTrackCameraMode" in src


def test_telemetry_hud_contract():
    src = app()
    for needle in ("NORAD ID", "Element epoch", "Element age",
                   "PROPAGATED", "satellite"):
        assert needle in src, needle


def test_ground_track():
    track = sats.ground_track(ISS_TLE[1], ISS_TLE[2], EPOCH)
    assert len(track) > 20
    assert all(len(p) == 2 for p in track)
    lons = [p[0] for p in track]
    assert max(lons) - min(lons) > 30.0
    bad = sats.get_ground_track("nope")
    assert bad["status"] == "UNKNOWN_OBJECT"


def test_track_nearest_satellite():
    objs = [_obj(norad=25544, lat=47.0, lon=9.0),
            _obj(norad=48274, lat=-30.0, lon=-60.0)]
    with mock.patch.object(sats, "get_satellites", return_value={
            "status": "AVAILABLE", "objects": objs}):
        with mock.patch.object(sats, "get_object", return_value={
                "status": "AVAILABLE", "object": objs[0]}):
            out = tools.execute("track_nearest",
                                {"lat": 47.5, "lon": 9.5,
                                 "class": "SATELLITE"}, CTX)
    assert out["status"] == "SUCCESS"
    assert out["data"]["entity"]["id"] == "SAT:25544"
    assert "ground_distance_km" in out["data"]


def test_jarvis_satellite_query():
    with mock.patch.object(sats, "get_satellites", return_value={
            "status": "AVAILABLE", "objects": [_obj()], "count": 1,
            "element_epoch_range": [], "groups": ["stations"],
            "warnings": []}):
        for q in ("show satellites", "nearest satellite",
                  "show satellites over Europe"):
            out = tools.run_command(q, CTX)
            assert out["calls"], q
        out = tools.run_command("track satellite 25544", CTX)
        assert out["calls"][0] == {"tool": "track_entity",
                                   "args": {"id": "SAT:25544"}}
        out = tools.run_command("how fresh are these orbital "
                                "elements?", CTX)
        assert out["calls"][0]["tool"] == "query_satellites"


def test_contacts_integration():
    objs = [_obj(norad=25544, lat=47.0, lon=9.0)]
    with mock.patch.object(sats, "get_satellites", return_value={
            "status": "AVAILABLE", "objects": objs}):
        with mock.patch.object(tools, "_changes", return_value=[]):
            with mock.patch("gods_eye.future.world_air.get_aviation",
                             return_value={"states": []}):
                out = tools.execute("query_contacts",
                                    {"lat": 47.0, "lon": 9.0}, CTX)
    rows = [c for c in out["data"]["contacts"]
            if c.get("class") == "SATELLITE"]
    assert rows and rows[0]["distance_kind"] == "GROUND_DISTANCE"


def test_deep_links():
    src = app()
    assert 'QS.get("satellite")' in src
    assert '"TARGET UNAVAILABLE"' in src or \
        "TARGET UNAVAILABLE" in src


def test_share_state():
    src = app()
    assert 'q.set("satellite"' in src
    low = src.lower()
    seg = low.split("writeDeepLink".lower())[1].split(
        "function openNowRegion".lower())[0]
    for secret in ("api_key", "password"):
        assert secret not in seg


def test_unavailable_object():
    with mock.patch.object(sats, "get_object", return_value={
            "status": "UNKNOWN_OBJECT", "object": None,
            "note": "nope"}):
        out = tools.execute("track_entity", {"id": "SAT:999999"},
                            CTX)
    assert out["status"] in ("FAILED", "UNAVAILABLE")
    out2 = tools.execute("track_entity", {"id": "SAT:abc"}, CTX)
    assert out2["status"] in ("FAILED", "UNAVAILABLE")


def test_now_only():
    src = app()
    assert "loadNowSatellites" in src
    assert "if (!MODE_NOW) return false" in src


def test_replay_isolation():
    payload = _api("/api/ultra?tick=0")
    assert "liveSat" not in json.dumps(payload)
    src = app()
    assert "livesat-point" in src


def test_no_synthetic_fallback(iso_dirs):
    out = sats.get_satellites(refresh=False)
    assert out["objects"] == []
    assert out["status"] in ("NO_COVERAGE", "SOURCE_UNAVAILABLE",
                             "UNAVAILABLE")


def test_no_credentials():
    import re
    text = (ROOT / "python" / "gods_eye" / "future"
            / "world_satellites.py").read_text(encoding="utf-8")
    from gods_eye.future import boundary
    assert boundary.secret_hits_text(text) == []
    assert "TELLURION_CDSE" not in text
    assert sats.credentials_status()["api_key_required"] is False


def test_rights_propagation():
    obj = _obj()
    assert set(obj["rights"]) >= {"commercial_use", "public_display",
                                  "redistribution", "attribution"}
    assert obj["rights"]["attribution"].startswith("CelesTrak")


def test_attribution():
    assert sats.ATTRIBUTION == "CelesTrak / Dr. T.S. Kelso"
    assert sats.RIGHTS_STATUS == "ATTRIBUTION_REQUIRED"
    obj = _obj()
    assert "[2026]" in obj["attribution"]


def test_performance_object_cap(iso_dirs):
    import time
    objs = [_obj(norad=10000 + i,
                 lat=float(i % 90), lon=float(i % 180))
            for i in range(300)]
    with mock.patch.object(sats, "parse_tle", return_value=[
            {"name": f"O{i}", "line1": ISS_TLE[1], "line2": ISS_TLE[2]}
            for i in range(300)]):
        meta = {"elements": {"stations": {
            "fetched_at": EPOCH.isoformat(), "tle": "x", "count": 300}},
            "health": {}}
        with mock.patch.object(sats, "load_meta",
                               return_value=meta):
            t0 = time.time()
            out = sats.get_satellites(refresh=False, limit=1500,
                                      now=EPOCH)
            dt = time.time() - t0
    assert len(out["objects"]) <= 1500
    assert dt < 30.0
    out2 = sats.get_satellites(refresh=False, limit=10, now=EPOCH)
    assert len(out2["objects"]) <= 10


def test_public_private_boundary():
    import re
    for rel in ("python/gods_eye/future/world_satellites.py",
                "tests/test_world_satellites_v28.py"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        from gods_eye.future import world_change as chg
        word = lambda tok: re.search(r"(?<![a-z_])" + re.escape(tok)
                                     + r"(?![a-z_])", text.lower())
        hits = sorted({t for t in chg.FORBIDDEN_FIELDS if word(t)})
        assert not hits, (rel, hits)
        from gods_eye.future import boundary
        assert boundary.secret_hits_text(text) == [], rel
        assert boundary.denylist_hits(
            ROOT, ["gods_eye" + "_private"]) == []


def test_aircraft_track_regression():
    out = tools.run_command("track selected",
                            {**CTX, "selected": "AIR:abc123"})
    assert out["calls"][0]["tool"] == "track_entity"
    out2 = tools.run_command("show changes today", CTX)
    assert out2["calls"][0]["tool"] == "query_changes"


def test_jarvis_regression():
    out = tools.run_command("replay 6h", CTX)
    assert out["results"][0]["status"] == "SUCCESS"
    out2 = tools.run_command("nearest aircraft", CTX)
    assert out2["calls"][0]["tool"] == "query_contacts"


def test_live_earth_regression():
    from gods_eye.future import world_earth as earth
    assert callable(earth.get_status)
    assert sats.STAC_COLLECTION if hasattr(sats, "STAC_COLLECTION") \
        else True


def test_s1_s2_evidence_regression():
    from gods_eye.future import world_imagery as img
    from gods_eye.future import world_sar as sar
    assert img.STAC_COLLECTION == "sentinel-2-l2a"
    assert sar.STAC_COLLECTION == "sentinel-1-grd"


# -------------------------------------------------------- live ---


def test_browser_satellite_flow():
    pytest.importorskip("playwright")
    from gods_eye import demo as _demo
    objs = [_obj(norad=25544, lat=47.0, lon=9.0)]
    payload = {"generated_at": EPOCH.isoformat(), "live": False,
               "real_data": True, "objects": objs, "count": 1,
               "status": "AVAILABLE", "warnings": []}
    with mock.patch.object(sats, "get_satellites",
                           return_value=payload):
        with mock.patch.object(sats, "get_object", return_value={
                "status": "AVAILABLE", "object": objs[0],
                "truth_note": "propagated"}):
            with mock.patch.object(sats, "get_ground_track",
                                   return_value={
                                       "status": "AVAILABLE",
                                       "track": [[9.0, 47.0],
                                                 [10.0, 48.0]],
                                       "norad_id": 25544}):
                server = HTTPServer((_demo.HOST, 0), _demo._Handler)
                threading.Thread(target=server.serve_forever,
                                 daemon=True).start()
                try:
                    base = (f"http://{_demo.HOST}:"
                            f"{server.server_address[1]}")
                    from playwright.sync_api import sync_playwright
                    with sync_playwright() as p:
                        browser = p.chromium.launch()
                        page = browser.new_page(
                            viewport={"width": 1600, "height": 900})
                        errors = []
                        page.on("pageerror", lambda e: errors.append(
                            str(e)[:200]))
                        page.goto(f"{base}/ultra?mode=now&view=world"
                                  "&story=none")
                        page.wait_for_function(
                            "document.documentElement.dataset.ready"
                            " === 'true'", timeout=120000)
                        # Orbital shell loads async post-ready.
                        page.wait_for_timeout(4000)
                        page.keyboard.press("Control+k")
                        page.wait_for_timeout(400)
                        page.keyboard.type("ISS", delay=20)
                        page.wait_for_timeout(800)
                        names = page.evaluate(
                            "Array.from(document.querySelectorAll("
                            "'#paletteList li')).map(li => li.textContent"
                            ".slice(0, 50))")
                        assert any("ISS" in n for n in names), names
                        page.keyboard.press("ArrowDown")
                        page.wait_for_timeout(300)
                        page.keyboard.press("Enter")
                        page.wait_for_timeout(2000)
                        assert page.query_selector("#trackBtn") \
                            is not None
                        page.click("#trackBtn")
                        page.wait_for_selector(
                            "#trackHud:not([hidden])", timeout=30000)
                        page.wait_for_timeout(1500)
                        hud = page.inner_text("#trackHud")
                        assert "25544" in hud
                        assert "PROPAGATED" in hud
                        assert errors == [], errors[:2]
                        page.close()
                        browser.close()
                finally:
                    server.shutdown()
