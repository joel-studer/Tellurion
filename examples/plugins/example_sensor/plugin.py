"""Example community sensor plugin (no secrets, no network).

Copy this directory to start a new plugin. Stdlib only at module scope.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

_HERE = Path(__file__).resolve().parent


def declaration() -> Dict[str, Any]:
    return json.loads((_HERE / "manifest.json").read_text(encoding="utf-8"))


class ExampleSensor:
    """Minimal poll() sensor over a redistributable local fixture."""

    kind = "Sensor"

    def poll(self) -> Dict[str, Any]:
        fixture = json.loads((_HERE / "fixture.json").read_text(encoding="utf-8"))
        return {"items": fixture["items"],
                "provenance": declaration()["provenance"],
                "rights": declaration()["data_rights"]}
