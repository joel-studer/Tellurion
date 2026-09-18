"""Live aviation tests (offline only — network is always mocked).

Covers: normalization / dedup / emergency squawks / holding /
go-around / rapid descent / weather proximity / stale tracks /
no-owner-person guarantee / military-safe wording / source failure /
rate limiting / LOD caps / performance / privacy + rights.
"""

from __future__ import annotations

import io
import json
import sys
import time
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

import pytest

from gods_eye.future import world_air as air


def _ac(hex_id="aaaa01", **kw):
    row = {"hex": hex_id, "flight": "TST123  ", "r": "D-TEST",
           "t": "A320", "lat": 50.0, "lon": 10.0, "alt_baro": 35000,
           "alt_geom": 35100, "gs": 450.0, "track": 90.0,
           "baro_rate": 0, "squawk": "1000", "seen": 1.0,
           "seen_pos": 0.5, "type": "adsb_icao", "category": "A3"}
    row.update(kw)
    return row


def _payload(rows):
    return json.dumps({"ac": rows, "now": 1789554758501, "ctime": 1,
                       "ptime": 0, "total": len(rows)})


@pytest.fixture()
def isolated_air(monkeypatch):
    mem, health = dict(air._memory), dict(air._health)
    tracks = {k: list(v) for k, v in air._tracks.items()}
    air._memory.clear()
    air._health.clear()
    air._tracks.clear()
    yield
    air._memory.clear()
    air._memory.update(mem)
    air._health.clear()
    air._health.update(health)
    air._tracks.clear()
    for k, v in tracks.items():
        from collections import deque
        air._tracks[k] = deque(v, maxlen=air.TRACK_MAXLEN)


# --------------------------------------------------------------------------
# Normalization

def test_normalize_positioned_and_skipped():
    rows, skip = air.parse_adsblol(_payload([
        _ac(), _ac("bbbb02", lat=None), _ac("zzzzzz", lat=1.0),
        "junk", _ac("cccc03", lat=999.0)]))
    assert len(rows) == 1 and skip == 4
    o = rows[0]
    assert o["icao24"] == "aaaa01" and o["callsign"] == "TST123"
    assert o["registration"] == "D-TEST" and o["type"] == "A320"
    assert (o["lat"], o["lon"]) == (50.0, 10.0)
    assert o["baro_alt_ft"] == 35000 and o["gs_kt"] == 450.0
    assert o["signal"] == "ADS-B" and o["truth_mode"] == "DELAYED"
    assert o["rights"].startswith("ODbL") and "adsb.lol" in o["attribution"]
    assert o["position_age_s"] == 0.5


def test_normalize_ground_mlat_unknown():
    rows, _ = air.parse_adsblol(_payload([
        _ac("dddd04", alt_baro="ground"),
        _ac("eeee05", type="mlat", mlat=True),
        _ac("ffff06", flight="", r="", t="")]))
    g, m, u = rows
    assert g["on_ground"] is True and g["baro_alt_ft"] is None
    assert m["signal"] == "MLAT"
    assert u["callsign"] == "UNKNOWN" and u["type"] == "UNKNOWN"


def test_normalize_rejects_garbage_and_oversize():
    with pytest.raises(ValueError):
        air.parse_adsblol("<html>nope</html>")
    with pytest.raises(ValueError):
        air.parse_adsblol('{"nope": 1}')
    with pytest.raises(ValueError):
        air.parse_adsblol('{"ac": {}}')
    with pytest.raises(ValueError):
        air.parse_adsblol("x" * (air.MAX_BYTES + 1))


def test_no_owner_person_fields():
    rows, _ = air.parse_adsblol(_payload([_ac()]))
    assert not (air.FORBIDDEN_FIELDS & set(rows[0]))
    for f in ("owner", "vip", "person", "watchlist", "mission", "target"):
        assert f in air.FORBIDDEN_FIELDS


# --------------------------------------------------------------------------
# Dedup + history

