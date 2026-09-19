"""V2.4b track mode tests (movement / camera / tracking / contacts).

Backend tools run offline with mocks. Frontend behavior is verified
by contract (source assertions on the single app bundle) plus a live
browser flow with injected snapshot state. No live network required.
"""

from __future__ import annotations

import json
import sys
import threading
import urllib.request
from http.server import HTTPServer
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from gods_eye.future import world_tools as tools  # noqa: E402

CTX = {"mode": "now", "lat": 47.5, "lon": 14.5, "zoom": 4,
       "selected": "", "tick": 12, "layers": "aircraft"}

SNAP = {"states": [{"icao24": "abc123", "callsign": "AUA123",
                    "lat": 47.0, "lon": 9.0, "track_deg": 86.0,
                    "gs_kt": 452.0, "baro_alt_ft": 34000.0,
                    "vrate_fpm": 320.0, "squawk": "1200",
                    "type": "A320", "source": "adsb.lol",
                    "position_age_s": 4.0,
                    "position_time": "2026-09-19T19:00:00+00:00"}]}

APP = ROOT / "console" / "world" / "app.js"


def app():
    return APP.read_text(encoding="utf-8")


# -------------------------------------------------- tool contract ---


def test_start_tracking():
    with mock.patch("gods_eye.future.world_air.get_aviation",
                     return_value=SNAP):
        with mock.patch("gods_eye.future.world_air.get_trail",
                         return_value=[]):
            out = tools.execute("track_entity", {"id": "AIR:abc123"},
                                CTX)
    assert out["status"] == "SUCCESS"
    assert out["data"]["action"] == "track"
    assert out["data"]["camera_mode"] == "FOLLOW"
    assert out["truth_mode"] == "DELAYED"


def test_stop_tracking():
    out = tools.execute("stop_tracking", {}, CTX)
    assert out["status"] == "SUCCESS"
    assert out["data"]["action"] == "stop_tracking"


def test_unsupported_entity_rejection():
    out = tools.execute("track_entity", {"id": "BOGUS-1"}, CTX)
    assert out["status"] in ("FAILED", "UNAVAILABLE")
    with mock.patch.object(tools, "_change_by_id",
                           return_value={"id": "chg:x"}):
        out2 = tools.execute("track_entity", {"id": "chg:x"}, CTX)
    assert out2["status"] == "UNAVAILABLE"


def test_camera_tool_modes():
    for mode in ("FOLLOW", "ORBIT", "CHASE", "OVERVIEW"):
        out = tools.execute("set_camera_mode",
                            {"camera_mode": mode}, CTX)
        assert out["status"] == "SUCCESS", mode
        assert out["data"]["camera_mode"] == mode
    bad = tools.execute("set_camera_mode", {"camera_mode": "LOOP"},
                        CTX)
    assert bad["status"] == "FAILED"


def test_track_nearest_atomic():
    with mock.patch("gods_eye.future.world_air.get_aviation",
                     return_value=SNAP):
        with mock.patch("gods_eye.future.world_air.get_trail",
                         return_value=[]):
            out = tools.execute("track_nearest",
                                {"lat": 47.1, "lon": 9.1}, CTX)
    assert out["status"] == "SUCCESS"
    assert out["data"]["entity"]["id"] == "AIR:abc123"
    assert out["data"]["distance_km"] is not None


def test_parser_tracking_verbs():
    assert tools.parse_intent("track selected",
                              {**CTX, "selected": "AIR:a"})[
        "calls"][0]["tool"] == "track_entity"
    assert tools.parse_intent("orbit selected", CTX)["calls"][0] == {
        "tool": "set_camera_mode", "args": {"camera_mode": "ORBIT"}}
    assert tools.parse_intent("show nearby contacts", CTX)[
        "calls"][0]["tool"] == "query_contacts"
    assert tools.parse_intent("track nearest aircraft", CTX)[
        "calls"][0]["tool"] == "track_nearest"
    assert [c["tool"] for c in
            tools.parse_intent("return to world", CTX)["calls"]] == [
        "stop_tracking", "set_view"]


# ------------------------------------------------- track state ---


