"""FUTURE-ONLY PyPortfolioOpt secondary validator (lightweight, optional).

Same fixture inputs as the skfolio-shaped path. Compares weights, risk
(volatility leg), and constraint satisfaction. Verdicts: AGREE / PARTIAL /
DISAGREE / UNKNOWN. Disagreement means INVESTIGATE — never pick the
higher-return weights.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def pypfopt_available() -> bool:
    try:
        import pypfopt  # noqa: F401
        return True
    except Exception:
        return False


def compare_weights(primary: List[tuple], secondary: List[tuple],
                    tol: float = 1e-6) -> Dict[str, Any]:
    p, s = dict(primary), dict(secondary)
    if set(p) != set(s):
        return {"verdict": "DISAGREE", "reason": "weight universe mismatch"}
    dev = max(abs(p[k] - s[k]) for k in p) if p else 0.0
    verdict = "AGREE" if dev <= tol else ("PARTIAL" if dev <= 0.05 else "DISAGREE")
    return {"verdict": verdict, "max_abs_dev": dev,
            "rule": "INVESTIGATE on anything but AGREE"}


def fixture_secondary(inputs: List[Any]) -> List[tuple]:
    """Inverse-volatility fixture as the stand-in second implementation."""
    from gods_eye.future.portfolio import PortfolioConstraintSet
    from gods_eye.future.portfolio_optimizer import FixturePortfolioOptimizer
    opt = FixturePortfolioOptimizer("inverse_volatility")
    return list(opt.optimize(inputs, PortfolioConstraintSet()).weights)
