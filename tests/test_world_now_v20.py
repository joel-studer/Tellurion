"""WORLD NOW tests (offline only — network is always mocked).

Covers: fetch hardening matrix / normalize + time semantics /
parsers incl. GDACS-RSS + GDELT + SWPC / dedup / linking + upstream
protection / no-synthetic guarantee / offline degradation / disk
cache / endpoints (mocked fetch) / privacy + rights rechecks.
"""

from __future__ import annotations

import io
import json
import sys
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

import pytest

from gods_eye.future import world_live as live
from gods_eye.future import world_now as now


# --------------------------------------------------------------------------
# Fixtures (minimal permissible shapes, hand-built for tests)
# --------------------------------------------------------------------------

USGS_OK = ('{"type":"FeatureCollection","features":[{"id":"us1",'
           '"properties":{"mag":5.2,"place":"offshore X",'
           '"time":1780000000000,"updated":1780000100000},'
           '"geometry":{"coordinates":[140.0,38.0,10.0]}}]}')

GDACS_OK = ('<rss version="2.0"><channel>'
            '<item><title>EQ title</title>'
            '<link>https://www.gdacs.org/report.aspx?eventtype=EQ&amp;eventid=7</link>'  # noqa: E501
            '<geo:lat xmlns:geo="http://www.w3.org/2003/01/geo/wgs84_pos#">38.1</geo:lat>'  # noqa: E501
            '<geo:long xmlns:geo="http://www.w3.org/2003/01/geo/wgs84_pos#">140.2</geo:long>'  # noqa: E501
            '<gdacs:eventtype xmlns:gdacs="x">EQ</gdacs:eventtype>'
            '<gdacs:eventid xmlns:gdacs="x">7</gdacs:eventid>'
            '<gdacs:alertlevel xmlns:gdacs="x">Orange</gdacs:alertlevel>'
            '<gdacs:fromdate xmlns:gdacs="x">Tue, 15 Sep 2026 12:00:00 GMT</gdacs:fromdate>'  # noqa: E501
            '</item></channel></rss>')

GDELT_OK = ('{"articles":[{"url":"https://example.com/q",'
            '"title":"Offshore X quake rattles coast",'
            '"seendate":"20260915T130000Z","domain":"example.com",'
            '"language":"English"}]}')

SWPC_OK = ('[{"product_id":"K1","issue_datetime":"2026-09-16 05:00:00",'
           '"message":"ALERT line\\nbody line"}]')

NWS_OK = ('{"features":[{"properties":{"id":"n1","event":"Flood Warning",'
          '"sent":"2026-09-16T00:00:00Z"},"geometry":null}]}')


class FakeHeaders:
    def __init__(self, ctype="application/json"):
        self._c = ctype

    def get_content_type(self):
        return self._c

    def get(self, k, d=""):
        return d


class FakeResp:
    def __init__(self, body, ctype="application/json"):
        self._b = body if isinstance(body, bytes) else body.encode()
        self.headers = FakeHeaders(ctype)
        self.status = 200

    def read(self, n=-1):
        if not self._b or n == 0:
            return b""
        if n is None or n < 0:
            out, self._b = self._b, b""
            return out
        out, self._b = self._b[:n], self._b[n:]
        return out


def router(mapping):
    def opener(req, timeout=None):
        for needle, value in mapping.items():
            if needle in req.full_url:
                if isinstance(value, Exception):
                    raise value
                body, ctype = value
                return FakeResp(body, ctype)
        raise AssertionError("unexpected url " + req.full_url)
    return opener


FULL_MAP = {
    "earthquake.usgs.gov": (USGS_OK, "application/json"),
    "eonet": ('{"events":[]}', "application/json"),
    "gdacs": (GDACS_OK, "application/xml"),
    "gdeltproject": (GDELT_OK, "application/json"),
    "alerts.json": (SWPC_OK, "application/json"),
    "noaa-scales": ('{"0": {"DateStamp": "2026-09-16"}}',
                    "application/json"),
    "api.weather.gov": (NWS_OK, "application/geo+json"),
}


