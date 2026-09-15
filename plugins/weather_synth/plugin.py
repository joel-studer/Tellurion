"""Weather synthetic sensor (first-party community plugin, offline)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

_HERE = Path(__file__).resolve().parent


def declaration() -> Dict[str, Any]:
    return json.loads((_HERE / "manifest.json").read_text(encoding="utf-8"))


class WeatherSynth:
    kind = "Sensor"

    def poll(self) -> Dict[str, Any]:
        import sys
        sys.path.insert(0, str(_HERE / ".." / ".." / "python"))
        from gods_eye.future import ultra_demo as _u
        return {"items": _u.weather()["cells"],
                "alerts": _u.weather()["alerts"],
                "provenance": declaration()["provenance"],
                "rights": declaration()["data_rights"]}
