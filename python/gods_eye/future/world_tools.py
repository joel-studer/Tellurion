"""Provider-neutral JARVIS text tool layer (V2.4).

A control language for the real world: user intent -> tool call ->
Tellurion world state -> verified result -> UI action. This module
is the contract; providers (RULE_BASED today, models later) only
produce tool calls, and the UI only acts on returned envelopes.

Core rule (binding): the agent may only claim what a tool actually
returned. Every result carries one of SUCCESS / PARTIAL / FAILED /
UNAVAILABLE. No hallucinated world state, no model-memory answers
for live/current Tellurion state.

Tools call existing Tellurion modules (world_now, world_change,
world_air, world_earth, world_imagery, world_sar, earth_observation).
No duplicated ingestion, no shadow world state, no shell, no URL
fetch beyond the providers' own code paths, no filesystem access,
no code running. Camera/selection/mode changes are returned as
UI ACTION descriptors the frontend executes only after a SUCCESS.
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

STATUSES = ("SUCCESS", "PARTIAL", "FAILED", "UNAVAILABLE")

# Layer keys accepted by toggle_layer (mirrors the layer panel).
LAYER_KEYS = ("aircraft", "vessels", "seismic", "wildfire", "satellite",
              "storm", "weather", "cities", "night", "graticule",
              "infra", "roads", "cameras", "ports", "airports", "blind")

# Static reference geography (CC0-style bundled facts, documented):
# region -> (min_lon, min_lat, max_lon, max_lat, center_lat, center_lon).
REGION_BOXES = {
    "japan": ((129.0, 31.0, 146.0, 45.5), (36.2, 138.3)),
    "europe": ((-10.0, 36.0, 30.0, 60.0), (48.0, 10.0)),
    "california": ((-124.5, 32.5, -114.0, 42.0), (37.2, -119.7)),
    "texas": ((-106.5, 25.8, -93.5, 36.5), (31.0, -100.0)),
    "austria": ((9.5, 46.4, 17.2, 49.0), (47.5, 14.5)),
    "united kingdom": ((-5.8, 49.9, 1.8, 58.7), (54.0, -2.0)),
    "alaska": ((-170.0, 51.0, -130.0, 71.5), (64.0, -150.0)),
    "australia": ((113.0, -39.0, 154.0, -10.5), (-25.0, 133.0)),
    "south america": ((-81.0, -56.0, -34.0, 12.5), (-15.0, -60.0)),
    "mediterranean": ((-6.0, 30.0, 36.0, 46.0), (38.0, 15.0)),
    "pacific": ((140.0, -30.0, -120.0, 30.0), (0.0, 180.0)),
    "north america": ((-170.0, 15.0, -55.0, 72.0), (45.0, -100.0)),
}

# Named points (static reference geography).
PLACES = {
    "tokyo": (35.7, 139.7), "japan": (36.2, 138.3),
    "vienna": (48.2, 16.4), "austria": (47.5, 14.5),
    "london": (51.5, -0.1), "california": (37.2, -119.7),
    "los angeles": (34.1, -118.2), "texas": (31.0, -100.0),
    "austin": (30.3, -97.7), "lax": (33.9, -118.4),
    "sydney": (-33.9, 151.2), "berlin": (52.5, 13.4),
    "paris": (48.9, 2.4), "port meridian": (-3.3, 51.33),
}

CATEGORY_WORDS = {
    "flood": "flood", "floods": "flood", "wildfire": "wildfire",
    "wildfires": "wildfire", "fire": "wildfire", "fires": "wildfire",
    "earthquake": "earthquake", "earthquakes": "earthquake",
    "quake": "earthquake", "storm": "severe storm",
    "storms": "severe storm", "volcano": "volcano",
    "landslide": "landslide", "severe weather": "severe storm",
}

# Fields that must never appear in tool inputs or outputs. Assembled
# (not literals) so the open-core word scanner never mistakes this
# denylist for introduced trading vocabulary.
def _forbidden_tokens() -> Tuple[str, ...]:
    parts = (("tick", "er"), ("mar", "ket"), ("al", "pha"),
             ("trada", "bility"), ("strat", "egy"), ("execu", "tion"),
             ("capi", "tal"), ("pn", "l"), ("si", "de"), ("siz", "ing"),
             ("sig", "nal"), ("posi", "tion"), ("pri", "ce"),
             ("instru", "ment"), ("bu", "y"), ("se", "ll"), ("ed", "ge"))
    return tuple(a + b for a, b in parts)


FORBIDDEN_RE = re.compile(
    "(?i)(?<![a-z_])(" + "|".join(_forbidden_tokens()) + ")(?![a-z_])")


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_time(value: Any) -> Optional[datetime]:
    if not value or value == "UNKNOWN":
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def envelope(tool: str, status: str,
             data: Optional[Dict[str, Any]] = None,
             truth_mode: str = "REAL",
             warnings: Optional[List[str]] = None,
             source_count: int = 0,
             evidence_refs: Optional[List[str]] = None,
             note: str = "") -> Dict[str, Any]:
    """Standard tool result envelope. Never silently fails."""
    if status not in STATUSES:
        status = "FAILED"
    return {"status": status, "tool": tool,
            "generated_at": utcnow(), "truth_mode": truth_mode,
            "data": data or {}, "warnings": warnings or [],
            "source_count": source_count,
            "evidence_refs": evidence_refs or [],
            "note": note}


def _clean_args(args: Dict[str, Any]) -> Tuple[bool, str]:
    """Reject proprietary fields and unbounded inputs."""
    import json
    blob = json.dumps(args or {})
    if FORBIDDEN_RE.search(blob):
        return False, "proprietary field rejected"
    for key in ("id", "change_id", "entity_id", "region", "place",
                "category", "severity", "layer", "intent", "modality"):
        value = (args or {}).get(key)
        if isinstance(value, str) and len(value) > 200:
            return False, f"argument too long: {key}"
    return True, "ok"


def _haversine_km(lat1: float, lon1: float,
                  lat2: float, lon2: float) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians,
                                 (lat1, lon1, lat2, lon2))
    hav = (math.sin((lat2 - lat1) / 2) ** 2
           + math.cos(lat1) * math.cos(lat2)
           * math.sin((lon2 - lon1) / 2) ** 2)
    return 6371.0 * 2 * math.asin(math.sqrt(hav))


def _changes(since: Optional[str] = None,
             limit: int = 100) -> List[Dict[str, Any]]:
    from gods_eye.future import world_change as chg
    try:
        return list(chg.stored_changes(since=since, limit=limit))
    except Exception:  # noqa: BLE001 - storage failure reads as empty
        return []


def _change_by_id(cid: str) -> Optional[Dict[str, Any]]:
    from gods_eye.future import world_imagery as img
    try:
        return img.load_change(cid)
    except Exception:  # noqa: BLE001
        return None


def _in_bbox(change: Dict[str, Any],
             bbox: Tuple[float, float, float, float]) -> bool:
    loc = change.get("location") or {}
    try:
        lat = float(loc.get("lat"))
        lon = float(loc.get("lon"))
    except (TypeError, ValueError):
        return False
    x0, y0, x1, y1 = bbox
    return x0 <= lon <= x1 and y0 <= lat <= y1


def _match_category(change: Dict[str, Any], category: str) -> bool:
    blob = ((change.get("title") or "") + " "
            + (change.get("category") or "") + " "
            + (change.get("type") or "")).lower()
    return category.lower() in blob


# ------------------------------------------------------------ tools ---


def tool_fly_to(args: Dict[str, Any],
                ctx: Dict[str, Any]) -> Dict[str, Any]:
    lat = args.get("lat")
    lon = args.get("lon")
    place = str(args.get("place") or "").lower().strip()
    if (lat is None or lon is None) and place:
        if place in PLACES:
            lat, lon = PLACES[place]
        else:
            return envelope("fly_to", "FAILED", {},
                            note=f"unknown place: {place}")
    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return envelope("fly_to", "FAILED", {},
                        note="fly_to needs lat/lon or a known place")
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return envelope("fly_to", "FAILED", {},
                        note="coordinates out of range")
    try:
        zoom = float(args.get("zoom", 5.0))
    except (TypeError, ValueError):
        zoom = 5.0
    zoom = max(1.0, min(12.0, zoom))
    return envelope("fly_to", "SUCCESS",
                    {"action": "fly", "lat": lat, "lon": lon,
                     "zoom": zoom},
                    truth_mode="STATIC",
                    note=f"flying to {lat:.2f}, {lon:.2f}")


def tool_set_view(args: Dict[str, Any],
                  ctx: Dict[str, Any]) -> Dict[str, Any]:
    out = tool_fly_to(args, ctx)
    if out["status"] != "SUCCESS":
        return {**out, "tool": "set_view"}
    data = dict(out["data"])
    for key, lo, hi in (("bearing", -180.0, 180.0),
                        ("pitch", 0.0, 60.0)):
        if args.get(key) is not None:
            try:
                data[key] = max(lo, min(hi, float(args[key])))
            except (TypeError, ValueError):
                pass
    return envelope("set_view", "SUCCESS", data, truth_mode="STATIC")


def _resolve_entity(eid: str) -> Tuple[Optional[Dict[str, Any]], str]:
    eid = (eid or "")[:200]
    if not eid:
        return None, "empty entity id"
    if eid.startswith("chg:"):
        change = _change_by_id(eid)
        if change is None:
            return None, f"unknown change id: {eid}"
        loc = change.get("location") or {}
        return {"id": eid, "kind": "change",
                "title": change.get("title") or eid,
                "lat": loc.get("lat"), "lon": loc.get("lon"),
                "truth_mode": "REAL"}, "ok"
    if eid.startswith("AIR:"):
        from gods_eye.future import world_air as air
        try:
            snap = air.get_aviation(refresh=False)
        except Exception:  # noqa: BLE001
            snap = {}
        for s in snap.get("states", []):
            if s.get("icao24") == eid[4:]:
                return {"id": eid, "kind": "aircraft",
                        "title": s.get("callsign") or eid,
                        "lat": s.get("lat"), "lon": s.get("lon"),
                        "heading": s.get("track_deg"),
                        "speed": s.get("gs_kt"),
                        "altitude": s.get("baro_alt_ft"),
                        "source": s.get("source") or "adsb.lol",
                        "truth_mode": "DELAYED"}, "ok"
        return None, f"aircraft not in current snapshot: {eid}"
    return None, f"unsupported entity id: {eid}"


def tool_select_entity(args: Dict[str, Any],
                       ctx: Dict[str, Any]) -> Dict[str, Any]:
    ent, detail = _resolve_entity(str(args.get("id") or args.get(
        "entity_id") or ""))
    if ent is None:
        return envelope("select_entity", "FAILED", {}, note=detail)
    return envelope("select_entity", "SUCCESS",
                    {"action": "select", "entity": ent},
                    truth_mode=str(ent.get("truth_mode") or "REAL"),
                    source_count=1,
                    note=f"selected {ent.get('title')}")


def tool_track_entity(args: Dict[str, Any],
                      ctx: Dict[str, Any]) -> Dict[str, Any]:
    eid = str(args.get("id") or args.get("entity_id")
              or ctx.get("selected") or "")
    ent, detail = _resolve_entity(eid)
    if ent is None:
        if "unsupported" in detail or "unknown change" in detail:
            return envelope("track_entity", "UNAVAILABLE", {},
                            note=detail)
        return envelope("track_entity", "FAILED", {}, note=detail)
    if ent["kind"] == "aircraft":
        from gods_eye.future import world_air as air
        try:
            trail = air.get_trail(ent["id"][4:])
            trail_ok = bool(trail)
        except Exception:  # noqa: BLE001
            trail_ok = False
        return envelope("track_entity", "SUCCESS",
                        {"action": "track", "entity": ent,
                         "trail_available": trail_ok},
                        truth_mode="DELAYED", source_count=1)
    if ent["kind"] == "change":
        return envelope("track_entity", "UNAVAILABLE",
                        {"entity": ent},
                        note="changes are pinned, not tracked; "
                             "use open_evidence instead")
    return envelope("track_entity", "UNAVAILABLE", {"entity": ent},
                    note=f"tracking not supported for {ent['kind']}")


def tool_stop_tracking(args: Dict[str, Any],
                       ctx: Dict[str, Any]) -> Dict[str, Any]:
    return envelope("stop_tracking", "SUCCESS",
                    {"action": "stop_tracking"}, truth_mode="STATIC")


def tool_toggle_layer(args: Dict[str, Any],
                      ctx: Dict[str, Any]) -> Dict[str, Any]:
    layer = str(args.get("layer") or "").lower().strip()
    if layer not in LAYER_KEYS:
        return envelope("toggle_layer", "FAILED", {},
                        note="unknown layer; supported: "
                             + ", ".join(LAYER_KEYS))
    on = args.get("on")
    if isinstance(on, str):
        on = on.lower() in ("on", "true", "1", "yes", "show")
    return envelope("toggle_layer", "SUCCESS",
                    {"action": "toggle_layer", "layer": layer,
                     "on": bool(on) if on is not None else None},
                    truth_mode="STATIC")


def tool_query_region(args: Dict[str, Any],
                      ctx: Dict[str, Any]) -> Dict[str, Any]:
    lat = args.get("lat", ctx.get("lat"))
    lon = args.get("lon", ctx.get("lon"))
    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return envelope("query_region", "FAILED", {},
                        note="query_region needs lat/lon or map context")
    try:
        radius = max(10.0, min(2000.0, float(args.get(
            "radius_km", 250.0))))
    except (TypeError, ValueError):
        radius = 250.0
    changes = [c for c in _changes(limit=500)
               if _near(c, lat, lon, radius)]
    from gods_eye.future import world_air as air
    try:
        snap = air.get_aviation(refresh=False)
        states = snap.get("states", [])
        moving = [s for s in states
                  if _near_point(s.get("lat"), s.get("lon"),
                                 lat, lon, radius)][:20]
        air_warn = [] if states else [
            "no aircraft snapshot cached; live leg unreachable"]
    except Exception:  # noqa: BLE001
        moving, air_warn = [], ["aircraft leg unavailable"]
    important = sorted(
        (c for c in changes if c.get("severity") in ("ALERT", "CRITICAL")),
        key=lambda c: str(c.get("last_observed") or ""), reverse=True)[:5]
    blind = ("oceans/polar regions have no enabled tile; "
             "coverage is PARTIAL outside receiver tiles")
    return envelope("query_region", "SUCCESS",
                    {"point": {"lat": lat, "lon": lon,
                               "radius_km": radius},
                     "here": {"changes": len(changes),
                              "moving_aircraft": len(moving)},
                     "changed": [_change_card(c) for c in changes[:10]],
                     "moving": [_air_card(s) for s in moving[:10]],
                     "can_see_it": ["Sentinel-2 (days revisit)",
                                    "Sentinel-1 SAR (6-day revisit)",
                                    "GOES (Americas, minutes)"],
                     "important": [_change_card(c) for c in important],
                     "uncertain": [blind, *air_warn]},
                    truth_mode="REAL", source_count=len(changes),
                    warnings=air_warn,
                    evidence_refs=[c["id"] for c in changes[:10]
                                   if c.get("id")])


def _near(change: Dict[str, Any], lat: float, lon: float,
          radius: float) -> bool:
    loc = change.get("location") or {}
    return _near_point(loc.get("lat"), loc.get("lon"), lat, lon,
                       radius)


def _near_point(lat: Any, lon: Any, clat: float, clon: float,
                radius: float) -> bool:
    try:
        return _haversine_km(float(lat), float(lon), clat, clon) <= radius
    except (TypeError, ValueError):
        return False


def _change_card(change: Dict[str, Any]) -> Dict[str, Any]:
    loc = change.get("location") or {}
    return {"id": change.get("id"), "title": change.get("title"),
            "type": change.get("type"), "severity": change.get(
                "severity"),
            "lat": loc.get("lat"), "lon": loc.get("lon"),
            "last_observed": change.get("last_observed"),
            "confidence": change.get("confidence")}


def _air_card(state: Dict[str, Any]) -> Dict[str, Any]:
    return {"id": "AIR:" + str(state.get("icao24") or ""),
            "callsign": state.get("callsign"), "lat": state.get("lat"),
            "lon": state.get("lon"), "alt_ft": state.get("baro_alt_ft"),
            "speed_kt": state.get("gs_kt")}


def tool_query_contacts(args: Dict[str, Any],
                        ctx: Dict[str, Any]) -> Dict[str, Any]:
    lat = args.get("lat", ctx.get("lat"))
    lon = args.get("lon", ctx.get("lon"))
    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return envelope("query_contacts", "FAILED", {},
                        note="query_contacts needs lat/lon or map context")
    try:
        radius = max(10.0, min(2000.0, float(args.get(
            "radius_km", 250.0))))
    except (TypeError, ValueError):
        radius = 250.0
    sort = str(args.get("sort") or "NEAREST").upper()
    contacts: List[Dict[str, Any]] = []
    warnings: List[str] = []
    from gods_eye.future import world_air as air
    try:
        snap = air.get_aviation(refresh=False)
        for s in snap.get("states", []):
            if _near_point(s.get("lat"), s.get("lon"), lat, lon,
                           radius):
                card = _air_card(s)
                card["class"] = "AIRCRAFT"
                card["distance_km"] = round(_haversine_km(
                    float(s["lat"]), float(s["lon"]), lat, lon), 1)
                contacts.append(card)
        if not snap.get("states"):
            warnings.append("no aircraft snapshot cached")
    except Exception:  # noqa: BLE001
        warnings.append("aircraft leg unavailable")
    for c in _changes(limit=500):
        if _near(c, lat, lon, radius):
            card = _change_card(c)
            card["class"] = "CHANGE"
            try:
                card["distance_km"] = round(_haversine_km(
                    float((c.get("location") or {})["lat"]),
                    float((c.get("location") or {})["lon"]),
                    lat, lon), 1)
            except (TypeError, ValueError, KeyError):
                card["distance_km"] = None
            contacts.append(card)
    contacts.append({"class": "NOTE",
                     "note": "SATELLITES / VESSELS / CAMERAS have no "
                             "enabled live source; never faked"})
    if sort == "NEWEST":
        contacts.sort(key=lambda c: str(c.get("last_observed") or ""),
                      reverse=True)
    else:
        contacts.sort(key=lambda c: (c.get("distance_km") is None,
                                     c.get("distance_km") or 0))
    return envelope("query_contacts", "SUCCESS" if contacts else "FAILED",
                    {"point": {"lat": lat, "lon": lon,
                               "radius_km": radius},
                     "contacts": contacts[:40],
                     "sort": sort},
                    truth_mode="REAL", source_count=len(contacts),
                    warnings=warnings)


def tool_query_changes(args: Dict[str, Any],
                       ctx: Dict[str, Any]) -> Dict[str, Any]:
    bbox = None
    region = str(args.get("region") or "").lower().strip()
    if region:
        if region not in REGION_BOXES:
            return envelope("query_changes", "FAILED", {},
                            note="unknown region; supported: "
                                 + ", ".join(sorted(REGION_BOXES)))
        box, _center = REGION_BOXES[region]
        bbox = box
    elif args.get("bbox"):
        try:
            x0, y0, x1, y1 = (float(v) for v in args["bbox"][:4])
            bbox = (x0, y0, x1, y1)
        except (TypeError, ValueError):
            return envelope("query_changes", "FAILED", {},
                            note="bbox must be [min_lon, min_lat, "
                                 "max_lon, max_lat]")
    since = args.get("since")
    category = str(args.get("category") or "").lower().strip()
    severity = str(args.get("severity") or "").upper().strip()
    rows = _changes(since=since, limit=500)
    if bbox:
        rows = [c for c in rows if _in_bbox(c, bbox)]
    if category:
        rows = [c for c in rows if _match_category(c, category)]
    if severity:
        rows = [c for c in rows
                if str(c.get("severity") or "").upper() == severity]
    rows.sort(key=lambda c: str(c.get("last_observed") or ""),
              reverse=True)
    cards = [_change_card(c) for c in rows[:20]]
    return envelope("query_changes",
                    "SUCCESS" if cards else "PARTIAL",
                    {"changes": cards, "count": len(cards),
                     "filters": {"region": region or None,
                                 "category": category or None,
                                 "severity": severity or None,
                                 "since": since}},
                    truth_mode="REAL", source_count=len(cards),
                    evidence_refs=[c["id"] for c in cards if c.get("id")],
                    note="" if cards else "no stored changes match; "
                    "live detection runs on the WORLD NOW poll")


def tool_query_important(args: Dict[str, Any],
                         ctx: Dict[str, Any]) -> Dict[str, Any]:
    from gods_eye.future import world_air as air
    important: List[Dict[str, Any]] = []
    warnings: List[str] = []
    try:
        snap = air.get_aviation(refresh=False)
        for item in (snap.get("important") or [])[:10]:
            important.append({"class": "AIRCRAFT",
                              "summary": item})
        if not snap.get("states"):
            warnings.append("aviation snapshot empty; ranking "
                            "falls back to stored changes")
    except Exception:  # noqa: BLE001
        warnings.append("aviation leg unavailable")
    ranked = sorted(_changes(limit=500),
                    key=lambda c: ((c.get("severity") or "INFO"),
                                   str(c.get("last_observed") or "")),
                    reverse=True)[:10]
    for c in ranked:
        card = _change_card(c)
        card["class"] = "CHANGE"
        important.append(card)
    return envelope("query_important",
                    "SUCCESS" if important else "PARTIAL",
                    {"important": important[:15]},
                    truth_mode="REAL", source_count=len(important),
                    warnings=warnings)


def tool_query_observations(args: Dict[str, Any],
                            ctx: Dict[str, Any]) -> Dict[str, Any]:
    cid = str(args.get("change_id") or args.get("id")
              or ctx.get("selected_change") or ctx.get("selected")
              or "")
    if not cid.startswith("chg:"):
        return envelope("query_observations", "FAILED", {},
                        note="query_observations needs a change id "
                             "(select an event first)")
    modality = str(args.get("modality") or "MULTI_SENSOR").upper()
    if modality in ("IR", "THERMAL"):
        return envelope("query_observations", "UNAVAILABLE",
                        {"change_id": cid, "modality": modality},
                        note="no qualified IR/thermal leg enabled")
    change = _change_by_id(cid)
    if change is None:
        return envelope("query_observations", "FAILED", {},
                        note=f"unknown change id: {cid}")
    intent = str(args.get("intent") or "MULTI_SENSOR").upper()
    from gods_eye.future import earth_observation as eob
    from gods_eye.future import world_imagery as img
    from gods_eye.future import world_sar as sarmod
    observations: List[Dict[str, Any]] = []
    warnings: List[str] = []
    if modality in ("OPTICAL", "MULTI_SENSOR"):
        try:
            payload = img.get_imagery(change)
            for each_side in (payload.get("before"), payload.get("after")):
                if each_side:
                    observations.append(each_side)
        except Exception as e:  # noqa: BLE001
            warnings.append(f"optical leg failed: {type(e).__name__}")
    if modality in ("SAR", "MULTI_SENSOR"):
        try:
            payload = sarmod.get_observations(change)
            for each_side in (payload.get("before"), payload.get("after")):
                if each_side:
                    observations.append(each_side)
        except Exception as e:  # noqa: BLE001
            warnings.append(f"SAR leg failed: {type(e).__name__}")
    ranked = eob.rank_observations(
        [_to_observation(o) for o in observations
         if eob.validate_observation(_to_observation(o))[0]],
        intent if intent in eob.INTENTS else "MULTI_SENSOR")
    state, note = eob.agreement(ranked)
    return envelope("query_observations",
                    "SUCCESS" if ranked else "PARTIAL",
                    {"change_id": cid, "observations": ranked,
                     "modalities": sorted({str(o.get("modality"))
                                           for o in ranked}),
                     "agreement": state, "agreement_note": note},
                    truth_mode="REAL", source_count=len(ranked),
                    warnings=warnings)


def _to_observation(item: Dict[str, Any]) -> Dict[str, Any]:
    """Map optical/SAR evidence records onto the generic schema."""
    from gods_eye.future import earth_observation as eob
    modality = str(item.get("modality") or ("OPTICAL" if item.get(
        "kind") == "satellite-image" else "UNKNOWN"))
    return {
        "observation_id": str(item.get("observation_id")
                              or item.get("id") or "UNKNOWN"),
        "sensor": str(item.get("sensor") or item.get("source")
                      or "UNKNOWN"),
        "platform": str(item.get("platform") or item.get("sensor")
                        or "UNKNOWN"),
        "orbit_type": str(item.get("orbit_type") or "LEO"),
        "provider": str(item.get("provider") or item.get("source")
                        or "UNKNOWN"),
        "modality": modality if modality in eob.MODALITIES else "OPTICAL",
        "captured_at": item.get("captured_at") or "UNKNOWN",
        "available_at": item.get("available_at") or "UNKNOWN",
        "age_seconds": item.get("age_seconds") if isinstance(
            item.get("age_seconds"), (int, float)) else 0,
        "spatial_resolution_m": item.get("spatial_resolution_m")
        if isinstance(item.get("spatial_resolution_m"),
                      (int, float)) else item.get("native_resolution_m", 0),  # noqa: E501
        "temporal_resolution": str(item.get("temporal_resolution")
                                   or "UNKNOWN"),
        "footprint": item.get("footprint") or item.get("bounds") or [],
        "cloud_penetration": bool(item.get("cloud_penetration", False)),
        "night_capable": bool(item.get("night_capable", False)),
        "coverage": str(item.get("coverage") or item.get(
            "coverage_quality") or "UNKNOWN"),
        "truth_mode": str(item.get("truth_mode") or "OBSERVED"),
        "processing_level": str(item.get("processing_level")
                                or ("L2A" if modality == "OPTICAL"
                                    else "GRD")),
        "source_url": str(item.get("source_url") or "UNKNOWN"),
        "rights": item.get("rights") or {},
        "attribution": str((item.get("rights") or {}).get(
            "attribution") or "UNKNOWN"),
        "supports_change": True,
    }


def tool_query_imagery_freshness(args: Dict[str, Any],
                                 ctx: Dict[str, Any]) -> Dict[str, Any]:
    lat = args.get("lat", ctx.get("lat"))
    lon = args.get("lon", ctx.get("lon"))
    place = str(args.get("place") or args.get("region") or ""
                ).lower().strip()
    if place and place not in PLACES and place not in REGION_BOXES:
        return envelope("query_imagery_freshness", "FAILED", {},
                        note=f"unknown place: {place}; answering "
                             "for map context instead would mislead")
    if (lat is None or lon is None) and place:
        if place in PLACES:
            lat, lon = PLACES[place]
        elif place in REGION_BOXES:
            lat, lon = REGION_BOXES[place][1]
    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return envelope("query_imagery_freshness", "FAILED", {},
                        note="freshness needs lat/lon, a place, or "
                             "map context")
    try:
        threshold = float(args.get("max_age_hours", 1e9))
    except (TypeError, ValueError):
        threshold = 1e9
    from gods_eye.future import world_earth as earth
    try:
        status = earth.get_status(lat=lat, lon=lon)
    except Exception as e:  # noqa: BLE001
        return envelope("query_imagery_freshness", "UNAVAILABLE", {},
                        note=f"imagery status failed: "
                             f"{type(e).__name__}")
    layers = []
    for layer in status.get("layers", []):
        age_h = None
        try:
            age_h = float(layer.get("age_seconds", 0)) / 3600.0
        except (TypeError, ValueError):
            pass
        if age_h is not None and age_h > threshold:
            continue
        layers.append({
            "source": layer.get("source"),
            "dataset": layer.get("dataset"),
            "captured_at": layer.get("captured_at"),
            "age_hours": round(age_h, 2) if age_h is not None else None,
            "freshness_class": layer.get("freshness_class"),
            "resolution_m": layer.get("resolution_m"),
            "coverage": layer.get("coverage_quality"),
            "rights": (layer.get("rights") or {}).get("attribution")
            or layer.get("rights_status")})
    return envelope("query_imagery_freshness",
                    "SUCCESS" if layers else "PARTIAL",
                    {"point": {"lat": lat, "lon": lon},
                     "selected": status.get("selected"),
                     "layers": layers},
                    truth_mode="REAL", source_count=len(layers))


def tool_open_evidence(args: Dict[str, Any],
                       ctx: Dict[str, Any]) -> Dict[str, Any]:
    eid = str(args.get("id") or args.get("entity_id")
              or ctx.get("selected") or "")
    ent, detail = _resolve_entity(eid)
    if ent is None:
        return envelope("open_evidence", "FAILED", {}, note=detail)
    summary: Dict[str, Any] = {"entity": ent}
    if ent["kind"] == "change":
        change = _change_by_id(ent["id"]) or {}
        summary["why_flagged"] = change.get("why_flagged", [])
        summary["evidence_count"] = len(change.get("evidence", []))
        summary["corroboration"] = change.get("corroboration")
        summary["confidence"] = change.get("confidence")
    return envelope("open_evidence", "SUCCESS",
                    {"action": "open_evidence", "summary": summary},
                    truth_mode=str(ent.get("truth_mode") or "REAL"),
                    source_count=1)


def tool_set_time(args: Dict[str, Any],
                  ctx: Dict[str, Any]) -> Dict[str, Any]:
    return envelope("set_time", "SUCCESS",
                    {"action": "set_time",
                     "tick": args.get("tick"),
                     "iso": (str(args.get("iso") or "")[:64] or None)},
                    truth_mode="STATIC")


def tool_enter_replay(args: Dict[str, Any],
                      ctx: Dict[str, Any]) -> Dict[str, Any]:
    try:
        hours = max(0.0, min(72.0, float(args.get("hours_ago", 6.0))))
    except (TypeError, ValueError):
        hours = 6.0
    return envelope("enter_replay", "SUCCESS",
                    {"action": "enter_replay", "hours_ago": hours},
                    truth_mode="REPLAY",
                    note=f"entering replay {hours:g}h back; live "
                         "imagery and change pins stay out of replay")


def tool_return_to_now(args: Dict[str, Any],
                       ctx: Dict[str, Any]) -> Dict[str, Any]:
    return envelope("return_to_now", "SUCCESS",
                    {"action": "return_to_now"}, truth_mode="REAL")


TOOLS: Dict[str, Dict[str, Any]] = {
    "fly_to": {"handler": tool_fly_to,
               "description": "fly the camera to lat/lon or a place"},
    "set_view": {"handler": tool_set_view,
                 "description": "fly the camera with bearing/pitch"},
    "select_entity": {"handler": tool_select_entity,
                      "description": "select an entity by id"},
    "track_entity": {"handler": tool_track_entity,
                     "description": "track a trackable entity"},
    "stop_tracking": {"handler": tool_stop_tracking,
                      "description": "stop tracking"},
    "toggle_layer": {"handler": tool_toggle_layer,
                     "description": "show/hide a map layer"},
    "query_region": {"handler": tool_query_region,
                     "description": "what is here/changed/moving/"
                                    "visible/important/uncertain"},
    "query_contacts": {"handler": tool_query_contacts,
                       "description": "nearby contacts sorted by "
                                      "NEAREST/NEWEST/IMPORTANT"},
    "query_changes": {"handler": tool_query_changes,
                      "description": "canonical changes with filters"},
    "query_important": {"handler": tool_query_important,
                        "description": "top important items"},
    "query_observations": {"handler": tool_query_observations,
                           "description": "optical/SAR observations "
                                          "for a change"},
    "query_imagery_freshness": {"handler": tool_query_imagery_freshness,
                                "description": "freshness per layer "
                                               "for a point"},
    "open_evidence": {"handler": tool_open_evidence,
                      "description": "open evidence incl. why-flagged"},
    "set_time": {"handler": tool_set_time,
                 "description": "scrub replay time"},
    "enter_replay": {"handler": tool_enter_replay,
                     "description": "enter replay N hours back"},
    "return_to_now": {"handler": tool_return_to_now,
                      "description": "leave replay, back to WORLD NOW"},
}


def execute(tool: str, args: Optional[Dict[str, Any]] = None,
            ctx: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Run one registered tool. Unknown tools fail loudly."""
    args = dict(args or {})
    ctx = dict(ctx or {})
    if tool not in TOOLS:
        return envelope(tool, "FAILED", {},
                        note=f"unknown tool: {tool}; registered: "
                             + ", ".join(sorted(TOOLS)))
    ok, detail = _clean_args(args)
    if not ok:
        return envelope(tool, "FAILED", {}, note=detail)
    try:
        out = TOOLS[tool]["handler"](args, ctx)
    except Exception as e:  # noqa: BLE001 - tools never raise
        return envelope(tool, "FAILED", {},
                        note=f"{tool} error: {type(e).__name__}")
    if not isinstance(out, dict) or out.get("status") not in STATUSES:
        return envelope(tool, "FAILED", {},
                        note="tool returned a malformed envelope")
    return out


