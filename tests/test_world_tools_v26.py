"""V2.4 JARVIS text tool layer tests (offline — providers mocked).

Covers: result envelope / unknown tool / fly_to / select / track
supported+unsupported / query_region / query_changes / query_important /
query_observations / query_imagery_freshness / replay entry + return /
layer toggle / deterministic parser + example commands / context /
truth+warning propagation / unavailable honesty / no model-memory
fallback / no private fields / boundary / replay isolation /
deep-link serialization + credential exclusion / API compatibility.
"""

from __future__ import annotations

import json
import sys
import threading
import urllib.parse
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


def _change(cid="chg:gdacs-new-flood", title="Flood in the valley"):
    return {
        "id": cid, "type": "gdacs-new", "category": "DISASTER",
        "title": title, "location": {"lat": 47.0, "lon": 9.0},
        "first_observed": "2026-09-10T12:00:00+00:00",
        "last_observed": "2026-09-10T12:00:00+00:00",
        "effective_time": "2026-09-10T12:00:00+00:00",
        "before": {}, "after": {},
        "magnitude": {"area_m2": None, "detail": "area not stated"},
        "confidence": "MODERATE", "observation_type": "OBSERVED",
        "corroboration": "ONE SOURCE", "source_count": 1,
        "corroborating_keys": [],
        "evidence": [{"source": "gdacs", "stable_key": "k",
                      "fields": {"event_type": "FL"}}],
        "freshness": {}, "rights": {}, "why_flagged": ["water rising"],
        "rank": {}, "severity": "WATCH",
        "real_data": True, "live": False,
    }


# ------------------------------------------------------- envelope ---


def test_tool_result_envelope():
    out = tools.execute("return_to_now", {}, CTX)
    assert out["status"] in tools.STATUSES
    assert set(out) >= {"status", "tool", "generated_at", "truth_mode",
                        "data", "warnings", "source_count",
                        "evidence_refs"}
    assert out["status"] == "SUCCESS"


def test_unknown_tool():
    out = tools.execute("launch_missiles", {}, CTX)
    assert out["status"] == "FAILED"
    assert "unknown tool" in out["note"]
    assert "fly_to" in out["note"]


def test_fly_to():
    out = tools.execute("fly_to", {"place": "Tokyo"}, CTX)
    assert out["status"] == "SUCCESS"
    assert out["data"]["action"] == "fly"
    assert abs(out["data"]["lat"] - 35.7) < 0.01
    bad = tools.execute("fly_to", {"place": "Atlantis"}, CTX)
    assert bad["status"] == "FAILED"
    bad2 = tools.execute("fly_to", {"lat": 999, "lon": 0}, CTX)
    assert bad2["status"] == "FAILED"


def test_select_entity():
    with mock.patch.object(tools, "_change_by_id",
                           return_value=_change()):
        out = tools.execute("select_entity",
                            {"id": "chg:gdacs-new-flood"}, CTX)
    assert out["status"] == "SUCCESS"
    assert out["data"]["action"] == "select"
    missing = tools.execute("select_entity", {"id": "chg:nope"}, CTX)
    assert missing["status"] == "FAILED"


def test_track_supported_entity():
    snap = {"states": [{"icao24": "abc123", "callsign": "DLH1",
                        "lat": 47.0, "lon": 9.0, "track_deg": 90.0,
                        "gs_kt": 400.0, "baro_alt_ft": 35000.0,
                        "source": "adsb.lol"}]}
    with mock.patch("gods_eye.future.world_air.get_aviation",
                     return_value=snap):
        with mock.patch("gods_eye.future.world_air.get_trail",
                         return_value=[{"lat": 47.0, "lon": 9.0}]):
            out = tools.execute("track_entity", {"id": "AIR:abc123"},
                                CTX)
    assert out["status"] == "SUCCESS"
    ent = out["data"]["entity"]
    assert ent["heading"] == 90.0 and ent["speed"] == 400.0
    assert ent["altitude"] == 35000.0
    assert out["data"]["trail_available"] is True