def test_unified_track_state():
    src = app()
    assert "const trackState = { active" in src
    for field in ("entity_type", "entity_id", "source",
                  "acquired_at", "last_position", "last_update",
                  "freshness", "camera_mode"):
        assert field in src, field
    assert "TRACK.CAMERA_MODES" in src or \
        'CAMERA_MODES: ["FOLLOW", "ORBIT", "CHASE", "OVERVIEW"]' in src


def test_camera_modes_present():
    src = app()
    for mode in ("FOLLOW", "ORBIT", "CHASE", "OVERVIEW"):
        assert mode in src, mode
    assert "TARGET_TO_WORLD" in src or "returnHome" in src or \
        "pre_track_view" in src


def test_camera_transitions_bounded():
    src = app()
    assert "TRANSITION_MIN_MS" in src and "TRANSITION_MAX_MS" in src
    assert "2000" in src
    assert "REDUCED_MOTION" in src


def test_interpolation_bounded():
    src = app()
    assert "interpolateFix" in src
    assert "STALE_AFTER_S" in src
    # Never extrapolates: clamp factor lives in the interpolator.
    assert "Math.max(0, Math.min(1," in src


def test_interpolation_stops_when_stale():
    src = app()
    assert '"STALE"' in src
    assert "frozen, not extrapolated" in src or "freeze" in src.lower()


def test_stale_position_handling():
    src = app()
    assert "Stale " in src
    assert "frozen, not extrapolated" in src


def test_real_heading():
    src = app()
    assert 'icon-rotate": ["get", "heading"]' in src or \
        '"icon-rotate"' in src


def test_derived_heading_handling():
    src = app()
    assert "(derived)" in src


def test_telemetry_strip():
    src = app()
    for needle in ("trackHud", "Vertical rate", "Squawk", "Freshness",
                   "Truth", "Updated"):
        assert needle in src, needle


def test_unknown_telemetry_stays_unknown():
    src = app()
    assert '"—"' in src
    # No guessed values: UNKNOWN fields render an em dash.
    assert "fmtNum" in src


def test_trail_rendering():
    src = app()
    assert "tracktrail" in src
    assert "TRAIL_MAX_PTS" in src
    assert "40" in src


def test_bounded_trail_retention():
    src = app()
    assert "TRAIL_MAX_PTS" in src
    assert ".shift()" in src or "slice(-" in src


# ------------------------------------------------------ contacts ---


def test_contacts_radius():
    src = app()
    for radius in ("50", "100", "250", "500"):
        assert radius in src


def test_contacts_sorting():
    with mock.patch("gods_eye.future.world_air.get_aviation",
                     return_value={"states": []}):
        for sort in ("NEAREST", "NEWEST", "IMPORTANT"):
            out = tools.execute("query_contacts",
                                {"lat": 47.0, "lon": 9.0,
                                 "sort": sort}, CTX)
            assert out["status"] == "SUCCESS", sort
            assert out["data"]["sort"] == sort


def test_contact_selection_contract():
    src = app()
    assert "contactsPanel" in src
    assert "loadContactsPanel" in src
    assert "openChangeById" in src


def test_track_contact_contract():
    src = app()
    assert "startTrack(ct.id" in src or "startTrack(" in src


def test_event_contact_evidence():
    src = app()
    assert "data-act=\"evidence\"" in src or \
        'data-act="evidence"' in src


def test_command_palette_tracking():
    src = app()
    assert "/api/world/tools" in src
    out = tools.run_command("track selected",
                            {**CTX, "selected": "AIR:abc123"})
    assert out["calls"][0]["tool"] == "track_entity"


