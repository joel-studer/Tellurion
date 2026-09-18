"""Extension slots: optional capabilities supplied by downstream packages.

The open-source core defines a slot and calls it; it never imports the
provider. An unfilled slot raises :class:`ExtensionUnavailable` with a
fix hint instead of a bare ``ModuleNotFoundError``.

    from gods_eye.future import extensions

    extensions.register("some.capability", my_provider_module)

A provider is any object exposing the attributes named in the slot
contract (a module, a class instance, or a ``types.SimpleNamespace``).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

# V1 declares no slots: the trading capabilities these once named
# left with the trading surface. The mechanism stays because it is
# the seam downstream packages plug into, and because the core
# adds a slot here the moment it needs a capability it will not
# implement itself.
SLOTS: Dict[str, str] = {}

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
