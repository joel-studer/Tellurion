"""V2.1 satellite evidence tests (offline only — network is always mocked).

Covers: eligible BEFORE+AFTER / missing sides / cloud rejection /
same-bounds comparability / capture-time preservation / attribution /
rights / ineligibility / no-synthetic fallback / provider failure /
rate limits / cache / API serialization / drawer contract /
AI-readable availability / leak gate / replay isolation / no trading
fields.
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

from gods_eye.future import world_imagery as img  # noqa: E402

FIRST = "2026-09-10T12:00:00+00:00"


def _jpeg(w=336, h=336):
    import struct
    return (b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 9
            + b"\xff\xc0\x00\x0b\x08"
            + struct.pack(">HH", h, w) + b"\x03\x01\x11\x00"
            + b"\xff\xd9")


def _feature(item_id, dt, cloud, tile="14RMU"):
    return {
        "id": item_id,
        "bbox": [-99.2, 30.5, -98.1, 31.6],
        "properties": {"datetime": dt, "eo:cloud_cover": cloud,
                       "updated": dt},
        "assets": {
            "thumbnail": {
                "href": f"https://example.test/t/{item_id}.jpg",
                "type": "image/jpeg", "roles": ["thumbnail"]},
        },
    }


def _change(cid="chg:eonet-opened-x", ctype="eonet-opened",
            title="New event \u2014 Wildfire Kurk",
            lat=31.06, lon=-98.65):
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
        "evidence": [{"source": "nasa-eonet", "stable_key": "k",
                      "fields": {"categories": ["Wildfires"]}}],
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


def _stac_router(features_by_window, thumbs=True, calls=None,
                 fail=None):
    """Window-aware fake catalog: filters features by the request's
    datetime window, like a real STAC search would."""
    def opener(req, timeout=None):
        url = req.full_url
        if calls is not None:
            calls.append(url)
        if fail and fail in url:
            raise fail(url)
        if "earth-search" in url:
            body = json.loads(req.data.decode("utf-8"))
            start, end = body.get("datetime", "/").split("/", 1)
            feats = [f for f in features_by_window
                     if start <= str(f["properties"]["datetime"]) <= end]
            return FakeResp(json.dumps({"features": feats}))
        if url.endswith(".jpg"):
            if thumbs:
                return FakeResp(_jpeg())
            raise ValueError("thumbnails disabled")
        raise AssertionError("unexpected url " + url)
    return opener


@pytest.fixture()
def iso_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(img, "_runtime_dir", lambda: tmp_path)
    yield tmp_path


def _win(before, after):
    return _stac_router(before + after)


# -------------------------------------------------- selection ---


def test_before_and_after_available(iso_dirs):
    feats = [_feature("B1", "2026-09-08T17:00:00Z", 8.1),
             _feature("A1", "2026-09-12T17:00:00Z", 4.2)]
    out = img.get_imagery(_change(), opener=_win(feats, feats))
    assert out["status"] == "AVAILABLE"
    assert out["before"]["product_id"] == "B1"
    assert out["after"]["product_id"] == "A1"
    assert out["before"]["role"] == "BEFORE"
    assert out["after"]["role"] == "AFTER"
    assert out["before"]["captured_at"] < FIRST < out["after"]["captured_at"]


def test_no_before_scene(iso_dirs):
    feats = [_feature("A1", "2026-09-12T17:00:00Z", 4.2)]
    out = img.get_imagery(_change(), opener=_win([], feats))
    assert out["status"] == "NO_BEFORE"
    assert out["after"]["product_id"] == "A1"
    assert out["before"] is None


def test_no_after_scene(iso_dirs):
    feats = [_feature("B1", "2026-09-08T17:00:00Z", 8.1)]
    out = img.get_imagery(_change(), opener=_win(feats, []))
    assert out["status"] == "NO_AFTER"
    assert out["before"]["product_id"] == "B1"
    assert out["after"] is None


def test_high_cloud_rejected(iso_dirs):
    cloudy = [_feature("C1", "2026-09-08T17:00:00Z", 85.0)]
    out = img.get_imagery(_change(), opener=_win(cloudy, cloudy))
    assert out["status"] == "NO_SUITABLE_OBSERVATION"
    assert out["before"] is None and out["after"] is None


def test_cloud_limited_partial_with_warning(iso_dirs):
    feats = [_feature("B1", "2026-09-08T17:00:00Z", 45.0),
             _feature("A1", "2026-09-12T17:00:00Z", 5.0)]
    out = img.get_imagery(_change(), opener=_win(feats, feats))
    assert out["status"] == "PARTIAL"
    assert out["before"]["cloud_state"] == "CLOUD_LIMITED"
    assert "cloud" in out["note"].lower()


def test_same_bounds_comparable(iso_dirs):
    feats = [_feature("B1", "2026-09-08T17:00:00Z", 8.1, tile="14RMU"),
             _feature("A1", "2026-09-12T17:00:00Z", 4.2, tile="14RMU")]
    out = img.get_imagery(_change(), opener=_win(feats, feats))
    assert out["before"]["bounds"] and out["after"]["bounds"]
    assert out["before"]["coverage_quality"] == "same-tile pair"
    assert out["after"]["coverage_quality"] == "same-tile pair"


def test_capture_time_preserved(iso_dirs):
    feats = [_feature("B1", "2026-09-08T17:25:28.743000Z", 8.1),
             _feature("A1", "2026-09-12T17:25:28.743000Z", 4.2)]
    out = img.get_imagery(_change(), opener=_win(feats, feats))
    assert out["before"]["captured_at"] == "2026-09-08T17:25:28.743000Z"
    assert out["after"]["captured_at"] == "2026-09-12T17:25:28.743000Z"
    assert out["before"]["age_seconds"] is not None


def test_attribution_present(iso_dirs):
    feats = [_feature("B1", "2026-09-08T17:00:00Z", 8.1),
             _feature("A1", "2026-09-12T17:00:00Z", 4.2)]
    out = img.get_imagery(_change(), opener=_win(feats, feats))
    assert out["before"]["rights"]["attribution"] == \
        "Contains modified Copernicus Sentinel data [2026]"
    assert out["before"]["rights_status"] == "ATTRIBUTION_REQUIRED"
    assert out["before"]["source"] == "Copernicus Sentinel-2"


def test_rights_propagated(iso_dirs):
    feats = [_feature("B1", "2026-09-08T17:00:00Z", 8.1),
             _feature("A1", "2026-09-12T17:00:00Z", 4.2)]
    out = img.get_imagery(_change(), opener=_win(feats, feats))
    for img_side in (out["before"], out["after"]):
        assert set(img_side["rights"]) == {
            "commercial_use", "public_display", "redistribution",
            "derived_products", "broadcast_use", "cache", "retention",
            "attribution",
        }
        assert img_side["truth_mode"] == "OBSERVED"


# ------------------------------------------------ eligibility ---


def test_ineligible_categories_get_none(iso_dirs):
    calls = []

    def boom(req, timeout=None):
        calls.append(req.full_url)
        raise AssertionError("must not fetch for ineligible changes")

    quake = _change(ctype="eonet-opened", title="M6 quake offshore")
    quake["evidence"] = [{"source": "x", "fields": {}}]
    for ch in (quake,
               _change(ctype="usgs-episode", title="Seismic episode"),
               _change(ctype="gdacs-transition", title="EQ alert"),
               _change(title="t", lat=None, lon=None)):
        out = img.get_imagery(ch, opener=boom)
        assert out["status"] == "NOT_ELIGIBLE", ch["type"]
        assert out["before"] is None and out["after"] is None
    assert calls == []


def test_no_synthetic_fallback(iso_dirs):
    out = img.get_imagery(_change(), opener=_win([], []))
    blob = json.dumps(out).lower()
    assert "synthetic" not in blob
    assert out["status"] == "NO_SUITABLE_OBSERVATION"


# --------------------------------------------- failure modes ---


def test_provider_failure_degrades(iso_dirs):
    import urllib.error

    def opener(req, timeout=None):
        raise urllib.error.URLError("catalog down")

    out = img.get_imagery(_change(), opener=opener)
    assert out["status"] == "SOURCE_UNAVAILABLE"


def test_rate_limit_state(iso_dirs):
    import urllib.error

    def opener(req, timeout=None):
        if req.full_url.endswith(".jpg"):
            return FakeResp(_jpeg())
        raise urllib.error.HTTPError(req.full_url, 429, "Slow Down", {}, None)  # noqa: E501

    out = img.get_imagery(_change(), opener=opener)
    assert out["status"] in ("RATE_LIMITED", "SOURCE_UNAVAILABLE",
                             "NO_SUITABLE_OBSERVATION")


def test_cache_behavior(iso_dirs):
    calls = []
    feats = [_feature("B1", "2026-09-08T17:00:00Z", 8.1),
             _feature("A1", "2026-09-12T17:00:00Z", 4.2)]
    op = _stac_router(feats, feats, calls=calls)
    img.get_imagery(_change(), opener=op)
    n_first = len(calls)
    assert n_first > 0
    img.get_imagery(_change(), opener=op)
    # Catalog cached (TTL), thumbnails cached (disk): no new fetches.
    assert len(calls) == n_first


# -------------------------------------------------------- API ---


def test_api_serialization(iso_dirs):
    canned = {"change_id": _change()["id"], "status": "AVAILABLE",
              "before": {"role": "BEFORE", "product_id": "B1"},
              "after": {"role": "AFTER", "product_id": "A1"},
              "generated_at": "2026-09-17T19:00:00+00:00",
              "truth_label": img.TRUTH_LABEL, "live": False,
              "real_data": True}
    from gods_eye import demo as _demo
    with mock.patch.object(img, "load_change", return_value=_change()):
        with mock.patch.object(img, "get_imagery", return_value=canned):
            server = HTTPServer((_demo.HOST, 0), _demo._Handler)
            threading.Thread(target=server.serve_forever,
                             daemon=True).start()
            try:
                base = f"http://{_demo.HOST}:{server.server_address[1]}"
                with urllib.request.urlopen(
                        base + "/api/world/changes/abc/imagery",
                        timeout=60) as r:
                    payload = json.load(r)
                with urllib.request.urlopen(
                        base + "/api/world/changes/abc/imagery?x=1",
                        timeout=60) as r:
                    assert json.load(r)["status"] == "AVAILABLE"
            finally:
                server.shutdown()
    assert payload == canned
    assert set(payload) >= {"change_id", "status", "before", "after",
                            "generated_at"}


def test_api_unknown_change_id(iso_dirs):
    from gods_eye import demo as _demo
    with mock.patch.object(img, "load_change", return_value=None):
        server = HTTPServer((_demo.HOST, 0), _demo._Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            base = f"http://{_demo.HOST}:{server.server_address[1]}"
            with urllib.request.urlopen(
                    base + "/api/world/changes/nope/imagery",
                    timeout=60) as r:
                payload = json.load(r)
        finally:
            server.shutdown()
    assert payload["status"] == "NO_SUITABLE_OBSERVATION"
    assert "unknown change" in payload.get("note", "")


def test_drawer_renders_satellite_evidence():
    src = (ROOT / "console" / "world" / "app.js").read_text(encoding="utf-8")
    low = src.lower()
    for needle in ("satellite evidence", "captured", "cloud",
                   "resolution", "rights", "open source",
                   "cloud_limited", "limited by cloud cover",
                   "loadsatevidence", "satpair"):
        assert needle in low, needle


def test_ai_readable_availability(iso_dirs):
    feats = [_feature("B1", "2026-09-08T17:00:00Z", 8.1),
             _feature("A1", "2026-09-12T17:00:00Z", 4.2)]
    out = img.get_imagery(_change(), opener=_win(feats, feats))
    assert out["status"] in ("AVAILABLE", "PARTIAL", "NO_BEFORE",
                             "NO_AFTER", "NO_SUITABLE_OBSERVATION",
                             "SOURCE_UNAVAILABLE", "RATE_LIMITED",
                             "NOT_ELIGIBLE")
    for img_side in (out["before"], out["after"]):
        for key in ("captured_at", "cloud_cover_pct", "cloud_state",
                    "resolution_m", "source", "rights_status"):
            assert key in img_side, key


# ----------------------------------------------- boundaries ---


def test_no_trading_fields_introduced(iso_dirs):
    from gods_eye.future import world_change as chg
    feats = [_feature("B1", "2026-09-08T17:00:00Z", 8.1),
             _feature("A1", "2026-09-12T17:00:00Z", 4.2)]
    out = img.get_imagery(_change(), opener=_win(feats, feats))
    blob = json.dumps(out).lower()
    for field in chg.FORBIDDEN_FIELDS:
        assert f'"{field}"' not in blob, field


def test_modules_stay_public_safe():
    import re
    for rel in ("python/gods_eye/future/world_imagery.py",
                "tests/test_world_imagery_v23.py"):
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
    assert "satellite-image" not in blob
    src = (ROOT / "console" / "world" / "app.js").read_text(encoding="utf-8")
    assert "satellite evidence" in src.lower()
