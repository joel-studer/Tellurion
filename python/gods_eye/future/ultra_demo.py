"""FUTURE-ONLY Ultra synthetic world (V18, CC0, deterministic, offline).

Seeded multi-sensor replay for the Ultra surface: aircraft, vessels,
satellite scenes, weather, wildfire, seismic, traffic, cameras, ports,
airports, infrastructure, notices, and two hero stories. No network,
no keys, no live claims — every object carries provenance +
observation state + rights.

Determinism: same (seed, tick) -> identical payload (JSON-stable).
"""

from __future__ import annotations

import math
import random
from typing import Any, Dict, List

DATASET_ID = "ultra-demo-v1"
LICENSE = "CC0-1.0 (synthetic)"
PROVENANCE = "Tellurion synthetic generator (seeded, deterministic)"
RIGHTS = "CC0: generated in-repo, no persons, no scraped rows"

# Synthetic demo geography (fictional harbour city + airfield).
HARBOR = {"name": "Port Meridian", "lat": 51.42, "lon": -3.18}
AIRFIELD = {"name": "Meridian Field", "lat": 51.55, "lon": -3.02}


def _rng(seed: int) -> random.Random:
    return random.Random(10_000 + seed)


def _drift(rng: random.Random, lat: float, lon: float,
           scale: float = 0.05) -> tuple[float, float]:
    return (round(lat + rng.uniform(-scale, scale), 4),
            round(lon + rng.uniform(-scale, scale), 4))


def _placed(rng: random.Random, lat: float, lon: float, scale: float,
            on_land: bool, anchor: tuple[float, float]) -> tuple[float, float]:
    """Drift around (lat, lon) until the point is on land or on water.

    Uses the Natural Earth land mask when it ships with the checkout, so
    synthetic vessels never sit on real land and roads never sit at sea.
    Falls back to the unconstrained drift when the data file is absent.
    """
    from gods_eye.future import geo
    mask = geo.land_mask()
    point = _drift(rng, lat, lon, scale)
    if mask is None:
        return point
    for _ in range(60):
        if mask.is_land(*point) == on_land:
            return point
        point = _drift(rng, lat, lon, scale)
    return anchor


def aircraft(seed: int = 7, n: int = 24,
             tick: int = 0) -> List[Dict[str, Any]]:
    rng = _rng(seed)
    out = []
    for i in range(n):
        lat, lon = _drift(rng, AIRFIELD["lat"], AIRFIELD["lon"], 0.9)
        hdg = rng.randint(0, 359)
        spd = rng.randint(180, 480)
        alt = rng.choice([3000, 8000, 15000, 28000, 35000, 41000])
        # replay motion: advance along heading with tick
        dist = tick * spd / 3600.0 / 60.0  # degrees-ish per tick step
        lat2 = round(lat + dist * math.cos(math.radians(hdg)), 4)
        lon2 = round(lon + dist * math.sin(math.radians(hdg)), 4)
        out.append({
            "id": f"SYN-AC{i:03d}", "callsign": f"GDU{i:03d}",
            "lat": lat2, "lon": lon2, "alt_ft": alt,
            "speed_kt": spd, "heading": hdg,
            "trail": [[lat, lon], [lat2, lon2]],
            "source_ts": f"demo-t{tick}", "precision": "APPROXIMATE",
            "provenance": PROVENANCE, "rights": RIGHTS,
            "observation": "OBSERVED", "freshness": "replay",
        })
    return out


def vessels(seed: int = 11, n: int = 18,
            tick: int = 0) -> List[Dict[str, Any]]:
    rng = _rng(seed)
    states = ["UNDERWAY", "ANCHORED", "MOORED"]
    out = []
    for i in range(n):
        lat, lon = _placed(rng, HARBOR["lat"], HARBOR["lon"], 0.5, False,
                           (HARBOR["lat"], HARBOR["lon"]))
        out.append({
            "id": f"SYN-VS{i:03d}", "name": f"Meridian Trader {i}",
            "lat": lat, "lon": lon,
            "speed_kt": round(rng.uniform(0, 18), 1),
            "course": rng.randint(0, 359),
            "nav_state": rng.choice(states),
            "source_ts": f"demo-t{tick}", "precision": "APPROXIMATE",
            "provenance": PROVENANCE, "rights": RIGHTS,
            "observation": "OBSERVED", "freshness": "replay",
        })
    return out


