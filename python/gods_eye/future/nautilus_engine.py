"""FUTURE-ONLY Nautilus engine boundary (version-pinned, separate process).

Shape: proprietary process holds canonical ExecutionDataset/OrderIntent;
a separate Nautilus engine process runs BacktestNode/BacktestEngine;
results return as ExecutionRunManifest. This module pins the expected
config surface and runs a synthetic-only smoke shape (no import, no
engine, no credentials) proving the mapping is executable.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

PINNED = {"nautilus_trader": "2.0.0rc (documented; not installed)",
          "config_surface": "BacktestRunConfig{venues[], data[], engine}",
          "venue_slot": "BacktestVenueConfig{fill_model, fee_model, latency_model}"}


def nautilus_available() -> bool:
    try:
        import nautilus_trader  # noqa: F401
        return True
    except Exception:
        return False


def build_run_config(dataset: Any, intents: List[Any],
                     fee_model: str = "PolymarketFeeModel",
                     venue: str = "SIM") -> Dict[str, Any]:
    """Canonical inputs → Nautilus-shaped run config dict (data only)."""
    return {
        "engine": "BacktestNode",
        "venues": [{"name": venue, "fee_model": fee_model,
                    "fill_model": "UNKNOWN (venue default)",
                    "latency_model": "UNKNOWN (venue default)"}],
        "data": [{"dataset_hash": getattr(dataset, "dataset_hash", lambda: "UNKNOWN")()
                  if hasattr(dataset, "dataset_hash") else "UNKNOWN",
                  "n_intents": len(intents)}],
        "pinned": PINNED,
        "status": "STAGED (engine not installed; no execution)",
    }


def smoke_mapping(dataset: Any, intents: List[Any]) -> Dict[str, Any]:
    """Synthetic-only smoke: every intent maps to a staged order shape."""
    from gods_eye.future.exec_engine import intent_to_request
    staged = []
    for i, intent in enumerate(intents):
        req = intent_to_request(intent, f"smoke-{i}")
        staged.append({"request_id": req.request_id, "venue": req.venue,
                       "side": req.side.value, "quantity": req.quantity})
    return {"n_staged": len(staged), "orders": staged,
            "engine": "nautilus-stub-disabled",
            "verdict": "MAPPING_EXECUTABLE (no engine run in V14)"}
