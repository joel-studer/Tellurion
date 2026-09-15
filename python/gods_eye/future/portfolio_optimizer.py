"""FUTURE-ONLY portfolio optimizer boundary (fixtures only in V13).

FixturePortfolioOptimizer implements transparent, auditable rules
(equal weight / inverse volatility) over eligible fixture inputs —
never a claim of optimality. Eligibility, risk, correlation, capacity,
explanation, and stress helpers are extension slots
(:mod:`gods_eye.future.extensions`) supplied by downstream packages. SkfolioPortfolioAdapter is a DISABLED
stub documenting the intended mapping; it never imports skfolio.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from gods_eye.future import extensions
from gods_eye.future.portfolio import (AllocationReceipt, PortfolioCandidate,
                                       PortfolioConstraintSet, RiskReceipt)

FORBIDDEN_IMPORTS = ("skfolio", "pypfopt", "riskfolio", "cvxpy", "pyfolio",
                     "empyrical", "alphalens", "torch")


class PortfolioOptimizerAdapter(ABC):
    optimizer_name: str = "UNKNOWN"

    @abstractmethod
    def validate_inputs(self, inputs: List[Any]) -> List[Any]:
        raise NotImplementedError

    @abstractmethod
    def estimate_risk(self, inputs: List[Any]) -> RiskReceipt:
        raise NotImplementedError

    @abstractmethod
    def estimate_correlation(self, inputs: List[Any]) -> List[Any]:
        raise NotImplementedError

    @abstractmethod
    def estimate_capacity(self, inputs: List[Any]) -> List[Any]:
        raise NotImplementedError

    @abstractmethod
    def optimize(self, inputs: List[Any],
                 constraints: PortfolioConstraintSet) -> PortfolioCandidate:
        raise NotImplementedError

    @abstractmethod
    def explain_allocation(self, candidate: PortfolioCandidate) -> AllocationReceipt:
        raise NotImplementedError

    @abstractmethod
    def stress_test(self, candidate: PortfolioCandidate,
                    scenarios: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        raise NotImplementedError


class FixturePortfolioOptimizer(PortfolioOptimizerAdapter):
    """Equal-weight / inverse-volatility over eligible fixtures only."""

    optimizer_name = "fixture"
    optimizer_version = "fixture-v1"

    def __init__(self, rule: str = "equal_weight"):
        if rule not in ("equal_weight", "inverse_volatility"):
            raise ValueError(f"unknown fixture rule: {rule}")
        self._rule = rule

    def validate_inputs(self, inputs: List[Any]) -> List[Any]:
        eligibility = extensions.get("portfolio.eligibility")
        return [eligibility.assert_eligible(i) for i in inputs]

    def estimate_risk(self, inputs: List[Any]) -> RiskReceipt:
        rm = extensions.get("portfolio.risk_measures")
        ests = []
        for i in inputs:
            rets = tuple(getattr(i, "returns", ()) or ())
            ests.append(rm.volatility(i.strategy_id, list(rets)))
        return RiskReceipt("RISK-FIX", "cand-UNKNOWN", tuple(ests), "DERIVED",
                           rm.METHOD_VERSION, "fixture rule")

    def estimate_correlation(self, inputs: List[Any]) -> List[Any]:
        co = extensions.get("portfolio.correlation")
        out = []
        for a in range(len(inputs)):
            for b in range(a + 1, len(inputs)):
                ra = list(getattr(inputs[a], "returns", ()) or ())
                rb = list(getattr(inputs[b], "returns", ()) or ())
                out.append(co.pearson(inputs[a].strategy_id,
                                      inputs[b].strategy_id, ra, rb))
        return out

    def estimate_capacity(self, inputs: List[Any]) -> List[Any]:
        cap = extensions.get("portfolio.capacity")
        return [cap.estimate_capacity(i.strategy_id) for i in inputs]

    def _weights(self, inputs: List[Any],
                 constraints: PortfolioConstraintSet) -> List[tuple]:
        ids = [i.strategy_id for i in inputs]
        if self._rule == "equal_weight":
            w = 1.0 / len(ids) if ids else 0.0
            raw = [(sid, w) for sid in sorted(ids)]
        else:
            rm = extensions.get("portfolio.risk_measures")
            vols = []
            for i in inputs:
                v = rm.volatility(i.strategy_id,
                                  list(getattr(i, "returns", ()) or ())).value
                vols.append((i.strategy_id, v if v and v > 0 else None))
            known = [(s, v) for s, v in vols if v is not None]
            if not known:
                raw = [(sid, 1.0 / len(ids)) for sid in sorted(ids)] if ids else []
            else:
                inv = [(s, 1.0 / v) for s, v in known]
                tot = sum(v for _, v in inv)
                raw = sorted([(s, v / tot) for s, v in inv])
                missing = sorted(set(ids) - {s for s, _ in raw})
                if missing:  # unknown-vol legs stay 0, labelled via unknowns
                    raw = raw + [(s, 0.0) for s in missing]
        return self._apply_constraints(raw, constraints)

    @staticmethod
    def _apply_constraints(raw: List[tuple],
                           c: PortfolioConstraintSet) -> List[tuple]:
        w = dict(raw)
        for sid, mx in c.max_weights:
            if sid in w:
                w[sid] = min(w[sid], mx)
        for sid, mn in c.min_weights:
            if sid in w:
                w[sid] = max(w[sid], mn)
        if c.max_concentration is not None:
            for sid in w:
                w[sid] = min(w[sid], c.max_concentration)
        if c.long_only:
            for sid in w:
                w[sid] = max(w[sid], 0.0)
        tot = sum(w.values())
        if tot > 0 and c.target_budget:
            w = {s: v / tot * c.target_budget for s, v in w.items()}
        return sorted(w.items())

    def optimize(self, inputs: List[Any],
                 constraints: PortfolioConstraintSet) -> PortfolioCandidate:
        eligible = self.validate_inputs(inputs)
        if not eligible:
            raise ValueError("no eligible inputs")
        weights = tuple(self._weights(eligible, constraints))
        return PortfolioCandidate("cand-fixture-1", weights, None, None,
                                  "GROSS_ONLY", self.optimizer_name,
                                  self.optimizer_version,
                                  f"rule={self._rule} (fixture, not optimal)")

    def explain_allocation(self, candidate: PortfolioCandidate) -> AllocationReceipt:
        explain = extensions.get("portfolio.explain").explain
        return explain(candidate, rule=self._rule)

    def stress_test(self, candidate: PortfolioCandidate,
                    scenarios: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        st = extensions.get("portfolio.stress")
        return [st.apply_scenario(candidate, s) for s in scenarios]


class SkfolioPortfolioAdapter(PortfolioOptimizerAdapter):
    """DISABLED stub: intended mapping GOD'S EYE inputs -> skfolio ->
    candidate weights -> AllocationReceipt. No install, no import, no use."""

    optimizer_name = "skfolio-stub-disabled"

    def _disabled(self) -> None:
        raise RuntimeError("SkfolioPortfolioAdapter DISABLED (V13 stub)")

    def validate_inputs(self, inputs: List[Any]) -> List[Any]:
        self._disabled()

    def estimate_risk(self, inputs: List[Any]) -> RiskReceipt:
        self._disabled()

    def estimate_correlation(self, inputs: List[Any]) -> List[Any]:
        self._disabled()

    def estimate_capacity(self, inputs: List[Any]) -> List[Any]:
        self._disabled()

    def optimize(self, inputs: List[Any],
                 constraints: PortfolioConstraintSet) -> PortfolioCandidate:
        self._disabled()

    def explain_allocation(self, candidate: PortfolioCandidate) -> AllocationReceipt:
        self._disabled()

    def stress_test(self, candidate: PortfolioCandidate,
                    scenarios: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        self._disabled()