def satellite_scenes(seed: int = 21, n: int = 6) -> List[Dict[str, Any]]:
    rng = _rng(seed)
    out = []
    for i in range(n):
        lat, lon = _drift(rng, HARBOR["lat"], HARBOR["lon"], 0.8)
        d = 0.12
        out.append({
            "id": f"SYN-SAT{i:02d}", "platform": "SYN-SAT-1",
            "scene_id": f"SYN_SCENE_{i:03d}",
            "acquired": f"2026-09-1{i % 9}T10:00:00Z",
            "footprint": [[lat - d, lon - d], [lat - d, lon + d],
                          [lat + d, lon + d], [lat + d, lon - d]],
            "cloud_cover_pct": rng.randint(0, 40),
            "sensor": "SYN-MSI", "resolution_m": 10,
            "provenance": PROVENANCE, "rights": RIGHTS,
            "observation": "OBSERVED",
        })
    return out


def weather(seed: int = 31, n_cells: int = 8) -> Dict[str, Any]:
    rng = _rng(seed)
    cells = []
    for i in range(n_cells):
        lat, lon = _drift(rng, HARBOR["lat"], HARBOR["lon"], 0.7)
        cells.append({"id": f"SYN-WX{i:02d}", "lat": lat, "lon": lon,
                      "radius_km": rng.randint(8, 40),
                      "wind_kt": rng.randint(15, 70),
                      "precip_mm_h": round(rng.uniform(0, 25), 1),
                      "observation": "INFERRED",
                      "provenance": PROVENANCE, "rights": RIGHTS})
    alerts = [{
        "id": "SYN-ALERT-01", "kind": "SEVERE_WEATHER",
        "title": "Severe gale warning — Port Meridian approaches",
        "polygon": [[51.2, -3.5], [51.2, -2.9], [51.7, -2.9], [51.7, -3.5]],
        "valid_from": "demo-T0", "valid_to": "demo-T+6h",
        "source": "synthetic met office", "observation": "INFERRED",
        "provenance": PROVENANCE, "rights": RIGHTS}]
    return {"cells": cells, "alerts": alerts}


def wildfires(seed: int = 41, n: int = 4) -> List[Dict[str, Any]]:
    rng = _rng(seed)
    out = []
    for i in range(n):
        lat, lon = _placed(rng, 51.9, -2.6, 0.4, True, (51.9, -2.6))
        out.append({"id": f"SYN-FIRE{i:02d}", "lat": lat, "lon": lon,
                    "confidence": rng.choice(["LOW", "NOMINAL", "HIGH"]),
                    "observed": f"demo-T+{i}h", "sensor": "SYN-VIIRS",
                    "observation": "OBSERVED",
                    "provenance": PROVENANCE, "rights": RIGHTS})
    return out


def seismic(seed: int = 51, n: int = 5) -> List[Dict[str, Any]]:
    rng = _rng(seed)
    out = []
    for i in range(n):
        lat, lon = _drift(rng, 51.0, -4.2, 0.6)
        out.append({"id": f"SYN-EQ{i:02d}",
                    "mag": round(rng.uniform(2.5, 5.8), 1),
                    "depth_km": round(rng.uniform(5, 60), 1),
                    "lat": lat, "lon": lon,
                    "precision": "REGIONAL",
                    "event_time": f"demo-T-{i}h",
                    "observation": "OBSERVED",
                    "provenance": PROVENANCE, "rights": RIGHTS})
    return out


def road_incidents(seed: int = 61, n: int = 12) -> List[Dict[str, Any]]:
    rng = _rng(seed)
    kinds = ["CLOSURE", "CONGESTION", "WORKS", "DELAY"]
    out = []
    for i in range(n):
        lat, lon = _placed(rng, HARBOR["lat"], HARBOR["lon"], 0.35, True,
                           (AIRFIELD["lat"], AIRFIELD["lon"]))
        out.append({"id": f"SYN-RD{i:02d}", "kind": rng.choice(kinds),
                    "lat": lat, "lon": lon,
                    "severity": rng.randint(1, 5),
                    "reported": f"demo-T+{i % 4}h",
                    "observation": "OBSERVED",
                    "provenance": PROVENANCE, "rights": RIGHTS})
    return out