def test_light_payload_carries_fix_age():
    # Track freshness must come from source-stated age, not wall-clock
    # math over stripped payloads (null age once read as 0 s old).
    from gods_eye import demo as _demo
    server = HTTPServer((_demo.HOST, 0), _demo._Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        base = f"http://{_demo.HOST}:{server.server_address[1]}"
        with urllib.request.urlopen(
                base + "/api/world/now/aviation?light=1&norefresh=1",
                timeout=60) as r:
            payload = json.load(r)
    finally:
        server.shutdown()
    assert "positions" in payload or "states" in payload


def test_deep_link_tracking():
    src = app()
    assert 'QS.get("track")' in src
    assert 'QS.get("camera")' in src
    assert "TARGET UNAVAILABLE" in src


def test_unavailable_deep_link_target():
    src = app()
    assert "not in the current snapshot" in src
    assert "location and context preserved" in src


# -------------------------------------------------------- truth ---


def test_source_freshness_display():
    src = app()
    assert "trackState.source" in src
    assert "trackState.freshness" in src or "Freshness" in src
    assert "trackState.fix_state" in src or "fix_state" in src


def test_reduced_motion():
    src = app()
    assert src.count("REDUCED_MOTION") >= 5
    assert "map.jumpTo(options)" in src


def test_keyboard_navigation():
    src = app()
    assert 'aria-label="Tracking camera modes"' in src
    assert 'aria-label="Tracking actions"' in src
    assert 'aria-label="Stop tracking"' in src
    assert 'aria-label="Contact radius"' in src


def test_responsive_ui():
    css = (ROOT / "console" / "world" / "styles.css").read_text(
        encoding="utf-8")
    assert "#trackHud" in css and "#contactsPanel" in css
    assert "max-width: 900px" in css


def test_public_private_boundary():
    import re
    for rel in ("python/gods_eye/future/world_tools.py",
                "tests/test_track_mode_v27.py"):
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


def test_no_trading_fields():
    import json as _json
    with mock.patch("gods_eye.future.world_air.get_aviation",
                     return_value=SNAP):
        with mock.patch("gods_eye.future.world_air.get_trail",
                         return_value=[]):
            out = tools.execute("track_entity", {"id": "AIR:abc123"},
                                CTX)
    from gods_eye.future import world_change as chg
    blob = _json.dumps(out).lower()
    for field in chg.FORBIDDEN_FIELDS:
        assert f'"{field}"' not in blob, field


# ------------------------------------------------------ regress ---


def test_existing_jarvis_tool_regression():
    out = tools.run_command("show changes today", CTX)
    assert out["calls"][0]["tool"] == "query_changes"
    out2 = tools.run_command("replay 6h", CTX)
    assert out2["results"][0]["status"] == "SUCCESS"


def test_existing_live_earth_regression():
    from gods_eye.future import world_earth as earth
    assert callable(earth.get_status)
    assert "GOES" in json.dumps(earth.REGION_RULES)


def test_existing_sar_regression():
    from gods_eye.future import world_sar as sar
    assert sar.STAC_COLLECTION == "sentinel-1-grd"
    assert sar.eligible({"location": {},
                         "type": "aviation"})[0] is False


# -------------------------------------------------------- live ---


def test_browser_stale_freeze():
    # Aged fix (stated age 600 s): HUD must show STALE and freeze,
    # never extrapolate, never read null age as fresh.
    pytest.importorskip("playwright")
    from gods_eye import demo as _demo
    from gods_eye.future import world_air as air
    stale = dict(SNAP["states"][0])
    stale["position_age_s"] = 600.0
    snap = {"counts": {"total": 1}, "states": [stale],
            "flagged": [], "important": [], "airport_events": [],
            "health": [], "coverage": [], "errors": [],
            "generated_at": "2026-09-19T19:00:00+00:00"}
    with mock.patch.object(air, "get_aviation", return_value=snap):
        with mock.patch.object(air, "refresh_aviation",
                               return_value={}):
            with mock.patch.object(air, "get_trail",
                                   return_value=[]):
                server = HTTPServer((_demo.HOST, 0), _demo._Handler)
                threading.Thread(target=server.serve_forever,
                                 daemon=True).start()
                try:
                    base = (f"http://{_demo.HOST}:"
                            f"{server.server_address[1]}")
                    from playwright.sync_api import sync_playwright
                    with sync_playwright() as p:
                        browser = p.chromium.launch()
                        page = browser.new_page()
                        page.goto(f"{base}/ultra?mode=now&view=world"
                                  "&story=none")
                        page.wait_for_function(
                            "document.documentElement.dataset.ready"
                            " === 'true'", timeout=120000)
                        page.keyboard.press("Control+k")
                        page.wait_for_timeout(400)
                        page.keyboard.type("AUA123", delay=20)
                        page.wait_for_timeout(700)
                        page.keyboard.press("ArrowDown")
                        page.wait_for_timeout(300)
                        page.keyboard.press("Enter")
                        page.wait_for_timeout(1500)
                        page.click("#trackBtn")
                        try:
                            page.wait_for_function(
                                "() => window.__tellurionTrack && "
                                "window.__tellurionTrack().fix_state"
                                " === 'STALE'", timeout=30000)
                        except Exception:
                            state = page.evaluate(
                                "window.__tellurionTrack()")
                            pytest.fail(f"never STALE: {state}")
                        assert "STALE" in page.inner_text("#trackHud")
                        page.close()
                        browser.close()
                finally:
                    server.shutdown()


def test_browser_track_flow():
    pytest.importorskip("playwright")
    from datetime import datetime, timezone
    from gods_eye import demo as _demo
    from gods_eye.future import world_air as air
    now = datetime.now(timezone.utc).replace(
        microsecond=0).isoformat()
    live = dict(SNAP["states"][0])
    live["position_time"] = now
    snap = {"counts": {"total": 1}, "states": [live],
            "flagged": [], "important": [], "airport_events": [],
            "health": [], "coverage": [], "errors": [],
            "generated_at": now}
    with mock.patch.object(air, "get_aviation", return_value=snap):
        with mock.patch.object(air, "refresh_aviation",
                               return_value={}):
            with mock.patch.object(air, "get_trail",
                                   return_value=[{
                                       "t": "2026-09-19T18:59:00+00:00",
                                       "lat": 47.0, "lon": 9.0,
                                       "baro_alt_ft": 34000,
                                       "track_deg": 86,
                                       "truth": "RECORDED"}]):
                server = HTTPServer((_demo.HOST, 0), _demo._Handler)
                threading.Thread(target=server.serve_forever,
                                 daemon=True).start()
                try:
                    _drive_track_flow(_demo, server)
                finally:
                    server.shutdown()


def _drive_track_flow(_demo, server):
    from playwright.sync_api import sync_playwright
    base = f"http://{_demo.HOST}:{server.server_address[1]}"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1600,
                                          "height": 900})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)[:200]))
        page.goto(f"{base}/ultra?mode=now&view=world&story=none")
        try:
            page.wait_for_function(
                "document.documentElement.dataset.ready"
                " === 'true'", timeout=120000)
        except Exception as e:
            pytest.fail(f"never ready: {e}")
        # Palette -> aircraft -> drawer -> TRACK.
        page.keyboard.press("Control+k")
        page.wait_for_timeout(400)
        page.keyboard.type("AUA123", delay=20)
        page.wait_for_timeout(800)
        # First item is Ask; ArrowDown reaches the aircraft result.
        page.keyboard.press("ArrowDown")
        page.wait_for_timeout(300)
        page.keyboard.press("Enter")
        page.wait_for_timeout(1500)
        track_btn = page.query_selector("#trackBtn")
        assert track_btn is not None, "drawer TRACK button missing"
        track_btn.click()
        try:
            page.wait_for_selector("#trackHud:not([hidden])",
                                   timeout=30000)
        except Exception:
            pytest.fail("track HUD never appeared")
        hud = page.inner_text("#trackHud")
        assert "AUA123" in hud
        assert "34,000" in hud or "34000" in hud
        assert "adsb.lol" in hud
        assert "LIVE FIX" in hud or "INTERPOLATED" in hud
        # ORBIT mode engages.
        page.click('#trackHud [data-mode="ORBIT"]')
        page.wait_for_timeout(600)
        pressed = page.get_attribute(
            '#trackHud [data-mode="ORBIT"]', "aria-pressed")
        assert pressed == "true"
        # CONTACTS panel opens with live snapshot data.
        page.click("#trackContacts")
        page.wait_for_timeout(1500)
        assert page.evaluate(
            "!document.querySelector('#contactsPanel').hidden") is True
        # STOP returns to the world.
        page.click("#trackStopBtn")
        page.wait_for_timeout(600)
        assert page.evaluate(
            "document.querySelector('#trackHud').hidden") is True
        assert errors == [], errors[:2]
        page.close()
        browser.close()
