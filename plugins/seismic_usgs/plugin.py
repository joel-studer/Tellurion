"""Seismic sensor (fixture default; optional USGS live leg, user opt-in).

Default poll() serves the bundled CC0 fixture (offline). The live leg
is a pure function over USGS GeoJSON text the *caller* supplies —
this module never fetches, keeping the base demo keyless/offline.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

_HERE = Path(__file__).resolve().parent


def declaration() -> Dict[str, Any]:
    return json.loads((_HERE / "manifest.json").read_text(encoding="utf-8"))


def from_usgs_geojson(text: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Map a USGS GeoJSON FeatureCollection (caller-fetched) to events."""
    data = json.loads(text)
    out = []
    for f in (data.get("features") or [])[:limit]:
        props = f.get("properties", {}) or {}
        geom = f.get("geometry", {}) or {}
        coords = geom.get("coordinates") or [None, None, None]
        out.append({"id": str(f.get("id") or props.get("code") or "UNKNOWN"),
                    "mag": props.get("mag"), "place": props.get("place"),
                    "lon": coords[0], "lat": coords[1],
                    "depth_km": coords[2], "event_time": props.get("time"),
                    "observation": "OBSERVED",
                    "provenance": "USGS Earthquake Hazards Program",
                    "rights": "US public domain"})
    return out


class SeismicUsgs:
    kind = "Sensor"

    def poll(self) -> Dict[str, Any]:
        fixture = json.loads((_HERE / "fixture.json").read_text(encoding="utf-8"))
        return {"items": fixture["items"],
                "provenance": declaration()["provenance"],
                "rights": declaration()["data_rights"]}
