"""Aviation synthetic sensor (first-party community plugin, offline).

Yields replay aircraft in the tar1090-inspired shape. No network,
no credentials.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

_HERE = Path(__file__).resolve().parent


def declaration() -> Dict[str, Any]:
    return json.loads((_HERE / "manifest.json").read_text(encoding="utf-8"))


class AviationSynth:
    kind = "Sensor"

    def poll(self) -> Dict[str, Any]:
        import sys
        sys.path.insert(0, str(_HERE / ".." / ".." / "python"))
        from gods_eye.future import ultra_demo as _u
        items = _u.aircraft(seed=7, n=24, tick=0)
        fixture = json.loads((_HERE / "fixture.json").read_text(encoding="utf-8"))
        return {"items": items, "fixture": fixture["note"],
                "provenance": declaration()["provenance"],
                "rights": declaration()["data_rights"]}