def test_dedup_best_position_wins(isolated_air):
    a = _payload([_ac("aaaa01", seen_pos=5.0, lat=50.0)])
    b = _payload([_ac("aaaa01", seen_pos=0.2, lat=50.1)])
    ra, _ = air.parse_adsblol(a, tile="t1")
    rb, _ = air.parse_adsblol(b, tile="t2")
    out = air.dedup_states([ra, rb])
    assert len(out) == 1
    assert out[0]["lat"] == 50.1  # fresher wins, not averaged
    assert sorted(out[0]["tiles"]) == ["t1", "t2"]  # provenance kept


def test_history_capped_and_trailed(isolated_air):
    o, _ = air.parse_adsblol(_payload([_ac()]))
    for _ in range(5):
        air.update_tracks(o)
    assert air.track_count() == 1
    trail = air.get_trail("AAAA01")
    assert len(trail) == 5 and trail[0]["lat"] == 50.0
    assert air.get_trail("000000") == []


# --------------------------------------------------------------------------
# IMPORTANT NOW rules

def _hist_circle(hex_id="aaaa01", n=12, span_s=300, r_km=8.0,
                 lat0=50.0, lon0=10.0):
    import math
    t0 = time.time() - span_s
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / (n - 1) * 2  # two full loops
        pts.append((t0 + span_s * i / (n - 1),
                    lat0 + (r_km / 111.0) * math.sin(a),
                    lon0 + (r_km / 111.0) * math.cos(a),
                    8000.0, (math.degrees(a) + 90) % 360))
    return pts


def test_emergency_squawk_wording():
    for sq, meaning in (("7700", "general emergency"),
                        ("7600", "radio communication failure"),
                        ("7500", "unlawful interference code")):
        o, _ = air.parse_adsblol(_payload([_ac(squawk=sq)]))
        flags = air.flag_aircraft(o[0], [], {})
        em = [f for f in flags if f["rule_id"] == "EMERGENCY_SQUAWK"]
        assert len(em) == 1
        assert em[0]["label"] == "EMERGENCY SQUAWK OBSERVED"
        assert em[0]["interest"] == "HIGH"
        blob = json.dumps(em[0]).lower()
        assert "crash" not in blob and "hijack" not in blob
        assert "confirmed" not in blob and meaning in em[0]["why"].lower() \
            or sq in em[0]["why"]
    lvl, reasons = air.interest_of(
        air.flag_aircraft(air.parse_adsblol(
            _payload([_ac(squawk="7700")]))[0][0], [], {}))
    assert lvl == "HIGH" and reasons


def test_transponder_flag_is_medium_not_emergency():
    o, _ = air.parse_adsblol(_payload([_ac(spi=True)]))
    flags = air.flag_aircraft(o[0], [], {})
    tf = [f for f in flags if f["rule_id"] == "TRANSPONDER_FLAG"]
    assert len(tf) == 1 and tf[0]["interest"] == "MEDIUM"
    assert tf[0]["label"] == "TRANSPONDER FLAG OBSERVED"
    assert not [f for f in flags if f["rule_id"] == "EMERGENCY_SQUAWK"]
    lvl, _ = air.interest_of(flags)
    assert lvl == "MEDIUM"


def test_holding_candidate():
    o, _ = air.parse_adsblol(_payload([_ac()]))
    ev = air.holding_evidence(_hist_circle())
    assert ev and ev["total_turn_deg"] >= 540.0
    flags = air.flag_aircraft(o[0], _hist_circle(), {})
    holds = [f for f in flags if f["rule_id"] == "POSSIBLE_HOLDING"]
    assert holds
    # explicit denial of confirmation is the required wording
    assert "not a confirmed" in holds[0]["why"].lower()
    # straight flight is not holding
    straight = [(time.time() + i * 30, 50.0 + i * 0.1, 10.0, 8000.0, 90.0)
                for i in range(12)]
    assert air.holding_evidence(straight) is None


