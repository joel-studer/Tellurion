"""FUTURE-ONLY prediction-market canonical model (open-core safe, V15).

Generic public-safe contracts for YES/NO, multi-outcome, tokenized
outcomes, and CLOB markets. Proprietary resolution intelligence, event
mapping, timing edge, and settlement edge are OUT OF SCOPE and must
never enter this module (no imports, no fields, no hooks for them).

Stdlib-only. No I/O, no network, no credentials.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class BinaryOutcome(str, Enum):
    YES = "YES"
    NO = "NO"
    UNKNOWN = "UNKNOWN"


def _require_tz(name: str, ts: Optional[datetime]) -> None:
    if ts is not None and (ts.tzinfo is None or ts.utcoffset() is None):
        raise ValueError(f"{name} must be timezone-aware (got naive)")


@dataclass(frozen=True)
class ProbabilityPrice:
    """Price-as-probability for a binary outcome (0..1). No edge implied."""

    outcome: BinaryOutcome = BinaryOutcome.UNKNOWN
    price: Optional[float] = None  # None == UNKNOWN
    currency: str = "UNKNOWN"
    event_time: Optional[datetime] = None
    source: str = "UNKNOWN"
    provenance: str = "UNKNOWN"

    def __post_init__(self) -> None:
        _require_tz("event_time", self.event_time)
        if not isinstance(self.outcome, BinaryOutcome):
            raise ValueError("outcome must be BinaryOutcome")
        if self.price is not None and not (0.0 <= self.price <= 1.0):
            raise ValueError("probability price must be in [0, 1]")

    def implied_probability(self) -> Optional[float]:
        return self.price


@dataclass(frozen=True)
class OutcomeToken:
    """Tokenized outcome share (e.g. YES/NO ERC-1155 style). Mechanics only."""

    token_id: str
    market_id: str
    outcome: BinaryOutcome = BinaryOutcome.UNKNOWN
    outcome_label: str = "UNKNOWN"  # for multi-outcome legs
    collateral: str = "UNKNOWN"  # e.g. "pUSD" or UNKNOWN
    decimals: Optional[int] = None
    mint_status: str = "UNKNOWN"
    provenance: str = "UNKNOWN"

    def __post_init__(self) -> None:
        if not self.token_id or not self.market_id:
            raise ValueError("OutcomeToken needs token_id + market_id")
        if not isinstance(self.outcome, BinaryOutcome):
            raise ValueError("outcome must be BinaryOutcome")


@dataclass(frozen=True)
class ResolutionRuleReference:
    """Pointer to human-readable resolution rules. Never the resolution itself."""

    market_id: str
    rules_uri: str = "UNKNOWN"
    rules_hash: str = "UNKNOWN"  # content hash when archived, else UNKNOWN
    resolver: str = "UNKNOWN"  # who resolves per public docs, or UNKNOWN
    resolve_time: Optional[datetime] = None  # None == unresolved/UNKNOWN
    status: str = "UNKNOWN"  # OPEN | RESOLVED | VOIDED | UNKNOWN
    provenance: str = "UNKNOWN"

    def __post_init__(self) -> None:
        _require_tz("resolve_time", self.resolve_time)
        if not self.market_id:
            raise ValueError("ResolutionRuleReference needs market_id")
        if self.status not in ("OPEN", "RESOLVED", "VOIDED", "UNKNOWN"):
            raise ValueError("status must be OPEN/RESOLVED/VOIDED/UNKNOWN")


@dataclass(frozen=True)
class BinaryMarket:
    """One YES/NO question with two outcome tokens on a venue."""

    market_id: str
    venue_id: str = "UNKNOWN"
    question: str = "UNKNOWN"
    yes_token: Optional[OutcomeToken] = None
    no_token: Optional[OutcomeToken] = None
    tick_size: Optional[float] = None
    min_notional: Optional[float] = None
    currency: str = "UNKNOWN"
    market_type: str = "CLOB"  # CLOB | AMM | ORDER_BOOK | UNKNOWN
    status: str = "UNKNOWN"  # OPEN | CLOSED | RESOLVED | VOIDED | UNKNOWN
    resolution: Optional[ResolutionRuleReference] = None
    provenance: str = "UNKNOWN"
    rights: str = "UNKNOWN"

    def __post_init__(self) -> None:
        if not self.market_id:
            raise ValueError("BinaryMarket needs market_id")
        if self.status not in ("OPEN", "CLOSED", "RESOLVED", "VOIDED", "UNKNOWN"):
            raise ValueError(f"unknown market status: {self.status}")

    def tokens(self) -> tuple:
        return tuple(t for t in (self.yes_token, self.no_token) if t is not None)


@dataclass(frozen=True)
class MultiOutcomeMarket:
    """One question with N>2 labelled outcomes (winner-takes-all or UNKNOWN)."""

    market_id: str
    venue_id: str = "UNKNOWN"
    question: str = "UNKNOWN"
    outcomes: tuple = ()  # tuple[OutcomeToken, ...]
    currency: str = "UNKNOWN"
    market_type: str = "UNKNOWN"
    status: str = "UNKNOWN"
    resolution: Optional[ResolutionRuleReference] = None
    provenance: str = "UNKNOWN"
    rights: str = "UNKNOWN"

    def __post_init__(self) -> None:
        if not self.market_id:
            raise ValueError("MultiOutcomeMarket needs market_id")
        if self.status not in ("OPEN", "CLOSED", "RESOLVED", "VOIDED", "UNKNOWN"):
            raise ValueError(f"unknown market status: {self.status}")

    def outcome_labels(self) -> tuple:
        return tuple(getattr(t, "outcome_label", "UNKNOWN") for t in self.outcomes)


@dataclass(frozen=True)
class SettlementReceipt:
    """Public settlement bookkeeping (statuses only — no private edge)."""

    receipt_id: str
    market_id: str
    venue_id: str = "UNKNOWN"
    status: str = "UNKNOWN"  # MATCHED | MINED | RETRYING | CONFIRMED | FAILED | VOIDED | UNKNOWN
    settled_outcome: str = "UNKNOWN"
    payout_per_share: Optional[float] = None
    currency: str = "UNKNOWN"
    settle_time: Optional[datetime] = None
    tx_ref: str = "UNKNOWN"  # public tx hash or UNKNOWN (never a secret)
    provenance: str = "UNKNOWN"

    def __post_init__(self) -> None:
        _require_tz("settle_time", self.settle_time)
        if not self.receipt_id or not self.market_id:
            raise ValueError("SettlementReceipt needs receipt_id + market_id")
        if self.status not in ("MATCHED", "MINED", "RETRYING", "CONFIRMED",
                               "FAILED", "VOIDED", "UNKNOWN"):
            raise ValueError(f"unknown settlement status: {self.status}")
