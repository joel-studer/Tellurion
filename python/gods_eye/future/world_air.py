"""FUTURE-ONLY live aviation leg for WORLD NOW (backend fetch, localhost only).

Primary source: adsb.lol v2 API (ODbL 1.0, keyless; see
docs/public/LIVE_AVIATION_SOURCE_DECISION.md). The browser never talks
to the provider; the Tellurion backend polls, caches, deduplicates,
normalizes to canonical observations and serves snapshots.

HARD BOUNDARIES (binding on this module and all its callers):
- No person/VIP/owner tracking, no watchlists, no deanonymization,
  no covert individual tracking, no tactical military targeting,
  no mission inference, no strike relevance.
- Filtering uses PUBLIC FLIGHT STATE + PUBLIC OPERATIONAL SIGNALS +
  PUBLIC WEATHER/AIRPORT CONTEXT only.
- No owner/passenger identity enrichment exists anywhere here: the
  provider does not supply it and this module must never add it.
- Certainty language is forbidden: POSSIBLE / LIKELY / OBSERVED SIGNAL
  only — never CONFIRMED INCIDENT unless a source explicitly confirms.
- Emergency squawks are reported as EMERGENCY SQUAWK OBSERVED, never
  as crash/hijack claims.

Ingest strategy (source-compliant, polite):
- 8 regional point tiles (250 nm), staggered, each refreshed at most
  every 120 s  -> ~1 request / 15 s average.
- Squawk legs (7700/7600/7500, tiny responses) at most every 60 s.
- Military leg (/v2/mil) at most every 120 s, display-only layer.
- Dynamic provider limits respected: any 4xx/429 backs off with the
  same honest health vocabulary as world_now (RATE_LIMITED + backoff).
- History is memory-only (rolling ~15 min, capped) and never written
  to disk: transient operational cache, minimal retention by design.
"""

from __future__ import annotations

import json
import re
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

SOURCE_ID = "adsb-lol-live"
ATTRIBUTION = "adsb.lol contributors (ODbL)"
RIGHTS = "ODbL 1.0 (display + transient cache; attribution mandatory)"
PROVENANCE = "adsb.lol v2 API (community receivers)"
TRUTH_MODE = "DELAYED"
NORMALIZER = "world-air-v1"

BASE = "https://api.adsb.lol/v2"
TILE_TTL_S = 120
SQUAWK_TTL_S = 60
MIL_TTL_S = 120
MAX_BYTES = 4_000_000
# Round-robin budget: at most this many provider fetches per refresh call,
# squawk legs first (tiny + emergency value), then oldest-due tiles.
# Spreads provider load over successive calls instead of bursting.
MAX_FETCH_PER_CALL = 4
FETCH_GAP_S = 4.0  # politeness gap between real fetches in one call
FETCH_JITTER = 0.3  # +/- fraction of jitter on the gap
COOLDOWN_429_S = 300.0  # per-leg cooldown after a 429 unless forced

# Regional tiles: honest PARTIAL global coverage (dense corridors only;
# oceans, Africa, polar regions have no tile by design — see coverage()).
TILES: List[Dict[str, Any]] = [
    {"id": "eu-central", "lat": 50.0, "lon": 10.0, "dist_nm": 250,
     "weight": 3},
    {"id": "us-northeast", "lat": 40.0, "lon": -75.0, "dist_nm": 250,
     "weight": 3},
    {"id": "us-southwest", "lat": 35.0, "lon": -115.0, "dist_nm": 250,
     "weight": 2},
    {"id": "se-asia", "lat": 15.0, "lon": 102.0, "dist_nm": 250,
     "weight": 2},
    {"id": "east-asia", "lat": 35.0, "lon": 138.0, "dist_nm": 250,
     "weight": 2},
    {"id": "south-asia", "lat": 22.0, "lon": 79.0, "dist_nm": 250,
     "weight": 2},
    {"id": "mideast", "lat": 25.0, "lon": 50.0, "dist_nm": 250,
     "weight": 1},
    {"id": "south-america", "lat": -23.0, "lon": -46.0, "dist_nm": 250,
     "weight": 1},
    {"id": "oceania", "lat": -33.9, "lon": 151.2, "dist_nm": 250,
     "weight": 1, "ttl": 300},
    # Probed 2026-09-16 and deliberately NOT polled (verified empty):
    # africa-west lat/6.5/lon/3.4/dist/250 -> 0 aircraft (no receiver
    # coverage); central-asia lat/41.5/lon/64/dist/250 -> 0 aircraft.
    # Polling empty tiles would spend provider budget for zero value.
]

SQUAWK_URLS = {
    "7700": f"{BASE}/squawk/7700",
    "7600": f"{BASE}/squawk/7600",
    "7500": f"{BASE}/squawk/7500",
}
MIL_URL = f"{BASE}/mil"

EMERGENCY_SQUAWKS = {
    "7700": "general emergency",
    "7600": "radio communication failure",
    "7500": "unlawful interference code",
}

_HEX_RE = re.compile(r"^[0-9a-f]{6}$")

# --- IMPORTANT NOW thresholds (documented, own-history relative) ---
STALE_AGE_S = 180          # position older than this -> POSITION STALE
HOLD_MIN_PTS = 8           # minimum track points for a holding verdict
HOLD_MIN_SPAN_S = 180      # minimum track duration for holding
HOLD_MAX_DIAM_KM = 60.0    # bounding diameter for a racetrack verdict
HOLD_MIN_TURN_DEG = 540.0  # cumulative heading change for looping verdict
DESC_FPM = -3000.0         # sustained vertical rate -> OBSERVED RAPID DESCENT
CLIMB_FPM = 3000.0         # sustained climb, only flagged high (see below)
DESC_FPM_LOW = -2000.0     # below 10 000 ft the descent band is tighter
CLIMB_MIN_ALT_FT = 15000.0  # climbs below this are routine departures:
                           # flag climbs only above it (or >= 6000 fpm
                           # anywhere, which is genuinely unusual)
CLIMB_FPM_EXTREME = 6000.0
ALT_DROP_FT_60S = 2000.0   # alt loss within 60 s from own history
GOAROUND_ALT_FT = 2500     # descend below this near an airport ...
GOAROUND_CLIMB_FT = 1500   # ... then climb this much ...
GOAROUND_DIST_KM = 25.0    # ... while staying this close -> POSSIBLE GO-AROUND
WX_DIST_KM = 50.0          # aircraft within this of a severe alert centroid
HOLD_GROUP_KM = 60.0       # holdings grouped per airport within this
HOLD_GROUP_MIN = 2         # >= this many holdings -> airport-level event