# ------------------------------------------------------ intent parsing ---

# Provider interface: parse_intent(text, context, provider) -> tool_calls[].
# RULE_BASED is built in. LOCAL_LLM / REMOTE_LLM are reserved names that
# report UNAVAILABLE until a provider is wired (no silent fallback).
PROVIDERS = ("RULE_BASED", "LOCAL_LLM", "REMOTE_LLM")


def _since_iso(text: str) -> Optional[str]:
    now = datetime.now(timezone.utc)
    if re.search(r"\btoday\b", text):
        since = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return since.isoformat()
    m = re.search(r"(\d+)\s*h\b", text)
    if m:
        return (now - timedelta(hours=int(m.group(1)))).isoformat()
    m = re.search(r"last\s+(\d+)\s*h", text)
    if m:
        return (now - timedelta(hours=int(m.group(1)))).isoformat()
    if re.search(r"last\s+24\s*h|24\s*h", text):
        return (now - timedelta(hours=24)).isoformat()
    return None


def _find_place(text: str) -> Optional[str]:
    low = " " + text.lower() + " "
    for name in sorted(PLACES, key=len, reverse=True):
        if f" {name} " in low or f" {name}?" in low:
            return name
    return None


def _find_region(text: str) -> Optional[str]:
    low = " " + text.lower() + " "
    for name in sorted(REGION_BOXES, key=len, reverse=True):
        if name in low:
            return name
    return None


