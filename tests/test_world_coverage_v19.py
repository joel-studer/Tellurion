"""World-coverage tests (offline, no network, no creds, public-safe).

Covers: truth model / registry expansion / global synthetic world /
live-leg pure parsers / world API endpoints / new plugins /
performance / privacy + rights audits.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))


def test_truth_model():
    from gods_eye.future import layers as ly
    assert set(ly.TRUTH_MODES) == {"LIVE", "DELAYED", "STATIC", "REPLAY",
                                   "SYNTHETIC"}
    assert set(ly.TIME_MODES) == set(ly.TRUTH_MODES)
    for cat in ("VOLCANO", "TRANSIT", "AIR_QUALITY", "SPACE_WEATHER",
                "HUMANITARIAN", "NEWS", "SPACE"):
        assert cat in ly.LAYER_CATEGORIES, cat
    assert ly.truth_label("SYNTHETIC") == "SYNTHETIC WORLD REPLAY"
    obs = ly.make_observation(
        source="usgs-earthquakes", precision="REGIONAL",
        rights="US public domain", provenance="USGS",
        observation_type="OBSERVED")
    assert obs["source_event_time"] == "UNKNOWN"
    assert obs["effective_time"] == "UNKNOWN"
    try:
        ly.make_observation(source="x", observation_type="MAYBE")
        raise AssertionError("must refuse unknown observation_type")
    except ValueError:
        pass
    try:
        ly.truth_label("LIVEISH")
        raise AssertionError("must refuse unknown truth mode")
    except ValueError:
        pass


def test_registry_expansion():
    from gods_eye.future import sensor_sources as ss
    assert ss.summary()["n_sources"] >= 20
    for sid, status in (("noaa-swpc", "QUALIFIED"),
                        ("gdacs-alerts", "QUALIFIED"),
                        ("reliefweb-reports", "QUALIFIED"),
                        ("copernicus-ems", "QUALIFIED"),
                        ("usgs-volcanoes", "QUALIFIED"),
                        ("osm-overpass", "QUALIFIED"),
                        ("celestrak", "NEEDS_TERMS_REVIEW"),
                            ("gdelt-events", "QUALIFIED"),
                        ("nasa-firms", "USER_KEY")):
        assert ss.get(sid).status == status, sid
    from gods_eye.rights import registry as rg
    for sid in ("usgs_earthquakes", "nws_alerts", "noaa_swpc",
                "nasa_eonet", "osm_overpass", "gdelt", "celestrak"):
        assert rg.lookup(sid) is not None, sid
    assert rg.lookup("celestrak").commercial_use == "UNKNOWN"


def test_world_determinism_and_counts():
    from gods_eye.future import world_demo as w
    p1 = w.world_payload(tick=2, density="standard")
    p2 = w.world_payload(tick=2, density="standard")
    assert json.dumps(p1, sort_keys=True) == json.dumps(p2, sort_keys=True)
    assert p1["dataset_id"] == "tellurion-world-v1"
    assert p1["live"] is False
    assert p1["truth_mode"] == "SYNTHETIC"
    assert p1["total_objects"] >= 3000
    dense = w.world_payload(tick=0, density="dense")
    assert dense["total_objects"] >= 5000
    full = w.world_payload(tick=0, density="full")
    assert full["total_objects"] >= 10000
    acts = w.activity_summary(p1)["counts"]
    assert acts["aircraft"] == 1200 and acts["vessels"] == 900
    # every object carries source + rights + truth
    for key in ("aircraft", "vessels", "seismic", "wildfire",
                "satellites", "transit", "notices"):
        for o in p1[key][:5]:
            assert o["rights"] and o["provenance"], (key, o.get("id"))
            assert o["truth_mode"] == "SYNTHETIC", (key, o.get("id"))


def test_world_search_region_whatshere_feed():
    from gods_eye.future import world_demo as w
    p = w.world_payload(tick=0, density="standard")
    hits = w.search_world("vienna", p)
    assert any(h["id"] == "APT-VIE" for h in hits)
    assert w.search_world("ISS", None) != []
    blocked = w.search_world("person tracking cctv", p)
    assert blocked and blocked[0]["kind"] == "blocked"
    assert w.search_world("x", p) == []  # too short
    reg = w.region_overview("Austria", p)
    assert reg["region"] == "Austria" and reg["center"]["lat"] == 47.52
    assert w.region_overview("Atlantis XYZ", p)["status"] == "UNKNOWN"
    # USA must never substring-match Busan again (regression).
    assert w.match_country("USA")["name"] == "United States"
    assert w.match_country("US")["name"] == "United States"
    assert w.match_country("UK")["name"] == "United Kingdom"
    assert w.match_country("Indonesia")["name"] == "Indonesia"
    assert w.match_country("Busan") is None
    assert w.region_overview("USA", p)["region"] == "United States"
    assert w.region_overview("UK", p)["region"] == "United Kingdom"
    assert w.region_overview("Indonesia", p)["region"] == "Indonesia"
    here = w.whats_here(48.2, 16.4, 250, p)
    assert "aircraft_density" in here["summary"]
    assert here["truth_mode"] == "SYNTHETIC"
    feed = w.event_feed(p, "DISASTER")
    assert feed and all(f["kind"] == "DISASTER" for f in feed)
    assert len(w.event_feed(p, "GLOBAL", limit=5)) == 5
    ev = w.evidence_for_world("WLD-AC00000", p)
    assert ev["truth_mode"] == "SYNTHETIC"
    assert ev["when"] != ""
    assert w.evidence_for_world("NOPE-1", p)["observation"] == "UNKNOWN"
    assert len(w.blindspot_grid()) >= 6
    assert any(s["source_id"] == "synthetic-world"
               for s in w.source_health_snapshot())


def test_live_parsers_pure_and_safe():
    from gods_eye.future import world_live as lv
    usgs = lv.parse_usgs(
        '{"type":"FeatureCollection","features":[{"id":"us1",'
        '"properties":{"mag":5.2,"place":"100km offshore",'
        '"time":"2026-01-01T00:00:00Z"},"geometry":'
        '{"coordinates":[140.0,38.0,10.0]}}]}')
    assert usgs[0]["observation"] == "OBSERVED"
    assert usgs[0]["truth_mode"] == "DELAYED"
    # bad coords are skipped, not crashed
    assert lv.parse_usgs(
        '{"features":[{"id":"b","properties":{},"geometry":'
        '{"coordinates":[999,999]}}]}') == []
    nws = lv.parse_nws_alerts(
        '{"features":[{"properties":{"id":"n1","event":"Tornado Warning",'
        '"sent":"2026-01-01T00:00:00Z"},"geometry":'
        '{"coordinates":[[[-97,38],[-96,38],[-96,39],[-97,39]]]}}]}')
    assert nws[0]["observation_type"] == "GOVERNMENT_NOTICE"
    eonet = lv.parse_eonet(
        '{"events":[{"id":"e1","title":"Wildfire","status":"open",'
        '"categories":[{"title":"Wildfires"}],"geometry":'
        '[{"date":"2026-01-01T00:00:00Z","coordinates":[10.0,20.0]}]}]}')
    assert eonet[0]["category"] == "DISASTER"
    gdacs = lv.parse_gdacs(
        '{"features":[{"properties":{"eventid":"g1"},"geometry":'
        '{"coordinates":[30.0,40.0]}}]}')
    assert gdacs[0]["provenance"].startswith("GDACS")
    rw = lv.parse_reliefweb(
        '{"data":[{"id":"1","fields":{"title":"Flood update",'
        '"source":[{"name":"OCHA"}],"country":[{"name":"Sudan"}],'
        '"date":{"created":"2026-01-01"},"url":"https://x"}}]}')
    assert rw[0]["observation_type"] == "PUBLIC_REPORT"
    sw = lv.parse_swpc('[{"kp":"4"}]')
    assert sw["provenance"] == "NOAA SWPC"
    try:
        lv.parse_usgs("x" * (lv.MAX_PAYLOAD_BYTES + 1))
        raise AssertionError("must refuse oversize payloads")
    except ValueError:
        pass
    c = lv.SourceCache(ttl_s=60)
    assert c.get("k") is None
    c.put("k", [1])
    assert c.get("k") == [1]
    for _ in range(3):
        c.record_failure("q")
    assert c.circuit_open("q") is True


def test_world_api_endpoints():
    """Globe-tree contracts: replay scene routes serve world_scene, and
    the ported world_demo library is exercised directly (it has no HTTP
    routes in this tree — /api/world belongs to the replay scene)."""
    import threading
    import urllib.request
    from http.server import HTTPServer
    from gods_eye import demo as _demo
    from gods_eye.future import world_scene as _ws
    server = HTTPServer((_demo.HOST, 0), _demo._Handler)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        base = f"http://{_demo.HOST}:{port}"

        def get(path):
            return json.load(urllib.request.urlopen(base + path, timeout=30))

        scene = get("/api/world?tick=2")
        assert scene["tick"] == 2
        assert "epoch" in scene and scene["synthetic"] is True
        assert get("/api/world/presets")["presets"] != []
        try:
            urllib.request.urlopen(base + "/api/world/export?layer=celestrak",
                                   timeout=10)
            raise AssertionError("no bulk-export surface may exist here")
        except urllib.error.HTTPError as e:
            assert e.code == 404
    finally:
        server.shutdown()


def test_world_demo_library_direct():
    """world_demo ships as a library: payload/search/region/whatshere/
    activity/feed/health/blindspots/evidence behave without HTTP."""
    from gods_eye.future import world_demo as w
    p = w.world_payload(tick=0, density="standard")
    assert p["total_objects"] >= 3000
    assert w.search_world("vienna", p) != []
    assert w.region_overview("Japan", p)["region"] == "Japan"
    assert "aircraft_density" in w.whats_here(48.2, 16.4, 250, p)["summary"]
    assert w.activity_summary(p)["counts"]["aircraft"] == 1200
    assert w.event_feed(p, "WEATHER")[0]["kind"] == "WEATHER"
    assert len(w.source_health_snapshot()) >= 8
    assert w.blindspot_grid() != []
    assert "WLD-AC" in w.evidence_for_world("WLD-AC00001", p)["what"]


def test_new_plugins_offline():
    import importlib.util
    cases = (("weather_nws", "WeatherNws", "from_nws_geojson"),
             ("disaster_eonet", "DisasterEonet", "from_eonet_json"),
             ("space_swpc", "SpaceSwpc", "from_swpc_json"),
             ("austria_pack", "AustriaPack", None))
    for name, cls, fn in cases:
        spec = importlib.util.spec_from_file_location(
            f"{name}.plugin", str(ROOT / "plugins" / name / "plugin.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        from gods_eye.future import plugins as pl
        out = pl.declare(**mod.declaration())
        assert pl.production_qualified(out) is True, name
        assert len(mod.__dict__[cls]().poll()["items"]) >= 1, name
        assert "CC0" in mod.__dict__[cls]().poll()["rights"], name


def test_world_performance():
    from gods_eye.future import world_demo as w
    t0 = time.time()
    w.world_payload(tick=0, density="standard")
    assert time.time() - t0 < 2.0
    t0 = time.time()
    w.world_payload(tick=0, density="full")
    assert time.time() - t0 < 5.0


def test_privacy_and_rights_audits():
    import json as _j
    from gods_eye.future import world_demo as w
    blob = _j.dumps(w.world_payload(tick=0, density="standard")).lower()
    for tok in ("cctv", "rtsp", "onvif", "facial", "plate recognition",
                "intercept", "deanon", "strike guidance", "targeting",
                "password", "paywall", "track_person", "phone track"):
        assert tok not in blob, tok
    # no fake live claims in the world payload
    assert '"live": false' in blob
    assert "synthetic world replay" in blob
    # rights visible on every sampled object + sources
    p = w.world_payload(tick=0, density="standard")
    assert p["rights"].startswith("CC0")
    for src in p["health"]:
        assert src["state"] in ("ONLINE", "STANDBY", "KEY REQUIRED",
                                "RIGHTS BLOCKED", "DEGRADED", "STALE",
                                "OFFLINE", "RATE LIMITED", "AUTH REQUIRED")
        assert src["rights"] and src["detail"]
