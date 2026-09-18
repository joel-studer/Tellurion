"""Generic public change detection V1 (sidecar over normalized NOW objects).

Answers WHAT CHANGED / WHEN / WHERE / WHAT EVIDENCE / HOW CERTAIN for
already-qualified public legs. This is generic public-world
intelligence — never financial advice: the serialized schema
forbids financial/trading fields (see FORBIDDEN_FIELDS, enforced by
test_world_change_v22.py).

V1 detectors (all deterministic, all real-data-only):
  EONET lifecycle  newly opened event / closure (inferred after
                   sustained absence — the open-events feed never
                   states closures) / open<->closed transitions.
  GDACS            newly observed Orange/Red alert; alert-level
                   transitions touching Orange/Red (escalation and
                   de-escalation). Green-only churn is noise: skipped.
  USGS             significant seismic episode: M5+ count in the last
                   24 h versus a rolling 7-day aggregate baseline.

Sidecar model: detectors read normalized NOW objects (world_now
envelope) plus a small aggregates-only baseline store. Ingestion
functions are untouched. Deduplication uses stable change IDs, so
reprocessing identical observations is idempotent; corrections bump
the record version under the same ID.

Baseline store (runtime state, never shipped):
  raw_store/world_change/baselines.json — per-object lifecycle state
  (status/level/last_seen), USGS daily M5+ counts, emitted change
  records. Aggregates, states and timestamps only: no identity
  database, no person or vehicle history, no aircraft retention.

BASELINE_RETENTION_DAYS = 14: the USGS detector needs 7 complete
prior days, plus a 7-day grace window for late/updated feed items
and week-over-week stability. Anything older is pruned. This is the
shortest retention that supports the V1 detectors; the changes API
is a recent-change feed, not an archive.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BASELINE_RETENTION_DAYS = 14
BASELINE_WINDOW_DAYS = 7
STORE_NAME = "baselines.json"

# EONET's configured leg polls the open-events feed, which never
# states closures. An id vanishes from curation as well as from
# closure, so absence becomes a closure only after sustained
# absence — stated as INFERRED, never OBSERVED.
EONET_ABSENT_DAYS = 3

# USGS episode rule (simple, documented, mechanistically justified):
# M5+ quakes have a global background of a few per day, so a single
# mainshock plus aftershocks must not trip the detector. An episode
# needs at least USGS_EPISODE_MIN events in 24 h AND at least
# USGS_EPISODE_FACTOR times the 7-day daily mean.
USGS_SIGNIFICANT_MAG = 5.0
USGS_EPISODE_MIN = 4
USGS_EPISODE_FACTOR = 3.0

# GDACS alert ranks. Transitions are emitted only when the old or the
# new level is Orange/Red; Green-only churn is noise.
GDACS_RANK = {"green": 0, "orange": 1, "red": 2}
GDACS_WATCH_LEVELS = {"orange", "red"}

# Change severities use the house scale (INFO/WATCH/ALERT/CRITICAL).
# Confidence is never inflated: corroborated by an independent leg
# (world_now.link_events independence == INDEPENDENT) -> HIGH;
# shared-upstream or single qualified leg -> MODERATE. Nothing is
# ever CERTAIN.
SEVERITY_ORDER = ("INFO", "WATCH", "ALERT", "CRITICAL")

# Absolutely forbidden in the serialized public schema. Enforced by
# test_world_change_v22.py::test_schema_forbids_trading_fields.
FORBIDDEN_FIELDS = frozenset({
    "price", "ticker", "market", "instrument", "alpha", "edge",
    "signal", "tradability", "expected_return", "position", "side",
    "buy", "sell", "strategy", "execution", "sizing", "capital",
    "pnl",
})

CHANGE_TYPES = (
    "eonet-opened", "eonet-closed", "eonet-transition",
    "gdacs-new", "gdacs-transition",
    "usgs-episode",
)

TRUTH_LABEL = "WORLD CHANGE (real public feeds)"


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _now_dt(value: Optional[str] = None) -> datetime:
    if value:
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _runtime_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in (here.parent, *here.parents):
        cand = parent / "raw_store" / "world_change"
        if (parent / "raw_store").is_dir() or (parent / "pyproject.toml").is_file():
            cand.mkdir(parents=True, exist_ok=True)
            return cand
    cand = Path.cwd() / "raw_store" / "world_change"
    cand.mkdir(parents=True, exist_ok=True)
    return cand


def _store_path() -> Path:
    return _runtime_dir() / STORE_NAME


def _blank_store() -> Dict[str, Any]:
    return {"eonet": {}, "gdacs": {}, "usgs_daily": {}, "emitted": {},
            "_polls": 0}


def load_store() -> Dict[str, Any]:
    try:
        data = json.loads(_store_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return _blank_store()
    store = _blank_store()
    for key in ("eonet", "gdacs", "usgs_daily", "emitted"):
        if isinstance(data.get(key), dict):
            store[key] = data[key]
    if isinstance(data.get("_polls"), int):
        store["_polls"] = data["_polls"]
    for flag in ("_seeded_eonet", "_seeded_gdacs"):
        if data.get(flag) is True:
            store[flag] = True
    return store


def save_store(store: Dict[str, Any]) -> None:
    path = _store_path()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(store, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8")
    tmp.replace(path)


def prune_store(store: Dict[str, Any], now: Optional[str] = None) -> None:
    """Drop baseline/emitted state older than the retention window."""
    cutoff = _now_dt(now) - timedelta(days=BASELINE_RETENTION_DAYS)
    for section in ("eonet", "gdacs"):
        for key in [k for k, v in store.get(section, {}).items()
                    if _now_dt((v or {}).get("last_seen")) < cutoff]:
            del store[section][key]
    for key in [k for k, v in store.get("usgs_daily", {}).items()
                if _day_dt(k) < cutoff]:
        del store["usgs_daily"][key]
    for key in [k for k, v in store.get("emitted", {}).items()
                if _now_dt((v or {}).get("emitted_at")) < cutoff]:
        del store["emitted"][key]


def _day_dt(day: str) -> datetime:
    try:
        return datetime(int(day[0:4]), int(day[5:7]), int(day[8:10]),
                        tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)


def _day_key(when: datetime) -> str:
    return when.astimezone(timezone.utc).strftime("%Y-%m-%d")


def _parse_time(value: Any) -> Optional[datetime]:
    if not value or value == "UNKNOWN":
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _mag_of(obj: Dict[str, Any]) -> Optional[float]:
    try:
        mag = float((obj.get("fields") or {}).get("mag"))
        return mag
    except (TypeError, ValueError):
        return None


def _status_of(obj: Dict[str, Any]) -> str:
    return str((obj.get("fields") or {}).get("status") or "").lower()


def _level_of(obj: Dict[str, Any]) -> str:
    return str((obj.get("fields") or {}).get("alert_level") or "").lower()


def _title_of(obj: Dict[str, Any]) -> str:
    fields = obj.get("fields") or {}
    return str(fields.get("title") or fields.get("place")
               or obj.get("stable_key") or obj.get("id") or "untitled")


def assert_schema_clean(change: Dict[str, Any]) -> None:
    """Fail closed if a forbidden trading/finance field ever appears."""
    seen: List[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if str(key).lower() in FORBIDDEN_FIELDS:
                    seen.append(str(key))
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(change)
    if seen:
        raise ValueError(f"forbidden schema fields in change object: {seen}")


def _rank_score(rank: Dict[str, int]) -> Tuple[str, int]:
    """Public-interest score (generic axes only): severity, freshness,
    corroboration, rarity, scope — each 0..2. Output reads as
    'worth investigating', never 'worth trading'."""
    total = sum(max(0, min(2, int(rank.get(axis, 0)))) for axis in
                ("severity", "freshness", "corroboration", "rarity", "scope"))
    return ("HIGH" if total >= 7 else "MODERATE" if total >= 4 else "LOW",
            total)


def _freshness(last_observed: Optional[str],
               now: Optional[str] = None) -> Dict[str, Any]:
    dt = _parse_time(last_observed)
    if dt is None:
        return {"observed_at": last_observed or "UNKNOWN",
                "age_hours": None, "age_class": "unknown"}
    age_h = max(0.0, (_now_dt(now) - dt).total_seconds() / 3600.0)
    cls = "fresh" if age_h < 24 else "recent" if age_h < 72 else "older"
    return {"observed_at": last_observed, "age_hours": round(age_h, 1),
            "age_class": cls}


def _evidence_entry(obj: Dict[str, Any]) -> Dict[str, Any]:
    fields = obj.get("fields") if isinstance(obj.get("fields"), dict) else {}
    return {
        "source": obj.get("source", "UNKNOWN"),
        "stable_key": obj.get("stable_key", ""),
        "title": _title_of(obj),
        "source_event_time": obj.get("source_event_time", "UNKNOWN"),
        "source_url": obj.get("source_url", "UNKNOWN"),
        "rights": obj.get("rights", "UNKNOWN"),
        "attribution": obj.get("attribution", ""),
        "truth_mode": obj.get("truth_mode", "DELAYED"),
        "observation_type": obj.get("observation_type", "OBSERVED"),
        # Minimal classification passthrough (source-stated categories /
        # event type) so downstream evidence consumers can apply
        # deterministic eligibility without refetching objects.
        "fields": {
            "categories": list(fields.get("categories") or []),
            "event_type": fields.get("event_type"),
        },
    }


def _rights_block(evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "sources": [{"source": e["source"], "rights": e["rights"],
                     "attribution": e["attribution"]} for e in evidence],
        "note": "Per-source rights; underlying data stays under its "
                "source licence with in-app attribution.",
    }


def _corroboration(primary_key: str,
                   links: List[Dict[str, Any]]) -> Tuple[str, int, List[str]]:
    """Count independent corroborating legs via world_now link records.

    Links whose independence is SHARED_UPSTREAM (same upstream feed)
    do not count as independent corroboration — the existing
    shared-upstream rule, reused unchanged.
    """
    independent: List[str] = []
    for link in links or []:
        other = None
        if link.get("a") == primary_key:
            other = link.get("b")
        elif link.get("b") == primary_key:
            other = link.get("a")
        if other and link.get("independence") == "INDEPENDENT":
            independent.append(str(other))
    if independent:
        return ("CORROBORATED", 1 + len(set(independent)),
                sorted(set(independent)))
    return ("ONE SOURCE", 1, [])


def _confidence(corroboration: str) -> str:
    return "HIGH" if corroboration == "CORROBORATED" else "MODERATE"


def _change_id(*parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"chg:{'-'.join(parts)}:{digest}"


def _build(type_: str, title: str, category: str,
           lat: Any, lon: Any,
           first_observed: str, last_observed: str,
           before: Dict[str, Any], after: Dict[str, Any],
           magnitude: Dict[str, Any],
           severity: str, observation_type: str,
           primary_key: str, links: List[Dict[str, Any]],
           objects: List[Dict[str, Any]],
           why_flagged: List[str],
           rank_axes: Dict[str, int],
           now: str,
           id_extra: Tuple[str, ...] = ()) -> Dict[str, Any]:
    corroboration, source_count, partners = _corroboration(primary_key,
                                                           links)
    evidence = [_evidence_entry(o) for o in objects]
    rank_label, rank_score = _rank_score(rank_axes)
    change = {
        "id": _change_id(type_, primary_key, *id_extra),
        "type": type_,
        "category": category,
        "title": title,
        "location": {"lat": lat, "lon": lon},
        "first_observed": first_observed,
        "last_observed": last_observed,
        "effective_time": last_observed,
        "before": before,
        "after": after,
        # area_m2 is present but ALWAYS null unless a source states an
        # area explicitly. Never estimated, never inferred.
        "magnitude": {"area_m2": magnitude.get("area_m2"),
                      "detail": magnitude.get("detail", "")},
        "confidence": _confidence(corroboration),
        "observation_type": observation_type,
        "corroboration": corroboration,
        "source_count": source_count,
        "corroborating_keys": partners,
        "evidence": evidence,
        "freshness": _freshness(last_observed, now),
        "rights": _rights_block(evidence),
        "why_flagged": list(why_flagged),
        "rank": {"label": rank_label, "score": rank_score,
                 "axes": {a: max(0, min(2, int(rank_axes.get(a, 0))))
                          for a in ("severity", "freshness", "corroboration",
                                    "rarity", "scope")}},
        "severity": severity,
        "real_data": True,
        "live": False,
    }
    assert_schema_clean(change)
    return change


def detect_eonet(objects: List[Dict[str, Any]],
                 links: List[Dict[str, Any]],
                 store: Dict[str, Any],
                 now: str,
                 seed_only: bool = False) -> List[Dict[str, Any]]:
    """EONET lifecycle transitions. The very first poll seeds the baseline
    silently (nothing has ever been seen, so nothing can honestly be
    called new); later polls emit opened/closed/transition changes."""
    out: List[Dict[str, Any]] = []
    seen = store.setdefault("eonet", {})
    # Seed rule: the first poll that actually carries this source's
    # objects establishes the baseline silently. Empty polls (cold
    # cache) neither seed nor emit, so a cold start can never flood.
    first_run = not store.get("_seeded_eonet", False)
    if objects:
        store["_seeded_eonet"] = True
    current = {}
    for obj in objects or []:
        key = str(obj.get("stable_key") or "")
        if not key:
            continue
        status = _status_of(obj) or "open"
        current[key] = obj
        prev = seen.get(key)
        if prev is None:
            seen[key] = {"status": status,
                         "first_seen": obj.get("first_seen", now),
                         "last_seen": now, "title": _title_of(obj),
                         "lat": obj.get("lat"), "lon": obj.get("lon"),
                         "rights": obj.get("rights", ""),
                         "attribution": obj.get("attribution", "")}
            if first_run or seed_only:
                continue
            out.append(_build(
                "eonet-opened", f"New event — {_title_of(obj)}",
                "DISASTER", obj.get("lat"), obj.get("lon"),
                obj.get("first_seen", now), now,
                {"status": "not previously listed"},
                {"status": status},
                {"area_m2": None, "detail": "area not stated by source"},
                "WATCH", "OBSERVED", key, links, [obj],
                [f"First listed by {(obj.get('source') or 'EONET')} at "
                 f"{obj.get('first_seen', now)}; not present in the "
                 f"previous baseline."],
                {"severity": 1, "freshness": 2, "corroboration": 0,
                 "rarity": 1, "scope": 1}, now, (status,)))
            continue
        prev_status = str(prev.get("status") or "open")
        prev["last_seen"] = now
        prev["title"] = _title_of(obj)
        if status != prev_status:
            prev["status"] = status
            out.append(_build(
                "eonet-transition",
                f"Event {status} — {_title_of(obj)}",
                "DISASTER", obj.get("lat"), obj.get("lon"),
                str(prev.get("first_seen", now)), now,
                {"status": prev_status}, {"status": status},
                {"area_m2": None, "detail": "area not stated by source"},
                "INFO" if status == "closed" else "WATCH", "OBSERVED",
                key, links, [obj],
                [f"Lifecycle state moved {prev_status} → {status} as "
                 f"stated by the source feed."],
                {"severity": 0, "freshness": 2, "corroboration": 0,
                 "rarity": 1, "scope": 0}, now, (prev_status, status)))
    # Sustained absence from the open-events feed: closure INFERRED.
    for key, prev in list(seen.items()):
        if key in current:
            continue
        if str(prev.get("status")) == "closed":
            continue
        last = _parse_time(prev.get("last_seen")) or _now_dt(now)
        absent_days = (_now_dt(now) - last).total_seconds() / 86400.0
        if absent_days < EONET_ABSENT_DAYS or seed_only:
            continue
        prev["status"] = "closed"
        lat = (prev.get("lat") if isinstance(prev.get("lat"), (int, float))
               else None)
        lon = (prev.get("lon") if isinstance(prev.get("lon"), (int, float))
               else None)
        pseudo = {"source": "nasa-eonet", "stable_key": key,
                  "source_event_time": prev.get("last_seen", "UNKNOWN"),
                  "source_url": "UNKNOWN", "rights": prev.get("rights", ""),
                  "attribution": prev.get("attribution", ""),
                  "truth_mode": "DELAYED", "observation_type": "INFERRED",
                  "fields": {"title": prev.get("title", key)}}
        out.append(_build(
            "eonet-closed", f"Event ended — {prev.get('title', key)}",
            "DISASTER", lat, lon,
            str(prev.get("first_seen", "UNKNOWN")),
            str(prev.get("last_seen", "UNKNOWN")),
            {"status": "open"}, {"status": "closed (inferred)"},
            {"area_m2": None, "detail": "area not stated by source"},
            "INFO", "INFERRED", key, links, [pseudo],
            [f"Absent from the open-events feed for "
             f"{absent_days:.0f} days (threshold {EONET_ABSENT_DAYS}). "
             f"The feed lists open events only, so closure is inferred, "
             f"not observed."],
            {"severity": 0, "freshness": 0, "corroboration": 0,
             "rarity": 0, "scope": 0}, now))
    return out


def detect_gdacs(objects: List[Dict[str, Any]],
                 links: List[Dict[str, Any]],
                 store: Dict[str, Any],
                 now: str,
                 seed_only: bool = False) -> List[Dict[str, Any]]:
    """GDACS new alerts and alert-level transitions. Only levels
    touching Orange/Red emit; Green-only churn is noise."""
    out: List[Dict[str, Any]] = []
    seen = store.setdefault("gdacs", {})
    first_run = not store.get("_seeded_gdacs", False)
    if objects:
        store["_seeded_gdacs"] = True
    for obj in objects or []:
        key = str(obj.get("stable_key") or "")
        if not key:
            continue
        level = _level_of(obj)
        rank = GDACS_RANK.get(level)
        if rank is None:
            continue
        prev = seen.get(key)
        entry = {"level": level, "last_seen": now,
                 "first_seen": prev.get("first_seen") if prev
                 else obj.get("first_seen", now),
                 "title": _title_of(obj),
                 "lat": obj.get("lat"), "lon": obj.get("lon"),
                 "rights": obj.get("rights", ""),
                 "attribution": obj.get("attribution", "")}
        if prev is None:
            seen[key] = entry
            if first_run or seed_only or level not in GDACS_WATCH_LEVELS:
                continue
            out.append(_build(
                "gdacs-new",
                f"New {level.title()} alert — {_title_of(obj)}",
                "DISASTER", obj.get("lat"), obj.get("lon"),
                obj.get("first_seen", now), now,
                {"alert_level": "not previously listed"},
                {"alert_level": level},
                {"area_m2": None, "detail": "area not stated by source"},
                "ALERT" if level == "red" else "WATCH", "OBSERVED",
                key, links, [obj],
                [f"First listed at alert level {level.title()} by GDACS."],
                {"severity": 2 if level == "red" else 1, "freshness": 2,
                 "corroboration": 0, "rarity": 1, "scope": 1}, now,
                (level,)))
            continue
        prev_level = str(prev.get("level") or "green")
        prev_rank = GDACS_RANK.get(prev_level, 0)
        seen[key] = entry
        if rank == prev_rank:
            continue
        watched = (level in GDACS_WATCH_LEVELS
                   or prev_level in GDACS_WATCH_LEVELS)
        if not watched:
            continue
        direction = ("escalated" if rank > prev_rank else "de-escalated")
        out.append(_build(
            "gdacs-transition",
            f"Alert {direction} {prev_level.title()} → {level.title()} — "
            f"{_title_of(obj)}",
            "DISASTER", obj.get("lat"), obj.get("lon"),
            str(prev.get("first_seen", obj.get("first_seen", now))), now,
            {"alert_level": prev_level}, {"alert_level": level},
            {"area_m2": None, "detail": "area not stated by source"},
            "ALERT" if level == "red" else ("WATCH" if rank > prev_rank
                                            else "INFO"),
            "OBSERVED", key, links, [obj],
            [f"GDACS alert level moved {prev_level.title()} → "
             f"{level.title()} as stated by the source feed."],
            {"severity": 2 if level == "red" else 1, "freshness": 2,
             "corroboration": 0, "rarity": 1, "scope": 1}, now,
            (prev_level, level)))
    return out


def usgs_daily_counts(objects: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:  # noqa: E501
    """Aggregate M5+ counts per UTC day from one feed snapshot (the
    configured USGS leg returns 7 days, so no stored history is
    needed for the baseline window itself)."""
    days: Dict[str, Dict[str, Any]] = {}
    for obj in objects or []:
        mag = _mag_of(obj)
        if mag is None or mag < USGS_SIGNIFICANT_MAG:
            continue
        dt = _parse_time(obj.get("source_event_time"))
        if dt is None:
            continue
        day = _day_key(dt)
        row = days.setdefault(day, {"n": 0, "max_mag": 0.0,
                                    "strongest": "", "keys": []})
        row["n"] += 1
        if mag > float(row["max_mag"]):
            row["max_mag"] = mag
            row["strongest"] = _title_of(obj)
        row["keys"].append(str(obj.get("stable_key") or ""))
    return days


def detect_usgs(objects: List[Dict[str, Any]],
                links: List[Dict[str, Any]],
                store: Dict[str, Any],
                now: str,
                seed_only: bool = False) -> List[Dict[str, Any]]:
    """Significant seismic episode versus the rolling 7-day baseline.

    Episode iff today's M5+ count >= max(USGS_EPISODE_MIN,
    USGS_EPISODE_FACTOR * prior-7-day daily mean). The absolute floor
    stops a lone mainshock plus aftershocks tripping the detector on
    quiet weeks; the factor stops background-rate weeks tripping it.
    One change per UTC day maximum (stable day-scoped ID).
    """
    out: List[Dict[str, Any]] = []
    days = usgs_daily_counts(objects)
    stored = store.setdefault("usgs_daily", {})
    for day, row in days.items():
        prev = stored.get(day) or {}
        merged_keys = sorted(set(prev.get("keys", [])) | set(row["keys"]))
        stored[day] = {"n": max(int(prev.get("n", 0)), int(row["n"])),
                       "max_mag": max(float(prev.get("max_mag", 0.0)),
                                      float(row["max_mag"])),
                       "strongest": row["strongest"] or prev.get("strongest", ""),  # noqa: E501
                       "keys": merged_keys}
    today = _now_dt(now)
    today_key = _day_key(today)
    prior = [stored.get(_day_key(today - timedelta(days=d)), {})
             for d in range(1, BASELINE_WINDOW_DAYS + 1)]
    have = [int(p.get("n", 0)) for p in prior if p]
    mean = (sum(have) / len(have)) if have else 0.0
    today_n = int(stored.get(today_key, {}).get("n", 0))
    threshold = max(USGS_EPISODE_MIN, USGS_EPISODE_FACTOR * mean)
    if seed_only or today_n < threshold:
        return out
    contributors = [k for k in stored.get(today_key, {}).get("keys", [])]
    pseudo_evidence = {"source": "usgs-earthquakes",
                       "stable_key": f"aggregate:{today_key}",
                       "title": f"{today_n} M5+ quakes on {today_key}",
                       "source_event_time": now, "source_url": "UNKNOWN",
                       "rights": "US public domain",
                       "attribution": "USGS Earthquake Hazards Program "
                                      "(courtesy of the U.S. Geological "
                                      "Survey)",
                       "truth_mode": "DELAYED",
                       "observation_type": "INFERRED",
                       "fields": {"title": f"{today_n} M5+ quakes"}}
    strongest = stored.get(today_key, {}).get("strongest", "")
    max_mag = stored.get(today_key, {}).get("max_mag", 0.0)
    out.append(_build(
        "usgs-episode",
        f"Seismic episode — {today_n} M5+ quakes in 24 h "
        f"(strongest M{max_mag})",
        "SEISMIC", None, None, today_key + "T00:00:00+00:00", now,
        {"m5_per_day_7d_mean": round(mean, 2),
         "window_days": BASELINE_WINDOW_DAYS},
        {"m5_last_24h": today_n, "max_mag": max_mag,
         "strongest": strongest},
        {"area_m2": None,
         "detail": "epicentres vary; no single area stated"},
        "ALERT", "INFERRED", f"aggregate:{today_key}", links,
        [pseudo_evidence] + [
            {"source": "usgs-earthquakes", "stable_key": k,
             "title": k, "source_event_time": now,
             "source_url": "UNKNOWN", "rights": "US public domain",
             "attribution": pseudo_evidence["attribution"],
             "truth_mode": "DELAYED", "observation_type": "OBSERVED",
             "fields": {}} for k in contributors[:5]],
        [f"{today_n} M5+ quakes in the last 24 h versus a 7-day mean "
         f"of {mean:.1f}/day (threshold: at least {USGS_EPISODE_MIN} "
         f"and at least {USGS_EPISODE_FACTOR:g}x the mean). "
         f"Strongest: {strongest or 'not stated'} (M{max_mag})."],
        {"severity": 2, "freshness": 2, "corroboration": 0,
         "rarity": 2, "scope": 2}, now))
    return out


def detect(objects_by_source: Dict[str, List[Dict[str, Any]]],
           links: Optional[List[Dict[str, Any]]] = None,
           now: Optional[str] = None,
           seed_only: bool = False) -> Tuple[List[Dict[str, Any]],
                                             List[Dict[str, Any]]]:
    """Run all V1 detectors. Returns (new_changes, updated_changes).

    New transitions are recorded in the emitted store under stable
    IDs; reprocessing identical observations yields nothing new
    (idempotent). A recomputed transition whose content changed bumps
    the stored version under the same ID (honest correction).
    """
    now = now or utcnow()
    store = load_store()
    links = links or []
    groups = objects_by_source or {}
    fresh: List[Dict[str, Any]] = []
    fresh += detect_eonet(groups.get("nasa-eonet", []), links, store, now,
                          seed_only)
    fresh += detect_gdacs(groups.get("gdacs-alerts", []), links, store, now,
                          seed_only)
    fresh += detect_usgs(groups.get("usgs-earthquakes", []), links, store,
                         now, seed_only)
    emitted = store.setdefault("emitted", {})
    new_out: List[Dict[str, Any]] = []
    updated_out: List[Dict[str, Any]] = []
    for change in fresh:
        cid = change["id"]
        prev = emitted.get(cid)
        if prev is None:
            emitted[cid] = {"emitted_at": now, "version": 1,
                            "change": change}
            new_out.append(change)
        elif json.dumps(prev.get("change"), sort_keys=True) != json.dumps(
                change, sort_keys=True):
            emitted[cid] = {"emitted_at": prev.get("emitted_at", now),
                            "version": int(prev.get("version", 1)) + 1,
                            "change": change}
            updated_out.append(change)
    # Late corroboration is an honest correction, never a duplicate:
    # upgrade stored "new"-type records when independent legs arrive
    # after emission. Upgrades only — corroboration never downgrades
    # just because the current link window moved on.
    for cid, rec in emitted.items():
        stored_change = (rec or {}).get("change") or {}
        if stored_change.get("type") not in CHANGE_TYPES:
            continue
        if stored_change.get("corroboration") == "CORROBORATED":
            continue
        ev0 = (stored_change.get("evidence") or [{}])[0]
        primary = str(ev0.get("stable_key") or "")
        if not primary:
            continue
        corroboration, source_count, partners = _corroboration(primary,
                                                               links)
        if corroboration != "CORROBORATED":
            continue
        upgraded = dict(stored_change)
        upgraded["corroboration"] = corroboration
        upgraded["source_count"] = source_count
        upgraded["corroborating_keys"] = partners
        upgraded["confidence"] = _confidence(corroboration)
        axes = dict((upgraded.get("rank") or {}).get("axes", {}))
        axes["corroboration"] = 2
        label, score = _rank_score(axes)
        upgraded["rank"] = {"label": label, "score": score, "axes": axes}
        assert_schema_clean(upgraded)
        emitted[cid] = {"emitted_at": rec.get("emitted_at", now),
                        "version": int(rec.get("version", 1)) + 1,
                        "change": upgraded}
        updated_out.append(upgraded)
    prune_store(store, now)
    store["_polls"] = int(store.get("_polls", 0)) + 1
    save_store(store)
    return new_out, updated_out


def stored_changes(since: Optional[str] = None,
                   limit: int = 100) -> List[Dict[str, Any]]:
    """Recent emitted changes, newest first, filtered by `since`
    (ISO time or generation cursor). The store is retention-bounded:
    this is a recent-change feed, not an archive."""
    store = load_store()
    rows = []
    for cid, rec in store.get("emitted", {}).items():
        change = (rec or {}).get("change")
        if not isinstance(change, dict):
            continue
        rows.append(change)
    if since:
        cursor = _parse_time(since)
        if cursor is not None:
            rows = [c for c in rows
                    if (_parse_time(c.get("last_observed")) or _now_dt())
                    > cursor]
    rows.sort(key=lambda c: str(c.get("last_observed", "")), reverse=True)
    return rows[:max(1, min(500, limit))]


def get_changes(refresh: bool = False, force: bool = False,
                since: Optional[str] = None,
                limit: int = 100) -> Dict[str, Any]:
    """Build the /api/world/changes payload from the NOW snapshot."""
    from gods_eye.future import world_now as now_mod
    payload = now_mod.get_now(refresh=refresh, force=force)
    groups = payload.get("objects", {})
    now = utcnow()
    detect(groups, payload.get("links", []), now)
    changes = stored_changes(since, limit)
    involved = sorted({e.get("source", "") for c in changes
                       for e in c.get("evidence", []) if e.get("source")})
    health = [h for h in payload.get("health", [])
              if h.get("source_id") in involved]
    return {
        "mode": "changes",
        "generated_at": now,
        "live": False,
        "real_data": True,
        "truth_label": TRUTH_LABEL,
        "changes": changes,
        "cursor": now,
        "counts": {"changes": len(changes)},
        "sources": {h.get("source_id"): h.get("state") for h in health},
        "retention_days": BASELINE_RETENTION_DAYS,
    }
