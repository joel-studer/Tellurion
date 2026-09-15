"""FUTURE-ONLY community-safe demo dataset (synthetic, redistributable, V15).

Everything in here is SYNTHETIC or clearly redistributable public-sample
data. No real trading data. No holdout data. No private
research data. Provenance is redistribution-safe by construction.

The dataset demonstrates one full loop:
  world event -> entity relation -> market instrument -> evidence trail
  -> time machine -> market reaction -> venue abstraction.

The story is one coherent intelligence trace (V17): a public announcement
from `synthetic-demo-sensor` is corroborated minutes later by an
independent synthetic timetable leg (`synthetic-timetable-feed`); the
OPERATES entity edge, evidence trail, belief timeline, generic market
context, and one explicit blind spot all describe the same event.
"""

from __future__ import annotations

from typing import Any, Dict, List

DATASET_ID = "community-demo-v1"
PROVENANCE = "synthetic-fixture (generated for GOD'S EYE community demo; no real persons, no real filings, redistribution allowed: CC0)"
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
        "market_instrument": {
            "instrument_id": "DEMO:XHB",
            "venue_id": "demo-venue",
            "symbol": "XHB",
            "asset_class": "ETF",
            "base": "XHB",
            "quote": "USD",
            "market_type": "UNKNOWN",
            "provenance": PROVENANCE,
            "rights": RIGHTS,
        },
        "venue": {
            "venue_id": "demo-venue",
            "name": "Demo Venue (synthetic)",
            "venue_type": "EXCHANGE",
            "timezone": "America/New_York",
            "asset_classes": ["ETF"],
            "capabilities": {"market_data": {"quotes": "SUPPORTED"},
                             "orders": {"limit": "SUPPORTED"},
                             "paper_support": "SUPPORTED",
                             "live_support": "UNSUPPORTED"},
            "provenance": PROVENANCE,
        },
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
        "market_reaction": {
            "instrument_id": "DEMO:XHB",
            "window": "2026-09-01T09:00:00+00:00/2026-09-01T10:00:00+00:00",
            "bars": [
                {"t": "2026-09-01T09:00:00+00:00", "open": 100.0,
                 "high": 100.5, "low": 99.8, "close": 100.2, "volume": 1200},
                {"t": "2026-09-01T09:30:00+00:00", "open": 100.2,
                 "high": 100.6, "low": 99.9, "close": 100.4, "volume": 900},
            ],
            "note": "synthetic bars for replay only; not a market claim",
        },
        "prediction_market": {
            "market_id": "demo-binary-001",
            "venue_id": "demo-prediction-venue",
            "question": "Will the synthetic inspection finish on schedule? (demo)",
            "status": "OPEN",
            "yes_price": 0.62,
            "no_price": 0.38,
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
