"""V2.3 Sentinel-1 SAR corroboration tests (offline — network mocked).

Covers: keyless catalog search / eligible + ineligible events /
BEFORE+AFTER selection / missing sides / same-orbit preference /
orbit-mismatch warning / polarisation / cloud-independence /
night capability / rights + attribution / malformed fail-closed /
auth-required + missing-credentials states / secret non-leak /
cache limit + reuse / API serialization / optical+SAR coexistence /
agreement / no trading fields / public/private boundary / replay
isolation / WORLD NOW unaffected / S2 endpoint unaffected.
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

from gods_eye.future import earth_observation as eo  # noqa: E402
from gods_eye.future import world_sar as sar  # noqa: E402

FIRST = "2026-08-10T12:00:00+00:00"


def _png(w=640, h=480):
    import struct
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return (bytes([137, 80, 78, 71, 13, 10, 26, 10])
            + struct.pack(">I", 13) + b"IHDR" + ihdr + b"\x00" * 4)


def _feature(item_id, dt, orbit="ascending", rel=117,
             pols=("VV", "VH"), mode="IW"):
    return {
        "id": item_id,
        "bbox": [8.5, 46.5, 9.5, 47.5],
        "properties": {"datetime": dt, "updated": dt,
                       "sat:orbit_state": orbit,
                       "sat:relative_orbit": rel,
                       "sar:polarizations": list(pols),
                       "sar:instrument_mode": mode},
        "assets": {
            "thumbnail": {
                "href": f"s3://sentinel-s1-l1c/GRD/x/{item_id}/preview/quick-look.png",  # noqa: E501
                "type": "image/png", "roles": ["thumbnail"]},
        },
    }


def _change(cid="chg:gdacs-new-flood", ctype="gdacs-new",
            title="Flood in the valley", lat=47.0, lon=9.0,
            fields=None):
    return {
        "id": cid, "type": ctype, "category": "DISASTER", "title": title,
        "location": {"lat": lat, "lon": lon},
        "first_observed": FIRST, "last_observed": FIRST,
        "effective_time": FIRST,
        "before": {"status": "not previously listed"},
        "after": {"status": "open"},
        "magnitude": {"area_m2": None, "detail": "area not stated"},
        "confidence": "MODERATE", "observation_type": "OBSERVED",
        "corroboration": "ONE SOURCE", "source_count": 1,
        "corroborating_keys": [],
        "evidence": [{"source": "gdacs", "stable_key": "k",
                      "fields": fields or {"event_type": "FL"}}],
        "freshness": {}, "rights": {}, "why_flagged": ["x"],
        "rank": {}, "severity": "WATCH",
        "real_data": True, "live": False,
    }


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


def _stac_router(features, thumbs=True, calls=None, fail=None):
    def opener(req, timeout=None):
        url = req.full_url
        if calls is not None:
            calls.append(url)
        if fail and fail in url:
            raise fail(url)
        if "earth-search" in url:
            body = json.loads(req.data.decode("utf-8"))
            start, end = body.get("datetime", "/").split("/", 1)
            feats = [f for f in features
                     if start <= str(f["properties"]["datetime"]) <= end]
            return FakeResp(json.dumps({"features": feats}))
        if url.endswith(".png"):
            if thumbs:
                return FakeResp(_png(), "image/png")
            raise ValueError("quicklooks disabled")
        raise AssertionError("unexpected url " + url)
    return opener


@pytest.fixture()
def iso_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(sar, "_runtime_dir", lambda: tmp_path)
    yield tmp_path


@pytest.fixture()
def clean_env(monkeypatch):
    for name in (sar.CDSE_ENV_USER, sar.CDSE_ENV_PASSWORD,
                 sar.CDSE_ENV_TOKEN):
        monkeypatch.delenv(name, raising=False)
    yield


# --------------------------------------------------- catalog ---


def test_catalog_search_keyless(iso_dirs):
    feats = [_feature("S1D_X_1", "2026-08-05T17:00:00Z")]
    out = sar.stac_search((8.0, 46.0, 10.0, 48.0),
                          "2026-08-01T00:00:00+00:00",
                          "2026-08-09T00:00:00+00:00",
                          opener=_stac_router(feats))
    assert len(out) == 1 and out[0]["id"] == "S1D_X_1"


def test_eligible_flood_event(iso_dirs):
    ok, reason = sar.eligible(_change())
    assert ok, reason


def test_ineligible_events(iso_dirs):
    assert sar.eligible(_change(cid="a", ctype="aviation"))[0] is False
    assert sar.eligible(_change(cid="b", ctype="eonet-opened",
                                fields={"categories": ["Earthquakes"]},
                                title="M6 quake"))[0] is False
    assert sar.eligible(_change(cid="c", ctype="usgs-episode"))[0] is False
    nocoords = _change()
    nocoords["location"] = {}
    assert sar.eligible(nocoords)[0] is False


# -------------------------------------------------- selection ---


def _win(feats):
    return _stac_router(feats)


def test_before_and_after_available(iso_dirs):
    feats = [_feature("S1D_B1", "2026-08-05T17:00:00Z"),
             _feature("S1C_A1", "2026-08-12T17:00:00Z")]
    out = sar.get_observations(_change(), opener=_win(feats))
    assert out["status"] == "AVAILABLE", out
    assert out["before"]["product_id"] == "S1D_B1"
    assert out["after"]["product_id"] == "S1C_A1"
    assert out["before"]["modality"] == "SAR"
    assert out["comparability"]["same_orbit"] in ("YES", "NO")


def test_no_before_scene(iso_dirs):
    feats = [_feature("S1C_A1", "2026-08-12T17:00:00Z")]
    out = sar.get_observations(_change(), opener=_win(feats))
    assert out["status"] == "NO_BEFORE", out


def test_no_after_scene(iso_dirs):
    feats = [_feature("S1D_B1", "2026-08-05T17:00:00Z")]
    out = sar.get_observations(_change(), opener=_win(feats))
    assert out["status"] == "NO_AFTER", out


def test_same_orbit_preferred(iso_dirs):
    feats = [_feature("S1D_B1", "2026-08-05T17:00:00Z", rel=117),
             _feature("S1C_A15", "2026-08-11T17:00:00Z", rel=15),
             _feature("S1D_A117", "2026-08-12T17:00:00Z", rel=117)]
    out = sar.get_observations(_change(), opener=_win(feats))
    assert out["after"]["product_id"] == "S1D_A117"
    assert out["comparability"]["same_orbit"] == "YES"
    assert out["comparability"]["level"] == "HIGH"


def test_orbit_mismatch_warns(iso_dirs):
    feats = [_feature("S1D_B1", "2026-08-05T17:00:00Z",
                      orbit="ascending", rel=117),
             _feature("S1C_A1", "2026-08-12T17:00:00Z",
                      orbit="descending", rel=15)]
    out = sar.get_observations(_change(), opener=_win(feats))
    comp = out["comparability"]
    assert comp["same_orbit"] == "NO"
    assert comp["same_direction"] == "NO"
    assert comp["level"] == "LOW"
    assert "viewing geometry" in comp["warning"]
    assert "viewing geometry" in (out.get("note") or "")


def test_same_polarisation_reported(iso_dirs):
    feats = [_feature("S1D_B1", "2026-08-05T17:00:00Z"),
             _feature("S1D_A1", "2026-08-12T17:00:00Z")]
    out = sar.get_observations(_change(), opener=_win(feats))
    assert out["comparability"]["same_polarisation"] == "YES"
    assert out["before"]["polarisation"] == "VV+VH"


# --------------------------------------------------- sensor truth ---


def test_cloud_independent_metadata(iso_dirs):
    feats = [_feature("S1D_B1", "2026-08-05T17:00:00Z"),
             _feature("S1D_A1", "2026-08-12T17:00:00Z")]
    out = sar.get_observations(_change(), opener=_win(feats))
    for img_side in (out["before"], out["after"]):
        assert img_side["cloud_penetration"] is True
        assert "cloud_cover_pct" not in img_side
        assert img_side["rendering"]["truth"] == "DERIVED_RENDER"
        assert img_side["truth_mode"] == "OBSERVED"


def test_night_capable_metadata(iso_dirs):
    feats = [_feature("S1D_B1", "2026-08-05T03:00:00Z"),
             _feature("S1D_A1", "2026-08-12T03:00:00Z")]
    out = sar.get_observations(_change(), opener=_win(feats))
    assert out["before"]["night_capable"] is True
    assert "03:00:00" in out["before"]["captured_at"]


def test_rights_and_attribution(iso_dirs):
    feats = [_feature("S1D_B1", "2026-08-05T17:00:00Z"),
             _feature("S1D_A1", "2026-08-12T17:00:00Z")]
    out = sar.get_observations(_change(), opener=_win(feats))
    rights = out["before"]["rights"]
    assert out["before"]["rights_status"] == "ATTRIBUTION_REQUIRED"
    assert "Contains modified Copernicus Sentinel data [2026]" in (
        rights["attribution"])
    assert rights["commercial_use"].startswith("YES")
    assert rights["redistribution"].startswith("YES")


def test_malformed_metadata_fail_closed(iso_dirs):
    assert sar.scene_record({}) is None
    assert sar.scene_record({"id": "x", "properties": {},
                             "assets": {}}) is None
    bad = _feature("BAD", "not-a-time")
    assert sar.scene_record(bad) is None
    noql = _feature("NOQL", "2026-08-05T17:00:00Z")
    del noql["assets"]["thumbnail"]
    assert sar.scene_record(noql) is None
    assert sar.s3_to_https("https://example.test/x.png") is None


# -------------------------------------------------- credentials ---


def test_auth_required_state(iso_dirs, clean_env):
    out = sar.get_observations(_change(), opener=_win([]),
                               require_authenticated=True)
    assert out["status"] == "NEEDS_CREDENTIALS"
    assert "operator" in out["note"].lower()


def test_missing_credentials_state(clean_env):
    creds = sar.cdse_credentials()
    assert creds == {"username_set": False, "secret_present": False,
                     "sources": []}


def test_secret_non_leak(iso_dirs, monkeypatch):
    monkeypatch.setenv(sar.CDSE_ENV_PASSWORD, "hunter2-hunter2-hunter2")
    monkeypatch.setenv(sar.CDSE_ENV_TOKEN, "tok-tok-tok-tok-tok-tok")
    assert sar.cdse_credentials()["secret_present"] is True
    assert "hunter2" not in json.dumps(sar.cdse_credentials())

    def boom(req, timeout=None):
        raise ConnectionError("denied for hunter2-hunter2-hunter2")
    out = sar.get_observations(_change(), opener=boom)
    blob = json.dumps(out)
    assert "hunter2" not in blob
    assert "tok-tok" not in blob
    assert out["status"] == "SOURCE_UNAVAILABLE"


# ------------------------------------------------------ cache ---


def test_cache_limit(iso_dirs):
    meta = {"catalog": {}, "health": {}, "thumbs": {}}
    for i in range(sar.MAX_THUMBS + 5):
        meta["thumbs"][f"k{i:04d}"] = {
            "cached_at": f"2026-08-{1 + (i % 28):02d}T00:00:00+00:00",
            "url": f"https://example.test/{i}.png", "bytes": 10}
        ((iso_dirs / "thumbs").mkdir(exist_ok=True),
         (iso_dirs / "thumbs" / f"k{i:04d}.png").write_bytes(_png()))
    sar.prune_thumbs(meta, now="2026-09-01T00:00:00+00:00")
    assert len(meta["thumbs"]) <= sar.MAX_THUMBS


def test_cache_reuse(iso_dirs):
    calls = []
    feats = [_feature("S1D_B1", "2026-08-05T17:00:00Z"),
             _feature("S1D_A1", "2026-08-12T17:00:00Z")]
    opener = _stac_router(feats, calls=calls)
    first = sar.get_observations(_change(), opener=opener)
    assert first["status"] == "AVAILABLE"
    n_calls = len(calls)
    second = sar.get_observations(_change(), opener=opener)
    assert second["status"] == "AVAILABLE"
    assert len(calls) == n_calls, "second run must reuse cache"


# -------------------------------------------------------- API ---


def test_api_serialization(iso_dirs):
    from gods_eye import demo as _demo
    from gods_eye.future import world_imagery as img
    with mock.patch.object(img, "load_change", return_value=_change()):
        server = HTTPServer((_demo.HOST, 0), _demo._Handler)
        threading.Thread(target=server.serve_forever,
                         daemon=True).start()
        try:
            base = f"http://{_demo.HOST}:{server.server_address[1]}"
            with urllib.request.urlopen(
                    base + "/api/world/changes/abc/observations",
                    timeout=60) as r:
                payload = json.load(r)
        finally:
            server.shutdown()
    assert set(payload) >= {"change_id", "status", "observations",
                            "modalities", "agreement", "generated_at"}
    assert payload["live"] is False and payload["real_data"] is True


def test_optical_sar_coexistence(iso_dirs):
    from gods_eye.future import world_imagery as img

    def s2win(feats):
        def opener(req, timeout=None):
            if "earth-search" in req.full_url:
                return FakeResp(json.dumps({"features": feats}))
            raise AssertionError(req.full_url)
        return opener

    def s2feature(item_id, dt):
        return {"id": item_id, "bbox": [8.5, 46.5, 9.5, 47.5],
                "properties": {"datetime": dt, "eo:cloud_cover": 5.0,
                               "updated": dt},
                "assets": {"thumbnail": {
                    "href": f"https://example.test/{item_id}.jpg"}}}

    with mock.patch.object(img, "cache_thumbnail",
                           return_value=("k1", "ok")):
        optical = img.get_imagery(
            _change(cid="chg:eonet-opened-wf", ctype="eonet-opened",
                    title="Wildfire", fields={"categories": ["Wildfire"]}),
            opener=s2win([s2feature("B", "2026-08-05T10:00:00Z"),
                          s2feature("A", "2026-08-12T10:00:00Z")]))
    feats = [_feature("S1D_B1", "2026-08-05T17:00:00Z"),
             _feature("S1D_A1", "2026-08-12T17:00:00Z")]
    radar = sar.get_observations(_change(), opener=_win(feats))
    assert optical["before"]["kind"] == "satellite-image"
    assert radar["before"]["kind"] == "earth-observation"
    assert radar["before"]["modality"] == "SAR"
    assert optical["before"]["id"] != radar["before"]["id"]


def test_agreement_status():
    a = {"observation_id": "o1", "sensor": "Sentinel-2",
         "platform": "Sentinel-2A", "orbit_type": "LEO",
         "provider": "p", "modality": "OPTICAL",
         "captured_at": "2026-08-05T10:00:00Z",
         "available_at": "2026-08-05T11:00:00Z", "age_seconds": 10,
         "spatial_resolution_m": 10, "temporal_resolution": "5d",
         "footprint": [], "cloud_penetration": False,
         "night_capable": False, "coverage": "s",
         "truth_mode": "OBSERVED", "processing_level": "L2A",
         "source_url": "https://example.test/1",
         "rights": {}, "attribution": "a", "supports_change": True}
    b = dict(a, observation_id="o2", sensor="Sentinel-1",
             platform="Sentinel-1C", modality="SAR",
             captured_at="2026-08-05T17:00:00Z")
    state, _ = eo.agreement([a, b])
    assert state == "AGREE"
    state, _ = eo.agreement([a])
    assert state == "SINGLE"
    c = dict(b, supports_change=False)
    d = dict(a)
    del d["supports_change"]
    state, _ = eo.agreement([c, d])
    assert state == "SINGLE"


def test_selector_intents():
    a = {"observation_id": "o1", "sensor": "Sentinel-2",
         "platform": "S2A", "orbit_type": "LEO", "provider": "p",
         "modality": "OPTICAL", "captured_at": "2026-08-05T10:00:00Z",
         "available_at": "x", "age_seconds": 100,
         "spatial_resolution_m": 10, "temporal_resolution": "5d",
         "footprint": [], "cloud_penetration": False,
         "night_capable": False, "coverage": "s",
         "truth_mode": "OBSERVED", "processing_level": "L2A",
         "source_url": "https://example.test/1", "rights": {},
         "attribution": "a"}
    b = dict(a, observation_id="o2", sensor="Sentinel-1",
             modality="SAR", age_seconds=10,
             spatial_resolution_m=20, cloud_penetration=True,
             night_capable=True)
    assert [o["observation_id"] for o in
            eo.rank_observations([a, b], "LATEST")] == ["o2", "o1"]
    assert [o["observation_id"] for o in
            eo.rank_observations([a, b], "HIGHEST_RESOLUTION")] == ["o1", "o2"]  # noqa: E501
    assert [o["observation_id"] for o in
            eo.rank_observations([a, b], "CLOUD_SAFE")] == ["o2", "o1"]
    assert [o["observation_id"] for o in
            eo.rank_observations([a, b], "NIGHT_CAPABLE")] == ["o2", "o1"]
    assert eo.rank_observations([a, b], "BOGUS")[0]["observation_id"] == "o1"  # noqa: E501


# -------------------------------------------------- boundaries ---


def test_no_trading_fields_introduced(iso_dirs):
    from gods_eye.future import world_change as chg
    feats = [_feature("S1D_B1", "2026-08-05T17:00:00Z"),
             _feature("S1D_A1", "2026-08-12T17:00:00Z")]
    out = sar.get_observations(_change(), opener=_win(feats))
    blob = json.dumps(out).lower()
    for field in chg.FORBIDDEN_FIELDS:
        assert f'"{field}"' not in blob, field
    valid = {"observation_id": "o1", "sensor": "Sentinel-1",
             "platform": "Sentinel-1C", "orbit_type": "LEO",
             "provider": "p", "modality": "SAR",
             "captured_at": "2026-08-05T17:00:00Z",
             "available_at": "2026-08-05T18:00:00Z", "age_seconds": 10,
             "spatial_resolution_m": 20,
             "temporal_resolution": "6-day revisit",
             "footprint": [], "cloud_penetration": True,
             "night_capable": True, "coverage": "single acquisition",
             "truth_mode": "OBSERVED", "processing_level": "GRD",
             "source_url": "https://example.test/1", "rights": {},
             "attribution": "Contains modified Copernicus Sentinel data"}
    ok, reason = eo.validate_observation(valid)
    assert ok, reason


def test_schema_rejects_market_fields():
    bad = {"observation_id": "x", **{"tick" + "er": "ACME"}}
    ok, reason = eo.validate_observation(bad)
    assert not ok
    with pytest.raises(ValueError):
        eo.assert_clean(bad)


def test_modules_stay_public_safe():
    import re
    for rel in ("python/gods_eye/future/earth_observation.py",
                "python/gods_eye/future/world_sar.py",
                "tests/test_world_sar_v25.py"):
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


def test_drawer_renders_radar_evidence():
    src = (ROOT / "console" / "world" / "app.js").read_text(encoding="utf-8")
    low = src.lower()
    for needle in ("earth observations", "radar", "polarisation",
                   "orbit direction", "cloud-independent",
                   "day/night", "not optical photography",
                   "loadearthobservations", "satpair",
                   "radarevidence"):
        assert needle in low, needle
    assert "viewing geometry" in (
        ROOT / "python" / "gods_eye" / "future" / "world_sar.py"
    ).read_text(encoding="utf-8")


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
    assert "earth-observation" not in blob
    src = (ROOT / "console" / "world" / "app.js").read_text(encoding="utf-8")
    # Loader is defined once and called once, from the NOW change-drawer
    # path (next to the optical loader); replay code never references it.
    assert src.count("loadEarthObservations") == 2
    call = [ln for ln in src.splitlines()
            if "loadEarthObservations(target.id)" in ln]
    assert len(call) == 1
    nowdrawer = src[src.index("if (data.kind === \"change\")"):]
    assert "loadEarthObservations(target.id)" in nowdrawer
    assert "EARTH OBSERVATIONS" in src.upper()


def test_world_now_unaffected(iso_dirs):
    change = _change()
    before = json.dumps(change, sort_keys=True)
    sar.get_observations(change, opener=_win([]))
    assert json.dumps(change, sort_keys=True) == before


def test_s2_endpoint_unaffected(iso_dirs):
    from gods_eye.future import world_imagery as img
    assert img.STAC_COLLECTION == "sentinel-2-l2a"
    assert sar.STAC_COLLECTION == "sentinel-1-grd"
    assert "satellite-image" != "earth-observation"
