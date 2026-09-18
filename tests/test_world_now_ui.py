"""WORLD NOW UI consistency regression (defect fix, no browser needed).

The defect: with ?mode=now the backend served real WORLD NOW data while the
top-center banner still read "SYNTHETIC SCENARIO" and the mode pill still
read "Replay - synthetic", because no JS ever synced those chrome surfaces.

These tests pin the fix:
- exactly ONE authoritative UI world-mode state (state.worldMode),
- exactly ONE chrome-sync owner (syncTruthChrome),
- NOW chrome is real-worded with no synthetic/replay wording,
- replay chrome keeps its synthetic wording,
- live drawers / source health / data builders stay real-only in NOW mode.

Every UI-mode test here FAILS on the pre-fix code (no syncTruthChrome,
no worldMode, no modeBadge hook, no .badge.now/.chip.real styles).
"""

from __future__ import annotations

import json
import re
import sys
import threading
import urllib.request
from http.server import HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

BRAND = "Tellurion"


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def base_url():
    from gods_eye import demo as _demo
    server = HTTPServer((_demo.HOST, 0), _demo._Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://{_demo.HOST}:{server.server_address[1]}"
    server.shutdown()


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.load(r)


def _get_text(url: str) -> str:
    with urllib.request.urlopen(url, timeout=20) as r:
        return r.read().decode("utf-8")


def _sync_fn_src(app_js: str) -> str:
    """Extract the syncTruthChrome function body (brace-balanced)."""
    start = app_js.index("function syncTruthChrome()")
    depth, i = 0, app_js.index("{", start)
    for j in range(i, len(app_js)):
        depth += (app_js[j] == "{") - (app_js[j] == "}")
        if depth == 0:
            return app_js[start : j + 1]
    raise AssertionError("unbalanced braces in syncTruthChrome")


# ------------------------------------------------------- backend truth ---


def test_now_backend_truth_contract(base_url):
    payload = _get_json(base_url + "/api/world/now?norefresh=1")
    assert payload["mode"] == "now"
    assert payload["real_data"] is True
    assert payload["truth_label"] == "WORLD NOW (real public feeds)"
    assert payload["live"] is False


def test_ultra_serves_tellurion_globe(base_url):
    body = _get_text(base_url + "/ultra?mode=now&view=world&sky=movement")
    assert BRAND in body
    assert "modeBadge" in body and 'id="scenario"' in body
    assert "GOD'S EYE ULTRA" not in body


# --------------------------------------- single authoritative UI mode ---


def test_single_authoritative_world_mode():
    app_js = _read("console/world/app.js")
    assert re.search(r'worldMode:\s*MODE_NOW\s*\?\s*"now"\s*:\s*"replay"', app_js), \
        "state.worldMode must derive once from the URL MODE_NOW flag"
    assert len(re.findall(r"function syncTruthChrome\(\)", app_js)) == 1, \
        "exactly one chrome-sync owner is allowed"
    # No widget may write the banner/pill/attribution except the sync owner.
    writes = [m for m in re.finditer(
        r'\$\("(modeBadge|scenario|attribution)"\)', app_js)]
    sync_src = _sync_fn_src(app_js)
    for m in writes:
        assert sync_src.find(m.group(0)) >= 0, \
            f"$({m.group(1)}) written outside syncTruthChrome"
    # The sync owner runs at boot (pre-data paint) and after NOW data lands.
    assert "syncTruthChrome();" in app_js
    assert app_js.index("function wireChrome()") < app_js.index(
        "syncTruthChrome();") < app_js.index("function onKey(")


def test_worldmode_exposed_for_verification():
    app_js = _read("console/world/app.js")
    assert "syncTruthChrome" in app_js.split(
        "window.__tellurion")[1], "sync owner must be reachable for tests"


# ------------------------------------------------------- NOW chrome ---


def test_now_chrome_is_real_and_never_synthetic():
    app_js = _read("console/world/app.js")
    sync_src = _sync_fn_src(app_js)
    assert "REAL WORLD NOW" in sync_src
    assert "WORLD NOW · real data" in sync_src
    # The NOW-worded sides must carry no synthetic/replay wording (the replay
    # else-branch keeps it — pinned by the replay test below).
    assert 'now ? "WORLD NOW · real data"' in sync_src
    scenario_now = sync_src.split("if (now) {", 1)[1].split("} else {", 1)[0]
    assert "REAL WORLD NOW" in scenario_now
    assert "synthetic" not in scenario_now.lower()
    assert "real public feeds, delayed" in sync_src
    assert '"now"' in sync_src and '"replay"' in sync_src


def test_now_banner_and_pill_hooks_exist():
    html = _read("console/world.html")
    assert 'id="modeBadge"' in html
    assert 'data-worldmode="replay"' in html  # replay is the safe default
    css = _read("console/world/styles.css")
    for needle in (".badge.now", "#scenario.now", ".chip.real"):
        assert needle in css, needle


def test_now_drawer_and_health_are_real():
    app_js = _read("console/world/app.js")
    now_drawer = app_js[app_js.index("function nowDrawer("):]
    now_drawer = now_drawer[: now_drawer.index("function wireNowDrawer(")]
    assert "chip real" in now_drawer and "REAL DATA" in now_drawer
    assert "SYNTHETIC" not in now_drawer
    # Replay drawer keeps its synthetic marking (per-object truth).
    replay_drawer = app_js[app_js.index("function renderDrawer("):]
    replay_drawer = replay_drawer[: replay_drawer.index(
        "function renderDrawerLoading(")]
    assert "SYNTHETIC" in replay_drawer


def test_now_data_builder_uses_real_pools_only():
    app_js = _read("console/world/app.js")
    assert "if (MODE_NOW) return buildNowData();" in app_js
    now_data = app_js[app_js.index("function buildNowData()"):]
    now_data = now_data[: now_data.index("function addNowLayers()")]
    for pool in ("sea: empty", "trails: empty", "corridors: empty",
                 "storm: empty", "scenes: empty", "cells: empty",
                 "roads: empty", "cameras: empty"):
        assert pool in now_data, pool


def test_static_pin_clicks_stay_out_of_replay_drawer():
    app_js = _read("console/world/app.js")
    feat = app_js[app_js.index("function targetFromFeature("):]
    feat = feat[: feat.index("/* ------------------------------------------------------ investigation */")]
    assert feat.count("now: true") >= 2, \
        "NOW fallback targets must stay flagged now (live path)"
    assert "SYNTHETIC" not in feat


# ---------------------------------------------------- replay chrome ---


def test_replay_chrome_stays_synthetic():
    html = _read("console/world.html")
    assert "SYNTHETIC SCENARIO" in html  # safe replay default pre-JS
    assert "Replay · synthetic" in html
    app_js = _read("console/world/app.js")
    sync_src = _sync_fn_src(app_js)
    assert "SYNTHETIC SCENARIO" in sync_src
    assert "Replay · synthetic" in sync_src
    assert "synthetic replay, not live" in sync_src
    # The replay branch must not leak WORLD NOW wording.
    else_branch = sync_src.split("} else {", 1)[1]
    assert "WORLD NOW" not in else_branch
    assert "REAL WORLD NOW" not in else_branch


# --------------------------------------------- density / framing pins ---


def test_now_coverage_defaults_on():
    app_js = _read("console/world/app.js")
    main_src = app_js[app_js.index("async function main()"):]
    assert "state.visible.blind = true" in main_src


def test_now_selection_keeps_regional_context():
    app_js = _read("console/world/app.js")
    fly = app_js[app_js.index("function flyToTarget("):]
    fly = fly[: fly.index("function toggleFollow(")]
    assert "target.now ? 5.5 : 8.2" in fly
    assert "target.now ? 30 : 45" in fly
    assert "zoom = 8.2" not in fly, "tight replay default must not apply to NOW"


def test_now_attribution_names_real_feeds():
    app_js = _read("console/world/app.js")
    sync_src = _sync_fn_src(app_js)
    assert "real public feeds, delayed" in sync_src


# ------------------------- final release pass (2026-09-17) regressions ---
# Each test below pins a defect found in a real browser, not in source review.


def _fn_src(app_js: str, name: str) -> str:
    start = app_js.index(f"function {name}(")
    depth, i = 0, app_js.index("{", start)
    for j in range(i, len(app_js)):
        depth += (app_js[j] == "{") - (app_js[j] == "}")
        if depth == 0:
            return app_js[start : j + 1]
    raise AssertionError(f"unbalanced braces in {name}")


def test_now_sun_and_clock_are_real_not_the_replay_epoch():
    """D1: WORLD NOW showed World time 2026-09-15 16:40 and a terminator
    computed from the synthetic replay clock."""
    from gods_eye.future import world_now as wn
    payload = wn.get_now(refresh=False)
    solar = payload["solar"]
    assert solar["at"] == payload["generated_at"]
    assert solar["night"][0] == solar["night"][-1] and len(solar["night"]) > 20
    app_js = _read("console/world/app.js")
    now_data = _fn_src(app_js, "buildNowData")
    assert "state.now?.solar?.night" in now_data
    # word boundary: `now.solar.night` (real) must not match `w.solar.night` (replay)
    assert not re.search(r"\bw\.solar\.night", now_data), "NOW must never draw the replay sun"
    timeline = _fn_src(app_js, "renderTimeline")
    assert "state.now?.generated_at" in timeline and "utcLabel(at)" in timeline


def test_now_coverage_does_not_claim_aviation_needs_a_key():
    """D2: coverage and blind spots said aviation needs an OpenSky key while
    the keyless adsb.lol leg served thousands of real aircraft."""
    from gods_eye.future import world_now as wn
    rows = [r for r in wn.real_coverage({}) if r["domain"] == "aviation"]
    assert rows and rows[0]["status"] != "KEY_REQUIRED"
    assert "OpenSky" not in rows[0]["detail"]
    spots = " ".join(s["reason"] for s in wn.real_blind_spots())
    assert "OpenSky" not in spots


def test_now_nav_wording_keys_on_url_mode_not_late_data():
    """D4: NAV is built at load, before data; `sub: nowOn()` froze replay
    subtitles ("Corridors and regional replay") onto real layers."""
    app_js = _read("console/world/app.js")
    start = app_js.index("const NAV = [")
    nav = app_js[start:app_js.index("\n];", start)]
    assert not re.search(r"sub:\s*nowOn\(\)", nav)
    assert 'sub: MODE_NOW ? "Live ADS-B (delayed seconds)"' in nav
    assert '"NO QUALIFIED SOURCE" : state.ultra.cameras' not in nav  # count column overlap


def test_now_label_flash_is_unpainted_until_sync():
    """D3: the static replay wording painted for 50-110 ms on NOW loads."""
    assert 'document.body.dataset.truthSynced = "true"' in _sync_fn_src(
        _read("console/world/app.js"))
    css = _read("console/world/styles.css")
    assert "body:not([data-truth-synced]) #modeBadge" in css
    assert "body:not([data-truth-synced]) #scenario" in css


def test_every_counted_aircraft_is_drawable_searchable_and_linkable():
    """D6: the boot request is ?light=1 (no `states`), so the globe drew
    none of the counted aircraft and deep links/search found almost none."""
    app_js = _read("console/world/app.js")
    for fn in ("nowAircraftPoints", "findNowObject", "searchItems"):
        src = _fn_src(app_js, fn)
        assert "state.airNow?.positions" in src or "state.airNow.positions" in src, fn


def test_now_globe_lod_shows_real_layers_at_globe_zoom():
    """D6: replay minzooms (4-6) hid every real quake, fire and notice."""
    lod = _fn_src(_read("console/world/app.js"), "tuneNowLod")
    for layer in ("quake-ring", "quake-point", "fire-point", "notice-point"):
        assert f'"{layer}"' in lod, layer
    assert "setLayerZoomRange" in lod


def test_now_search_never_offers_synthetic_objects_or_demo_stories():
    """Search in WORLD NOW listed replay aircraft, fictional ports and
    'Story:' commands that select synthetic objects."""
    search = _fn_src(_read("console/world/app.js"), "searchItems")
    assert "if (!MODE_NOW) {" in search
    assert search.index("if (!MODE_NOW) {") < search.index("u.aircraft")
    assert "!(MODE_NOW && /^Story:/.test(c.label))" in search


def test_now_drawer_shows_why_flagged_and_honest_precision():
    """Important Now reasons were API-only; coordinates showed 15 decimals."""
    app_js = _read("console/world/app.js")
    why = _fn_src(app_js, "importantWhy")
    assert "it.reasons" in why and "observed_or_inferred" in why
    assert "state.importantV2?.n" in why  # same total as the HUD chip
    assert "${ev.lat}, ${ev.lon}" not in app_js
    assert "formatLatLon(ev.lat, ev.lon)" in app_js


def test_open_sources_deep_link_works_in_world_now():
    """D10: ?open=sources was handled only on the replay path."""
    opening = _fn_src(_read("console/world/app.js"), "openingNow")
    assert 'QS.get("open") === "sources"' in opening
    assert opening.count("await finish();") >= 3