@pytest.fixture()
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr(now, "_runtime_dir", lambda: tmp_path)
    now._memory.clear()
    now._health.clear()
    yield tmp_path
    now._memory.clear()
    now._health.clear()


# --------------------------------------------------------------------------
# Fetch hardening
# --------------------------------------------------------------------------

def test_fetch_ok_path(isolated_store):
    fr = now.fetch_url(
        "https://earthquake.usgs.gov/x", 20, ("application/json",),
        opener=router({"earthquake.usgs.gov": (USGS_OK,
                                               "application/json")}))
    assert fr.ok and fr.http_status == 200 and "FeatureCollection" in fr.text


def test_fetch_refuses_wrong_content_type(isolated_store):
    fr = now.fetch_url("https://earthquake.usgs.gov/x", 20,
                       ("application/json",),
                       opener=router({"earthquake.usgs.gov":
                                      ("<html>login</html>", "text/html")}))
    assert fr.ok is False and "content-type" in fr.detail


def test_fetch_refuses_huge_payload(isolated_store):
    big = "x" * (now.MAX_BYTES + 10)
    fr = now.fetch_url("https://example.test/big", 20, ("text/html",),
                       opener=router({"example.test": (big, "text/html")}))
    assert fr.ok is False and "exceeds" in fr.detail


def test_fetch_304_429_500_timeout(isolated_store):
    err429 = urllib.error.HTTPError("u", 429, "Too Many", {}, io.BytesIO(b"slow down"))  # noqa: E501
    fr = now.fetch_url("https://gdelt.test/", 20, ("application/json",),
                       opener=router({"gdelt.test": err429}))
    assert fr.ok is False and fr.http_status == 429
    err500 = urllib.error.HTTPError("u", 500, "Boom", {}, io.BytesIO(b"err"))  # noqa: E501
    fr = now.fetch_url("https://usgs.test/", 20, ("application/json",),
                       opener=router({"usgs.test": err500}))
    assert fr.ok is False and fr.http_status == 500
    fr = now.fetch_url("https://t.test/", 5, ("application/json",),
                       opener=router({"t.test": TimeoutError("timed out")}))
    assert fr.ok is False and "TimeoutError" in fr.detail


# --------------------------------------------------------------------------
# Parsers
# --------------------------------------------------------------------------

def test_gdacs_rss_parser():
    rows = live.parse_gdacs_rss(GDACS_OK)
    assert len(rows) == 1
    r = rows[0]
    assert (r["lat"], r["lon"]) == (38.1, 140.2)
    assert r["alert_level"] == "Orange"  # verbatim, not reinterpreted
    assert r["observation_type"] == "GOVERNMENT_NOTICE"
    assert r["truth_mode"] == "DELAYED"
    with pytest.raises(ValueError):
        live.parse_gdacs_rss("<not xml")
    # bad coords -> None, not crash
    bad = GDACS_OK.replace("38.1", "999").replace("140.2", "999")
    assert live.parse_gdacs_rss(bad)[0]["lat"] is None


def test_gdelt_parser():
    rows = live.parse_gdelt_artlist(GDELT_OK)
    assert len(rows) == 1
    r = rows[0]
    assert r["observation_type"] == "NEWS_REPORT"
    assert r["lat"] is None and r["lon"] is None
    assert rows == live.parse_gdelt_artlist(GDELT_OK)  # stable ids
    with pytest.raises(ValueError):
        live.parse_gdelt_artlist('{"nope": 1}')
    with pytest.raises(ValueError):
        live.parse_gdelt_artlist('{"articles": {}}')
    with pytest.raises(ValueError):
        live.parse_gdelt_artlist('not json')


def test_swpc_alerts_parser():
    rows = live.parse_swpc_alerts(SWPC_OK)
    assert rows[0]["title"] == "ALERT line"
    assert rows[0]["category"] == "SPACE_WEATHER"
    with pytest.raises(ValueError):
        live.parse_swpc_alerts('{"a": 1}')


def test_legacy_parsers_reject_garbage():
    for fn in (live.parse_usgs, live.parse_nws_alerts, live.parse_eonet):
        with pytest.raises(Exception):
            fn("definitely not json {{{")