def cameras(seed: int = 71, n: int = 6) -> List[Dict[str, Any]]:
    rng = _rng(seed)
    out = []
    for i in range(n):
        lat, lon = _placed(rng, HARBOR["lat"], HARBOR["lon"], 0.25, True,
                           (AIRFIELD["lat"], AIRFIELD["lon"]))
        out.append({"id": f"SYN-CAM{i:02d}", "lat": lat, "lon": lon,
                    "operator": "synthetic roads authority",
                    "feed": "snapshot", "last_update": f"demo-T+{i}m",
                    "status": "OK" if i % 3 else "STALE",
                    "rights": RIGHTS, "provenance": PROVENANCE,
                    "observation": "OBSERVED"})
    return out


def public_osint(seed: int = 81) -> List[Dict[str, Any]]:
    """Public-source observations only (NOTAMs, exercise areas, notices).

    Every object carries OBSERVED + source + timestamp + precision +
    rights. No tracking, no targeting, no protected communications.
    """
    del seed
    return [
        {"id": "SYN-NOTAM-01", "kind": "NOTAM",
         "title": "Aerodrome advisory — crane ops near Meridian Field",
         "lat": AIRFIELD["lat"], "lon": AIRFIELD["lon"],
         "issued": "demo-T+6m", "precision": "APPROXIMATE",
         "observation": "OBSERVED", "confidence": "official notice",
         "provenance": "synthetic aerodrome notice (public-shape)",
         "rights": RIGHTS},
        {"id": "SYN-EXER-01", "kind": "EXERCISE_REGION",
         "title": "Published naval exercise area (offshore, dated)",
         "polygon": [[50.6, -5.4], [50.6, -4.6], [51.1, -4.6], [51.1, -5.4]],
         "lat": 50.85, "lon": -5.0, "issued": "demo-T0",
         "precision": "REGIONAL", "observation": "OBSERVED",
         "confidence": "official notice",
         "provenance": "synthetic maritime notice (public-shape)",
         "rights": RIGHTS},
        {"id": "SYN-PROC-01", "kind": "PROCUREMENT",
         "title": "Harbour board publishes dredging tender",
         "lat": HARBOR["lat"], "lon": HARBOR["lon"],
         "issued": "demo-T-2d", "precision": "REGIONAL",
         "observation": "OBSERVED", "confidence": "official notice",
         "provenance": "synthetic procurement notice (public-shape)",
         "rights": RIGHTS},
    ]


def entities() -> List[Dict[str, Any]]:
    """Bounded public-safe entity set for the graph view."""
    return [
        {"id": "ENT-PORT", "kind": "PORT", "label": "Port Meridian",
         "lat": HARBOR["lat"], "lon": HARBOR["lon"]},
        {"id": "ENT-APT", "kind": "AIRPORT", "label": "Meridian Field",
         "lat": AIRFIELD["lat"], "lon": AIRFIELD["lon"]},
        {"id": "ENT-VS002", "kind": "VESSEL", "label": "Meridian Trader 2",
         "lat": HARBOR["lat"], "lon": HARBOR["lon"]},
        {"id": "ENT-AC001", "kind": "AIRCRAFT", "label": "GDU001",
         "lat": AIRFIELD["lat"], "lon": AIRFIELD["lon"]},
        {"id": "ENT-SAT00", "kind": "SATELLITE", "label": "SYN-SAT-1",
         "lat": None, "lon": None},
        {"id": "ENT-HARBOUR-BOARD", "kind": "GOVERNMENT",
         "label": "Meridian Harbour Board", "lat": None, "lon": None},
        {"id": "ENT-ESTUARY", "kind": "REGION", "label": "Meridian Estuary",
         "lat": 51.45, "lon": -3.1},
        {"id": "ENT-STORM", "kind": "EVENT",
         "label": "Severe weather near Port Meridian",
         "lat": 51.45, "lon": -3.2},
        {"id": "ENT-SYNTH-FEED", "kind": "SOURCE",
         "label": "Synthetic replay feed", "lat": None, "lon": None},
    ]


