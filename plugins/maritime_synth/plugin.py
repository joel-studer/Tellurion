"""Maritime synthetic sensor (first-party community plugin, offline).

No live AIS source is keyless-redistributable, so the base demo stays
synthetic; this adapter mirrors the live shape for later user-key legs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

_HERE = Path(__file__).resolve().parent


def declaration() -> Dict[str, Any]:
    return json.loads((_HERE / "manifest.json").read_text(encoding="utf-8"))


class MaritimeSynth:
    kind = "Sensor"

    def poll(self) -> Dict[str, Any]:
        import sys
        sys.path.insert(0, str(_HERE / ".." / ".." / "python"))
        from gods_eye.future import ultra_demo as _u
        return {"items": _u.vessels(seed=11, n=18, tick=0),
                "provenance": declaration()["provenance"],
                "rights": declaration()["data_rights"]}