# --------------------------------------------------------------------------
# Refresh pipeline: time semantics, dedup, TTL, degradation
# --------------------------------------------------------------------------

def test_refresh_timestamps_and_dedup(isolated_store):
    dup = ('{"type":"FeatureCollection","features":'
           '[{"id":"same","properties":{"mag":4.6,"time":1780000000000},'
           '"geometry":{"coordinates":[1.0,2.0,5.0]}},'
           '{"id":"same","properties":{"mag":4.7,"time":1780000000000},'
           '"geometry":{"coordinates":[1.0,2.0,5.0]}}]}')
    op = router({"earthquake.usgs.gov": (dup, "application/json")})
    res = now.refresh_source("usgs-earthquakes", force=True, opener=op)
    assert res["refreshed"] is True and res["n"] == 2
    items = now._memory["usgs-earthquakes"]["items"]
    keys = {i["stable_key"] for i in items}
    assert len(keys) == 2 and "usgs-earthquakes:same#2" in keys
    first = items[0]
    assert first["source_event_time"] != "UNKNOWN"
    assert first["ingested_at"] != first["source_event_time"]
    assert first["first_seen"] == first["ingested_at"]
    assert first["normalizer"] == now.NORMALIZER
    assert first["raw_hash"]
    # UNKNOWN event time stays UNKNOWN (never ingest-substituted)
    op2 = router({"earthquake.usgs.gov": (
        '{"features":[{"id":"u","properties":{},"geometry":'
        '{"coordinates":[1.0,2.0]}}]}', "application/json")})
    now.refresh_source("usgs-earthquakes", force=True, opener=op2)
    item = now._memory["usgs-earthquakes"]["items"][0]
    assert item["source_event_time"] == "UNKNOWN"
    assert item["effective_time"] == "UNKNOWN"


def test_ttl_and_force(isolated_store):
    op = router(FULL_MAP)
    now.refresh_source("usgs-earthquakes", force=True, opener=op)
    calls = []
    orig = now.fetch_url

    def counting(*a, **k):
        calls.append(1)
        return orig(*a, **k)
    import unittest.mock as mock
    with mock.patch.object(now, "fetch_url", counting):
        now.refresh_source("usgs-earthquakes", opener=op)
        assert calls == []  # TTL fresh: no fetch
        now.refresh_source("usgs-earthquakes", force=True, opener=op)
        assert len(calls) == 1


def test_degradation_matrix(isolated_store):
    # failure with memory -> STALE; without -> OFFLINE
    op_ok = router(FULL_MAP)
    now.refresh_source("usgs-earthquakes", force=True, opener=op_ok)
    op_bad = router({"earthquake.usgs.gov":
                     urllib.error.HTTPError("u", 500, "x", {},
                                            io.BytesIO(b"e"))})
    # force TTL expiry by clearing memory timestamp
    now._memory["usgs-earthquakes"]["at"] = 0
    res = now.refresh_source("usgs-earthquakes", opener=op_bad)
    assert res["served"] == "memory"
    assert now._health["usgs-earthquakes"]["state"] == "STALE"
    now._memory.clear()
    # disk cache from the first refresh still serves (cold-start path)
    res = now.refresh_source("usgs-earthquakes", opener=op_bad)
    assert res["served"] == "disk"
    assert now._health["usgs-earthquakes"]["state"] == "STALE"
    # with neither memory nor disk -> OFFLINE, nothing served
    now._memory.clear()
    (isolated_store / "usgs-earthquakes.json").unlink()
    res = now.refresh_source("usgs-earthquakes", opener=op_bad)
    assert res["served"] == "none"
    assert now._health["usgs-earthquakes"]["state"] == "OFFLINE"
    # rate limit without cache
    err429 = urllib.error.HTTPError("u", 429, "slow", {}, io.BytesIO(b"s"))
    res = now.refresh_source(
        "gdelt-doc",
        opener=router({"gdeltproject": err429}))
    assert res["reason"] == "rate_limited"
    assert now._health["gdelt-doc"]["state"] == "RATE_LIMITED"


