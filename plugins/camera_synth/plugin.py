"""Camera synthetic sensor (first-party community plugin, offline).

Public-camera abstraction: id/operator/location/rights/feed-type/
last-update/health/provenance. Snapshots are synthetic placeholders.
No discovery, no streams, no person identification — ever.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

_HERE = Path(__file__).resolve().parent

FORBIDDEN = ("discover", "scan", "identify", "recognise", "recognize",
             "track_person")


def declaration() -> Dict[str, Any]:
    return json.loads((_HERE / "manifest.json").read_text(encoding="utf-8"))


class CameraSynth:
    kind = "Sensor"

    def poll(self) -> Dict[str, Any]:
        import sys
        sys.path.insert(0, str(_HERE / ".." / ".." / "python"))
        from gods_eye.future import ultra_demo as _u
        return {"items": _u.cameras(seed=71, n=6),
                "provenance": declaration()["provenance"],
                "rights": declaration()["data_rights"]}
