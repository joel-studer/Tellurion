"""FUTURE-ONLY TCA benchmark contracts (measurements, honest GAP).

No mature unified OSS TCA exists (tcapy: FX-only/alpha/stale; equity-tca:
demo app; flowpy*: researchy). This module defines benchmark/measurement
shapes — arrival price, TWAP/VWAP benchmarks, implementation-shortfall
decomposition, spread decomposition — without claiming a calibrated
impact model. orderflow-metrics (MIT, dependency-free) is the WRAP_NOW
candidate for the numeric blocks when the market env is created.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

BENCHMARKS = ("arrival", "twap", "vwap", "mid", "close", "UNKNOWN")


@dataclass(frozen=True)
class TCABenchmark:
    name: str
    price: Optional[float] = None  # None == UNKNOWN
    basis: str = "UNKNOWN"

    def __post_init__(self) -> None:
        if self.name not in BENCHMARKS:
            raise ValueError(f"unknown TCA benchmark: {self.name}")


@dataclass(frozen=True)
class ShortfallDecomposition:
    execution: Optional[float] = None
    opportunity: Optional[float] = None
    fees: Optional[float] = None
    basis: str = "UNKNOWN"

    def total(self) -> Optional[float]:
        parts = (self.execution, self.opportunity, self.fees)
        if any(p is None for p in parts):
            return None
        return sum(p for p in parts if p is not None)


def arrival_slippage_bps(side: str, arrival: Optional[float],
                         fill: Optional[float]) -> Optional[float]:
    if arrival is None or fill is None or arrival == 0:
        return None
    sign = 1.0 if side == "BUY" else -1.0
    return sign * (fill - arrival) / abs(arrival) * 10_000.0


def square_root_impact(vol: Optional[float], qty: Optional[float],
                       adv: Optional[float], coeff: float = 1.0) -> Optional[float]:
    """Y·σ·√(Q/V) shape only — coeff UNCALIBRATED, result is an assumption."""
    if vol is None or qty is None or adv is None or adv <= 0:
        return None
    return coeff * vol * (qty / adv) ** 0.5


def describe_gap() -> dict:
    return {"unified_tca": "GAP (no mature maintained OSS; tcapy stale/FX-only)",
            "blocks": "orderflow-metrics WRAP_NOW (OFI/VPIN/impact/IS)",
            "rule": "impact numbers stay labelled assumptions until calibrated"}