def relations() -> List[Dict[str, Any]]:
    """Bounded typed relations (effective time + evidence + method)."""
    return [
        {"src": "ENT-STORM", "dst": "ENT-PORT", "type": "THREATENS",
         "effective": "demo-T0", "evidence": "SYN-ALERT-01",
         "source": PROVENANCE, "confidence": "demo-fixed",
         "method": "hero-timeline-link"},
        {"src": "ENT-VS002", "dst": "ENT-PORT", "type": "CALLS_AT",
         "effective": "demo-T+4m", "evidence": "SYN-VS002",
         "source": PROVENANCE, "confidence": "demo-fixed",
         "method": "fixture-schedule"},
        {"src": "ENT-AC001", "dst": "ENT-APT", "type": "HOLDS_FOR",
         "effective": "demo-T+3m", "evidence": "SYN-AC001",
         "source": PROVENANCE, "confidence": "demo-fixed",
         "method": "hero-timeline-link"},
        {"src": "ENT-SAT00", "dst": "ENT-ESTUARY", "type": "IMAGED",
         "effective": "demo-T+8m", "evidence": "SYN-SAT00",
         "source": PROVENANCE, "confidence": "demo-fixed",
         "method": "footprint-overlap"},
        {"src": "ENT-HARBOUR-BOARD", "dst": "ENT-PORT", "type": "OPERATES",
         "effective": "demo-T-2d", "evidence": "SYN-PROC-01",
         "source": PROVENANCE, "confidence": "demo-fixed",
         "method": "public-notice"},
        {"src": "ENT-SYNTH-FEED", "dst": "ENT-STORM", "type": "REPORTS",
         "effective": "demo-T0", "evidence": "SYN-ALERT-01",
         "source": PROVENANCE, "confidence": "demo-fixed",
         "method": "fixture-generation"},
    ]


def hero_story_earth_event() -> Dict[str, Any]:
    """Hero 3: offshore earthquake (proves non-aviation breadth)."""
    return {
        "id": "HERO-EARTH", "title": "Offshore earthquake — response picture",
        "steps": [
            {"at": "T0", "layer": "SEISMIC",
             "text": "M5.2 offshore event recorded",
             "ref": "SYN-EQ00"},
            {"at": "T+2m", "layer": "DISASTER",
             "text": "Event bulletin published (open bulletin)",
             "ref": "SYN-EQ00"},
            {"at": "T+5m", "layer": "SATELLITE",
             "text": "Tasked overpass footprint covers epicentre",
             "ref": "SYN-SAT01"},
            {"at": "T+8m", "layer": "TRAFFIC",
             "text": "Coast-road precautionary closures",
             "ref": "SYN-RD02"},
            {"at": "T+11m", "layer": "INFRASTRUCTURE",
             "text": "Grid + port integrity checks, all nominal",
             "ref": "SYN-GRID-01"},
        ],
        "blind_spots": ["offshore sensor fringe (sparse)",
                        "rural road sensors (sparse)"],
        "observation": "CORROBORATED", "rights": RIGHTS,
        "provenance": PROVENANCE,
    }


def hero_story_port_storm() -> Dict[str, Any]:
    """Hero 1: severe weather near a major port (deterministic timeline)."""
    return {
        "id": "HERO-PORT-STORM", "title": "Severe weather near Port Meridian",
        "steps": [
            {"at": "T0", "layer": "WEATHER",
             "text": "Gale warning issued for the approaches",
             "ref": "SYN-ALERT-01"},
            {"at": "T+2m", "layer": "TRAFFIC",
             "text": "Coast-road congestion builds (3 segments)",
             "ref": "SYN-RD00"},
            {"at": "T+4m", "layer": "MARITIME",
             "text": "Inbound vessels hold; 2 anchor",
             "ref": "SYN-VS002"},
            {"at": "T+5m", "layer": "PUBLIC_CAMERA",
             "text": "Harbour camera snapshot refreshes",
             "ref": "SYN-CAM00"},
            {"at": "T+8m", "layer": "SATELLITE",
             "text": "Overpass footprint covers the estuary",
             "ref": "SYN-SAT00"},
            {"at": "T+10m", "layer": "GOVERNMENT",
             "text": "Harbour notice: berth delays expected",
             "ref": "SYN-NOTICE-01"},
            {"at": "T+12m", "layer": "INFRASTRUCTURE",
             "text": "Grid zone on storm watch; no outage",
             "ref": "SYN-GRID-01"},
        ],
        "blind_spots": ["open-sea vessel fringe (no receiver)",
                        "rural road sensors (sparse)"],
        "observation": "CORROBORATED", "rights": RIGHTS,
        "provenance": PROVENANCE,
    }


