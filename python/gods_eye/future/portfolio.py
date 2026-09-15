"""FUTURE-ONLY canonical portfolio/risk contracts (infrastructure only).

Inputs pass the portfolio.eligibility extension slot first. No defaults
that flatter: correlation UNKNOWN (never 0), liquidity/capacity UNKNOWN
(never infinite), fees UNKNOWN (never 0), returns UNKNOWN (never normal).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class StrategyReturnSeries:
    strategy_id: str
    returns: tuple = ()  # per-period simple returns, oldest first
    periods: tuple = ()  # matching period labels (or empty == UNKNOWN)
    frequency: str = "UNKNOWN"
    dataset_id: str = "UNKNOWN"  # return dataset id (fixtures in V13)
    market_snapshot_id: str = "UNKNOWN"
    basis: str = "UNKNOWN"  # OBSERVED | SIMULATED_FIXTURE | UNKNOWN
    n: int = 0
    notes: str = "UNKNOWN"

    def __post_init__(self) -> None:
        if self.periods and len(self.periods) != len(self.returns):
            raise ValueError("periods/returns length mismatch")


@dataclass(frozen=True)
class StrategyExposure:
    strategy_id: str
    gross_exposure: Optional[float] = None
    net_exposure: Optional[float] = None
    leverage: Optional[float] = None
    basis: str = "UNKNOWN"
    notes: str = "UNKNOWN"


@dataclass(frozen=True)
class StrategyRiskEstimate:
    strategy_id: str
    measure: str  # volatility|downside|VaR|CVaR|EVaR|max_drawdown|CDaR|ulcer|...
    value: Optional[float] = None  # None == UNKNOWN
    sample_count: int = 0
    window: str = "UNKNOWN"
    basis: str = "UNKNOWN"
    method_version: str = "UNKNOWN"
    uncertainty: Optional[float] = None
    notes: str = "UNKNOWN"


@dataclass(frozen=True)
class CorrelationEstimate:
    pair: tuple  # (strategy_a, strategy_b)
    method: str = "UNKNOWN"  # Pearson|Spearman|rolling|tail_placeholder|cluster|UNKNOWN
    value: Optional[float] = None
    sample_count: int = 0
    window: str = "UNKNOWN"
    basis: str = "UNKNOWN"
    dependence_tags: tuple = ()  # same-event|same-market|same-factor|same-source|macro-regime
    notes: str = "UNKNOWN"


@dataclass(frozen=True)
class CapacityEstimate:
    strategy_id: str
    capacity_capital: Optional[float] = None
    uncertainty: Optional[float] = None
    binding_constraint: str = "UNKNOWN"
    basis: str = "UNKNOWN"  # OBSERVED|BOUNDED|MODELED|UNKNOWN
    method_version: str = "UNKNOWN"
    notes: str = "UNKNOWN"


@dataclass(frozen=True)
class LiquidityEstimate:
    strategy_id: str
    adv: Optional[float] = None
    spread_bps: Optional[float] = None
    depth: Optional[float] = None
    basis: str = "UNKNOWN"
    notes: str = "UNKNOWN"


@dataclass(frozen=True)
class DrawdownEstimate:
    strategy_id: str
    max_drawdown: Optional[float] = None
    avg_drawdown: Optional[float] = None
    ulcer_index: Optional[float] = None
    cdar: Optional[float] = None
    sample_count: int = 0
    basis: str = "UNKNOWN"
    notes: str = "UNKNOWN"


@dataclass(frozen=True)
class TailRiskEstimate:
    strategy_id: str
    var_95: Optional[float] = None
    cvar_95: Optional[float] = None
    evar_95: Optional[float] = None
    tail_ratio: Optional[float] = None
    expected_shortfall: Optional[float] = None
    sample_count: int = 0
    basis: str = "UNKNOWN"
    notes: str = "UNKNOWN"


@dataclass(frozen=True)
class PortfolioConstraintSet:
    long_only: bool = True
    min_weights: tuple = ()  # ((strategy_id, min), ...)
    max_weights: tuple = ()
    max_concentration: Optional[float] = None
    max_gross_exposure: Optional[float] = None
    max_turnover: Optional[float] = None
    group_limits: tuple = ()  # ((group, max_weight), ...)
    cardinality_max: Optional[int] = None
    target_budget: float = 1.0
    notes: str = "UNKNOWN"


@dataclass(frozen=True)
class PortfolioCandidate:
    candidate_id: str
    weights: tuple  # ((strategy_id, weight), ...) sorted by id
    gross_returns: Optional[float] = None  # None == UNKNOWN
    net_returns: Optional[float] = None  # None == UNKNOWN/gross-only
    cost_basis: str = "UNKNOWN"  # GROSS_ONLY | NET_OF_KNOWN_COSTS | UNKNOWN
    optimizer: str = "UNKNOWN"
    optimizer_version: str = "UNKNOWN"
    notes: str = "UNKNOWN"

    def weight_sum(self) -> float:
        return sum(w for _, w in self.weights)

    def weight_of(self, strategy_id: str) -> Optional[float]:
        for sid, w in self.weights:
            if sid == strategy_id:
                return w
        return None


@dataclass(frozen=True)
class AllocationReceipt:
    receipt_id: str
    candidate_id: str
    weights: tuple
    binding_constraints: tuple = ()
    dominant_risks: tuple = ()
    key_dependencies: tuple = ()
    unknowns: tuple = ()
    execution_notes: str = "UNKNOWN"


@dataclass(frozen=True)
class RiskReceipt:
    receipt_id: str
    candidate_id: str
    risk_estimates: tuple = ()  # StrategyRiskEstimate...
    basis: str = "UNKNOWN"
    method_version: str = "UNKNOWN"
    notes: str = "UNKNOWN"