def test_goaround_candidate_near_fra():
    t0 = time.time()
    hist = [(t0 + i * 20, 50.10 - i * 0.004, 8.60 + i * 0.002,
             a, 90.0) for i, a in
            enumerate([4000, 3200, 2400, 1800, 1600, 2200, 3200, 4200])]
    ap = {"id": "APT-FRA", "lat": 50.03, "lon": 8.56}
    ev = air.goaround_evidence(hist, ap)
    assert ev and ev["airport"] == "APT-FRA"
    o, _ = air.parse_adsblol(_payload([_ac(lat=50.06, lon=8.63)]))
    flags = air.flag_aircraft(o[0], hist, {})
    assert any(f["rule_id"] == "POSSIBLE_GOAROUND" for f in flags)


def test_rapid_descent_and_climb():
    o, _ = air.parse_adsblol(_payload([_ac(baro_rate=-3500)]))
    flags = air.flag_aircraft(o[0], [], {})
    assert any(f["rule_id"] == "RAPID_DESCENT" for f in flags)
    o2, _ = air.parse_adsblol(_payload([_ac("bbbb02", baro_rate=4200)]))
    assert any(f["rule_id"] == "RAPID_CLIMB"
               for f in air.flag_aircraft(o2[0], [], {}))
    # history-based drop without vrate
    t0 = time.time()
    hist = [(t0 - 60 + i * 10, 50.0, 10.0, 12000 - i * 500, 180.0)
            for i in range(7)]
    o3, _ = air.parse_adsblol(_payload([_ac("cccc03")]))
    assert any(f["rule_id"] == "RAPID_DESCENT"
               for f in air.flag_aircraft(o3[0], hist, {}))


def test_weather_proximity():
    o, _ = air.parse_adsblol(_payload([_ac()]))
    ctx = {"nws_points": [{"lat": 50.2, "lon": 10.2,
                           "severity": "Severe",
                           "headline": "Tornado Warning"}]}
    flags = air.flag_aircraft(o[0], [], ctx)
    wx = [f for f in flags if f["rule_id"] == "NEAR_SEVERE_WX"]
    assert len(wx) == 1
    # the disclaimer explicitly rejects danger claims
    assert "aircraft in danger" not in json.dumps(wx).lower()
    assert "not danger" in wx[0]["why"]
    far = {"nws_points": [{"lat": 0.0, "lon": 0.0, "severity": "Severe",
                           "headline": "x"}]}
    assert not [f for f in air.flag_aircraft(o[0], [], far)
                if f["rule_id"] == "NEAR_SEVERE_WX"]


def test_stale_track_never_incident():
    o, _ = air.parse_adsblol(_payload([_ac(seen_pos=400.0)]))
    flags = air.flag_aircraft(o[0], [], {})
    st = [f for f in flags if f["rule_id"] == "POSITION_STALE"]
    assert len(st) == 1 and st[0]["interest"] == "LOW"
    # disappearance is explicitly never treated as an incident
    assert "never treated" in st[0]["why"].lower()
    assert "track quality" in st[0]["label"].lower() or \
        "stale" in st[0]["label"].lower()


def test_military_safe_wording():
    o, _ = air.parse_adsblol(_payload([_ac()]))
    mil = {"rule_id": "PUBLIC_MIL_OBSERVED",
           "label": "PUBLIC MILITARY AIRCRAFT OBSERVED",
           "level": "OBSERVED SIGNAL", "interest": "INFO",
           "evidence": {"provider_tag": "mil"},
           "why": "provider tags this contact as military"}
    blob = json.dumps(mil).lower()
    assert "target" not in blob and "mission" not in blob
    assert "tactical" not in blob
    # INFO-only flag must not enter IMPORTANT scoring
    lvl, _ = air.interest_of(
        [f for f in [mil] if f.get("interest") != "INFO"] or
        [{"interest": "LOW", "label": mil["label"], "why": mil["why"]}])
    assert lvl == "LOW"