def hero_story_airport_event() -> Dict[str, Any]:
    """Hero 2: airspace event at the regional airport."""
    return {
        "id": "HERO-AIRPORT", "title": "Holding pattern over Meridian Field",
        "steps": [
            {"at": "T0", "layer": "WEATHER",
             "text": "Low-visibility cell over the field",
             "ref": "SYN-WX00"},
            {"at": "T+3m", "layer": "AIRCRAFT",
             "text": "4 arrivals enter holding pattern",
             "ref": "SYN-AC001"},
            {"at": "T+6m", "layer": "GOVERNMENT",
             "text": "Public aerodrome notice published",
             "ref": "SYN-NOTICE-02"},
            {"at": "T+9m", "layer": "TRAFFIC",
             "text": "Airport access road congested",
             "ref": "SYN-RD04"},
        ],
        "blind_spots": ["general-aviation transponders (unequipped)"],
        "observation": "CORROBORATED", "rights": RIGHTS,
        "provenance": PROVENANCE,
    }


def density_scene() -> Dict[str, Any]:
    """Deterministic load scene for renderer validation (counts only)."""
    return {"aircraft": aircraft(seed=7, n=500),
            "vessels": vessels(seed=11, n=300),
            "weather_cells": weather(seed=31, n_cells=50)["cells"],
            "road": road_incidents(seed=61, n=100),
            "satellite": satellite_scenes(seed=21, n=30),
            "seismic": seismic(seed=51, n=20),
            "counts": {"aircraft": 500, "vessels": 300, "weather": 50,
                       "road": 100, "satellite": 30, "seismic": 20,
                       "total": 1000}}


def _near(lat: float, lon: float, items: List[Dict[str, Any]],
          radius: float = 0.3, limit: int = 5) -> List[Dict[str, Any]]:
    scored = sorted(items,
                    key=lambda o: abs(o.get("lat", 0) - lat)
                    + abs(o.get("lon", 0) - lon))
    return [{"id": o.get("id"), "layer_hint": True,
             "observation": o.get("observation", "UNKNOWN")}
            for o in scored[:limit]
            if abs(o.get("lat", 0) - lat)
            + abs(o.get("lon", 0) - lon) <= radius]


def context_for(lat: float, lon: float,
                tick: int = 0) -> Dict[str, Any]:
    """Cross-sensor context: descriptive proximity only (no inference)."""
    ac = aircraft(tick=tick)
    vs = vessels(tick=tick)
    wx = weather()["cells"]
    rd = road_incidents()
    return {"at": {"lat": lat, "lon": lon},
            "nearby_aircraft": _near(lat, lon, ac),
            "nearby_vessels": _near(lat, lon, vs),
            "nearby_weather": _near(lat, lon, wx, radius=0.5),
            "nearby_road": _near(lat, lon, rd),
            "note": "proximity only; not corroboration",
            "observation": "INFERRED"}


