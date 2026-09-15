"""Satellite synthetic sensor (first-party community plugin, offline).

STAC-vocabulary scenes (footprint/acquisition/cloud-cover/preview).
No live imagery claimed; preview is footprint-only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

_HERE = Path(__file__).resolve().parent


def declaration() -> Dict[str, Any]:
    return json.loads((_HERE / "manifest.json").read_text(encoding="utf-8"))


class SatelliteSynth:
    kind = "Sensor"

    def poll(self) -> Dict[str, Any]:
        import sys
        sys.path.insert(0, str(_HERE / ".." / ".." / "python"))
        from gods_eye.future import ultra_demo as _u
        return {"items": _u.satellite_scenes(seed=21, n=6),
                "provenance": declaration()["provenance"],
                "rights": declaration()["data_rights"]}
