"""FUTURE-ONLY skfolio lazy wrapper (probe + fixture smoke, no install).

Availability probe first: without skfolio installed every optimizer call
explains the disabled state. The fixture smoke path runs the identical
mapping (eligible inputs → weights → AllocationReceipt +
PortfolioRunManifest) so the wiring PR only swaps the numeric kernel.
"""

from __future__ import annotations

from typing import Any, Dict, List

PINNED = {"skfolio": "unpinned (not installed; pin at wiring PR + SBOM)"}


def skfolio_available() -> bool:
    try:
        import skfolio  # noqa: F401
        return True
    except Exception:
        return False


def smoke_optimize(inputs: List[Any], rule: str = "MeanRisk") -> Dict[str, Any]:
    """Fixture smoke through the skfolio-shaped mapping (no skfolio needed)."""
    from gods_eye.future.portfolio import PortfolioConstraintSet
    from gods_eye.future import extensions
    PortfolioRunManifest = extensions.get("portfolio.manifest").PortfolioRunManifest
    from gods_eye.future.portfolio_optimizer import FixturePortfolioOptimizer
    opt = FixturePortfolioOptimizer("equal_weight")
    cand = opt.optimize(inputs, PortfolioConstraintSet())
    rec = opt.explain_allocation(cand)
    m = PortfolioRunManifest.build([i.strategy_id for i in inputs],
                                   weights=[(s, w) for s, w in cand.weights],
                                   optimizer="skfolio-shape", optimizer_version="v1")
    return {"rule": rule, "weights": cand.weights, "receipt_id": rec.receipt_id,
            "manifest_id": m.id, "backend": "skfolio" if skfolio_available() else "fixture-kernel",
            "status": "SMOKE (real kernel at wiring PR)"}