def test_track_unsupported_entity():
    with mock.patch.object(tools, "_change_by_id",
                           return_value=_change()):
        out = tools.execute("track_entity",
                            {"id": "chg:gdacs-new-flood"}, CTX)
    assert out["status"] == "UNAVAILABLE"
    assert "open_evidence" in out["note"]
    out2 = tools.execute("track_entity", {"id": "BOGUS-1"}, CTX)
    assert out2["status"] in ("FAILED", "UNAVAILABLE")


def test_query_region():
    with mock.patch.object(tools, "_changes",
                           return_value=[_change()]):
        with mock.patch("gods_eye.future.world_air.get_aviation",
                         return_value={"states": []}):
            out = tools.execute("query_region",
                                {"lat": 47.0, "lon": 9.0}, CTX)
    assert out["status"] == "SUCCESS"
    data = out["data"]
    assert set(data) >= {"point", "here", "changed", "moving",
                         "can_see_it", "important", "uncertain"}
    assert data["here"]["changes"] == 1
    assert "PARTIAL" in " ".join(data["uncertain"])


def test_query_changes():
    rows = [_change(), _change(cid="chg:eonet-opened-wf",
                               title="Wildfire near hills")]
    rows[1]["type"] = "eonet-opened"
    rows[1]["location"] = {"lat": 48.0, "lon": 11.0}
    rows[1]["evidence"] = [{"source": "nasa-eonet", "stable_key": "k",
                            "fields": {"categories": ["Wildfire"]}}]
    with mock.patch.object(tools, "_changes", return_value=rows):
        out = tools.execute("query_changes",
                            {"region": "europe",
                             "category": "wildfire"}, CTX)
    assert out["status"] == "SUCCESS"
    assert out["data"]["count"] == 1
    assert out["evidence_refs"] == ["chg:eonet-opened-wf"]
    bad = tools.execute("query_changes", {"region": "atlantis"}, CTX)
    assert bad["status"] == "FAILED"


def test_query_important():
    rows = [_change()]
    with mock.patch.object(tools, "_changes", return_value=rows):
        with mock.patch("gods_eye.future.world_air.get_aviation",
                         return_value={"states": [],
                                       "important": []}):
            out = tools.execute("query_important", {}, CTX)
    assert out["status"] == "SUCCESS"
    assert out["data"]["important"]


def test_query_observations():
    with mock.patch.object(tools, "_change_by_id",
                           return_value=_change()):
        with mock.patch(
                "gods_eye.future.world_imagery.get_imagery",
                return_value={"status": "NOT_ELIGIBLE",
                              "before": None, "after": None}):
            with mock.patch(
                    "gods_eye.future.world_sar.get_observations",
                    return_value={"status": "NOT_ELIGIBLE",
                                  "before": None, "after": None}):
                out = tools.execute(
                    "query_observations",
                    {"change_id": "chg:gdacs-new-flood",
                     "modality": "MULTI_SENSOR"}, CTX)
    assert out["status"] in ("SUCCESS", "PARTIAL")
    assert "modalities" in out["data"]
    ir = tools.execute("query_observations",
                       {"change_id": "x"}, CTX)
    assert ir["status"] == "FAILED"
    with mock.patch.object(tools, "_change_by_id",
                           return_value=_change()):
        thermal = tools.execute(
            "query_observations",
            {"change_id": "chg:gdacs-new-flood",
             "modality": "THERMAL"}, CTX)
    assert thermal["status"] == "UNAVAILABLE"


