"""FUTURE-ONLY Nautilus <-> GOD'S EYE Polymarket mapping (fixtures only, V15).

Canonical mapping layer between our generic prediction-market /
execution contracts and the audited Nautilus Polymarket interface
surface (see docs/future/NAUTILUS_INTEGRATION_REVIEW.md):

  GOD'S EYE BinaryMarket   <-> Nautilus BinaryOption
  GOD'S EYE OrderIntent    <-> Nautilus Polymarket order semantics
  GOD'S EYE ExecutionReceipt <-> Nautilus fill/reconciliation output

No credentials. No network. No engine import. Fixtures only.
Every mapping is total on fixtures and explicit about UNKNOWNs:
unknown venue semantics surface as UNKNOWN instead of being guessed.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# Audited Nautilus surface (static inspection 2026-09-14; not installed).
NAUTILUS_SHAPE = {
    "instrument": "nautilus_trader.model.instruments.BinaryOption",
    "fee_model": "PolymarketFeeModel (+ ProbabilityPriceFeeModel, exponent-1)",
    "order_semantics": {
        "MARKET BUY": "quote-notional pUSD (quote_quantity=True; base-denominated refused)",
        "TIF": "GTC/GTD->resting LIMIT, IOC->FAK, FOK->FOK (MARKET only IOC/FOK)",
        "post_only": "GTC/GTD LIMIT only",
        "unsupported": ["STOP", "MIT", "trailing", "iceberg", "bracket", "OCO", "modify"],
        "batch": "submit<=15 LIMIT (POST /orders); cancel chunked (DELETE /orders)",
    },
    "settlement_statuses": ["MATCHED", "MINED", "RETRYING", "CONFIRMED", "FAILED"],
    "fill_void": "OrderFillVoided on FAILED",
    "collateral": "pUSD (Polygon; token address intentionally not recorded)",
    "provenance": "docs/future/NAUTILUS_INTEGRATION_REVIEW.md",
}

# GOD'S EYE order-type -> Nautilus Polymarket order semantics.
ORDER_SEMANTICS = {
    "MARKET": "MARKET IOC/FOK quote-notional (base-denominated refused)",
    "LIMIT": "resting LIMIT GTC/GTD (post-only allowed)",
    "IOC": "FAK",
    "FOK": "FOK (MARKET only)",
    "POST_ONLY": "GTC/GTD LIMIT post-only",
    "STOP": "UNSUPPORTED (refused)",
    "STOP_LIMIT": "UNSUPPORTED (refused)",
    "UNKNOWN": "UNKNOWN (refused until concrete)",
}


def binary_market_to_nautilus_shape(market: Any) -> Dict[str, Any]:
    """GOD'S EYE BinaryMarket -> Nautilus BinaryOption-shaped dict (data only)."""
    mid = getattr(market, "market_id", "UNKNOWN")
    venue = getattr(market, "venue_id", "UNKNOWN")
    currency = getattr(market, "currency", "UNKNOWN")
    tick = getattr(market, "tick_size", "UNKNOWN")
    status = getattr(market, "status", "UNKNOWN")
    tokens = market.tokens() if hasattr(market, "tokens") else ()
    return {
        "nautilus_instrument": "BinaryOption",
        "instrument_id": f"{venue}:{mid}",
        "underlying": mid,
        "quote_currency": currency if currency != "UNKNOWN" else "UNKNOWN (pUSD on live venue; UNKNOWN in fixtures)",
        "tick_size": tick,
        "status": status,
        "n_tokens": len(tokens),
        "provenance": "gods_eye.future.nautilus_polymarket:fixtures-only",
        "engine_status": "STAGED (engine not installed; no execution)",
    }


def order_intent_to_nautilus_shape(intent: Any, request_id: str) -> Dict[str, Any]:
    """GOD'S EYE OrderIntent -> Nautilus Polymarket order-shaped dict.

    Refuses anything Nautilus cannot express (STOP/MIT/modify/UNKNOWN).
    """
    from gods_eye.future.exec_engine import intent_to_request
    req = intent_to_request(intent, request_id)
    otype = req.order_type.value if hasattr(req.order_type, "value") else str(req.order_type)
    if otype in ("STOP", "STOP_LIMIT"):
        raise ValueError(f"Nautilus Polymarket shape refuses {otype} (unsupported)")
    if otype == "UNKNOWN":
        raise ValueError("Nautilus Polymarket shape refuses UNKNOWN order type")
    tif = req.time_in_force.value if hasattr(req.time_in_force, "value") else str(req.time_in_force)
    semantics = ORDER_SEMANTICS.get(otype, "UNKNOWN (refused until concrete)")
    return {
        "request_id": req.request_id,
        "instrument_id": req.instrument_id,
        "venue": req.venue,
        "side": req.side.value if hasattr(req.side, "value") else str(req.side),
        "quantity": req.quantity,
        "order_type": otype,
        "time_in_force": tif,
        "price": req.price,
        "nautilus_semantics": semantics,
        "quote_notional_rule": "MARKET BUY is quote-notional (pUSD) on live venue",
        "provenance": "gods_eye.future.nautilus_polymarket:fixtures-only",
        "engine_status": "STAGED (engine not installed; no execution)",
    }


def execution_receipt_to_nautilus_shape(receipt: Any) -> Dict[str, Any]:
    """GOD'S EYE ExecutionReceipt -> Nautilus fill/reconciliation-shaped dict."""
    fills = list(getattr(receipt, "fills", ()) or ())
    return {
        "receipt_id": getattr(receipt, "receipt_id", "UNKNOWN"),
        "request_id": getattr(receipt, "request_id", "UNKNOWN"),
        "engine": getattr(receipt, "engine", "UNKNOWN"),
        "status": getattr(receipt, "status", "UNKNOWN"),
        "n_fills": len(fills),
        "nautilus_equivalent": "ExecutionEngine reconciliation report (sim)",
        "settlement_statuses": list(NAUTILUS_SHAPE["settlement_statuses"]),
        "fill_void_rule": NAUTILUS_SHAPE["fill_void"],
        "provenance": "gods_eye.future.nautilus_polymarket:fixtures-only",
    }


def smoke_fixture_mapping(market: Any, intents: List[Any]) -> Dict[str, Any]:
    """End-to-end fixture smoke: market + intents -> staged Nautilus shapes."""
    mapped_market = binary_market_to_nautilus_shape(market)
    orders = [order_intent_to_nautilus_shape(i, f"stage-{n}")
              for n, i in enumerate(intents)]
    return {"market": mapped_market, "orders": orders,
            "n_orders": len(orders),
            "verdict": "MAPPING_EXECUTABLE (fixtures only; no engine run)",
            "shape": NAUTILUS_SHAPE["instrument"]}
