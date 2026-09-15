"""FUTURE-ONLY multi-venue canonical model (open-core safe, V15).

Infrastructure only — no proprietary market-selection logic, no signal
mapping, no timing edge, no ranking. Every capability/fee/order field has
an explicit UNKNOWN default; UNKNOWN is never silently upgraded.

Stdlib-only dataclasses + enums. No I/O, no network, no credentials,
no imports of downstream research modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class AssetClass(str, Enum):
    EQUITY = "EQUITY"
    ETF = "ETF"
    INDEX = "INDEX"
    FX = "FX"
    CRYPTO_SPOT = "CRYPTO_SPOT"
    CRYPTO_PERPETUAL = "CRYPTO_PERPETUAL"
    FUTURE = "FUTURE"
    OPTION = "OPTION"
    BINARY_CONTRACT = "BINARY_CONTRACT"
    PREDICTION_MARKET = "PREDICTION_MARKET"
    RATE = "RATE"
    COMMODITY = "COMMODITY"
    UNKNOWN = "UNKNOWN"


class SettlementType(str, Enum):
    CASH = "CASH"
    PHYSICAL = "PHYSICAL"
    ONCHAIN = "ONCHAIN"
    CFD = "CFD"
    UNKNOWN = "UNKNOWN"


class TradingSessionState(str, Enum):
    REGULAR = "REGULAR"
    PRE = "PRE"
    POST = "POST"
    CLOSED = "CLOSED"
    HALTED = "HALTED"
    UNKNOWN = "UNKNOWN"


def _require_tz(name: str, ts: Optional[datetime]) -> None:
    if ts is not None and (ts.tzinfo is None or ts.utcoffset() is None):
        raise ValueError(f"{name} must be timezone-aware (got naive)")


@dataclass(frozen=True)
class MarketDataCapability:
    quotes: str = "UNKNOWN"  # SUPPORTED | UNSUPPORTED | UNKNOWN
    trades: str = "UNKNOWN"
    l1: str = "UNKNOWN"
    l2: str = "UNKNOWN"
    l3: str = "UNKNOWN"
    funding: str = "UNKNOWN"
    historical: str = "UNKNOWN"
    websocket: str = "UNKNOWN"
    rest: str = "UNKNOWN"

    def __post_init__(self) -> None:
        for f in ("quotes", "trades", "l1", "l2", "l3", "funding",
                  "historical", "websocket", "rest"):
            if getattr(self, f) not in ("SUPPORTED", "UNSUPPORTED", "UNKNOWN"):
                raise ValueError(f"MarketDataCapability.{f} must be "
                                 f"SUPPORTED/UNSUPPORTED/UNKNOWN")


@dataclass(frozen=True)
class OrderCapability:
    market: str = "UNKNOWN"
    limit: str = "UNKNOWN"
    stop: str = "UNKNOWN"
    stop_limit: str = "UNKNOWN"
    ioc: str = "UNKNOWN"
    fok: str = "UNKNOWN"
    post_only: str = "UNKNOWN"
    cancel: str = "UNKNOWN"
    modify: str = "UNKNOWN"
    batch: str = "UNKNOWN"

    def __post_init__(self) -> None:
        for f in ("market", "limit", "stop", "stop_limit", "ioc", "fok",
                  "post_only", "cancel", "modify", "batch"):
            if getattr(self, f) not in ("SUPPORTED", "UNSUPPORTED", "UNKNOWN"):
                raise ValueError(f"OrderCapability.{f} must be "
                                 f"SUPPORTED/UNSUPPORTED/UNKNOWN")


@dataclass(frozen=True)
class FeeCapability:
    maker_bps: Optional[float] = None  # None == UNKNOWN, never 0-by-default
    taker_bps: Optional[float] = None
    funding_bps: Optional[float] = None
    schedule_id: str = "UNKNOWN"
    basis: str = "UNKNOWN"  # OBSERVED | VENDOR_DOCS | MODELED | UNKNOWN
    notes: str = "UNKNOWN"


@dataclass(frozen=True)
class VenueCapability:
    market_data: MarketDataCapability = field(
        default_factory=MarketDataCapability)
    orders: OrderCapability = field(default_factory=OrderCapability)
    fees: FeeCapability = field(default_factory=FeeCapability)
    paper_support: str = "UNKNOWN"  # SUPPORTED | UNSUPPORTED | UNKNOWN
    live_support: str = "UNKNOWN"
    credentials_required: str = "UNKNOWN"  # YES | NO | UNKNOWN
    commercial_rights: str = "UNKNOWN"
    redistribution_rights: str = "UNKNOWN"
    status: str = "UNKNOWN"  # ACTIVE | DEPRECATED | UNKNOWN
    notes: str = "UNKNOWN"

    def __post_init__(self) -> None:
        for f in ("paper_support", "live_support"):
            if getattr(self, f) not in ("SUPPORTED", "UNSUPPORTED", "UNKNOWN"):
                raise ValueError(f"{f} must be SUPPORTED/UNSUPPORTED/UNKNOWN")


@dataclass(frozen=True)
class Venue:
    venue_id: str  # canonical id, e.g. "XNYS", "binance", "polymarket"
    name: str = "UNKNOWN"
    venue_type: str = "UNKNOWN"  # EXCHANGE | CLOB | BROKER | DATA_VENDOR | UNKNOWN
    country: str = "UNKNOWN"
    timezone: str = "UNKNOWN"  # IANA name or UNKNOWN (never guessed)
    website: str = "UNKNOWN"
    asset_classes: tuple = ()  # tuple[AssetClass, ...]
    capabilities: VenueCapability = field(default_factory=VenueCapability)
    rights_basis: str = "UNKNOWN"
    provenance: str = "UNKNOWN"  # e.g. "ccxt-4.5.46:describe:offline"
    status: str = "UNKNOWN"

    def __post_init__(self) -> None:
        if not self.venue_id:
            raise ValueError("Venue needs a venue_id")
        for a in self.asset_classes:
            if not isinstance(a, AssetClass):
                raise ValueError(f"asset_classes must be AssetClass (got {a!r})")

    def supports(self, asset: AssetClass) -> str:
        """SUPPORTED if listed, UNKNOWN otherwise (never UNSUPPORTED by guess)."""
        return "SUPPORTED" if asset in self.asset_classes else "UNKNOWN"


@dataclass(frozen=True)
class MarketInstrument:
    instrument_id: str  # canonical, e.g. "XNYS:LMT", "binance:BTC/USDT"
    venue_id: str
    symbol: str  # venue-native symbol
    asset_class: AssetClass = AssetClass.UNKNOWN
    base: str = "UNKNOWN"
    quote: str = "UNKNOWN"
    market_type: str = "UNKNOWN"  # spot | swap | future | option | binary | UNKNOWN
    settlement: SettlementType = SettlementType.UNKNOWN
    tick_size: Optional[float] = None
    lot_size: Optional[float] = None
    precision: str = "UNKNOWN"
    limits: str = "UNKNOWN"  # free-text summary or UNKNOWN (detail in venue docs)
    provenance: str = "UNKNOWN"
    rights: str = "UNKNOWN"
    status: str = "UNKNOWN"

    def __post_init__(self) -> None:
        if not self.instrument_id or not self.venue_id or not self.symbol:
            raise ValueError("MarketInstrument needs instrument_id + venue_id + symbol")
        if not isinstance(self.asset_class, AssetClass):
            raise ValueError("asset_class must be AssetClass")
        if not isinstance(self.settlement, SettlementType):
            raise ValueError("settlement must be SettlementType")


@dataclass(frozen=True)
class TradingSession:
    venue_id: str
    day: str  # YYYY-MM-DD
    state: TradingSessionState = TradingSessionState.UNKNOWN
    open_time: Optional[datetime] = None
    close_time: Optional[datetime] = None
    timezone: str = "UNKNOWN"
    basis: str = "UNKNOWN"  # OBSERVED | CALENDAR | UNKNOWN
    note: str = "UNKNOWN"

    def __post_init__(self) -> None:
        _require_tz("open_time", self.open_time)
        _require_tz("close_time", self.close_time)
        if not isinstance(self.state, TradingSessionState):
            raise ValueError("state must be TradingSessionState")


@dataclass(frozen=True)
class VenueReceipt:
    """Provenance receipt for any venue-metadata read (offline-first)."""

    receipt_id: str
    venue_id: str
    what: str  # e.g. "describe", "markets-shape", "calendar-day"
    retrieved_at: str = "UNKNOWN"  # ISO ts or UNKNOWN
    basis: str = "UNKNOWN"  # OBSERVED_OFFLINE | VENDOR_DOCS | UNKNOWN
    rights: str = "UNKNOWN"  # per-venue rights or UNKNOWN
    source_version: str = "UNKNOWN"  # e.g. "ccxt-4.5.46"
    raw_hash: str = "UNKNOWN"
    notes: str = "UNKNOWN"