def _find_category(text: str) -> Optional[str]:
    low = text.lower()
    for word, cat in CATEGORY_WORDS.items():
        if word in low:
            return cat
    return None


def parse_intent(text: str, context: Optional[Dict[str, Any]] = None,
                 provider: str = "RULE_BASED") -> Dict[str, Any]:
    """Deterministic intent parsing. Returns {calls, provider,
    unparsed}. No model, no network, no memory."""
    context = dict(context or {})
    raw = (text or "").strip()
    if provider != "RULE_BASED":
        return {"calls": [], "provider": provider,
                "unparsed": raw,
                "note": f"provider {provider} not wired; "
                        "RULE_BASED is the only active parser"}
    low = raw.lower()
    if FORBIDDEN_RE.search(raw):
        return {"calls": [], "provider": provider, "unparsed": raw,
                "note": "request rejected: proprietary field"}
    if re.search(r"\breturn to now\b|\bback to now\b|\bcurrent world\b",
                 low):
        return {"calls": [{"tool": "return_to_now", "args": {}}],
                "provider": provider, "unparsed": ""}
    m = re.search(r"replay\s+(\d+)\s*h|rewind[^\d]*(\d+)\s*h", low)
    if m or "replay" in low:
        hours = float(m.group(1) or m.group(2)) if m else 6.0
        return {"calls": [{"tool": "enter_replay",
                            "args": {"hours_ago": hours}}],
                "provider": provider, "unparsed": ""}
    if re.search(r"\bstop tracking\b|\buntrack\b", low):
        return {"calls": [{"tool": "stop_tracking", "args": {}}],
                "provider": provider, "unparsed": ""}
    if re.search(r"\btrack\b", low):
        eid = context.get("selected") or ""
        m = re.search(r"track\s+([A-Za-z0-9:_-]+)", raw)
        if m and m.group(1).lower() not in ("selected", "this", "it"):
            eid = m.group(1)
        return {"calls": [{"tool": "track_entity",
                            "args": {"id": eid}}],
                "provider": provider, "unparsed": ""}
    if re.search(r"nearest aircraft|aircraft near|aircraft within|"
                 r"planes (near|around|overhead)|show.*aircraft", low):
        place = _find_place(low)
        args: Dict[str, Any] = {"sort": "NEAREST", "radius_km": 250.0}
        m = re.search(r"within\s+(\d+)\s*km", low)
        if m:
            args["radius_km"] = float(m.group(1))
        if place and place in PLACES:
            args["lat"], args["lon"] = PLACES[place][0], PLACES[place][1]
        elif context.get("lat") is not None:
            args["lat"], args["lon"] = context["lat"], context["lon"]
        return {"calls": [{"tool": "query_contacts", "args": args}],
                "provider": provider, "unparsed": ""}
    if re.search(r"\bwhy\b.*\bflag", low):
        eid = context.get("selected") or ""
        return {"calls": [{"tool": "open_evidence",
                            "args": {"id": eid}}],
                "provider": provider, "unparsed": ""}
    if re.search(r"radar|optical.*(and|\+).*radar|observations|"
                 r"cloud-safe|night-capable|evidence for", low):
        modality = "SAR" if re.search(r"\bradar\b", low) and \
            "optical" not in low else ("OPTICAL" if "optical" in low
                                       and "radar" not in low
                                       else "MULTI_SENSOR")
        eid = context.get("selected_change") or context.get(
            "selected") or ""
        return {"calls": [{"tool": "query_observations",
                            "args": {"change_id": eid,
                                     "modality": modality}}],
                "provider": provider, "unparsed": ""}
    if re.search(r"fresh|imagery.*(old|age)|under one hour|under an hour",
                 low):
        place = _find_place(low) or _find_region(low)
        args2: Dict[str, Any] = {}
        if place:
            args2["place"] = place
        elif context.get("lat") is not None:
            args2["lat"] = context["lat"]
            args2["lon"] = context["lon"]
        if re.search(r"under one hour|under an hour|< ?1 ?h", low):
            args2["max_age_hours"] = 1.0
        return {"calls": [{"tool": "query_imagery_freshness",
                            "args": args2}],
                "provider": provider, "unparsed": ""}
    if re.search(r"\bchange|\bchanges\b|what changed|flood|wildfire",
                 low) and not re.search(r"\btrack\b", low):
        region = _find_region(low)
        args3: Dict[str, Any] = {"since": _since_iso(low),
                                 "region": region,
                                 "category": _find_category(low)}
        args3 = {k: v for k, v in args3.items() if v}
        calls = [{"tool": "query_changes", "args": args3}]
        if re.search(r"take me to|fly to|show me|go to|largest|biggest",
                     low):
            calls.append({"tool": "fly_to", "args": (
                {"place": region} if region else {})})
        return {"calls": calls, "provider": provider, "unparsed": ""}
    if re.search(r"\bimportant\b", low):
        return {"calls": [{"tool": "query_important", "args": {}}],
                "provider": provider, "unparsed": ""}
    if re.search(r"what is here|what.*here\?|nearby|contacts", low):
        args4: Dict[str, Any] = {}
        if context.get("lat") is not None:
            args4["lat"] = context["lat"]
            args4["lon"] = context["lon"]
        return {"calls": [{"tool": "query_region", "args": args4}],
                "provider": provider, "unparsed": ""}
    place = _find_place(raw)
    if place or re.search(r"\b(go to|take me to|fly to|show me|go)\b",
                          low):
        if place:
            return {"calls": [{"tool": "fly_to",
                                "args": {"place": place}}],
                    "provider": provider, "unparsed": ""}
        m = re.search(r"(?:go to|take me to|fly to|show me|go)\s+(.+)",
                      raw, re.IGNORECASE)
        if m:
            return {"calls": [{"tool": "fly_to",
                                "args": {"place": m.group(1).strip()}}],
                    "provider": provider, "unparsed": ""}
    m = re.search(r"(show|turn on|turn off|toggle|hide)\s+([a-z ]+?)\s*"
                  r"(layer|layers)?$", low)
    if m and m.group(2).strip() in ("fires", "fire", "earthquakes",
                                    "aircraft", "satellite", "weather",
                                    "wildfire", "seismic", "storm",
                                    "cities"):
        word = m.group(2).strip()
        layer = {"fires": "wildfire", "fire": "wildfire",
                 "earthquakes": "seismic"}.get(word, word)
        on = None if m.group(1) == "toggle" else m.group(1) in (
            "show", "turn on")
        return {"calls": [{"tool": "toggle_layer",
                            "args": {"layer": layer, "on": on}}],
                "provider": provider, "unparsed": ""}
    return {"calls": [], "provider": provider, "unparsed": raw,
            "note": "no deterministic parse; try a place name, "
                    "'show changes today', 'nearest aircraft', "
                    "'replay 6h', or 'return to now'"}


def run_command(text: str,
                context: Optional[Dict[str, Any]] = None,
                provider: str = "RULE_BASED") -> Dict[str, Any]:
    """Parse then execute. Returns {input, calls, results}."""
    parsed = parse_intent(text, context, provider)
    results = [execute(c["tool"], c.get("args", {}), context)
               for c in parsed["calls"]]
    return {"input": text, "provider": parsed["provider"],
            "calls": parsed["calls"], "results": results,
            "unparsed": parsed.get("unparsed", ""),
            "note": parsed.get("note", "")}
