"""Extension slots: optional capabilities supplied by downstream packages.

The open-source core defines a slot and calls it; it never imports the
provider. An unfilled slot raises :class:`ExtensionUnavailable` with a
fix hint instead of a bare ``ModuleNotFoundError``.

    from gods_eye.future import extensions

    extensions.register("portfolio.eligibility", my_eligibility_module)

A provider is any object exposing the attributes named in the slot
contract (a module, a class instance, or a ``types.SimpleNamespace``).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

SLOTS: Dict[str, str] = {
    "portfolio.eligibility":
        "assert_eligible(input) -> input; raises on ineligible strategy inputs",
    "portfolio.risk_measures":
        "volatility(strategy_id, returns) -> estimate with .value; METHOD_VERSION",
    "portfolio.correlation":
        "pearson(a_id, b_id, a_returns, b_returns) -> estimate",
    "portfolio.capacity":
        "estimate_capacity(strategy_id) -> estimate",
    "portfolio.explain":
        "explain(candidate, rule=...) -> AllocationReceipt",
    "portfolio.stress":
        "apply_scenario(candidate, scenario) -> dict",
    "portfolio.manifest":
        "PortfolioRunManifest.build(strategy_ids, weights=..., ...) -> manifest",
    "execution.fillability":
        "assess_fillability(intent, market, tier) -> assessment",
}

_providers: Dict[str, Any] = {}


class ExtensionUnavailable(NotImplementedError):
    """Raised when core code calls a slot that has no registered provider."""


def _check_slot(slot: str) -> None:
    if slot not in SLOTS:
        raise KeyError(f"unknown extension slot: {slot!r} "
                       f"(known: {sorted(SLOTS)})")


def register(slot: str, provider: Any) -> Dict[str, str]:
    """Register ``provider`` for ``slot``; replaces any previous provider."""
    _check_slot(slot)
    if provider is None:
        raise ValueError("provider must not be None (use unregister)")
    _providers[slot] = provider
    name = getattr(provider, "__name__", type(provider).__name__)
    return {"slot": slot, "provider": str(name)}


def get(slot: str) -> Any:
    """Return the provider for ``slot`` or raise ExtensionUnavailable."""
    _check_slot(slot)
    try:
        return _providers[slot]
    except KeyError:
        raise ExtensionUnavailable(
            f"extension slot {slot!r} has no provider. The open-source core "
            f"defines this capability but does not implement it. Register "
            f"one with gods_eye.future.extensions.register({slot!r}, "
            f"provider). Contract: {SLOTS[slot]}") from None


def available(slot: str) -> bool:
    _check_slot(slot)
    return slot in _providers


def unregister(slot: Optional[str] = None) -> None:
    """Remove one provider, or all providers when ``slot`` is None."""
    if slot is None:
        _providers.clear()
        return
    _check_slot(slot)
    _providers.pop(slot, None)


def describe() -> Dict[str, Any]:
    return {"schema": "extensions-v1",
            "slots": {s: {"contract": c, "provided": s in _providers}
                      for s, c in sorted(SLOTS.items())}}
