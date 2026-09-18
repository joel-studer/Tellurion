"""Austria demo pack (static CC0 reference points; live legs per-agency opt-in).

Bundled data is synthetic reference context only. Live Austrian feeds
(GeoSphere Austria, data.gv.at, OEBB GTFS, ASFINAG, ORF-weather widgets)
are documented in docs/public/AUSTRIA_PACK.md and fetched only by the
operator after per-feed rights verification. No scraping, no private
sites, no credentials bundled.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

_HERE = Path(__file__).resolve().parent


def declaration() -> Dict[str, Any]:
    return json.loads((_HERE / "manifest.json").read_text(encoding="utf-8"))


class AustriaPack:
    kind = "Sensor"

    def poll(self) -> Dict[str, Any]:
        fixture = json.loads((_HERE / "fixture.json").read_text(encoding="utf-8"))
        return {"items": fixture["items"],
                "provenance": declaration()["provenance"],
                "rights": declaration()["data_rights"]}
