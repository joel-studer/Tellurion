"""Infrastructure context sensor (first-party community plugin, offline).

Static public-shape reference points: port, airport, grid watch zone.
No restricted infrastructure datasets; locations are synthetic.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

_HERE = Path(__file__).resolve().parent


def declaration() -> Dict[str, Any]:
    return json.loads((_HERE / "manifest.json").read_text(encoding="utf-8"))


class InfraContext:
    kind = "Sensor"

    def poll(self) -> Dict[str, Any]:
        import sys
        sys.path.insert(0, str(_HERE / ".." / ".." / "python"))
        from gods_eye.future import ultra_demo as _u
        p = _u.ultra_payload(tick=0)
        return {"items": [
                    {"ref": "SYN-PORT-01", "kind": "PORT",
                     "label": _u.HARBOR["name"], "lat": _u.HARBOR["lat"],
                     "lon": _u.HARBOR["lon"]},
                    {"ref": "SYN-APT-01", "kind": "AIRPORT",
                     "label": _u.AIRFIELD["name"], "lat": _u.AIRFIELD["lat"],
                     "lon": _u.AIRFIELD["lon"]},
                    {"ref": "SYN-GRID-01", "kind": "GRID_ZONE",
                     "label": "Meridian grid watch zone",
                     "lat": _u.HARBOR["lat"], "lon": _u.HARBOR["lon"]}],
                "provenance": declaration()["provenance"],
                "rights": declaration()["data_rights"]}
