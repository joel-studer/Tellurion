"""CHANGE ENGINE V1 tests (offline only — network is always mocked).

Covers: EONET lifecycle / GDACS transitions / USGS aggregate baseline /
stable IDs + idempotent replay + versioned corrections / first_observed
preservation / evidence chain + rights / independent-source counting +
ONE SOURCE honesty / schema allowlist + forbidden trading fields /
no-synthetic guarantee / retention / API since+cursor / replay isolation /
globe drawer rendering contract / private-leak scan.
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

from gods_eye.future import world_change as chg  # noqa: E402

UTC = timezone.utc


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).replace(microsecond=0).isoformat()


NOW = datetime(2026, 9, 17, 18, 0, tzinfo=UTC)
NOW_ISO = _iso(NOW)


def _obj(source, key, lat=10.0, lon=20.0, fields=None, first_seen=None,
         event_time=None):
    return {
        "source": source,
        "source_item_id": key.split(":", 1)[-1],
        "source_url": f"https://example.test/{key}",
        "id": "NOW-X-12345678",
        "stable_key": key,
        "lat": lat, "lon": lon,
        "source_event_time": event_time or NOW_ISO,
        "published_time": "UNKNOWN",
        "first_seen": first_seen or NOW_ISO,
        "ingested_at": NOW_ISO,
        "effective_time": event_time or NOW_ISO,
        "precision": "REGIONAL",
        "rights": f"rights-for-{source}",
        "attribution": f"attribution-for-{source}",
        "provenance": f"attribution-for-{source}",
        "observation": "OBSERVED",
        "observation_type": "OBSERVED",
        "truth_mode": "DELAYED",
        "fields": fields or {},
    }


def _eonet(key="nasa-eonet:EONET-1", status="open", **kw):
    return _obj("nasa-eonet", key, fields={"title": "Cedar Creek Fire",
                                           "status": status,
                                           "categories": ["Wildfires"]},
                **kw)


def _gdacs(key="gdacs-alerts:GDACS-EQ-9", level="Orange", **kw):
    return _obj("gdacs-alerts", key, lat=38.0, lon=140.0,
                fields={"title": "EQ offshore", "event_type": "EQ",
                        "alert_level": level}, **kw)


def _usgs(key, mag, day, **kw):
    dt = datetime(2026, 9, 17, 12, 0, tzinfo=UTC) - timedelta(days=day)
    return _obj("usgs-earthquakes", key, lat=35.0, lon=139.0,
                fields={"mag": mag, "place": "offshore"},
                event_time=_iso(dt), **kw)


@pytest.fixture()
def store_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(chg, "_runtime_dir", lambda: tmp_path)
    yield tmp_path


def _groups(**kw):
    return kw


# ------------------------------------------------------- EONET ---


def test_eonet_first_run_seeds_silently(store_dir):
    new, updated = chg.detect(_groups(**{"nasa-eonet": [_eonet()]}),
                              [], NOW_ISO)
    assert (new, updated) == ([], [])


def test_eonet_new_event_detected_once(store_dir):
    chg.detect(_groups(**{"nasa-eonet": [_eonet()]}), [], NOW_ISO)
    new, _ = chg.detect(_groups(**{"nasa-eonet": [_eonet(), _eonet(
        "nasa-eonet:EONET-2")]}), [], NOW_ISO)
    assert len(new) == 1
    c = new[0]
    assert c["type"] == "eonet-opened" and c["observation_type"] == "OBSERVED"
    assert c["severity"] == "WATCH" and c["real_data"] is True
    assert "Cedar Creek Fire" in c["title"]
    # Identical reprocessing emits nothing new (idempotent).
    new2, upd2 = chg.detect(_groups(**{"nasa-eonet": [_eonet(), _eonet(
        "nasa-eonet:EONET-2")]}), [], NOW_ISO)
    assert (new2, upd2) == ([], [])


def test_eonet_stated_transition(store_dir):
    chg.detect(_groups(**{"nasa-eonet": [_eonet()]}), [], NOW_ISO)
    new, _ = chg.detect(_groups(**{"nasa-eonet": [_eonet(status="closed")]}),
                        [], NOW_ISO)
    assert len(new) == 1 and new[0]["type"] == "eonet-transition"
    assert new[0]["before"] == {"status": "open"}
    assert new[0]["after"] == {"status": "closed"}


def test_eonet_closure_inferred_after_absence(store_dir):
    chg.detect(_groups(**{"nasa-eonet": [_eonet()]}), [], NOW_ISO)
    day2 = _iso(NOW + timedelta(days=1))
    new, _ = chg.detect(_groups(**{"nasa-eonet": []}), [], day2)
    assert new == []  # 1 day absent: too early, honest silence
    day5 = _iso(NOW + timedelta(days=5))
    new, _ = chg.detect(_groups(**{"nasa-eonet": []}), [], day5)
    assert len(new) == 1
    c = new[0]
    assert c["type"] == "eonet-closed"
    assert c["observation_type"] == "INFERRED"
    assert "inferred, not observed" in " ".join(c["why_flagged"])
    assert c["first_observed"] == NOW_ISO  # preserved, not reset


def test_eonet_feed_only_without_coords(store_dir):
    chg.detect(_groups(**{"nasa-eonet": [_eonet()]}), [], NOW_ISO)
    o = _eonet("nasa-eonet:EONET-9", lat=None, lon=None)
    new, _ = chg.detect(_groups(**{"nasa-eonet": [_eonet(), o]}), [],
                        NOW_ISO)
    assert len(new) == 1
    assert new[0]["location"] == {"lat": None, "lon": None}


# ------------------------------------------------------- GDACS ---


def test_gdacs_new_and_green_noise_skipped(store_dir):
    chg.detect(_groups(**{"gdacs-alerts": []}), [], NOW_ISO)
    assert chg.detect(_groups(**{"gdacs-alerts": [
        _gdacs(level="Green")]}), [], NOW_ISO) == ([], [])
    new, _ = chg.detect(_groups(**{"gdacs-alerts": [
        _gdacs(level="Green"), _gdacs("gdacs-alerts:GDACS-FL-1",
                                     level="Orange")]}), [], NOW_ISO)
    assert len(new) == 1
    assert new[0]["type"] == "gdacs-new"
    assert new[0]["severity"] == "WATCH"
    assert new[0]["after"] == {"alert_level": "orange"}


def test_gdacs_transition_once(store_dir):
    chg.detect(_groups(**{"gdacs-alerts": [_gdacs(level="Green")]}), [],
               NOW_ISO, seed_only=True)
    new, _ = chg.detect(_groups(**{"gdacs-alerts": [_gdacs(level="Orange")]}),
                        [], NOW_ISO)
    assert len(new) == 1
    c = new[0]
    assert c["type"] == "gdacs-transition"
    assert c["before"] == {"alert_level": "green"}
    assert "Green → Orange" in c["title"] or "green" in " ".join(
        c["why_flagged"]).lower()
    # Repeat poll: no duplicate.
    assert chg.detect(_groups(**{"gdacs-alerts": [_gdacs(level="Orange")]}),
                      [], NOW_ISO) == ([], [])
    # De-escalation from a watched level also emits (material).
    new, _ = chg.detect(_groups(**{"gdacs-alerts": [_gdacs(level="Green")]}),
                        [], NOW_ISO)
    assert len(new) == 1 and new[0]["severity"] == "INFO"


# -------------------------------------------------------- USGS ---


def _quiet_week(today_n, today_day=0, base_n=1):
    objs = []
    for d in range(1, 8):
        for i in range(base_n):
            objs.append(_usgs(f"usgs-earthquakes:q{d}-{i}", 5.1, d))
    for i in range(today_n):
        objs.append(_usgs(f"usgs-earthquakes:t-{i}", 5.4, today_day))
    return objs


def test_usgs_episode_thresholds_and_mutations(store_dir):
    assert chg.detect(_groups(**{"usgs-earthquakes": _quiet_week(0)}), [],
                      NOW_ISO, seed_only=True) == ([], [])
    # 3 events on a quiet week: below the absolute floor of 4.
    assert chg.detect(_groups(**{"usgs-earthquakes": _quiet_week(3)}), [],
                      NOW_ISO) == ([], [])
    # 4 events: episode, exactly one change, transparent rule text.
    new, _ = chg.detect(_groups(**{"usgs-earthquakes": _quiet_week(4)}), [],
                        NOW_ISO)
    assert len(new) == 1
    c = new[0]
    assert c["type"] == "usgs-episode"
    assert c["observation_type"] == "INFERRED"
    assert c["severity"] == "ALERT"
    assert c["after"]["m5_last_24h"] == 4
    assert "3x" in " ".join(c["why_flagged"]) or "3.0x" in " ".join(
        c["why_flagged"])
    assert c["magnitude"]["area_m2"] is None
    # Same snapshot again: idempotent, no duplicate.
    assert chg.detect(_groups(**{"usgs-earthquakes": _quiet_week(4)}), [],
                      NOW_ISO) == ([], [])


def test_usgs_factor_gate_on_busy_weeks(store_dir):
    chg.detect(_groups(**{"usgs-earthquakes": _quiet_week(0, base_n=2)}), [],
               NOW_ISO, seed_only=True)
    # mean=2 -> threshold max(4, 6) = 6; 5 events must NOT fire.
    assert chg.detect(_groups(**{"usgs-earthquakes": _quiet_week(5, base_n=2)}),  # noqa: E501
                      [], NOW_ISO) == ([], [])
    new, _ = chg.detect(_groups(**{"usgs-earthquakes": _quiet_week(6, base_n=2)}),  # noqa: E501
                        [], NOW_ISO)
    assert len(new) == 1


# ------------------------------------------- ids / versioning ---


def test_stable_ids_and_versioned_correction(store_dir):
    # Lifecycle transitions carry direction in the ID: escalate then
    # de-escalate are distinct changes, never collapsed.
    chg.detect(_groups(**{"gdacs-alerts": [_gdacs(level="Green")]}), [],
               NOW_ISO, seed_only=True)
    new, _ = chg.detect(_groups(**{"gdacs-alerts": [_gdacs(level="Orange")]}),
                        [], NOW_ISO)
    up_id = new[0]["id"]
    assert up_id.startswith("chg:gdacs-transition-")
    new, _ = chg.detect(_groups(**{"gdacs-alerts": [_gdacs(level="Green")]}),
                        [], NOW_ISO)
    assert len(new) == 1 and new[0]["id"] != up_id
    # Rebuilt changes (USGS episode, recomputed every poll while the day
    # is active) version honestly under one stable ID on correction.
    objs = _quiet_week(4)
    new, _ = chg.detect(_groups(**{"usgs-earthquakes": objs}), [], NOW_ISO)
    cid = new[0]["id"]
    assert cid.startswith("chg:usgs-episode-")
    bigger = objs + [_usgs("usgs-earthquakes:t-9", 6.2, 0)]
    new2, upd2 = chg.detect(_groups(**{"usgs-earthquakes": bigger}), [],
                            NOW_ISO)
    assert new2 == [] and len(upd2) == 1 and upd2[0]["id"] == cid
    store = chg.load_store()
    assert store["emitted"][cid]["version"] == 2
    assert upd2[0]["after"]["m5_last_24h"] == 5


# --------------------------------- evidence / corroboration ---


def test_evidence_chain_and_rights(store_dir):
    chg.detect(_groups(**{"nasa-eonet": [_eonet()]}), [], NOW_ISO)
    new, _ = chg.detect(_groups(**{"nasa-eonet": [_eonet(), _eonet(
        "nasa-eonet:EONET-2")]}), [], NOW_ISO)
    c = new[0]
    assert len(c["evidence"]) == 1
    ev = c["evidence"][0]
    for key in ("source", "stable_key", "source_event_time", "source_url",
                "rights", "attribution", "truth_mode"):
        assert ev[key], key
    assert c["rights"]["sources"][0]["source"] == "nasa-eonet"
    assert "Per-source rights" in c["rights"]["note"]


def test_one_source_honesty_then_independent_corroboration(store_dir):
    chg.detect(_groups(**{"gdacs-alerts": [_gdacs(
        "gdacs-alerts:GDACS-EQ-0", level="Green")]}), [], NOW_ISO)
    new, _ = chg.detect(_groups(**{"gdacs-alerts": [
        _gdacs("gdacs-alerts:GDACS-EQ-0", level="Green"),
        _gdacs("gdacs-alerts:GDACS-EQ-9", level="Red")]}), [], NOW_ISO)
    c = new[0]
    assert c["corroboration"] == "ONE SOURCE" and c["source_count"] == 1
    assert c["confidence"] == "MODERATE"
    # Shared-upstream link (USGS+GDACS same quake) must NOT inflate.
    shared = [{"a": "gdacs-alerts:GDACS-EQ-9", "b": "usgs-earthquakes:u1",
               "independence": "SHARED_UPSTREAM",
               "corroboration": "MULTIPLE SOURCES"}]
    chg.detect(_groups(**{"gdacs-alerts": [_gdacs(level="Red")]}), shared,
               NOW_ISO)
    rec = chg.load_store()["emitted"]
    cid = next(iter(rec))
    assert rec[cid]["change"]["corroboration"] == "ONE SOURCE"
    # Independent leg (news report) corroborates -> HIGH.
    indep = [{"a": "gdacs-alerts:GDACS-EQ-9", "b": "gdelt-doc:r1",
              "independence": "INDEPENDENT",
              "corroboration": "CORROBORATED"}]
    chg.detect(_groups(**{"gdacs-alerts": [_gdacs(level="Red")]}), indep,
               NOW_ISO)
    rec = chg.load_store()["emitted"]
    assert rec[cid]["change"]["corroboration"] == "CORROBORATED"
    assert rec[cid]["change"]["confidence"] == "HIGH"
    assert rec[cid]["change"]["source_count"] == 2


# --------------------------------------------- schema gates ---


def test_schema_allowlist_and_clean(store_dir):
    chg.detect(_groups(**{"nasa-eonet": [_eonet()]}), [], NOW_ISO)
    new, _ = chg.detect(_groups(**{"nasa-eonet": [_eonet(), _eonet(
        "nasa-eonet:EONET-2")]}), [], NOW_ISO)
    c = new[0]
    assert set(c) == {
        "id", "type", "category", "title", "location", "first_observed",
        "last_observed", "effective_time", "before", "after", "magnitude",
        "confidence", "observation_type", "corroboration", "source_count",
        "corroborating_keys", "evidence", "freshness", "rights",
        "why_flagged", "rank", "severity", "real_data", "live",
    }
    chg.assert_schema_clean(c)


def test_schema_forbids_trading_fields():
    for field in sorted(chg.FORBIDDEN_FIELDS):
        assert field, "empty forbidden token"
        with pytest.raises(ValueError):
            chg.assert_schema_clean({"id": "x", field: 1,
                                     "evidence": [{field: 2}]})
    assert chg.FORBIDDEN_FIELDS == frozenset({
        "price", "ticker", "market", "instrument", "alpha", "edge",
        "signal", "tradability", "expected_return", "position", "side",
        "buy", "sell", "strategy", "execution", "sizing", "capital",
        "pnl",
    })


def test_no_synthetic_objects(store_dir):
    chg.detect(_groups(**{"nasa-eonet": [_eonet()]}), [], NOW_ISO)
    new, _ = chg.detect(_groups(**{"nasa-eonet": [_eonet(), _eonet(
        "nasa-eonet:EONET-2")]}), [], NOW_ISO)
    blob = json.dumps(new).lower()
    assert "synthetic" not in blob
    assert "syn-" not in blob
    assert new[0]["real_data"] is True and new[0]["live"] is False


def test_area_never_fabricated(store_dir):
    chg.detect(_groups(**{"nasa-eonet": [_eonet()]}), [], NOW_ISO)
    new, _ = chg.detect(_groups(**{"nasa-eonet": [_eonet(), _eonet(
        "nasa-eonet:EONET-2")]}), [], NOW_ISO)
    assert new[0]["magnitude"]["area_m2"] is None


# -------------------------------------------------- retention ---


def test_retention_policy(store_dir):
    assert chg.BASELINE_RETENTION_DAYS == 14
    old = _iso(NOW - timedelta(days=30))
    store = chg.load_store()
    store["eonet"]["stale"] = {"status": "open", "last_seen": old,
                               "first_seen": old, "title": "old"}
    store["usgs_daily"]["2020-01-01"] = {"n": 1, "keys": []}
    store["emitted"]["old"] = {"emitted_at": old, "version": 1,
                               "change": {"id": "old"}}
    chg.save_store(store)
    chg.detect(_groups(), [], NOW_ISO)
    pruned = chg.load_store()
    # The staged stale open entry legitimately closes (absent 30 days),
    # then its baseline row ages out; the hand-planted old rows vanish.
    assert "stale" not in pruned["eonet"]
    assert "2020-01-01" not in pruned["usgs_daily"]
    assert "old" not in pruned["emitted"]


# -------------------------------------------------------- API ---


def _fake_now_payload():
    return {"objects": {"nasa-eonet": [_eonet()]}, "links": [],
            "health": [{"source_id": "nasa-eonet", "state": "ONLINE"}]}


def test_api_since_cursor_and_limit(store_dir):
    with mock.patch("gods_eye.future.world_now.get_now",
                    return_value=_fake_now_payload()):
        chg.get_changes()
        with mock.patch("gods_eye.future.world_now.get_now",
                        return_value={"objects": {"nasa-eonet": [
                            _eonet(), _eonet("nasa-eonet:EONET-2")]},
                            "links": [], "health": [
                                {"source_id": "nasa-eonet",
                                 "state": "ONLINE"}]}):
            payload = chg.get_changes()
    assert payload["truth_label"] == chg.TRUTH_LABEL
    assert payload["real_data"] is True and payload["live"] is False
    assert payload["cursor"] and payload["retention_days"] == 14
    assert payload["sources"] == {"nasa-eonet": "ONLINE"}
    assert payload["counts"]["changes"] == 1
    # since=cursor filters to strictly newer changes.
    with mock.patch("gods_eye.future.world_now.get_now",
                    return_value=_fake_now_payload()):
        again = chg.get_changes(since=payload["cursor"])
    assert again["counts"]["changes"] == 0
    limited = chg.stored_changes(limit=1)
    assert len(limited) <= 1


def test_api_route_contract():
    from gods_eye import demo as _demo
    server = HTTPServer((_demo.HOST, 0), _demo._Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        base = f"http://{_demo.HOST}:{server.server_address[1]}"
        with urllib.request.urlopen(base + "/api/world/changes?norefresh=1",
                                    timeout=60) as r:
            payload = json.load(r)
    finally:
        server.shutdown()
    assert payload["truth_label"] == chg.TRUTH_LABEL
    assert payload["real_data"] is True
    assert set(payload) >= {"changes", "cursor", "counts", "sources",
                            "generated_at", "mode"}


# ------------------------------------------- replay isolation ---


def test_replay_payload_has_no_changes():
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
    assert "chg:" not in blob and "CHANGE_DETECTED" not in blob


def test_changes_only_enter_now_event_path():
    src = (ROOT / "console" / "world" / "app.js").read_text(encoding="utf-8")
    assert "state.changes" in src
    # The only event-list entry point for changes is the NOW branch.
    idx = src.index("function nowEvents")
    end = src.index("function nowAircraftPoints")
    assert "state.changes" in src[idx:end]
    replay_builders = src[src.index("function buildData"):
                          src.index("function buildNowData")]
    assert "state.changes" not in replay_builders
    # Replay ships an empty changes source so the shared ring layer can
    # exist in both modes without ever rendering synthetic content.
    assert "changes: fc([])" in replay_builders
    assert '"change-ring"' in src and '"changes"' in src


def test_globe_drawer_renders_changes():
    src = (ROOT / "console" / "world" / "app.js").read_text(encoding="utf-8")
    assert 'CATEGORY.CHANGE' in src or 'CHANGE: {' in src
    assert 'data.kind === "change"' in src
    assert 'id.startsWith("chg:")' in src
    for needle in ("first observed", "why flagged", "before / after",
                     "change detected", "never estimated"):
        assert needle in src.lower(), needle


# ------------------------------------------ private boundary ---


def test_new_modules_stay_public_safe():
    import re
    module = (ROOT / "python" / "gods_eye" / "future"
              / "world_change.py").read_text(encoding="utf-8")
    # The denylist definition itself is allowed; everything else must
    # be clean. Whole-word matching: prose that merely names a ban is
    # still a leak vector, so the module avoids the tokens entirely
    # (verified below).
    start = module.index("FORBIDDEN_FIELDS = frozenset({")
    end = module.index("})", start)
    body = module[:start] + module[end + 2:]
    word = lambda tok: re.search(r"(?<![a-z_])" + re.escape(tok)
                                 + r"(?![a-z_])", body.lower())
    hits = sorted({t for t in chg.FORBIDDEN_FIELDS if word(t)})
    assert not hits, hits
    extra = ["market_mapping", "impact_model", "backtest", "sharpe",
             "portfolio", "credential", "password"]
    hits = sorted({t for t in extra if word(t)})
    assert not hits, hits
    from gods_eye.future import boundary
    for rel in ("python/gods_eye/future/world_change.py",
                "tests/test_world_change_v22.py"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert boundary.secret_hits_text(text) == [], rel
        kinds = {k for k, rx in boundary._LOCAL_RES if rx.search(text)}
        assert kinds == set(), (rel, kinds)