def test_disk_cache_cold_start(isolated_store):
    op = router(FULL_MAP)
    now.refresh_source("usgs-earthquakes", force=True, opener=op)
    assert (isolated_store / "usgs-earthquakes.json").is_file()
    now._memory.clear()
    now._health.clear()
    op_down = router({"earthquake.usgs.gov": TimeoutError("no net")})
    res = now.refresh_source("usgs-earthquakes", opener=op_down)
    assert res["served"] == "disk"
    payload = now.get_now(refresh=False)
    assert payload["counts"]["usgs-earthquakes"] == 1


# --------------------------------------------------------------------------
# NOW payload guarantees
# --------------------------------------------------------------------------

def test_now_payload_guarantees(isolated_store):
    payload = now.get_now(refresh=True, force=True,
                          opener=router(FULL_MAP))
    assert payload["real_data"] is True
    assert payload["live"] is False
    assert payload["mode"] == "now"
    blob = json.dumps(payload).lower()
    assert "synthetic" not in blob
    for bad in ("wld-", "syn-", "tellurion-world-v1"):
        assert bad not in blob, bad
    assert payload["counts"]["total_real"] >= 6
    assert "static_geo" in payload and "unavailable" in payload
    assert any(u["domain"] == "CAMERAS" for u in payload["unavailable"])


def test_offline_first_boot_has_no_filler(isolated_store):
    op = router({"example.invalid": TimeoutError("no net")})

    def boom(req, timeout=None):
        raise TimeoutError("no net")
    payload = now.get_now(refresh=True, force=True, opener=boom)
    assert payload["counts"]["total_real"] == 0
    assert payload["real_data"] is True
    blob = json.dumps(payload).lower()
    assert "synthetic" not in blob
    states = {h["source_id"]: h["state"] for h in payload["health"]
              if h.get("enabled")}
    assert set(states.values()) <= {"OFFLINE", "RATE_LIMITED"}


# --------------------------------------------------------------------------
# Linking + upstream protection
# --------------------------------------------------------------------------

def _ev(source, lat, lon, evt, fields=None, key="k"):
    return {"source": source, "stable_key": f"{source}:{key}",
            "lat": lat, "lon": lon, "source_event_time": evt,
            "fields": fields or {}}


def test_usgs_gdacs_link_shared_upstream():
    groups = {
        "usgs-earthquakes": [_ev("usgs-earthquakes", 38.0, 140.0,
                                 "2026-09-15T12:00:00+00:00",
                                 {"mag": 6.1}, "u1")],
        "gdacs-alerts": [_ev("gdacs-alerts", 38.05, 140.05,
                             "Tue, 15 Sep 2026 14:00:00 GMT",
                             {"event_type": "EQ"}, "g1")],
        "gdelt-doc": [],
        "nasa-eonet": [],
    }
    links = now.link_events(groups)
    assert len(links) == 1
    assert links[0]["independence"] == "SHARED_UPSTREAM"
    assert links[0]["corroboration"] == "MULTIPLE SOURCES"
    # far apart in time -> no link
    groups["gdacs-alerts"][0]["source_event_time"] = \
        "Tue, 01 Sep 2026 12:00:00 GMT"
    assert now.link_events(groups) == []


def test_gdelt_report_corroborates_independently():
    groups = {
        "usgs-earthquakes": [_ev("usgs-earthquakes", 38.0, 140.0,
                                 "2026-09-15T12:00:00+00:00",
                                 {"mag": 6.1, "place": "offshore Honshu"},
                                 "u1")],
        "gdacs-alerts": [],
        "nasa-eonet": [],
        "gdelt-doc": [_ev("gdelt-doc", None, None,
                          "20260915T150000Z",
                          {"title": "Powerful Honshu quake triggers checks"},
                          "r1")],
    }
    links = now.link_events(groups)
    assert len(links) == 1
    assert links[0]["corroboration"] == "CORROBORATED"
    assert links[0]["independence"] == "INDEPENDENT"


# --------------------------------------------------------------------------
# whats-here / region scoping
# --------------------------------------------------------------------------

