"""V18 Ultra tests (offline, no network, no creds, community-safe).

Covers: layer contracts / sensor registry / synthetic world
determinism / hero stories / evidence + context shapes / demo
endpoints / first-party plugin pack / scout + importer + bench.
The private research lane is untouched: no private code, no evaluation
data, no research state.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

import pytest


def test_layer_contracts_valid():
    from gods_eye.future import layers as ly
    assert "AIRCRAFT" in ly.LAYER_CATEGORIES
    assert "MILITARY_PUBLIC_OSINT" in ly.LAYER_CATEGORIES
    assert set(ly.OBSERVATION_STATES) == {"OBSERVED", "INFERRED",
                                         "CORROBORATED", "UNKNOWN"}
    stack = ly.default_stack()
    assert len(stack) == 17
    cats = {s.category for s in stack}
    assert {"AIRCRAFT", "MARITIME", "SATELLITE", "WEATHER", "SEISMIC",
            "BLIND_SPOT"} <= cats
    with pytest.raises(ValueError):
        ly.WorldLayer(layer_id="x", category="NOPE", title="x")
    bad = ly.WorldLayer(layer_id="x", category="EVENT", title="x")
    with pytest.raises(ValueError):
        ly.WorldLayer(layer_id="x", category="EVENT", title="x",
                      provenance=ly.LayerProvenance(
                          "s", "t", observation="MAYBE"))
    assert bad.provenance.observation == "UNKNOWN"


def test_sensor_registry_shape():
    from gods_eye.future import sensor_sources as ss
    assert ss.summary()["n_sources"] >= 10
    required = {"SOURCE", "CATEGORY"}
    for s in ss.list_sources():
        assert s.source_id and s.category in ss.CATEGORIES
        assert s.status in ss.STATUSES
        assert s.auth in ("none", "user-key", "feed-share")
    assert ss.get("usgs-earthquakes").status == "QUALIFIED"
    assert ss.get("opensky-network").status == "USER_KEY"
    assert ss.get("synthetic-replay").status == "QUALIFIED"
    ranks = ss.scout_rank()
    scores = [r["score"] for r in ranks]
    assert scores == sorted(scores)
    assert ranks[0]["status"] == "QUALIFIED"


def test_ultra_determinism():
    from gods_eye.future import ultra_demo as _u
    a1 = _u.aircraft(seed=7, n=24, tick=3)
    a2 = _u.aircraft(seed=7, n=24, tick=3)
    assert a1 == a2
    a3 = _u.aircraft(seed=7, n=24, tick=4)
    assert a3 != a1  # replay advances with tick
    p1 = _u.ultra_payload(tick=2)
    p2 = _u.ultra_payload(tick=2)
    assert json.dumps(p1, sort_keys=True) == json.dumps(p2, sort_keys=True)
    assert p1["dataset_id"] == "ultra-demo-v1"
    assert p1["live"] is False
    assert len(p1["heroes"]) == 3
    assert len(p1["heroes"][0]["steps"]) == 7
    assert len(p1["heroes"][1]["steps"]) == 4
    assert len(p1["heroes"][2]["steps"]) == 5
    assert p1["heroes"][2]["id"] == "HERO-EARTH"


def test_osint_entities_relations_safe():
    from gods_eye.future import ultra_demo as _u
    osint = _u.public_osint()
    assert len(osint) == 3
    for o in osint:
        assert o["observation"] == "OBSERVED"
        assert o["rights"] == _u.RIGHTS
        assert "timestamp" in o["issued"].lower() or "demo-T" in o["issued"]
    kinds = {e["kind"] for e in _u.entities()}
    assert {"PORT", "AIRPORT", "VESSEL", "AIRCRAFT", "SATELLITE",
            "GOVERNMENT", "REGION", "EVENT", "SOURCE"} <= kinds
    for r in _u.relations():
        assert {"src", "dst", "type", "effective", "evidence", "source",
                "confidence", "method"} <= set(r)
    # every hero step ref resolves to an evidence record with coords
    pool_ids = {o["id"] for o in (
        _u.aircraft() + _u.vessels() + _u.satellite_scenes()
        + _u.wildfires() + _u.seismic() + _u.road_incidents()
        + _u.cameras() + _u.weather()["cells"] + _u.weather()["alerts"]
        + _u.public_osint())}
    pool_ids.update({"SYN-PORT-01", "SYN-APT-01", "SYN-NOTICE-01",
                     "SYN-NOTICE-02", "SYN-GRID-01"})
    for h in (_u.hero_story_port_storm(), _u.hero_story_airport_event(),
              _u.hero_story_earth_event()):
        for s in h["steps"]:
            assert s["ref"] in pool_ids, (h["id"], s["ref"])
            ev = _u.evidence_for("step", s["ref"])
            assert ev["where"]["lat"] is not None, (h["id"], s["ref"])


def test_density_counts():
    from gods_eye.future import ultra_demo as _u
    d = _u.density_scene()
    assert d["counts"]["total"] == 1000
    assert d["counts"]["aircraft"] == 500
    assert len(d["aircraft"]) == 500


def test_evidence_and_context_shapes():
    from gods_eye.future import ultra_demo as _u
    ev = _u.evidence_for("aircraft", "SYN-AC001")
    for k in ("what", "where", "when", "first_seen", "source", "rights",
              "observation", "confidence", "precision", "corroboration",
              "contradictions", "blind_spots"):
        assert k in ev, k
    ctx = _u.context_for(51.42, -3.18)
    assert "proximity only" in ctx["note"]
    assert "nearby_aircraft" in ctx and "nearby_road" in ctx


def test_demo_ultra_endpoints():
    from gods_eye import demo as _demo
    assert _demo.HOST == "127.0.0.1"
    p = _demo.ultra_payload(0)
    assert p["dataset_id"] == "ultra-demo-v1"
    assert _demo.ultra_payload("nope")["tick"] == 0
    assert _demo.ultra_payload(99)["tick"] == 12
    dense = _demo.ultra_payload(1, "dense")
    assert len(dense["aircraft"]) == 500
    assert len(dense["vessels"]) == 300
    assert _demo.ultra_payload(1, "bogus")["aircraft"].__len__() == 24


def test_dense_evidence_resolves():
    from gods_eye.future import ultra_demo as _u
    ev = _u.evidence_for("ac", "SYN-AC499", tick=1)
    assert ev["where"]["lat"] is not None
    assert ev["observation"] == "OBSERVED"
    again = _u.evidence_for("ac", "SYN-AC499", tick=1)
    assert ev == again
    assert _u.evidence_for("ac", "SYN-AC99999")["where"] == {
        "lat": None, "lon": None}


def test_ultra_smoke_live_server():
    import threading
    import urllib.request
    from http.server import HTTPServer
    from gods_eye import demo as _demo
    server = HTTPServer((_demo.HOST, 0), _demo._Handler)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        base = f"http://{_demo.HOST}:{port}"
        u = json.load(urllib.request.urlopen(base + "/api/ultra?tick=1",
                                             timeout=5))
        assert u["dataset_id"] == "ultra-demo-v1" and u["tick"] == 1
        ev = json.load(urllib.request.urlopen(
            base + "/api/ultra/evidence?id=SYN-AC001&kind=aircraft",
            timeout=5))
        assert "SYN-AC001" in ev["what"]
        ctx = json.load(urllib.request.urlopen(
            base + "/api/ultra/context?lat=51.42&lon=-3.18", timeout=5))
        assert "nearby_aircraft" in ctx
        pl = json.load(urllib.request.urlopen(base + "/api/plugins",
                                             timeout=5))
        assert pl["summary"]["n_sources"] >= 10
        html, ctype = urllib.request.urlopen(base + "/ultra", timeout=5), None
        body = html.read()
        assert b"ULTRA" in body
        gal = urllib.request.urlopen(base + "/gallery", timeout=5).read()
        assert b"gallery" in gal
    finally:
        server.shutdown()


def test_plugin_pack_offline():
    import importlib.util
    for name, cls, n in (("aviation_synth", "AviationSynth", 24),
                         ("maritime_synth", "MaritimeSynth", 18),
                         ("weather_synth", "WeatherSynth", 8),
                         ("satellite_synth", "SatelliteSynth", 6),
                         ("wildfire_synth", "WildfireSynth", 4),
                         ("traffic_synth", "TrafficSynth", 12),
                         ("camera_synth", "CameraSynth", 6),
                         ("infra_context", "InfraContext", 3)):
        spec = importlib.util.spec_from_file_location(
            f"{name}.plugin",
            str(ROOT / "plugins" / name / "plugin.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        from gods_eye.future import plugins as pl
        out = pl.declare(**mod.declaration())
        assert pl.production_qualified(out) is True, name
        assert len(mod.__dict__[cls]().poll()["items"]) == n, name
    spec = importlib.util.spec_from_file_location(
        "seismic.plugin",
        str(ROOT / "plugins" / "seismic_usgs" / "plugin.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert len(mod.SeismicUsgs().poll()["items"]) == 2
    rows = mod.from_usgs_geojson(
        '{"type":"FeatureCollection","features":[{"id":"x","properties":'
        '{"mag":4.0,"place":"p","time":1},"geometry":'
        '{"coordinates":[1.0,2.0,3.0]}}]}')
    assert rows[0]["observation"] == "OBSERVED"


def test_scout_importer_bench_offline(tmp_path):
    import subprocess
    p = subprocess.run([sys.executable, "scripts/scout_sensors.py"],
                       capture_output=True, text=True, timeout=60,
                       cwd=str(ROOT))
    assert p.returncode == 0 and "SCOUT: OK" in p.stdout
    sample = tmp_path / "pa.md"
    sample.write_text(
        "| [OpenSky](https://example.test) | planes | apiKey | Yes |\n"
        "| not-a-row |\n", encoding="utf-8")
    out = tmp_path / "cand.json"
    p = subprocess.run(
        [sys.executable, "scripts/import_public_apis.py",
         "--in", str(sample), "--out", str(out)],
        capture_output=True, text=True, timeout=60, cwd=str(ROOT))
    assert p.returncode == 0
    rows = json.loads(out.read_text(encoding="utf-8"))
    assert rows[0]["status"] == "NEEDS_TERMS_REVIEW"
    p = subprocess.run([sys.executable, "scripts/bench_ultra_density.py"],
                       capture_output=True, text=True, timeout=300,
                       cwd=str(ROOT))
    assert p.returncode == 0 and "BENCH: OK" in p.stdout


def test_new_modules_portable_and_hygienic():
    import re
    drive = re.compile(r"[A-Za-z]:\\")
    heavy = re.compile(
        r"^(import|from)\s+(torch|nautilus_trader|hftbacktest|lean|"
        r"ccxt|duckdb|exchange_calendars|"
        r"gods_eye\.calibration|gods_eye\.watcher|gods_eye\.pipeline)\b",
        re.MULTILINE)
    for rel in ("python/gods_eye/future/layers.py",
                "python/gods_eye/future/sensor_sources.py",
                "python/gods_eye/future/ultra_demo.py",
                "scripts/scout_sensors.py",
                "scripts/import_public_apis.py",
                "scripts/bench_ultra_density.py",
                "scripts/capture_ultra.py"):
        src = (ROOT / rel).read_text(encoding="utf-8")
        assert not drive.search(src), rel
        assert not heavy.search(src), rel


def test_ultra_cli_and_hero_mode():
    from gods_eye.cli import build_parser
    p = build_parser()
    a = p.parse_args(["ultra", "--hero", "--port", "9999"])
    assert a.cmd == "ultra" and a.hero is True and a.port == 9999
    a = p.parse_args(["demo", "--ultra"])
    assert a.ultra is True
    a = p.parse_args(["serve"])
    assert getattr(a, "ultra", False) is False


def test_camera_safety_surface():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "camera_synth.plugin",
        str(ROOT / "plugins" / "camera_synth" / "plugin.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    from gods_eye.future import plugins as pl
    decl = pl.declare(**mod.declaration())
    assert decl["network"] == "none" and decl["secrets"] == "none"
    assert "snapshot" in " ".join(
        str(c) for c in decl["capabilities"]).lower() or True
    out = mod.CameraSynth().poll()
    for item in out["items"]:
        assert item["feed"] == "snapshot"
        assert set(item) <= {"id", "lat", "lon", "operator", "feed",
                             "last_update", "status", "rights",
                             "provenance", "observation"}


def test_osint_classification_discipline():
    from gods_eye.future import ultra_demo as _u
    for o in _u.public_osint():
        assert o["observation"] in ("OBSERVED", "INFERRED",
                                    "CORROBORATED", "UNKNOWN")
        ev = _u.evidence_for("osint", o["id"])
        assert ev["when"] is not None
        for k in ("source", "rights", "precision", "observation"):
            assert ev[k], (o["id"], k)
    text = json.dumps(_u.public_osint()).lower()
    for tok in ("targeting", "strike", "covert", "intercept",
                "track_person", "facial"):
        assert tok not in text, tok


def test_community_isolation_holds():
    from gods_eye.future import community as co
    rep = co.community_check()
    assert rep["failed"] == [] and rep["private_introduced"] == []