def evidence_for(obj_type: str, obj_id: str,
                 tick: int = 0) -> Dict[str, Any]:
    """Evidence-first record for any demo object id.

    Dense-scene ids (SYN-AC100+, SYN-VS100+) resolve deterministically
    by regenerating the seeded series — same generator, same result.
    """
    import re
    pool: Dict[str, Any] = {}
    for o in aircraft(tick=tick) + vessels(tick=tick):
        pool[o["id"]] = o
    m = re.fullmatch(r"SYN-AC(\d+)", obj_id or "")
    if m and obj_id not in pool:
        idx = int(m.group(1))
        if 0 <= idx < 5000:
            pool[obj_id] = aircraft(seed=7, n=idx + 1, tick=tick)[idx]
    m = re.fullmatch(r"SYN-VS(\d+)", obj_id or "")
    if m and obj_id not in pool:
        idx = int(m.group(1))
        if 0 <= idx < 3000:
            pool[obj_id] = vessels(seed=11, n=idx + 1, tick=tick)[idx]
    for o in satellite_scenes() + wildfires() + seismic() + \
            road_incidents() + cameras():
        pool[o["id"]] = o
    for a in weather()["alerts"]:
        poly = a.get("polygon") or []
        lat = sum(p[0] for p in poly) / len(poly) if poly else HARBOR["lat"]
        lon = sum(p[1] for p in poly) / len(poly) if poly else HARBOR["lon"]
        pool[a["id"]] = {**a, "lat": round(lat, 4), "lon": round(lon, 4),
                         "source_ts": a.get("valid_from"),
                         "precision": "REGIONAL",
                         "rights": RIGHTS, "provenance": PROVENANCE}
    for c in weather()["cells"]:
        pool[c["id"]] = {**c, "source_ts": "demo-t0", "precision": "REGIONAL",
                         "rights": RIGHTS}
    pool["SYN-PORT-01"] = {"id": "SYN-PORT-01", **HARBOR,
                           "source_ts": "demo-t0", "observation": "OBSERVED",
                           "provenance": PROVENANCE, "rights": RIGHTS}
    pool["SYN-APT-01"] = {"id": "SYN-APT-01", **AIRFIELD,
                          "source_ts": "demo-t0", "observation": "OBSERVED",
                          "provenance": PROVENANCE, "rights": RIGHTS}
    pool["SYN-NOTICE-01"] = {"id": "SYN-NOTICE-01",
                             "lat": HARBOR["lat"], "lon": HARBOR["lon"],
                             "source_ts": "demo-T+10m",
                             "observation": "OBSERVED",
                             "provenance": PROVENANCE, "rights": RIGHTS}
    pool["SYN-NOTICE-02"] = {"id": "SYN-NOTICE-02",
                             "lat": AIRFIELD["lat"], "lon": AIRFIELD["lon"],
                             "source_ts": "demo-T+6m",
                             "observation": "OBSERVED",
                             "provenance": PROVENANCE, "rights": RIGHTS}
    pool["SYN-GRID-01"] = {"id": "SYN-GRID-01",
                           "lat": HARBOR["lat"], "lon": HARBOR["lon"],
                           "source_ts": "demo-T+12m",
                           "observation": "INFERRED",
                           "provenance": PROVENANCE, "rights": RIGHTS}
    for o in public_osint():
        pool[o["id"]] = {**o, "source_ts": o.get("issued"),
                         "rights": RIGHTS,
                         "provenance": o.get("provenance", PROVENANCE)}
    o = pool.get(obj_id, {})
    lat, lon = o.get("lat"), o.get("lon")
    if (lat is None or lon is None) and isinstance(o.get("footprint"),
                                                  list) and o["footprint"]:
        pts = o["footprint"]
        lat = round(sum(p[0] for p in pts) / len(pts), 4)
        lon = round(sum(p[1] for p in pts) / len(pts), 4)
    return {"what": f"{obj_type} {obj_id}",
            "where": {"lat": lat, "lon": lon},
            "when": o.get("source_ts") or o.get("observed")
            or o.get("event_time") or o.get("acquired"),
            "first_seen": "demo-t0",
            "source": o.get("provenance", PROVENANCE),
            "rights": o.get("rights", RIGHTS),
            "raw_vs_normalized": "fixture == normalized (synthetic)",
            "observation": o.get("observation", "UNKNOWN"),
            "confidence": "demo-fixed",
            "precision": o.get("precision", "APPROXIMATE"),
            "corroboration": "single synthetic source; see hero stories "
                             "for multi-source examples",
            "contradictions": "none in demo",
            "blind_spots": ["fringe coverage", "unequipped craft"]}


def ultra_payload(tick: int = 0, n_ac: int = 24,
                  n_vs: int = 18) -> Dict[str, Any]:
    wx = weather()
    return {
        "dataset_id": DATASET_ID, "license": LICENSE,
        "provenance": PROVENANCE, "rights": RIGHTS, "tick": tick,
        "harbor": HARBOR, "airfield": AIRFIELD,
        "aircraft": aircraft(tick=tick, n=n_ac),
        "vessels": vessels(tick=tick, n=n_vs),
        "satellite": satellite_scenes(),
        "weather": wx,
        "wildfire": wildfires(),
        "seismic": seismic(),
        "road": road_incidents(),
        "cameras": cameras(),
        "ports": [{"id": "SYN-PORT-01", **HARBOR,
                   "observation": "OBSERVED", "provenance": PROVENANCE,
                   "rights": RIGHTS}],
        "airports": [{"id": "SYN-APT-01", **AIRFIELD,
                      "observation": "OBSERVED", "provenance": PROVENANCE,
                      "rights": RIGHTS}],
        "notices": [
            {"id": "SYN-NOTICE-01", "title": "Berth delays expected",
             "observation": "OBSERVED"},
            {"id": "SYN-NOTICE-02", "title": "Aerodrome visibility notice",
             "observation": "OBSERVED"}],
        "osint": public_osint(),
        "entities": entities(),
        "relations": relations(),
        "heroes": [hero_story_port_storm(), hero_story_airport_event(),
                   hero_story_earth_event()],
        "community_mode": True, "live": False,
    }
