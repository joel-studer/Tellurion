"""EONET disaster sensor (fixture default; optional live leg, user opt-in).

Default poll() serves the bundled CC0 fixture (offline). The live leg
is a pure function over EONET JSON text the *caller* supplies —
this module never fetches, keeping the base demo keyless/offline.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

_HERE = Path(__file__).resolve().parent


def declaration() -> Dict[str, Any]:
    return json.loads((_HERE / "manifest.json").read_text(encoding="utf-8"))


def from_eonet_json(text: str, limit: int = 20):
    """Map EONET v3 JSON (caller-fetched) to canonical events."""
    from gods_eye.future import world_live as _live
    return _live.parse_eonet(text, limit=limit)


class DisasterEonet:
    kind = "Sensor"

    def poll(self) -> Dict[str, Any]:
        fixture = json.loads((_HERE / "fixture.json").read_text(encoding="utf-8"))
        return {"items": fixture["items"],
                "provenance": declaration()["provenance"],
                "rights": declaration()["data_rights"]}