def test_query_imagery_freshness():
    status = {"selected": "VIIRS_SNPP_TrueColor",
              "layers": [{"source": "NASA GIBS",
                          "dataset": "VIIRS",
                          "captured_at": "2026-09-19T10:00:00Z",
                          "age_seconds": 1800,
                          "freshness_class": "VERY_FRESH",
                          "resolution_m": 250,
                          "coverage_quality": "global",
                          "rights": {}, "rights_status": "OK"}]}
    with mock.patch("gods_eye.future.world_earth.get_status",
                     return_value=status):
        out = tools.execute("query_imagery_freshness",
                            {"place": "california",
                             "max_age_hours": 1.0}, CTX)
    assert out["status"] == "SUCCESS"
    layer = out["data"]["layers"][0]
    assert set(layer) >= {"source", "dataset", "captured_at",
                          "age_hours", "freshness_class",
                          "resolution_m", "coverage", "rights"}
    bad = tools.execute("query_imagery_freshness",
                        {"place": "atlantis"}, CTX)
    assert bad["status"] == "FAILED"


def test_replay_entry_and_return():
    out = tools.execute("enter_replay", {"hours_ago": 6}, CTX)
    assert out["status"] == "SUCCESS"
    assert out["data"]["action"] == "enter_replay"
    assert out["truth_mode"] == "REPLAY"
    back = tools.execute("return_to_now", {}, CTX)
    assert back["status"] == "SUCCESS"
    assert back["data"]["action"] == "return_to_now"


def test_layer_toggle():
    out = tools.execute("toggle_layer", {"layer": "wildfire",
                                         "on": True}, CTX)
    assert out["status"] == "SUCCESS"
    assert out["data"]["layer"] == "wildfire"
    bad = tools.execute("toggle_layer", {"layer": "death-star"},
                        CTX)
    assert bad["status"] == "FAILED"
    assert "wildfire" in bad["note"]


# -------------------------------------------------------- parser ---


def test_deterministic_parser():
    assert tools.parse_intent("show changes today", CTX)["calls"][
        0]["tool"] == "query_changes"
    assert tools.parse_intent("replay 6h", CTX)["calls"][0] == {
        "tool": "enter_replay", "args": {"hours_ago": 6.0}}
    assert tools.parse_intent("return to now", CTX)["calls"][0][
        "tool"] == "return_to_now"
    assert tools.parse_intent("track selected",
                              {**CTX, "selected": "AIR:abc"})["calls"][
        0]["args"] == {"id": "AIR:abc"}
    assert tools.parse_intent("gibberish xyzzy qqq", CTX)[
        "calls"] == []


def test_show_changes_today():
    out = tools.run_command("show changes today", CTX)
    assert out["calls"] and out["calls"][0]["tool"] == "query_changes"
    assert out["calls"][0]["args"]["since"] is not None
    assert out["results"]


def test_replay_6h_command():
    out = tools.run_command("replay 6h", CTX)
    assert out["results"][0]["status"] == "SUCCESS"
    assert out["results"][0]["data"]["hours_ago"] == 6.0


def test_nearest_aircraft_command():
    snap = {"states": [{"icao24": "a1", "callsign": "X1", "lat": 47.6,
                        "lon": 14.6, "baro_alt_ft": 30000.0,
                        "gs_kt": 450.0}]}
    with mock.patch("gods_eye.future.world_air.get_aviation",
                     return_value=snap):
        out = tools.run_command("nearest aircraft", CTX)
    assert out["calls"][0]["tool"] == "query_contacts"
    res = out["results"][0]
    assert res["status"] == "SUCCESS"
    assert res["data"]["contacts"][0]["class"] == "AIRCRAFT"


def test_radar_evidence_command():
    out = tools.run_command("radar evidence",
                            {**CTX, "selected": "chg:zz"})
    assert out["calls"][0]["tool"] == "query_observations"
    assert out["calls"][0]["args"]["modality"] == "SAR"


def test_context_propagation():
    out = tools.run_command("what is here",
                            {"lat": 1.0, "lon": 2.0})
    assert out["calls"][0]["tool"] == "query_region"
    with mock.patch.object(tools, "_changes", return_value=[]):
        with mock.patch("gods_eye.future.world_air.get_aviation",
                         return_value={"states": []}):
            res = tools.run_command("what is here",
                                    {"lat": 1.0, "lon": 2.0})
    assert res["results"][0]["data"]["point"] == {
        "lat": 1.0, "lon": 2.0, "radius_km": 250.0}