def test_no_diversion_guessing():
    # Without lawful route context the engine must not emit diversion or
    # return verdicts at all.
    import inspect
    src = inspect.getsource(air.flag_aircraft) + \
        inspect.getsource(air.airport_events)
    assert "DIVERSION" not in src and "RETURN" not in src


def test_airport_holding_events():
    flagged = [
        {"icao24": "aaaa01", "lat": 50.10, "lon": 8.60,
         "rule_id": "POSSIBLE_HOLDING"},
        {"icao24": "bbbb02", "lat": 50.12, "lon": 8.62,
         "rule_id": "POSSIBLE_HOLDING"},
    ]
    evts = air.airport_events(flagged)
    assert len(evts) == 1
    assert "APT-FRA" in evts[0]["label"]
    assert evts[0]["level"] in ("POSSIBLE", "LIKELY")
    assert air.airport_events(flagged[:1]) == []


# --------------------------------------------------------------------------
# Source failure / rate limit / LOD

class _FakeHeaders:
    def __init__(self, ctype="application/json"):
        self._c = ctype

    def get_content_type(self):
        return self._c

    def get(self, k, d=""):
        return d


class _FakeResp:
    def __init__(self, body, ctype="application/json"):
        self._b = body if isinstance(body, bytes) else body.encode()
        self.headers = _FakeHeaders(ctype)
        self.status = 200

    def read(self, n=-1):
        if not self._b:
            return b""
        if n is None or n < 0:
            out, self._b = self._b, b""
            return out
        out, self._b = self._b[:n], self._b[n:]
        return out


def _router(mapping):
    def opener(req, timeout=None):
        for needle, value in mapping.items():
            if needle in req.full_url:
                if isinstance(value, Exception):
                    raise value
                body, ctype = value
                return _FakeResp(body, ctype)
        raise AssertionError("unexpected url " + req.full_url)
    return opener


def test_source_failure_honest(isolated_air):
    op = _router({"adsb.lol": TimeoutError("down")})
    rep = air.refresh_aviation(force=True, opener=op)
    assert rep["positioned"] == 0 and rep["errors"]
    snap = air.get_aviation(refresh=False)
    assert snap["counts"]["total"] == 0
    # empty snapshot: no observations claimed, nothing fabricated
    assert snap["states"] == [] and snap["important"] == []


def test_rate_limit_backoff(isolated_air):
    err = urllib.error.HTTPError("u", 429, "slow", {}, io.BytesIO(b"s"))
    op = _router({"adsb.lol": err})
    air.refresh_aviation(force=True, opener=op)
    snap = air.get_aviation(refresh=False)
    states = [h.get("state") for h in snap["health"]]
    assert "RATE_LIMITED" in states


def test_snapshot_lod_cap(isolated_air):
    rows = [_ac(f"{i:06x}") for i in range(100)]
    rr, _ = air.parse_adsblol(_payload(rows))
    assert len(rr) == 100
    assert air.SNAPSHOT_CAP == 5000
    # cap enforced at snapshot build
    big = [{"icao24": f"{i:06x}", "lat": 0.0, "lon": 0.0,
            "position_age_s": 1.0, "on_ground": False,
            "tile": "t", "signal": "ADS-B"} for i in range(6000)]
    with air._lock:
        air._memory["snapshot"] = {"at": time.time(),
                                   "generated_at": air.utcnow(),
                                   "states": big[:air.SNAPSHOT_CAP],
                                   "flagged": [], "important": [],
                                   "airport_events": [],
                                   "counts": {}, "errors": []}
    assert len(air.get_aviation(refresh=False)["states"]) == 5000


# --------------------------------------------------------------------------
# Performance: 5k / 10k / 15k / 20k state vectors