MAX_AIRCRAFT = 20000
TRACK_MAXLEN = 40
TRACK_KEEP_S = 900
SNAPSHOT_CAP = 5000        # LOD: never serve more than this many markers

# Fields that must NEVER appear on a canonical aircraft observation.
FORBIDDEN_FIELDS = frozenset({
    "owner", "operator", "passenger", "passengers", "vip", "person",
    "persons", "crew", "name", "address", "phone", "mission", "target",
    "watchlist", "profile",
})


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _finite(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f and abs(f) != float("inf") else None


def _valid_coords(lat: Any, lon: Any) -> bool:
    la, lo = _finite(lat), _finite(lon)
    if la is None or lo is None:
        return False
    return -90.0 <= la <= 90.0 and -180.0 <= lo <= 180.0


def _haversine_km(lat1: float, lon1: float,
                  lat2: float, lon2: float) -> float:
    import math
    r = 6371.0
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * \
        math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# --------------------------------------------------------------------------
# Pure adapter: adsb.lol v2 point/squawk/mil payload -> canonical observations
# --------------------------------------------------------------------------

def parse_adsblol(text: str, limit: int = 5000,
                  tile: str = "UNKNOWN") -> Tuple[List[Dict[str, Any]], int]:
    """Map one adsb.lol v2 response to canonical aircraft observations.

    Returns (positioned, non_positioned_count). Contacts without a valid
    position are counted but never rendered. Raises on malformed input
    (fail closed); never fabricates fields the provider did not supply.
    """
    if len(text.encode("utf-8", "ignore")) > MAX_BYTES:
        raise ValueError("payload exceeds 4 MB cap (refused)")
    try:
        data = json.loads(text)
    except Exception as e:
        raise ValueError(f"adsb.lol payload is not JSON: {e}") from e
    ac = data.get("ac")
    if ac is None:
        raise ValueError("adsb.lol payload missing 'ac'")
    if not isinstance(ac, list):
        raise ValueError("adsb.lol 'ac' is not a list")
    now_ms = data.get("now") or data.get("ctime") or 0
    try:
        now_s = float(now_ms) / 1000.0 if float(now_ms) > 10_000_000_000 \
            else float(now_ms)
    except (TypeError, ValueError):
        now_s = time.time()
    out: List[Dict[str, Any]] = []
    skipped = 0
    for row in ac[:max(1, min(20000, limit))]:
        if not isinstance(row, dict):
            skipped += 1
            continue
        obs = _normalize_one(row, tile, now_s)
        if obs is None:
            skipped += 1
        else:
            out.append(obs)
    return out, skipped


def _normalize_one(row: Dict[str, Any], tile: str,
                   now_s: float) -> Optional[Dict[str, Any]]:
    hex_id = str(row.get("hex") or "").strip().lower()
    if not _HEX_RE.match(hex_id):
        return None
    lat, lon = _finite(row.get("lat")), _finite(row.get("lon"))
    if lat is None or lon is None or not _valid_coords(lat, lon):
        return None
    on_ground = str(row.get("alt_baro") or "").strip().lower() == "ground"
    baro = None if on_ground else _finite(row.get("alt_baro"))
    geom = _finite(row.get("alt_geom"))
    gs = _finite(row.get("gs"))
    vr = _finite(row.get("baro_rate"))
    if vr is None:
        vr = _finite(row.get("geom_rate"))
    mlat = row.get("type") == "mlat" or bool(row.get("mlat"))
    tisb = bool(row.get("tisb"))
    signal = "MLAT" if mlat else ("TIS-B" if tisb else "ADS-B")
    seen_pos = _finite(row.get("seen_pos"))
    seen = _finite(row.get("seen"))
    age = seen_pos if seen_pos is not None else seen
    try:
        age_s = max(0.0, float(age)) if age is not None else None
    except (TypeError, ValueError):
        age_s = None
    obs: Dict[str, Any] = {
        "icao24": hex_id,
        "callsign": str(row.get("flight") or "").strip() or "UNKNOWN",
        # Registration as publicly broadcast by the provider; display is
        # permitted (open data), but it is NEVER enriched with owner data.
        "registration": str(row.get("r") or "").strip() or "UNKNOWN",
        "type": str(row.get("t") or "").strip() or "UNKNOWN",
        "lat": lat, "lon": lon,
        "baro_alt_ft": baro, "geo_alt_ft": geom,
        "gs_kt": gs, "vrate_fpm": vr,
        "track_deg": _finite(row.get("track")),
        "squawk": str(row.get("squawk") or "").strip() or "UNKNOWN",
        "on_ground": bool(on_ground),
        "signal": signal,
        "position_age_s": age_s,
        "fetched_at": utcnow(),
        "alert": bool(row.get("alert")),
        "spi": bool(row.get("spi")),
        "source": SOURCE_ID,
        "attribution": ATTRIBUTION,
        "rights": RIGHTS,
        "provenance": PROVENANCE,
        "observation_type": "OBSERVED",
        "truth_mode": TRUTH_MODE,
        "tile": tile,
    }
    if FORBIDDEN_FIELDS & set(obs):
        raise ValueError("forbidden field on canonical observation")
    return obs


# --------------------------------------------------------------------------
# Dedup: canonical aircraft by icao24 across tiles/legs
# --------------------------------------------------------------------------

def dedup_states(groups: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Reconcile overlapping tile/leg observations into canonical aircraft.

    One icao24 -> one aircraft. Best position = smallest position_age.
    Contributing tiles are preserved as provenance; nothing is averaged
    into a fake position.
    """
    best: Dict[str, Dict[str, Any]] = {}
    tiles: Dict[str, List[str]] = {}
    for grp in groups:
        for o in grp:
            hx = o.get("icao24", "")
            tiles.setdefault(hx, [])
            if o.get("tile") and o["tile"] not in tiles[hx]:
                tiles[hx].append(o["tile"])
            cur = best.get(hx)
            if cur is None:
                best[hx] = o
                continue
            ao = o.get("position_age_s")
            bo = cur.get("position_age_s")
            ao = float("inf") if ao is None else ao
            bo = float("inf") if bo is None else bo
            if ao < bo:
                best[hx] = o
    out = []
    for hx, o in best.items():
        o = dict(o)
        o["tiles"] = tiles.get(hx, [])
        out.append(o)
    return out


# --------------------------------------------------------------------------
# Rolling history (memory only, capped, pruned — never persisted)
# --------------------------------------------------------------------------

_lock = threading.Lock()
_tracks: Dict[str, deque] = {}
_memory: Dict[str, Any] = {}
_health: Dict[str, Any] = {}


def update_tracks(states: List[Dict[str, Any]],
                  now_ts: Optional[float] = None) -> int:
    """Append current positions to rolling per-aircraft history."""
    now_ts = now_ts if now_ts is not None else time.time()
    with _lock:
        for o in states[:MAX_AIRCRAFT]:
            dq = _tracks.get(o["icao24"])
            if dq is None:
                dq = deque(maxlen=TRACK_MAXLEN)
                _tracks[o["icao24"]] = dq
            dq.append((now_ts, o["lat"], o["lon"],
                       o.get("baro_alt_ft"), o.get("track_deg")))
        # Prune expired + enforce aircraft cap (drop stalest first).
        cutoff = now_ts - TRACK_KEEP_S
        dead = [k for k, dq in _tracks.items()
                if not dq or dq[-1][0] < cutoff]
        for k in dead:
            del _tracks[k]
        if len(_tracks) > MAX_AIRCRAFT:
            ordered = sorted(_tracks.items(), key=lambda kv: kv[1][-1][0])
            for k, _ in ordered[:len(_tracks) - MAX_AIRCRAFT]:
                del _tracks[k]
        return len(_tracks)


def get_trail(icao24: str, limit: int = 40) -> List[Dict[str, Any]]:
    hx = (icao24 or "").strip().lower()
    with _lock:
        dq = _tracks.get(hx)
        pts = list(dq)[-max(1, min(100, limit)):] if dq else []
    return [{"t": datetime.fromtimestamp(p[0], tz=timezone.utc).isoformat(
        timespec="seconds"), "lat": p[1], "lon": p[2],
        "baro_alt_ft": p[3], "track_deg": p[4],
        "truth": "RECORDED"} for p in pts]


def track_count() -> int:
    with _lock:
        return len(_tracks)


# --------------------------------------------------------------------------
# IMPORTANT NOW engine (transparent rules, no certainty claims)
# --------------------------------------------------------------------------

def _turn_deg(a: Optional[float], b: Optional[float]) -> float:
    if a is None or b is None:
        return 0.0
    d = (b - a + 540.0) % 360.0 - 180.0
    return d


def holding_evidence(history: List[Tuple]) -> Optional[Dict[str, Any]]:
    """Racetrack verdict: heading reversals + bounded region + duration."""
    if len(history) < HOLD_MIN_PTS:
        return None
    dur = history[-1][0] - history[0][0]
    if dur < HOLD_MIN_SPAN_S:
        return None
    lats = [p[1] for p in history]
    lons = [p[2] for p in history]
    diam = _haversine_km(min(lats), min(lons), max(lats), max(lons))
    if diam > HOLD_MAX_DIAM_KM:
        return None
    turns = [_turn_deg(history[i][4], history[i + 1][4])
             for i in range(len(history) - 1)]
    total = sum(abs(t) for t in turns)
    reversals = sum(1 for i in range(len(turns) - 1)
                    if turns[i] * turns[i + 1] < 0
                    and abs(turns[i]) > 10 and abs(turns[i + 1]) > 10)
    # A steady orbit turns one way (no reversals); S-turns reverse.
    # Either pattern counts when bounded + long enough: a straight
    # flight cannot accumulate 540 deg of heading change from noise
    # (typical jitter sums far below this over 8+ points).
    if total < HOLD_MIN_TURN_DEG:
        return None
    return {"reversals": reversals,
            "total_turn_deg": round(total, 1),
            "span_km": round(diam, 1),
            "duration_s": int(dur)}


def goaround_evidence(history: List[Tuple],
                      airport: Optional[Dict[str, Any]]) -> Optional[Dict]:
    """Descend low near an airport, then climb while staying near it."""
    if airport is None or len(history) < 6:
        return None
    alts = [(p[0], p[3]) for p in history if p[3] is not None]
    if len(alts) < 6:
        return None
    low = min(a[1] for a in alts[-8:])
    end_alt = alts[-1][1]
    if low > GOAROUND_ALT_FT or (end_alt - low) < GOAROUND_CLIMB_FT:
        return None
    for p in history[-6:]:
        if _haversine_km(p[1], p[2], airport["lat"],
                         airport["lon"]) > GOAROUND_DIST_KM:
            return None
    return {"low_ft": round(low), "climbed_ft": round(end_alt - low),
            "airport": airport.get("id", "UNKNOWN")}


def descent_evidence(obs: Dict[str, Any],
                     history: List[Tuple]) -> Optional[Dict[str, Any]]:
    """Rapid vertical motion from own history + current vertical rate."""
    vr = obs.get("vrate_fpm")
    alt = obs.get("baro_alt_ft")
    band_low = alt is not None and alt < 10000
    d_lim = DESC_FPM_LOW if band_low else DESC_FPM
    if vr is not None:
        if vr <= d_lim:
            return {"kind": "descent", "vrate_fpm": vr,
                    "basis": "sustained vertical rate"}
        # Departure climbs are routine: only flag climbs that are high
        # (past departure phase) or extreme anywhere.
        if vr >= CLIMB_FPM_EXTREME or (
                vr >= CLIMB_FPM and alt is not None
                and alt >= CLIMB_MIN_ALT_FT):
            return {"kind": "climb", "vrate_fpm": vr,
                    "basis": "sustained vertical rate above departure "
                             "phase" if alt is not None and
                    alt >= CLIMB_MIN_ALT_FT else "extreme vertical rate"}
    alts = [(p[0], p[3]) for p in history if p[3] is not None]
    if len(alts) >= 2:
        t0, a0 = alts[0], alts[-1][0] - 60.0
        recent = [a for t, a in alts if t >= a0]
        if len(recent) >= 2 and recent[-1] - recent[0] <= -ALT_DROP_FT_60S:
            return {"kind": "descent",
                    "drop_ft": round(recent[0] - recent[-1]),
                    "basis": "own 60 s history"}
    return None


def nearest_airport(lat: float, lon: float,
                    max_km: float = 60.0) -> Optional[Dict[str, Any]]:
    try:
        from gods_eye.future import world_demo as _w
    except Exception:
        return None
    best, bd = None, max_km
    for a in _w.AIRPORTS:
        d = _haversine_km(lat, lon, a["lat"], a["lon"])
        if d < bd:
            best, bd = a, d
    return best


def flag_aircraft(obs: Dict[str, Any], history: List[Tuple],
                  ctx: Optional[Dict[str, Any]] = None
                  ) -> List[Dict[str, Any]]:
    """Transparent interest flags for one aircraft (no certainty claims)."""
    ctx = ctx or {}
    flags: List[Dict[str, Any]] = []
    sq = str(obs.get("squawk") or "")
    if sq in EMERGENCY_SQUAWKS:
        flags.append({
            "rule_id": "EMERGENCY_SQUAWK",
            "label": "EMERGENCY SQUAWK OBSERVED",
            "level": "OBSERVED SIGNAL",
            "interest": "HIGH",
            "evidence": {"squawk": sq, "meaning": EMERGENCY_SQUAWKS[sq]},
            "why": f"transponder squawk {sq} ({EMERGENCY_SQUAWKS[sq]}) "
                   f"is publicly broadcasting; this states the observed "
                   f"signal only, not the situation on board"})
    elif obs.get("alert") or obs.get("spi"):
        flags.append({
            "rule_id": "TRANSPONDER_FLAG",
            "label": "TRANSPONDER FLAG OBSERVED",
            "level": "OBSERVED SIGNAL",
            "interest": "MEDIUM",
            "evidence": {"alert": bool(obs.get("alert")),
                         "spi": bool(obs.get("spi"))},
            "why": "provider squawk-change/IDENT bit is set; routine on "
                   "ATC handoffs, kept at MEDIUM — not an emergency, "
                   "only 7500/7600/7700 are HIGH"})
    d = descent_evidence(obs, history)
    if d:
        flags.append({
            "rule_id": "RAPID_" + d["kind"].upper(),
            "label": "OBSERVED RAPID " + d["kind"].upper(),
            "level": "OBSERVED SIGNAL",
            "interest": "MEDIUM",
            "evidence": d,
            "why": "vertical motion vs the aircraft's own recent history; "
                   "no cause is claimed"})
    h = holding_evidence(history)
    ap = nearest_airport(obs["lat"], obs["lon"]) \
        if len(history) >= 6 else None
    if h and not obs.get("on_ground"):
        flags.append({
            "rule_id": "POSSIBLE_HOLDING",
            "label": "POSSIBLE HOLDING PATTERN",
            "level": "POSSIBLE",
            "interest": "MEDIUM",
            "evidence": h,
            "why": "looping track in a bounded region; not a confirmed "
                   "ATC hold"})
    if ap:
        g = goaround_evidence(history, ap)
        if g:
            flags.append({
                "rule_id": "POSSIBLE_GOAROUND",
                "label": "POSSIBLE GO-AROUND",
                "level": "POSSIBLE",
                "interest": "MEDIUM",
                "evidence": g,
                "why": "low approach near " + str(ap.get("id")) +
                       " followed by climb; cause is not inferred"})
    for wp in ctx.get("nws_points", []) or []:
        try:
            dist = _haversine_km(obs["lat"], obs["lon"],
                                 wp["lat"], wp["lon"])
        except (KeyError, TypeError):
            continue
        if dist <= WX_DIST_KM and str(wp.get("severity", "")).lower() in (
                "extreme", "severe"):
            flags.append({
                "rule_id": "NEAR_SEVERE_WX",
                "label": "AIRCRAFT NEAR SEVERE WEATHER",
                "level": "OBSERVED SIGNAL",
                "interest": "MEDIUM",
                "evidence": {"distance_km": round(dist, 1),
                             "alert": str(wp.get("headline", ""))[:120]},
                "why": "position vs public NWS alert centroid; proximity "
                       "only, not danger"})
            break
    age = obs.get("position_age_s")
    try:
        stale = age is not None and float(age) > STALE_AGE_S
    except (TypeError, ValueError):
        stale = False
    if stale and not flags:
        flags.append({
            "rule_id": "POSITION_STALE",
            "label": "POSITION STALE",
            "level": "OBSERVED SIGNAL",
            "interest": "LOW",
            "evidence": {"position_age_s": age},
            "why": "no fresh position; disappearance is never treated "
                   "as an incident"})
    return flags


def interest_of(flags: List[Dict[str, Any]]) -> Tuple[str, List[str]]:
    """Transparent composition: HIGH/MEDIUM/LOW + human reasons."""
    if any(f.get("interest") == "HIGH" for f in flags):
        level = "HIGH"
    elif any(f.get("interest") == "MEDIUM" for f in flags):
        level = "MEDIUM"
    elif flags:
        level = "LOW"
    else:
        return "LOW", []
    return level, [f["label"] + " — " + f["why"] for f in flags
                   if f.get("interest") == level or level == "LOW"]


def airport_events(flagged: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Airport-level disruption context (more useful than individuals)."""
    by_apt: Dict[str, Dict[str, Any]] = {}
    for f in flagged:
        if f.get("rule_id") != "POSSIBLE_HOLDING":
            continue
        ap = nearest_airport(f["lat"], f["lon"], HOLD_GROUP_KM)
        if not ap:
            continue
        b = by_apt.setdefault(ap["id"], {"airport": ap, "members": []})
        b["members"].append(f["icao24"])
    out = []
    for aid, b in by_apt.items():
        if len(b["members"]) >= HOLD_GROUP_MIN:
            out.append({
                "rule_id": "AIRPORT_HOLDING",
                "label": f"MULTIPLE AIRCRAFT HOLDING NEAR {aid}",
                "level": "LIKELY" if len(b["members"]) >= 3 else "POSSIBLE",
                "interest": "MEDIUM",
                "evidence": {"airport": aid, "n": len(b["members"]),
                             "members": b["members"][:12]},
                "why": f"{len(b['members'])} aircraft show possible "
                       f"holding within {HOLD_GROUP_KM:g} km of {aid}; "
                       f"airport disruption context, not per-aircraft "
                       f"claims"})
    return out


# --------------------------------------------------------------------------
# Backend ingest (backend only; responses are untrusted input)
# --------------------------------------------------------------------------

def _tile_url(t: Dict[str, Any]) -> str:
    return (f"{BASE}/lat/{t['lat']}/lon/{t['lon']}/dist/{t['dist_nm']}")


def nws_points_from_now(limit: int = 300) -> List[Dict[str, Any]]:
    """Public NWS alert centroids with geometry (US only) for WX context."""
    try:
        from gods_eye.future import world_now as _now
        mem = _now._memory.get("nws-alerts", {})
        pts = []
        for o in (mem.get("items") or [])[:limit]:
            if o.get("lat") is None:
                continue
            f = o.get("fields") or {}
            pts.append({"lat": o["lat"], "lon": o["lon"],
                        "severity": f.get("severity", ""),
                        "headline": f.get("headline", "")})
        return pts
    except Exception:
        return []


def refresh_aviation(force: bool = False,
                     opener: Optional[Callable] = None,
                     include_mil: bool = False,
                     max_legs: int = MAX_FETCH_PER_CALL,
                     viewport: Optional[Dict[str, float]] = None
                     ) -> Dict[str, Any]:
    """Poll due legs (tiles/squawk/mil), normalize, dedup, flag, cache.

    Memory-only: positions + short history never touch disk. At most
    max_legs real fetches per call with a jittered politeness gap;
    scheduling is a priority queue over staleness x traffic weight x
    provider cooldown, with an optional viewport boost (visible tiles
    first). Deferred due legs keep serving cached rows (their growing
    position_age self-labels them STALE through the normal rules).
    """
    from gods_eye.future import world_now as _now
    now_s = utcnow()
    tile_rows: List[List[Dict[str, Any]]] = []
    positioned = 0
    skipped = 0
    errors: List[str] = []
    with _lock:
        tile_state = _memory.setdefault("tiles", {})
        sq_state = _memory.setdefault("squawk", {})
        mil_state = _memory.setdefault("mil", {"at": 0.0, "n": 0})
    legs = [("squawk:" + k, u, SQUAWK_TTL_S, sq_state, "squawk-" + k,
             10)
            for k, u in SQUAWK_URLS.items()]
    legs += [("tile:" + t["id"], _tile_url(t), t.get("ttl", TILE_TTL_S),
              tile_state, t["id"], t.get("weight", 1)) for t in TILES]
    # Priority queue: squawk legs first (tiny + emergency value), then
    # due tiles by staleness x traffic weight x viewport boost.
    # Legs inside a 429 cooldown are skipped unless forced.
    due = []
    for leg in legs:
        _name, url, ttl, store, _tag, weight = leg
        with _lock:
            rec = store.get(url, {})
            at = float(rec.get("at", 0.0))
            cool = float(rec.get("backoff_until", 0.0))
        if not force and (time.time() - at) < ttl:
            continue
        if not force and time.time() < cool:
            continue
        age_f = (time.time() - at) / ttl if ttl else 1.0
        boost = 1.0
        if viewport and _name.startswith("tile:"):
            try:
                t = next(x for x in TILES if x["id"] == _tag)
                d = _haversine_km(float(viewport.get("lat", 0.0)),
                                  float(viewport.get("lon", 0.0)),
                                  t["lat"], t["lon"])
                if d < t["dist_nm"] * 1.852 * 1.5:
                    boost = 2.0
            except (TypeError, ValueError, StopIteration):
                pass
        score = age_f * weight * boost
        due.append((0 if _name.startswith("squawk:") else 1, -score, at,
                    leg))
    due.sort()
    due_urls = {leg[1] for _, _, _, leg in due}
    # Fresh legs: serve cache, no fetch.
    for _name, url, _ttl, store, _tag, _w in legs:
        if url in due_urls:
            continue
        with _lock:
            tile_rows.append(store.get(url, {}).get("rows", []))
    budget = max(1, int(max_legs))
    fetched = 0
    gap = False
    for _, _, _, (_name, url, ttl, store, tag, _w) in due:
        with _lock:
            cached = store.get(url, {}).get("rows", [])
        if fetched >= budget:
            # Deferred: serve cached rows; staleness self-labels via
            # position_age in the normal flag rules.
            tile_rows.append(cached)
            continue
        if gap and opener is None:
            # Politeness gap applies to real provider fetches only;
            # injected openers (tests / local fixtures) skip it.
            import random as _r
            time.sleep(FETCH_GAP_S * (1.0 + _r.uniform(-FETCH_JITTER,
                                                       FETCH_JITTER)))
        gap = True
        fr = _now.fetch_url(url, 20, ("application/json",),
                            opener=opener)
        if fr.not_modified:
            with _lock:
                rec = dict(store.get(url, {}))
                rec["at"] = time.time()  # revalidated: not due again yet
                store[url] = rec
            tile_rows.append(cached)
            continue
        if not fr.ok:
            errors.append(f"{tag}: {fr.detail[:100]}")
            with _lock:
                cached = store.get(url, {}).get("rows", [])
                state = dict(_health.get(_name) or {})
                state.update({"state": "RATE_LIMITED"
                              if fr.http_status == 429 else "STALE",
                              "detail": fr.detail[:140],
                              "latency_ms": fr.latency_ms,
                              "last_attempt": now_s})
                _health[_name] = state
                if fr.http_status == 429:
                    rec = dict(store.get(url, {}))
                    rec["backoff_until"] = time.time() + COOLDOWN_429_S
                    store[url] = rec
            tile_rows.append(cached)
            continue
        try:
            rows, skip = parse_adsblol(fr.text, tile=tag)
        except Exception as e:
            errors.append(f"{tag}: parse failed {type(e).__name__}")
            with _lock:
                cached = store.get(url, {}).get("rows", [])
            tile_rows.append(cached)
            continue
        fetched += 1
        skipped += skip
        with _lock:
            store[url] = {"at": time.time(), "rows": rows}
            state = dict(_health.get(_name) or {})
            state.update({"state": "ONLINE", "detail": f"{len(rows)} "
                          f"positioned", "latency_ms": fr.latency_ms,
                          "last_success": now_s, "last_attempt": now_s})
            _health[_name] = state
        tile_rows.append(rows)
    mil_hexes: set = set()
    if include_mil:
        with _lock:
            mat = float(mil_state.get("at", 0.0))
        if force or (time.time() - mat) >= MIL_TTL_S:
            fr = _now.fetch_url(MIL_URL, 20, ("application/json",),
                                opener=opener)
            if fr.ok:
                try:
                    rows, _ = parse_adsblol(fr.text, tile="mil")
                    mil_hexes = {r["icao24"] for r in rows}
                    with _lock:
                        mil_state.update({"at": time.time(),
                                          "n": len(rows)})
                except Exception as e:
                    errors.append(f"mil: parse failed {type(e).__name__}")
    states = dedup_states(tile_rows)
    positioned = len(states)
    n_tracks = update_tracks(states)
    ctx = {"nws_points": nws_points_from_now()}
    flagged: List[Dict[str, Any]] = []
    with _lock:
        histories = {hx: list(dq) for hx, dq in _tracks.items()}
    for o in states:
        fl = flag_aircraft(o, histories.get(o["icao24"], []), ctx)
        if mil_hexes and o["icao24"] in mil_hexes:
            fl.append({
                "rule_id": "PUBLIC_MIL_OBSERVED",
                "label": "PUBLIC MILITARY AIRCRAFT OBSERVED",
                "level": "OBSERVED SIGNAL",
                "interest": "INFO",
                "evidence": {"provider_tag": "mil"},
                "why": "provider tags this contact as military; shown "
                       "with generic movement fields only, never as a "
                       "target and never in IMPORTANT scoring"})
        if fl:
            lvl, reasons = interest_of(
                [f for f in fl if f.get("interest") != "INFO"]
                or [{"interest": "LOW", "label": x["label"],
                     "why": x["why"]} for x in fl])
            flagged.append({
                "icao24": o["icao24"], "callsign": o["callsign"],
                "type": o["type"], "lat": o["lat"], "lon": o["lon"],
                "baro_alt_ft": o.get("baro_alt_ft"),
                "gs_kt": o.get("gs_kt"), "track_deg": o.get("track_deg"),
                "squawk": o.get("squawk"),
                "interest": lvl if not (
                    len(fl) == 1 and fl[0]["rule_id"] ==
                    "PUBLIC_MIL_OBSERVED") else "INFO",
                "flags": fl, "reasons": reasons,
                "source": SOURCE_ID})
    important = [f for f in flagged if f["interest"] in ("HIGH", "MEDIUM")]
    ap_evts = airport_events(
        [{"icao24": f["icao24"], "lat": f["lat"], "lon": f["lon"],
          "rule_id": next((x["rule_id"] for x in f["flags"]
                           if x["rule_id"] == "POSSIBLE_HOLDING"),
                          "")} for f in flagged
         if any(x["rule_id"] == "POSSIBLE_HOLDING" for x in f["flags"])])
    counts = _counts(states, flagged, important)
    with _lock:
        _memory["snapshot"] = {"at": time.time(), "generated_at": now_s,
                               "states": states[:SNAPSHOT_CAP],
                               "flagged": flagged, "important": important,
                               "airport_events": ap_evts, "counts": counts,
                               "errors": errors[:10]}
    return {"refreshed": True, "fetched_legs": fetched,
            "positioned": positioned, "skipped_no_position": skipped,
            "flagged": len(flagged), "important": len(important),
            "tracks": n_tracks, "errors": errors[:10],
            "pending_legs": max(0, len(due) - fetched),
            "generated_at": now_s}


def _counts(states: List[Dict], flagged: List[Dict],
            important: List[Dict]) -> Dict[str, int]:
    n_air = sum(1 for o in states if not o.get("on_ground"))
    n_gnd = sum(1 for o in states if o.get("on_ground"))
    sig: Dict[str, int] = {}
    for o in states:
        sig[o.get("signal", "OTHER")] = sig.get(o.get("signal", "OTHER"),
                                                0) + 1
    em = sum(1 for f in flagged for x in f["flags"]
             if x["rule_id"] == "EMERGENCY_SQUAWK")
    ho = sum(1 for f in flagged for x in f["flags"]
             if x["rule_id"] == "POSSIBLE_HOLDING")
    wx = sum(1 for f in flagged for x in f["flags"]
             if x["rule_id"] == "NEAR_SEVERE_WX")
    st = sum(1 for f in flagged for x in f["flags"]
             if x["rule_id"] == "POSITION_STALE")
    return {"total": len(states), "airborne": n_air, "on_ground": n_gnd,
            "signals": sig, "flagged": len(flagged),
            "important": len(important), "emergency_squawks": em,
            "holding": ho, "weather_conflicts": wx, "stale": st}


def get_aviation(refresh: bool = True,
                 opener: Optional[Callable] = None,
                 include_mil: bool = False) -> Dict[str, Any]:
    if refresh:
        refresh_aviation(opener=opener, include_mil=include_mil)
    with _lock:
        snap = dict(_memory.get("snapshot") or {})
        health = {k: dict(v) for k, v in _health.items()}
        n_tracks = len(_tracks)
    if not snap:
        return {"mode": "aviation", "real_data": False, "live": False,
                "counts": {"total": 0}, "states": [], "flagged": [],
                "important": [], "airport_events": [],
                "health": [], "truth_label": "AVIATION (no data yet)",
                "coverage": coverage([])}
    states = snap.get("states", [])
    return {
        "mode": "aviation",
        "dataset": "tellurion-aviation-v1",
        "normalizer": NORMALIZER,
        "generated_at": snap.get("generated_at", "UNKNOWN"),
        "live": False,
        "real_data": True,
        "truth_label": "LIVE AVIATION (public ADS-B, delayed seconds)",
        "license_note": RIGHTS,
        "attribution": ATTRIBUTION,
        "counts": snap.get("counts", {}),
        "tracks_held": n_tracks,
        "states": states,
        "capped": len(states) >= SNAPSHOT_CAP,
        "flagged": snap.get("flagged", []),
        "important": snap.get("important", []),
        "airport_events": snap.get("airport_events", []),
        "health": [{"leg": k, **v} for k, v in health.items()],
        "coverage": coverage(states),
        "errors": snap.get("errors", []),
    }


def coverage(states: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    with _lock:
        tile_health = {k: v.get("state", "UNKNOWN")
                       for k, v in _health.items()}
    rows = []
    for t in TILES:
        st = tile_health.get("tile:" + t["id"], "UNKNOWN")
        n = sum(1 for o in states if t["id"] in (o.get("tiles") or []))
        rows.append({"tile": t["id"], "state": st, "aircraft": n,
                     "coverage": "PARTIAL (regional tile, receiver-"
                                 "dependent)"})
    rows.append({"tile": "oceans/africa/polar", "state": "NO TILE",
                 "aircraft": 0,
                 "coverage": "NO CURRENT ENABLED SOURCE in these regions"})
    return rows


def source_rollup() -> Dict[str, Any]:
    """Aggregate per-leg health to one honest source row (never hides)."""
    with _lock:
        legs = dict(_health)
        snap = dict(_memory.get("snapshot") or {})
    tiles = {k: v for k, v in legs.items() if k.startswith("tile:")}
    sq = {k: v for k, v in legs.items() if k.startswith("squawk:")}
    order = {"OFFLINE": 0, "STALE": 1, "RATE_LIMITED": 2, "ONLINE": 3}
    worst = "UNKNOWN"
    for v in list(tiles.values()) + list(sq.values()):
        st = str(v.get("state", "UNKNOWN"))
        if st not in order:
            continue  # UNKNOWN legs carry no signal, never mask known
        if worst == "UNKNOWN" or order[st] < order[worst]:
            worst = st
    online = sum(1 for v in tiles.values() if v.get("state") == "ONLINE")
    counts = snap.get("counts", {}) if snap else {}
    return {"source_id": SOURCE_ID, "state": worst,
            "tiles_online": f"{online}/{len(TILES)}",
            "aircraft": counts.get("total", 0),
            "important": counts.get("important", 0),
            "attribution": ATTRIBUTION, "rights": RIGHTS,
            "truth_mode": TRUTH_MODE,
            "detail": "aggregate of per-leg states; worst state shown, "
                      "nothing hidden"}


# --------------------------------------------------------------------------
# IMPORTANT NOW V2 — cross-domain ranking (additive; world_now untouched)
# --------------------------------------------------------------------------

def _event_age_h(value: Any) -> Optional[float]:
    try:
        from gods_eye.future import world_now as _now
        t = _now._parse_time(value)
    except Exception:
        return None
    if t is None:
        return None
    return (time.time() - t) / 3600.0


def _fresh_points(age_h: Optional[float]) -> Tuple[int, str]:
    if age_h is None:
        return 0, "event time UNKNOWN"
    if age_h < 6:
        return 2, f"event age {age_h:.1f} h"
    if age_h < 24:
        return 1, f"event age {age_h:.1f} h"
    return 0, f"event age {age_h:.1f} h"


def _rank_item(domain: str, title: str, key: str, lat: Any, lon: Any,
               when: Any, source: str, quality: int, quality_why: str,
               severity: int, severity_why: str,
               corroboration: int, corroboration_why: str,
               rarity: int, rarity_why: str, scope: int, scope_why: str,
               certainty: str, observed: str, inferred: str,
               why: List[str]) -> Dict[str, Any]:
    scores = {"severity": severity, "freshness": 0, "source_quality": quality,
              "corroboration": corroboration, "rarity": rarity,
              "scope": scope}
    reasons = [f"severity: {severity_why}", f"source: {quality_why}",
               f"corroboration: {corroboration_why}",
               f"rarity: {rarity_why}", f"scope: {scope_why}"]
    fp, fw = _fresh_points(_event_age_h(when))
    scores["freshness"] = fp
    reasons.append(f"freshness: {fw}")
    reasons.extend(why)
    age = _event_age_h(when)
    n_sources = 2 if corroboration >= 2 else (
        2 if corroboration == 1 and domain != "AVIATION" else 1)
    return {"domain": domain, "title": title, "key": key,
            "lat": lat, "lon": lon, "when": when if when else "UNKNOWN",
            "freshness_age_h": round(age, 1) if age is not None else None,
            "n_sources": n_sources,
            "source": source, "certainty": certainty,
            "observed": observed, "inferred": inferred,
            "observed_or_inferred": "OBSERVED" if certainty in (
                "OBSERVED SIGNAL", "GOVERNMENT_NOTICE") else "INFERRED",
            "scores": scores, "total": sum(scores.values()),
            "reasons": reasons}


def _context(prefix: str, lat: Any, lon: Any) -> str:
    """`prefix; context: a; b`, or just `prefix` when nothing public is near
    (never a dangling empty "context:")."""
    near = _infra_near(lat, lon)
    return f"{prefix}; context: {'; '.join(near)}" if near else prefix


def _infra_near(lat: Any, lon: Any,
                max_km: float = 300.0) -> List[str]:
    """Conservative cross-domain context: public infra near an event."""
    if lat is None or lon is None:
        return []
    try:
        from gods_eye.future import world_demo as _w
    except Exception:
        return []
    out = []
    for a in _w.AIRPORTS:
        if _haversine_km(lat, lon, a["lat"], a["lon"]) <= max_km:
            out.append(f"near airport {a['id']} "
                       f"({_haversine_km(lat, lon, a['lat'], a['lon']):.0f} "
                       f"km; proximity only)")
            break
    for p in _w.PORTS:
        if _haversine_km(lat, lon, p["lat"], p["lon"]) <= max_km:
            out.append(f"near port {p['id']} "
                       f"({_haversine_km(lat, lon, p['lat'], p['lon']):.0f} "
                       f"km; proximity only)")
            break
    return out


def important_v2(limit: int = 60) -> Dict[str, Any]:
    """Unified cross-domain IMPORTANT NOW with explicit ranking.

    Reads the world_now snapshot (no refresh) + aviation snapshot.
    Every item answers WHY/SOURCE/WHEN/CERTAINTY/OBSERVED/INFERRED.
    No black-box score: six explicit 0-2 dimensions, all reasons shown.
    """
    from gods_eye.future import world_now as _now
    groups = {}
    try:
        mem = _now._memory
        for sid in ("usgs-earthquakes", "gdacs-alerts", "nasa-eonet",
                    "nws-alerts", "noaa-swpc", "gdelt-doc"):
            items = (mem.get(sid) or {}).get("items", [])
            if items:
                groups[sid] = items
    except Exception:
        groups = {}
    try:
        links = _now.link_events(groups) if groups else []
    except Exception:
        links = []
    linked = {l["a"] for l in links} | {l["b"] for l in links}
    items: List[Dict[str, Any]] = []
    # Aviation first (movement is the scarcest signal).
    air = get_aviation(refresh=False)
    for f in (air.get("important", []) or [])[:40]:
        fl = f.get("flags") or []
        top = fl[0] if fl else {}
        sev = 2 if f.get("interest") == "HIGH" else 1
        items.append(_rank_item(
            "AVIATION", f"{f.get('callsign')} {f.get('icao24')}",
            f"AIR:{f.get('icao24')}", f.get("lat"), f.get("lon"),
            None, SOURCE_ID, 2, "direct ADS-B sensor observation",
            sev, top.get("label", "flagged"), 0, "single-sensor track",
            2 if any(x.get("rule_id") == "EMERGENCY_SQUAWK" for x in fl)
            else (1 if f.get("interest") == "MEDIUM" else 0),
            "operational rarity of " + top.get("rule_id", "track"),
            1 if any(x.get("rule_id") == "POSSIBLE_HOLDING" for x in fl)
            else 0, "airport-cluster vs single track",
            top.get("level", "POSSIBLE"),
            top.get("label", "flag") + " " +
            json.dumps(top.get("evidence", {}))[:200],
            "; ".join(x.get("label", "") for x in fl[1:]) or "none",
            ["WHY: " + x.get("why", "") for x in fl]))
    for e in (air.get("airport_events", []) or [])[:10]:
        items.append(_rank_item(
            "AVIATION", e.get("label", "airport event"), "AIR:APT",
            None, None, None, SOURCE_ID, 2, "multi-track airport context",
            1, "airport disruption context", 2, "multi-aircraft pattern",
            1, "unusual clustering", 1, "airport scope",
            e.get("level", "POSSIBLE"), e.get("label", ""),
            "per-aircraft causes not inferred", [e.get("why", "")]))
    # Earth / disaster / weather / space / reports.
    for q in sorted(groups.get("usgs-earthquakes", []),
                    key=lambda o: -((o.get("fields") or {}).get("mag")
                                    or 0))[:15]:
        f = q.get("fields") or {}
        mag = f.get("mag") or 0
        sev = 2 if mag >= 6 else (1 if mag >= 5 else 0)
        cor = 2 if q.get("stable_key") in linked and any(
            l.get("corroboration") == "CORROBORATED"
            for l in links
            if q.get("stable_key") in (l.get("a"), l.get("b"))) else (
            1 if q.get("stable_key") in linked else 0)
        items.append(_rank_item(
            "EARTH", f"M{mag} — {f.get('place', 'earthquake')}",
            q.get("stable_key", ""), q.get("lat"), q.get("lon"),
            q.get("source_event_time"), "usgs-earthquakes", 2,
            "USGS sensor network", sev, f"magnitude {mag}",
            cor, "linked" if cor else "one source",
            1 if mag >= 6 else 0, "M6+ rarity",
            1 if mag >= 6 else 0, "wide-felt scope",
            "OBSERVED SIGNAL", f"magnitude {mag} at {f.get('place')}",
            _context("impact not inferred", q.get("lat"), q.get("lon")),
            ["WHY: sensor magnitude + recency; no damage claims"]))
    for g in groups.get("gdacs-alerts", [])[:30]:
        f = g.get("fields") or {}
        al = str(f.get("alert_level", "")).lower()
        if al not in ("red", "orange"):
            continue
        sev = 2 if al == "red" else 1
        items.append(_rank_item(
            "DISASTER", str(f.get("title", g.get("stable_key", "")))[:120],
            g.get("stable_key", ""), g.get("lat"), g.get("lon"),
            g.get("source_event_time"), "gdacs-alerts", 1,
            "GDACS curated alerts (summary leg)", sev,
            f"GDACS alert level {al} (verbatim)",
            1 if g.get("stable_key") in linked else 0,
            "linked" if g.get("stable_key") in linked else "one source",
            1 if al == "red" else 0, "red-alert rarity",
            1, "disaster scope", "GOVERNMENT_NOTICE",
            f"alert level {al}, type {f.get('event_type', '?')}",
            _context("severity wording is provider-verbatim, never "
                     "reinterpreted", g.get("lat"), g.get("lon")),
            ["WHY: official alert level + recency"]))
    for a in groups.get("nws-alerts", [])[:60]:
        f = a.get("fields") or {}
        sv = str(f.get("severity", "")).lower()
        if sv not in ("extreme", "severe"):
            continue
        items.append(_rank_item(
            "WEATHER", str(f.get("title", f.get("headline", "")))[:120],
            a.get("stable_key", ""), a.get("lat"), a.get("lon"),
            a.get("source_event_time"), "nws-alerts", 2,
            "NWS official alert (US ONLY)", 2 if sv == "extreme" else 1,
            f"NWS severity {sv}",
            1 if a.get("stable_key") in linked else 0, "link state",
            0, "routine alert class", 1, "US regional scope",
            "GOVERNMENT_NOTICE", f"{sv}: {f.get('headline', '')[:100]}",
            "US ONLY — never global weather; no impact claims",
            ["WHY: official severity + recency"]))
    for s in groups.get("noaa-swpc", [])[:10]:
        t = ((s.get("fields") or {}).get("title")) or ""
        if not any(k in t for k in ("WARNING", "WATCH", "ALERT", "WARNING")):
            continue
        items.append(_rank_item(
            "SPACE", t[:120], s.get("stable_key", ""), None, None,
            s.get("source_event_time"), "noaa-swpc", 2,
            "NOAA SWPC official product", 1, "space-weather watch class",
            0, "single product", 1, "unusual product",
            1, "global-products scope", "GOVERNMENT_NOTICE", t[:120],
            "solar/geomagnetic product, not ground impact",
            ["WHY: official watch/warning class"]))
    for e in groups.get("nasa-eonet", [])[:15]:
        f = e.get("fields") or {}
        items.append(_rank_item(
            "DISASTER", str(f.get("title", ""))[:120],
            e.get("stable_key", ""), e.get("lat"), e.get("lon"),
            e.get("source_event_time"), "nasa-eonet", 1,
            "NASA EONET curated events", 1, "curated natural event",
            2 if e.get("stable_key") in linked else 0,
            "news-corroborated" if e.get("stable_key") in linked else
            "one source",
            0, "routine class", 0, "local scope", "OBSERVED SIGNAL",
            str(f.get("title", ""))[:120],
            "severity never inferred from categories",
            ["WHY: curation + recency"]))
    items.sort(key=lambda x: (-x["total"], str(x.get("when", ""))))
    return {"mode": "important-v2", "generated_at": utcnow(), "live": False,
            "real_data": True,
            "truth_label": "IMPORTANT NOW V2 (explicit ranking, no AI)",
            "ranking": "severity+freshness+source+corroboration+rarity+"
                       "scope (each 0-2); all reasons exposed",
            "items": items[:max(1, min(100, limit))],
            "n": len(items)}
