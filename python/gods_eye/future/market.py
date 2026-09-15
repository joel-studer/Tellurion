"""FUTURE-ONLY canonical market/research interfaces (V10+ contracts, not wired).

Design rules (from the frozen-lane lessons):
  * UNKNOWN must remain representable — every quality/rights/timing field has
    an explicit UNKNOWN default. Never substitute "now" for a missing
    timestamp; missing times are None.
  * No timestamp substitution, no timezone guessing (tz field required;
    naive datetimes rejected at construction).
  * No fake quote construction from OHLC (Quote.bid/ask must be observed;
    bar-to-quote synthesis is a documented constructor refusal).
  * Amounts are integers in minor units where applicable; floats only for
    quoted prices/ratios with explicit precision field.
  * Every record carries raw provenance (source, raw hash, dataset version).

Stdlib-only dataclasses with validation in __post_init__. No I/O, no imports
of downstream research modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class Quality(str, Enum):
    UNKNOWN = "UNKNOWN"
    RAW = "RAW"
    VALIDATED = "VALIDATED"
    SUSPECT = "SUSPECT"


class Rights(str, Enum):
    UNKNOWN = "UNKNOWN"
    BLOCKED_RIGHTS = "BLOCKED_RIGHTS"
    DISCOVERY_ONLY = "DISCOVERY_ONLY"
    RESEARCH_TRIAL = "RESEARCH_TRIAL"
    QUALIFIED_RESEARCH = "QUALIFIED_RESEARCH"
    QUALIFIED_PAPER = "QUALIFIED_PAPER"
    QUALIFIED_LIVE = "QUALIFIED_LIVE"


def _require_tz(name: str, ts: Optional[datetime]) -> None:
    if ts is not None and (ts.tzinfo is None or ts.utcoffset() is None):
        raise ValueError(f"{name} must be timezone-aware (got naive)")


@dataclass(frozen=True)
class MarketDatasetVersion:
    dataset_id: str
    version: str
    rights: Rights = Rights.UNKNOWN
    provenance: str = ""  # vendor + terms snapshot id + retrieval method


@dataclass(frozen=True)
class CostModelVersion:
    model_id: str
    version: str
    commissions_bps: Optional[float] = None  # None == UNKNOWN, never 0-by-default
    spread_bps: Optional[float] = None
    slippage_bps: Optional[float] = None
    borrow_bps: Optional[float] = None
    funding_bps: Optional[float] = None
    notes: str = ""


@dataclass(frozen=True)
class ExecutionModelVersion:
    model_id: str
    version: str
    latency_ms: Optional[float] = None
    partial_fills: bool = False
    queue_model: str = "UNKNOWN"
    notes: str = ""


@dataclass(frozen=True)
class MarketBar:
    instrument_id: str
    venue: str
    timeframe: str  # e.g. "1m", "1d" — never implies quote availability
    open: float
    high: float
    low: float
    close: float
    volume: Optional[int]  # None == UNKNOWN (do not zero-fill silently)
    event_time: datetime   # bar close / period end, tz-aware, exchange tz named
    timezone: str          # IANA name, e.g. "America/New_York"
    ingest_time: Optional[datetime] = None
    source: str = "UNKNOWN"
    quality: Quality = Quality.UNKNOWN
    rights: Rights = Rights.UNKNOWN
    dataset: Optional[MarketDatasetVersion] = None
    raw_hash: str = ""

    def __post_init__(self) -> None:
        _require_tz("event_time", self.event_time)
        _require_tz("ingest_time", self.ingest_time)
        if not self.timezone:
            raise ValueError("timezone IANA name required (never guess)")


@dataclass(frozen=True)
class Quote:
    instrument_id: str
    venue: str
    bid: float
    ask: float
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None
    event_time: datetime = field(default=None)  # type: ignore[assignment]
    visibility_time: Optional[datetime] = None  # when WE could see it (<= ingest)
    ingest_time: Optional[datetime] = None
    timezone: str = ""
    sequence: Optional[int] = None
    source: str = "UNKNOWN"
    quality: Quality = Quality.UNKNOWN
    rights: Rights = Rights.UNKNOWN
    dataset: Optional[MarketDatasetVersion] = None
    raw_hash: str = ""

    def __post_init__(self) -> None:
        if self.event_time is None:
            raise ValueError("Quote.event_time required (no substitution)")
        _require_tz("event_time", self.event_time)
        _require_tz("visibility_time", self.visibility_time)
        _require_tz("ingest_time", self.ingest_time)
        if self.ask < self.bid:
            raise ValueError("crossed quote refused (ask < bid)")

    @classmethod
    def from_ohlc(cls, bar: MarketBar) -> "Quote":
        """Refuse fake quote construction from OHLC. Always raises."""
        raise ValueError(
            "quotes cannot be synthesized from bars "
            f"(instrument={bar.instrument_id} timeframe={bar.timeframe})")


@dataclass(frozen=True)
class Trade:
    instrument_id: str
    venue: str
    price: float
    size: Optional[int]
    event_time: datetime = field(default=None)  # type: ignore[assignment]
    ingest_time: Optional[datetime] = None
    timezone: str = ""
    aggressor_side: str = "UNKNOWN"  # BUY | SELL | UNKNOWN (never guess)
    sequence: Optional[int] = None
    source: str = "UNKNOWN"
    quality: Quality = Quality.UNKNOWN
    rights: Rights = Rights.UNKNOWN
    dataset: Optional[MarketDatasetVersion] = None
    raw_hash: str = ""

    def __post_init__(self) -> None:
        if self.event_time is None:
            raise ValueError("Trade.event_time required (no substitution)")
        _require_tz("event_time", self.event_time)
        _require_tz("ingest_time", self.ingest_time)
        if self.aggressor_side not in ("BUY", "SELL", "UNKNOWN"):
            raise ValueError("aggressor_side must be BUY/SELL/UNKNOWN")


@dataclass(frozen=True)
class OrderBookLevel:
    price: float
    size: int
    orders: Optional[int] = None  # None on L1/L2 (UNKNOWN, not 0)


@dataclass(frozen=True)
class OrderBookSnapshot:
    instrument_id: str
    venue: str
    bids: tuple = ()  # tuple[OrderBookLevel, ...] best-first
    asks: tuple = ()  # tuple[OrderBookLevel, ...] best-first
    depth: str = "UNKNOWN"  # L1 | L2 | L3 | UNKNOWN
    event_time: datetime = field(default=None)  # type: ignore[assignment]
    ingest_time: Optional[datetime] = None
    timezone: str = ""
    sequence: Optional[int] = None
    source: str = "UNKNOWN"
    quality: Quality = Quality.UNKNOWN
    rights: Rights = Rights.UNKNOWN
    dataset: Optional[MarketDatasetVersion] = None
    raw_hash: str = ""

    def __post_init__(self) -> None:
        if self.event_time is None:
            raise ValueError("OrderBookSnapshot.event_time required")
        _require_tz("event_time", self.event_time)
        if self.depth not in ("L1", "L2", "L3", "UNKNOWN"):
            raise ValueError("depth must be L1/L2/L3/UNKNOWN")


@dataclass(frozen=True)
class OrderBookDelta:
    instrument_id: str
    venue: str
    side: str  # BID | ASK | UNKNOWN
    price: float
    size: int  # 0 == level removal (explicit, never UNKNOWN-as-0 for size otherwise)
    event_time: datetime = field(default=None)  # type: ignore[assignment]
    sequence: Optional[int] = None
    is_snapshot: bool = False
    source: str = "UNKNOWN"
    dataset: Optional[MarketDatasetVersion] = None
    raw_hash: str = ""

    def __post_init__(self) -> None:
        if self.event_time is None:
            raise ValueError("OrderBookDelta.event_time required")
        _require_tz("event_time", self.event_time)
        if self.side not in ("BID", "ASK", "UNKNOWN"):
            raise ValueError("side must be BID/ASK/UNKNOWN")


@dataclass(frozen=True)
class TradingHalt:
    instrument_id: str
    venue: str
    halt_start: datetime
    halt_end: Optional[datetime] = None  # None == ongoing/UNKNOWN
    reason: str = "UNKNOWN"
    timezone: str = ""
    source: str = "UNKNOWN"
    dataset: Optional[MarketDatasetVersion] = None

    def __post_init__(self) -> None:
        _require_tz("halt_start", self.halt_start)
        _require_tz("halt_end", self.halt_end)


@dataclass(frozen=True)
class CorporateAction:
    instrument_id: str
    venue: str
    action: str  # SPLIT | DIVIDEND | SYMBOL_CHANGE | DELIST | MERGER | UNKNOWN
    ex_date: Optional[str] = None  # YYYY-MM-DD, None == UNKNOWN
    ratio: Optional[str] = None    # exact string, e.g. "4:1" (never float)
    old_symbol: Optional[str] = None
    new_symbol: Optional[str] = None
    adjustment: str = "UNKNOWN"    # how prices were adjusted, or UNKNOWN
    source: str = "UNKNOWN"
    dataset: Optional[MarketDatasetVersion] = None

    def __post_init__(self) -> None:
        if self.action not in ("SPLIT", "DIVIDEND", "SYMBOL_CHANGE", "DELIST",
                               "MERGER", "UNKNOWN"):
            raise ValueError(f"unknown corporate action kind: {self.action}")


@dataclass(frozen=True)
class ResearchExperiment:
    """Declarative experiment definition (future-only)."""
    experiment_id: str
    signal_id: str              # versioned id, e.g. "storm-landfall@v1"
    signal_version: str
    event_ids: tuple = ()
    evidence_cutoff: Optional[str] = None  # ISO date; None == UNKNOWN
    dataset: Optional[MarketDatasetVersion] = None
    engine: str = "UNKNOWN"     # lean | nautilus | hftbacktest | qanat-replay | UNKNOWN
    engine_version: str = "UNKNOWN"
    cost_model: Optional[CostModelVersion] = None
    execution_model: Optional[ExecutionModelVersion] = None
    code_commit: str = "UNKNOWN"
    model_version: Optional[str] = None
    seed: Optional[int] = None
    rights_state: Rights = Rights.UNKNOWN
    # V11: every future backtest references a MarketDatasetSnapshot ID
    # (never "latest market data"). None == pre-snapshot (UNKNOWN).
    snapshot_id: Optional[str] = None

    def lineage_keys(self) -> dict:
        return {
            "experiment_id": self.experiment_id,
            "signal_id": self.signal_id,
            "signal_version": self.signal_version,
            "event_ids": sorted(self.event_ids),
            "evidence_cutoff": self.evidence_cutoff,
            "dataset": None if self.dataset is None else
                f"{self.dataset.dataset_id}@{self.dataset.version}",
            "engine": f"{self.engine}@{self.engine_version}",
            "cost_model": None if self.cost_model is None else
                f"{self.cost_model.model_id}@{self.cost_model.version}",
            "execution_model": None if self.execution_model is None else
                f"{self.execution_model.model_id}@{self.execution_model.version}",
            "code_commit": self.code_commit,
            "model_version": self.model_version,
            "seed": self.seed,
            "rights_state": self.rights_state.value,
            "snapshot_id": self.snapshot_id,
        }


def utc(ts: str) -> datetime:
    """Parse ISO -> tz-aware UTC datetime (helper; naive input refused)."""
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        raise ValueError(f"naive timestamp refused: {ts}")
    return dt.astimezone(timezone.utc)
