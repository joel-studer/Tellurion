"""FUTURE-ONLY community-safe demo dataset (synthetic, redistributable, V15).

Everything in here is SYNTHETIC or clearly redistributable public-sample
data. No market data. No private research data. Provenance is redistribution-safe by construction.

The dataset demonstrates one full loop:
  world event -> entity relation -> evidence trail -> time machine
  -> source health -> blind spot.

The story is one coherent intelligence trace (V17): a public announcement
from `synthetic-demo-sensor` is corroborated minutes later by an
independent synthetic timetable leg (`synthetic-timetable-feed`); the
OPERATES entity edge, evidence trail, belief timeline, source health,
and one explicit blind spot all describe the same event.
"""

from __future__ import annotations

from typing import Any, Dict, List

DATASET_ID = "community-demo-v1"
PROVENANCE = "synthetic-fixture (generated for the Tellurion community demo; no real persons, no real filings, redistribution allowed: CC0)"
LICENSE = "CC0-1.0 (synthetic)"
RIGHTS = "REDISTRIBUTION_ALLOWED (synthetic CC0)"


def demo_dataset() -> Dict[str, Any]:
    return {
        "dataset_id": DATASET_ID,
        "provenance": PROVENANCE,
        "license": LICENSE,
        "rights": RIGHTS,
        "world_event": {
            "event_id": "demo-event-001",
            "family": "DEMO_SYNTHETIC",
            "label": "Synthetic Harborview bridge inspection announcement",
            "ts": "2026-09-01T09:00:00+00:00",
            "lat": 47.6062,
            "lon": -122.3321,
            "precision": "city-block (synthetic)",
            "source": "synthetic-demo-sensor",
        },
        "entities": [
            {"id": "demo:org:harborview-transit", "kind": "ORG",
             "label": "Harborview Transit Authority (synthetic)"},
            {"id": "demo:bridge:harborview-7", "kind": "INFRA",
             "label": "Harborview Bridge 7 (synthetic)"},
        ],
        "relations": [
            {"src": "demo:org:harborview-transit",
             "dst": "demo:bridge:harborview-7",
             "method": "synthetic-demo", "model_version": "demo-v1",
             "label": "OPERATES"},
        ],
        "evidence": [
            {"id": "demo-ev-001", "event_ref": "demo-event-001",
             "kind": "announcement", "src": "synthetic-demo-sensor",
             "ts": "2026-09-01T09:00:00+00:00",
             "quote": "Synthetic notice: inspection scheduled (demo text)."},
            {"id": "demo-ev-002", "event_ref": "demo-event-001",
             "kind": "timetable", "src": "synthetic-timetable-feed",
             "ts": "2026-09-01T09:05:00+00:00",
             "quote": "Synthetic timetable entry (demo text)."},
        ],
        "time_machine": {
            "as_of": "2026-09-01T10:00:00+00:00",
            "mode": "belief",
            "belief": "inspection announced; no outcome recorded (synthetic)",
        },
        "source_health": [
            {"source_id": "synthetic-demo-sensor", "state": "UP",
             "last_success_at": "2026-09-01T09:00:00+00:00", "polls_total": 1},
            {"source_id": "synthetic-timetable-feed", "state": "UP",
             "last_success_at": "2026-09-01T09:05:00+00:00", "polls_total": 1},
        ],
        "blind_spots": [
            {"area": "demo-satellite", "status": "NOT_OBSERVED",
             "evidence": "no synthetic satellite leg in demo"},
        ],
    }


def timeline(limit: int = 30) -> List[Dict[str, Any]]:
    ds = demo_dataset()
    ev = ds["world_event"]
    return [{"ts": ev["ts"], "family": ev["family"], "label": ev["label"],
             "event_id": ev["event_id"]}][:limit]


def validate_no_holdout_refs() -> Dict[str, Any]:
    """Guard: demo dataset must never reference holdout/private paths."""
    import json
    blob = json.dumps(demo_dataset()).lower()
    forbidden = ("holdout", "api_key", "api_secret", "private_key",
                 "passphrase", "mnemonic", "password", ".sqlite")
    hits = [t for t in forbidden if t in blob]
    return {"ok": not hits, "hits": hits,
            "provenance": PROVENANCE, "rights": RIGHTS}