def test_whatshere_nws_scoping(isolated_store):
    payload = now.get_now(refresh=True, force=True,
                          opener=router(FULL_MAP))
    groups = payload["objects"]
    us = now.whats_here_now(40.0, -98.0, 1500, groups)
    assert us["summary"]["us_weather_alerts"] >= 1
    at = now.whats_here_now(48.2, 16.4, 250, groups)
    assert at["summary"]["us_weather_alerts"] == 0
    assert "UNITED STATES ONLY" in " ".join(at["coverage_notes"])
    bad = now.whats_here_now("x", "y", 10, groups)
    assert "error" in bad
    assert now.region_now("Atlantis XYZ", groups)["status"] == "UNKNOWN"


# --------------------------------------------------------------------------
# Endpoints (fetch mocked — no network)
# --------------------------------------------------------------------------

def test_world_now_endpoints_mocked(isolated_store):
    import threading
    import urllib.request
    from http.server import HTTPServer
    from unittest import mock
    from gods_eye import demo as _demo
    with mock.patch.object(now, "fetch_url",
                           wraps=now.fetch_url) as _:
        pass
    real_fetch = now.fetch_url

    def fake_fetch(url, timeout_s, content_types, etag="",
                   last_modified="", opener=None):
        return real_fetch(url, timeout_s, content_types, etag,
                          last_modified,
                          opener=router(FULL_MAP))
    with mock.patch.object(now, "fetch_url", side_effect=fake_fetch):
        server = HTTPServer((_demo.HOST, 0), _demo._Handler)
        port = server.server_address[1]
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        try:
            base = f"http://{_demo.HOST}:{port}"

            def get(path):
                return json.load(urllib.request.urlopen(
                    base + path, timeout=30))
            payload = get("/api/world/now?norefresh=0&refresh=1")
            assert payload["real_data"] is True
            assert payload["counts"]["total_real"] >= 6
            key = payload["objects"]["usgs-earthquakes"][0]["stable_key"]
            ev = get("/api/world/now/evidence?key=" + key)
            assert ev["evidence"]["stable_key"] == key
            assert "related" in ev
            here = get("/api/world/now/whatshere?lat=38&lon=140&radius_km=500")  # noqa: E501
            assert "summary" in here
            reg = get("/api/world/now/region?region=Austria")
            assert reg["region"] == "Austria" and reg["mode"] == "now"
        finally:
            server.shutdown()


# --------------------------------------------------------------------------
# Privacy + rights rechecks
# --------------------------------------------------------------------------

def test_now_privacy_rights(isolated_store):
    payload = now.get_now(refresh=True, force=True,
                          opener=router(FULL_MAP))
    blob = json.dumps(payload).lower()
    for tok in ("cctv", "rtsp", "onvif", "facial", "plate recognition",
                "intercept", "deanon", "strike", "targeting", "password"):
        assert tok not in blob, tok
    # no local secret *values* ever leak into the payload (config names
    # like MAP_KEY/appname in guidance copy are fine; values are not)
    import os
    for k, v in os.environ.items():
        if k.startswith("TELLURION_") and v and len(v) >= 4:
            assert v not in json.dumps(payload), k
    for items in payload["objects"].values():
        for o in items:
            assert o["rights"] and o["attribution"]
            assert o["truth_mode"] in ("DELAYED", "STATIC")
            assert o["source_event_time"] != ""
    for h in payload["health"]:
        assert h["state"] in ("ONLINE", "DEGRADED", "STALE", "OFFLINE",
                              "RATE_LIMITED", "STANDBY", "KEY_REQUIRED")
    # standby reasons are explicit
    standby = {h["source_id"]: h["detail"] for h in payload["health"]
               if not h.get("enabled")}
    assert "appname" in standby["reliefweb"]


def test_new_live_leg_plugins():
    import importlib.util
    for name, cls in (("weather_nws", "WeatherNws"),
                      ("disaster_eonet", "DisasterEonet"),
                      ("space_swpc", "SpaceSwpc")):
        spec = importlib.util.spec_from_file_location(
            f"{name}.plugin", str(ROOT / "plugins" / name / "plugin.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        out = mod.__dict__[cls]().poll()
        assert out["items"] and "CC0" in out["rights"], name
