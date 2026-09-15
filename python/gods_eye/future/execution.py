"""FUTURE-ONLY canonical execution contracts (framework-independent).

Infrastructure only — no strategies, no signal definitions, no alpha.
Every timestamp is explicit; nothing is fabricated. Naive datetimes
are refused. Amounts that count shares/contracts are integers;
prices/ratios are floats with explicit precision notes where needed.

Lifecycle: OrderIntent (what a hypothetical strategy wants) ->
OrderRequest (routed, venue-bound) -> OrderAccepted | OrderRejected ->
Fill* -> Position, with ExecutionReceipt/FeeReceipt/SlippageReceipt/
LatencyReceipt attached. Cancel/modify are explicit terminal paths.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"
    IOC = "IOC"
    FOK = "FOK"
    POST_ONLY = "POST_ONLY"
    UNKNOWN = "UNKNOWN"


class TimeInForce(str, Enum):
    GTC = "GTC"
    DAY = "DAY"
    IOC = "IOC"
    FOK = "FOK"
    GTD = "GTD"
    UNKNOWN = "UNKNOWN"


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    UNKNOWN = "UNKNOWN"


def _require_tz(name: str, ts: Optional[datetime]) -> None:
    if ts is not None and (ts.tzinfo is None or ts.utcoffset() is None):
        raise ValueError(f"{name} must be timezone-aware (got naive)")


@dataclass(frozen=True)
class OrderIntent:
    """Pre-venue desire. No exchange semantics implied."""

    intent_id: str
    instrument_id: str
    venue: str = "UNKNOWN"
    side: Side = Side.UNKNOWN
    quantity: int = 0  # base units; 0 == UNKNOWN/unspecified, never silently filled
    price: Optional[float] = None  # limit price; None == market/unspecified
    stop_price: Optional[float] = None
    order_type: OrderType = OrderType.UNKNOWN
    time_in_force: TimeInForce = TimeInForce.UNKNOWN
    decision_time: Optional[datetime] = None
    event_time: Optional[datetime] = None  # triggering market event time, if any
    source: str = "UNKNOWN"
    model_version: str = "UNKNOWN"
    provenance: str = "UNKNOWN"  # e.g. fixture id, never a live signal ref
    currency: str = "UNKNOWN"
    notes: str = ""

    def __post_init__(self) -> None:
        _require_tz("decision_time", self.decision_time)
        _require_tz("event_time", self.event_time)
        if self.quantity < 0:
            raise ValueError("quantity must be >= 0")


@dataclass(frozen=True)
class OrderRequest:
    """Venue-bound, validated request derived from exactly one OrderIntent."""

    request_id: str
    intent_id: str
    instrument_id: str
    venue: str
    side: Side
    quantity: int
    order_type: OrderType = OrderType.UNKNOWN
    time_in_force: TimeInForce = TimeInForce.UNKNOWN
    price: Optional[float] = None
    stop_price: Optional[float] = None
    expire_time: Optional[datetime] = None  # GTD only
    submission_time: Optional[datetime] = None
    source: str = "UNKNOWN"
    model_version: str = "UNKNOWN"
    provenance: str = "UNKNOWN"
    currency: str = "UNKNOWN"

    def __post_init__(self) -> None:
        _require_tz("expire_time", self.expire_time)
        _require_tz("submission_time", self.submission_time)
        if not self.instrument_id or not self.venue or self.venue == "UNKNOWN":
            raise ValueError("OrderRequest needs instrument_id + concrete venue")
        if self.side not in (Side.BUY, Side.SELL):
            raise ValueError("OrderRequest side must be BUY/SELL (never guess)")
        if self.quantity <= 0:
            raise ValueError("OrderRequest quantity must be > 0")


@dataclass(frozen=True)
class OrderAccepted:
    request_id: str
    venue_order_id: str
    exchange_receive_time: Optional[datetime] = None  # None == UNKNOWN, never invented
    sequence: Optional[int] = None
    notes: str = ""

    def __post_init__(self) -> None:
        _require_tz("exchange_receive_time", self.exchange_receive_time)


@dataclass(frozen=True)
class OrderRejected:
    request_id: str
    reason: str  # machine-readable code, e.g. VENUE_HALTED, UNKNOWN_QUEUE
    detail: str = "UNKNOWN"
    reject_time: Optional[datetime] = None

    def __post_init__(self) -> None:
        _require_tz("reject_time", self.reject_time)
        if not self.reason:
            raise ValueError("OrderRejected needs a reason code")


@dataclass(frozen=True)
class OrderCancelled:
    request_id: str
    venue_order_id: str = "UNKNOWN"
    cancel_time: Optional[datetime] = None
    reason: str = "UNKNOWN"

    def __post_init__(self) -> None:
        _require_tz("cancel_time", self.cancel_time)


@dataclass(frozen=True)
class OrderModified:
    request_id: str
    venue_order_id: str = "UNKNOWN"
    new_quantity: Optional[int] = None
    new_price: Optional[float] = None
    modify_time: Optional[datetime] = None

    def __post_init__(self) -> None:
        _require_tz("modify_time", self.modify_time)


@dataclass(frozen=True)
class Fill:
    """One fill event. Partial fills are explicit PartialFill records."""

    fill_id: str
    request_id: str
    venue_order_id: str = "UNKNOWN"
    instrument_id: str = "UNKNOWN"
    venue: str = "UNKNOWN"
    side: Side = Side.UNKNOWN
    quantity: int = 0
    price: float = 0.0
    fill_time: Optional[datetime] = None  # None == UNKNOWN
    liquidity_role: str = "UNKNOWN"  # MAKER | TAKER | UNKNOWN
    fee_minor: Optional[int] = None  # signed minor units; None == UNKNOWN
    rebate_minor: Optional[int] = None
    slippage_bps: Optional[float] = None
    currency: str = "UNKNOWN"
    source: str = "UNKNOWN"
    provenance: str = "UNKNOWN"

    def __post_init__(self) -> None:
        _require_tz("fill_time", self.fill_time)
        if self.quantity < 0:
            raise ValueError("fill quantity must be >= 0")
        if self.liquidity_role not in ("MAKER", "TAKER", "UNKNOWN"):
            raise ValueError("liquidity_role must be MAKER/TAKER/UNKNOWN")


@dataclass(frozen=True)
class PartialFill:
    fill_id: str
    request_id: str
    quantity: int
    price: float
    remaining: int  # explicitly open remainder, never hidden
    fill_time: Optional[datetime] = None
    venue_order_id: str = "UNKNOWN"

    def __post_init__(self) -> None:
        _require_tz("fill_time", self.fill_time)
        if self.quantity <= 0 or self.remaining < 0:
            raise ValueError("PartialFill needs quantity > 0 and remaining >= 0")


@dataclass(frozen=True)
class Position:
    instrument_id: str
    venue: str = "UNKNOWN"
    quantity: int = 0  # signed; 0 == flat
    avg_price: Optional[float] = None
    realized_pnl_minor: int = 0
    fees_paid_minor: int = 0
    source: str = "UNKNOWN"

    def with_fill(self, side: Side, qty: int, price: float,
                  fee_minor: int = 0) -> "Position":
        signed = qty if side == Side.BUY else -qty
        new_qty = self.quantity + signed
        if self.quantity == 0 or (self.quantity > 0) != (new_qty > 0):
            avg = price if new_qty != 0 else None
        else:
            total = abs(self.quantity) + qty
            avg = ((abs(self.quantity) * (self.avg_price or 0.0) + qty * price)
                   / total) if total else None
        return Position(self.instrument_id, self.venue, new_qty, avg,
                        self.realized_pnl_minor, self.fees_paid_minor + fee_minor,
                        self.source)


@dataclass(frozen=True)
class ExecutionReceipt:
    receipt_id: str
    request_id: str
    engine: str  # e.g. fixture
    engine_version: str = "UNKNOWN"
    realism_tier: str = "UNKNOWN"  # DAILY_COARSE | BAR_INTRADAY | QUOTE_L1 | BOOK_L2 | BOOK_L3
    fills: tuple = ()
    status: str = "UNKNOWN"  # FILLED | PARTIAL | REJECTED | CANCELLED | UNKNOWN
    seed: Optional[int] = None
    code_commit: str = "UNKNOWN"
    notes: str = "UNKNOWN"


@dataclass(frozen=True)
class FeeReceipt:
    receipt_id: str
    request_id: str
    fee_minor: int  # signed: fees positive, rebates recorded separately
    rebate_minor: int = 0
    currency: str = "UNKNOWN"
    schedule_id: str = "UNKNOWN"  # FeeScheduleVersion id
    notes: str = "UNKNOWN"


@dataclass(frozen=True)
class SlippageReceipt:
    receipt_id: str
    request_id: str
    requested_price: Optional[float] = None
    fill_price: Optional[float] = None
    slippage_bps: Optional[float] = None  # None == UNKNOWN
    model_id: str = "UNKNOWN"  # SlippageModelVersion id


@dataclass(frozen=True)
class LatencyReceipt:
    receipt_id: str
    request_id: str
    decision_to_submit_ms: Optional[float] = None
    submit_to_receive_ms: Optional[float] = None
    receive_to_fill_ms: Optional[float] = None
    total_ms: Optional[float] = None
    basis: str = "UNKNOWN"  # OBSERVED | BOUNDED | MODELED | UNKNOWN
