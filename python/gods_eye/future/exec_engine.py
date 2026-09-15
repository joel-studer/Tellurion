"""FUTURE-ONLY execution adapter boundary (canonical contracts only).

FixtureExecutionEngine replays synthetic/replay intents deterministically:
no network, no credentials, no live signals. NautilusExecutionAdapter
exists as a DISABLED stub documenting the future wiring point — it never
imports nautilus_trader (lazy inside a disabled method that raises).

Hard rule (tested): importing this module must never import the heavy
frameworks (nautilus_trader / hftbacktest / lean / ...).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from gods_eye.future import isolation
from gods_eye.future.exec_safety import assert_mode_allowed, assert_no_credentials
from gods_eye.future.execution import (OrderAccepted, OrderIntent, OrderRejected,
                                        OrderRequest, Side)

FORBIDDEN_IMPORTS = ("nautilus_trader", "hftbacktest", "lean", "skfolio",
                     "qanat", "torch", "ccxt", "cryptofeed")


class ExecutionEngineAdapter(ABC):
    engine_name: str = "UNKNOWN"

    @abstractmethod
    def configure_venue(self, venue: str, rules: Dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def load_instrument(self, instrument_id: str, venue: str) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def submit_order(self, request: OrderRequest) -> Any:
        raise NotImplementedError

    @abstractmethod
    def modify_order(self, request_id: str, **changes: Any) -> Any:
        raise NotImplementedError

    @abstractmethod
    def cancel_order(self, request_id: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    def advance_time(self, timestamp: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def read_fills(self) -> List[Any]:
        raise NotImplementedError

    @abstractmethod
    def read_positions(self) -> List[Any]:
        raise NotImplementedError

    @abstractmethod
    def read_execution_receipts(self) -> List[Any]:
        raise NotImplementedError


def _vet_intent(intent: OrderIntent) -> None:
    from pathlib import Path
    ref = (intent.provenance or "")
    if ref and ("/" in ref or "\\" in ref or ref.endswith(".json")):
        p = Path(ref)
        rp = p.resolve() if p.is_absolute() else (isolation.ROOT / ref).resolve()
        if isolation.is_holdout(rp):
            raise isolation.IsolationViolation("read-forbidden data cannot feed execution adapter")
        if isolation.is_protected(rp):
            raise isolation.IsolationViolation("protected research state cannot feed execution adapter")


class FixtureExecutionEngine(ExecutionEngineAdapter):
    """Deterministic fixture replay (synthetic intents only)."""

    engine_name = "fixture"

    def __init__(self, mode: str = "REPLAY", config: Optional[Dict[str, Any]] = None):
        assert_mode_allowed(mode)
        assert_no_credentials(config or {})
        self._mode = mode
        self._venues: Dict[str, Dict[str, Any]] = {}
        self._instruments: Dict[str, Dict[str, Any]] = {}
        self._orders: Dict[str, OrderRequest] = {}
        self._fills: List[Any] = []
        self._receipts: List[Any] = []
        self._clock = "UNKNOWN"

    def configure_venue(self, venue: str, rules: Dict[str, Any]) -> None:
        assert_no_credentials(rules)
        self._venues[venue] = dict(rules)

    def load_instrument(self, instrument_id: str, venue: str) -> Dict[str, Any]:
        rec = {"instrument_id": instrument_id, "venue": venue, "tick": "UNKNOWN"}
        self._instruments[instrument_id] = rec
        return rec

    def submit_order(self, request: OrderRequest) -> Any:
        assert_no_credentials(request)
        if request.venue not in self._venues:
            return OrderRejected(request.request_id, "UNKNOWN_VENUE",
                                 f"venue not configured: {request.venue}")
        self._orders[request.request_id] = request
        # Fixture: accept without fill (fills come from replay driver/tests).
        return OrderAccepted(request.request_id, f"FIX-{request.request_id}")

    def modify_order(self, request_id: str, **changes: Any) -> Any:
        from gods_eye.future.execution import OrderModified
        assert_no_credentials(changes)
        if request_id not in self._orders:
            return OrderRejected(request_id, "UNKNOWN_ORDER", "no such request")
        return OrderModified(request_id, f"FIX-{request_id}",
                             new_quantity=changes.get("quantity"),
                             new_price=changes.get("price"))

    def cancel_order(self, request_id: str) -> Any:
        from gods_eye.future.execution import OrderCancelled
        if request_id not in self._orders:
            return OrderRejected(request_id, "UNKNOWN_ORDER", "no such request")
        return OrderCancelled(request_id, f"FIX-{request_id}", reason="FIXTURE_CANCEL")

    def advance_time(self, timestamp: str) -> None:
        self._clock = timestamp

    def read_fills(self) -> List[Any]:
        return list(self._fills)

    def read_positions(self) -> List[Any]:
        return []

    def read_execution_receipts(self) -> List[Any]:
        return list(self._receipts)


class NautilusExecutionAdapter(ExecutionEngineAdapter):
    """DISABLED stub: documents the future Nautilus wiring point.

    Today every method raises (engine not wired, no install, no creds).
    The real wiring (BacktestEngine/BacktestNode + adapters.polymarket)
    happens only in a separately reviewed PR with freeze-manifest update.
    """

    engine_name = "nautilus-stub-disabled"

    def _disabled(self) -> None:
        raise RuntimeError("NautilusExecutionAdapter is DISABLED (V12 stub; "
                           "no install, no wiring, no credentials)")

    def configure_venue(self, venue: str, rules: Dict[str, Any]) -> None:
        self._disabled()

    def load_instrument(self, instrument_id: str, venue: str) -> Dict[str, Any]:
        self._disabled()

    def submit_order(self, request: OrderRequest) -> Any:
        self._disabled()

    def modify_order(self, request_id: str, **changes: Any) -> Any:
        self._disabled()

    def cancel_order(self, request_id: str) -> Any:
        self._disabled()

    def advance_time(self, timestamp: str) -> None:
        self._disabled()

    def read_fills(self) -> List[Any]:
        self._disabled()

    def read_positions(self) -> List[Any]:
        self._disabled()

    def read_execution_receipts(self) -> List[Any]:
        self._disabled()


def intent_to_request(intent: OrderIntent, request_id: str,
                      submission_time: Optional[str] = None) -> OrderRequest:
    """Intent -> venue-bound request (provenance-guarded, no live refs)."""
    _vet_intent(intent)
    if intent.side not in (Side.BUY, Side.SELL):
        raise ValueError("intent side must be BUY/SELL")
    if intent.quantity <= 0:
        raise ValueError("intent quantity must be > 0")
    if not intent.venue or intent.venue == "UNKNOWN":
        raise ValueError("intent needs a concrete venue for routing")
    return OrderRequest(request_id=request_id, intent_id=intent.intent_id,
                        instrument_id=intent.instrument_id, venue=intent.venue,
                        side=intent.side,
                        quantity=intent.quantity, order_type=intent.order_type,
                        time_in_force=intent.time_in_force, price=intent.price,
                        stop_price=intent.stop_price, source=intent.source,
                        model_version=intent.model_version,
                        provenance=intent.provenance, currency=intent.currency)