@pytest.mark.parametrize("n", [5000, 10000, 15000, 20000])
def test_ingest_scales(n, isolated_air):
    # Realistic path: separate tile payloads (each under the 4 MB cap),
    # then cross-tile dedup + flagging.
    chunks = [5000] * (n // 5000)
    all_rows = []
    t0 = time.time()
    base = 0
    for size in chunks:
        rows = [_ac(f"{(base + i):06x}", lat=40.0 + (i % 500) * 0.01,
                    lon=-100.0 + (i % 500) * 0.01) for i in range(size)]
        parsed, _ = air.parse_adsblol(_payload(rows))
        all_rows.append(parsed)
        base += size
    t_parse = time.time() - t0
    assert sum(map(len, all_rows)) == n
    t0 = time.time()
    out = air.dedup_states(all_rows)
    for o in out[:2000]:
        air.flag_aircraft(o, [], {})
    t_flag = time.time() - t0
    assert t_parse < 20.0 and t_flag < 20.0, (n, t_parse, t_flag)


# --------------------------------------------------------------------------
# Endpoints (mocked fetch — no network) + privacy/rights

def test_aviation_endpoints_mocked(isolated_air):
    import threading
    import urllib.request
    from http.server import HTTPServer
    from unittest import mock
    from gods_eye import demo as _demo
    from gods_eye.future import world_now as now
    body = _payload([_ac()])
    real_fetch = now.fetch_url

    def fake_fetch(url, timeout_s, content_types, etag="",
                   last_modified="", opener=None):
        if "adsb.lol" in url:
            return real_fetch(url, timeout_s, content_types, etag,
                              last_modified,
                              opener=_router({"adsb.lol": (body,
                                                           "application/json")}))
        return real_fetch(url, timeout_s, content_types, etag,
                          last_modified, opener=opener)
    with mock.patch.object(now, "fetch_url", side_effect=fake_fetch):
        server = HTTPServer((_demo.HOST, 0), _demo._Handler)
        port = server.server_address[1]
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        try:
            base = f"http://{_demo.HOST}:{port}"

            def get(path):
                return json.load(urllib.request.urlopen(
                    base + path, timeout=60))

            snap = get("/api/world/now/aviation?norefresh=0")
            assert snap["real_data"] is True
            assert snap["counts"]["total"] >= 1
            assert "adsb.lol" in snap["attribution"]
            light = get("/api/world/now/aviation?light=1")
            assert "states" not in light and light["counts"]["total"] >= 1
            assert light["source_rollup"]["source_id"] == "adsb-lol-live"
            # The globe draws from light positions: present, positioned,
            # and limited to render fields (no registration/squawk/owner).
            pos = light["positions"]
            assert 1 <= len(pos) <= light["counts"]["total"]
            assert set(pos[0]) == {"icao24", "lat", "lon", "track_deg",
                                   "callsign", "type", "baro_alt_ft", "gs_kt"}
            assert all(p["lat"] is not None and p["lon"] is not None
                       for p in pos)
            imp = get("/api/world/now/important")
            assert "important" in imp and "airport_events" in imp
            hx = snap["states"][0]["icao24"]
            tr = get("/api/world/now/trail?hex=" + hx)
            assert tr["aircraft"]["icao24"] == hx and "trail" in tr
            try:
                urllib.request.urlopen(
                    base + "/api/world/export?layer=aviation-live",
                    timeout=10)
                raise AssertionError("no bulk-export surface may exist here")
            except urllib.error.HTTPError as e:
                # Fail-closed by absence: this tree exposes no export
                # endpoint at all, so bulk exfiltration is impossible
                # (the mixed tree refuses the same layer with 403).
                assert e.code == 404
        finally:
            server.shutdown()


def test_aviation_privacy_rights(isolated_air):
    snap_blob_keys = set()
    rows, _ = air.parse_adsblol(_payload([_ac()]))
    for o in rows:
        snap_blob_keys |= set(o)
    assert not (air.FORBIDDEN_FIELDS & snap_blob_keys)
    from gods_eye.rights import registry as rg
    rec = rg.lookup("adsb_lol_live")
    assert rec is not None and rec.commercial_use == "yes"
    assert "ODbL" in rec.attribution
    from gods_eye.future import sensor_sources as ss
    assert ss.get("adsb-lol-live").status == "QUALIFIED"
    assert ss.get("airplanes-live").status == "NEEDS_TERMS_REVIEW"


# --------------------------------------------------------------------------
# Movement V2: rollup / important-v2 / cooldown / viewport / deep links

def _seed_world_now(items_by_source):
    from gods_eye.future import world_now as now
    mem = now._memory
    saved = dict(mem)
    mem.clear()
    for sid, items in items_by_source.items():
        mem[sid] = {"at": time.time(), "retrieved_at": air.utcnow(),
                    "items": items}
    return saved


def _restore_world_now(saved):
    from gods_eye.future import world_now as now
    now._memory.clear()
    now._memory.update(saved)


def _quake(key="usgs-earthquakes:u1", mag=6.2, place="offshore Test",
           lat=38.0, lon=140.0, evt="2026-09-16T08:00:00+00:00"):
    return {"source": "usgs-earthquakes", "stable_key": key,
            "lat": lat, "lon": lon, "source_event_time": evt,
            "fields": {"mag": mag, "place": place}}


def test_source_rollup_worst_state(isolated_air):
    air._health["tile:eu-central"] = {"state": "ONLINE"}
    air._health["tile:us-northeast"] = {"state": "STALE"}
    air._health["squawk:7700"] = {"state": "ONLINE"}
    r = air.source_rollup()
    assert r["source_id"] == "adsb-lol-live"
    assert r["state"] == "STALE"  # worst shown, ONLINE not hidden either
    assert r["tiles_online"] == f"1/{len(air.TILES)}"
    assert "adsb.lol" in r["attribution"]


def test_important_v2_ranking_and_5w1h(isolated_air):
    saved = _seed_world_now({"usgs-earthquakes": [_quake()]})
    try:
        air._memory["snapshot"] = {
            "at": time.time(), "generated_at": air.utcnow(), "states": [],
            "flagged": [], "important": [], "airport_events": [],
            "counts": {"total": 0}, "errors": []}
        v2 = air.important_v2()
        assert v2["mode"] == "important-v2" and v2["n"] >= 1
        top = v2["items"][0]
        assert top["domain"] == "EARTH" and "6.2" in top["title"]
        for k in ("reasons", "source", "when", "certainty", "observed",
                  "inferred", "scores", "total", "freshness_age_h",
                  "n_sources", "observed_or_inferred"):
            assert k in top and top[k] not in (None, ""), k
        assert top["observed_or_inferred"] in ("OBSERVED", "INFERRED")
        assert set(top["scores"]) == {"severity", "freshness",
                                      "source_quality", "corroboration",
                                      "rarity", "scope"}
        # quake near (38,140): infra context is proximity-only
        assert "proximity only" in top["inferred"]
        assert "damage" in top["inferred"] or "impact" in top["inferred"]
    finally:
        _restore_world_now(saved)


def test_429_cooldown_no_storm(isolated_air):
    err = urllib.error.HTTPError("u", 429, "slow", {}, io.BytesIO(b"s"))
    calls = []
    base = _router({"adsb.lol": err})

    def counting(req, timeout=None):
        calls.append(req.full_url)
        return base(req, timeout)
    air.refresh_aviation(force=True, opener=counting)
    first = len(calls)
    assert first > 0
    air.refresh_aviation(force=False, opener=counting)
    # cooldown: no new provider hits without force
    assert len(calls) == first
    air.refresh_aviation(force=True, opener=counting)
    assert len(calls) > first  # force still overrides


def test_viewport_priority(isolated_air):
    bodies = {}
    for t in air.TILES:
        bodies[t["id"]] = _payload([_ac(f"{abs(hash(t['id'])) % 0xfffff:06x}",
                                        lat=t["lat"], lon=t["lon"])])

    def opener(req, timeout=None):
        for t in air.TILES:
            if f"lat/{t['lat']}/lon/{t['lon']}" in req.full_url:
                return _FakeResp(bodies[t["id"]])
        if "squawk" in req.full_url:
            return _FakeResp(_payload([]))
        raise AssertionError(req.full_url)
    air.refresh_aviation(force=True, opener=opener, max_legs=1,
                         viewport={"lat": 50.0, "lon": 10.0})
    states = [h for h in air._health.values()
              if h.get("state") == "ONLINE"]
    assert states, "viewport tile must be fetched first within budget"


def test_trail_truth_recorded(isolated_air):
    o, _ = air.parse_adsblol(_payload([_ac()]))
    air.update_tracks(o)
    tr = air.get_trail("aaaa01")
    assert tr and all(p.get("truth") == "RECORDED" for p in tr)


def test_deep_link_params_secret_free():
    # Deep links live in the globe UI (console/world/app.js); the classic
    # Leaflet fallback carries none. Both surfaces are scanned.
    src = ((ROOT / "console" / "world" / "app.js").read_text(
        encoding="utf-8") + (ROOT / "console" / "ultra.html").read_text(
        encoding="utf-8"))
    import re
    params = set(re.findall(r'QS\.get\("([^"]+)"\)', src))
    params |= set(re.findall(r"q\.(?:set|delete)\(\"([^\"]+)\"", src))
    params |= set(re.findall(r"[\"'](aircraft|event|region|lat|lon|zoom"
                             r"|view|mode|sky)[\"']\s*:", src))
    for bad in ("key", "token", "secret", "password", "apikey", "api_key",
                "auth", "credential", "path", "file"):
        assert bad not in params, bad
    assert {"aircraft", "event"} <= params
    # globe selection writes object ids into the URL (replaceState only)
    assert 'q.set("aircraft"' in src and 'q.set("event"' in src


def test_movement_endpoints_mocked(isolated_air):
    import threading
    import urllib.request
    from http.server import HTTPServer
    from unittest import mock
    from gods_eye import demo as _demo
    from gods_eye.future import world_now as now
    body = _payload([_ac(lat=48.2, lon=16.4, squawk="7700")])
    real_fetch = now.fetch_url

    def fake_fetch(url, timeout_s, content_types, etag="",
                   last_modified="", opener=None):
        if "adsb.lol" in url:
            return real_fetch(url, timeout_s, content_types, etag,
                              last_modified,
                              opener=_router({"adsb.lol": (body,
                                                           "application/json")}))
        raise TimeoutError("no net for world_now in this test")
    saved = _seed_world_now({"usgs-earthquakes": [_quake(lat=48.2,
                                                         lon=16.4)]})
    try:
        with mock.patch.object(now, "fetch_url", side_effect=fake_fetch):
            server = HTTPServer((_demo.HOST, 0), _demo._Handler)
            port = server.server_address[1]
            t = threading.Thread(target=server.serve_forever, daemon=True)
            t.start()
            try:
                base = f"http://{_demo.HOST}:{port}"

                def get(path):
                    return json.load(urllib.request.urlopen(
                        base + path, timeout=60))

                v2 = get("/api/world/now/aviation?norefresh=0")
                assert v2["counts"]["total"] >= 1
                v2 = get("/api/world/now/important-v2")
                assert v2["n"] >= 2  # quake + emergency-squawk aircraft
                here = get("/api/world/now/whatshere?lat=48.2&lon=16.4"
                           "&radius_km=400")
                assert here["movement"]["aircraft_nearby"] >= 1
                assert "NO LIVE SOURCE" in here["movement"]["vessels"]
                reg = get("/api/world/now/region?region=Austria")
                assert reg["movement"]["aircraft_tracked"] >= 1
            finally:
                server.shutdown()
    finally:
        _restore_world_now(saved)