def test_truth_and_warning_propagation():
    with mock.patch.object(tools, "_changes", return_value=[]):
        with mock.patch("gods_eye.future.world_air.get_aviation",
                         side_effect=RuntimeError("down")):
            out = tools.run_command("what is here",
                                    {"lat": 1.0, "lon": 2.0})
    res = out["results"][0]
    assert res["truth_mode"] == "REAL"
    assert res["warnings"] == ["aircraft leg unavailable"]


def test_unavailable_result_honesty():
    out = tools.execute("query_observations",
                        {"change_id": "chg:ok", "modality": "IR"},
                        CTX)
    assert out["status"] == "UNAVAILABLE"
    assert "IR" in out["note"] or "thermal" in out["note"].lower()
    out2 = tools.parse_intent("hello", CTX, provider="REMOTE_LLM")
    assert "not wired" in out2["note"]


def test_no_model_memory_fallback():
    parsed = tools.parse_intent("tell me about Paris", CTX)
    assert parsed["calls"] and parsed["calls"][0]["tool"] == "fly_to"
    res = tools.run_command("tell me about Paris", CTX)
    assert res["results"][0]["status"] == "SUCCESS"
    blob = json.dumps(res["results"][0])
    assert "Eiffel" not in blob and "Seine" not in blob


def test_no_private_fields():
    import re
    for rel in ("python/gods_eye/future/world_tools.py",
                "tests/test_world_tools_v26.py"):
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


def test_public_private_boundary():
    src = (ROOT / "python" / "gods_eye" / "future"
           / "world_tools.py").read_text(encoding="utf-8")
    assert "gods_eye" + "_private" not in src
    assert "import world_tools" not in src.replace(
        "world_tools.py", "")
    from gods_eye.future import world_tools as t
    assert set(t.TOOLS) <= {"fly_to", "set_view", "select_entity",
                            "track_entity", "stop_tracking",
                            "set_camera_mode", "track_nearest",
                            "toggle_layer", "query_region",
                            "query_contacts", "query_changes",
                            "query_important", "query_observations",
                            "query_imagery_freshness", "query_satellites",
                            "open_evidence",
                            "set_time", "enter_replay", "return_to_now"}
    assert {"set_camera_mode", "track_nearest",
            "query_satellites"} <= set(t.TOOLS)


def test_replay_isolation():
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
    assert "world_tools" not in blob
    assert "/api/world/tools" not in blob


def test_deep_link_serialization():
    src = (ROOT / "console" / "world" / "app.js").read_text(encoding="utf-8")
    for param in ("bearing", "pitch", "layers", "tick", "zoom", "event",
                  "aircraft"):
        assert f'q.set("{param}"' in src or f"'{param}'" in src, param
    low = src.lower()
    for secret in ("api_key", "apikey", "token", "password", "secret"):
        assert secret not in low.split("writedeeplink")[1].split(
            "function opennowregion")[0], secret


def test_credential_exclusion():
    out = tools.run_command("show changes today", CTX)
    blob = json.dumps(out)
    assert "TELLURION_CDSE" not in blob
    assert "OPENAI" not in blob
    assert "api_key" not in blob.lower()


def test_existing_api_compatibility():
    from gods_eye import demo as _demo
    server = HTTPServer((_demo.HOST, 0), _demo._Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        base = f"http://{_demo.HOST}:{server.server_address[1]}"
        params = urllib.parse.urlencode({"q": "return to now",
                                         "mode": "now"})
        with urllib.request.urlopen(base + "/api/world/tools?"
                                    + params, timeout=60) as r:
            payload = json.load(r)
        with urllib.request.urlopen(
                base + "/api/world/imagery/status?norefresh=1",
                timeout=60) as r:
            status = json.load(r)
    finally:
        server.shutdown()
    assert payload["results"][0]["status"] == "SUCCESS"
    assert "layers" in status
