"""FUTURE-ONLY generic provider adapter contract.

One interface every future market-data provider implements. Methods a
provider does not support MUST return :data:`UNSUPPORTED` (never empty
success — empty success hides gaps and downstream code would mistake it
for "no data"). Capability discovery via describe_capabilities() feeds
the snapshot builder (which refuses ambiguous material fields).

No real provider wiring here (fixtures-first). Heavy client libraries
(ccxt, lse-data, pandas) must never be imported at module scope.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class Unsupported:
    """Sentinel: provider does not offer this method. Always explicit."""

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return "UNSUPPORTED"


UNSUPPORTED = Unsupported()


class ProviderAdapter(ABC):
    """Generic future market-data provider (lawful sources only)."""

    provider_name: str = "UNKNOWN"

    @abstractmethod
    def describe_capabilities(self) -> Dict[str, Any]:
        """provider, venues, asset_classes, bars/ticks/quotes/book flags,
        timezone_semantics, corporate_action_policy, survivorship_policy,
        retrieval_time, method. UNKNOWN where unmeasured."""
        raise NotImplementedError

    @abstractmethod
    def list_instruments(self, asset_class: str = "UNKNOWN") -> Any:
        raise NotImplementedError

    @abstractmethod
    def fetch_bars(self, instrument_id: str, resolution: str,
                   start: str, end: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    def fetch_quotes(self, instrument_id: str, start: str, end: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    def fetch_trades(self, instrument_id: str, start: str, end: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    def fetch_order_book(self, instrument_id: str, depth: str,
                         start: str, end: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    def fetch_corporate_actions(self, instrument_id: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    def fetch_fundamentals(self, instrument_id: str, as_of: str) -> Any:
        raise NotImplementedError


class FixtureAdapter(ProviderAdapter):
    """In-memory fixture provider for tests/lab (no network, no secrets)."""

    def __init__(self, caps: Dict[str, Any],
                 store: Optional[Dict[str, List[Dict[str, Any]]]] = None):
        self._caps = dict(caps)
        self._store = store or {}

    provider_name = "fixture"

    def describe_capabilities(self) -> Dict[str, Any]:
        base = {"provider": "fixture", "provider_version": "fixture-v1",
                "retrieval_time": "UNKNOWN", "method": "fixture",
                "venues": (), "asset_classes": (), "bars": False,
                "ticks": False, "quotes": False, "book": "NONE",
                "timezone_semantics": "UNKNOWN",
                "corporate_action_policy": "UNKNOWN",
                "survivorship_policy": "UNKNOWN"}
        base.update(self._caps)
        return base

    def _get(self, kind: str, key: str) -> Any:
        vals = self._store.get(f"{kind}:{key}")
        return vals if vals is not None else UNSUPPORTED

    def list_instruments(self, asset_class: str = "UNKNOWN") -> Any:
        return self._get("instruments", asset_class)

    def fetch_bars(self, instrument_id: str, resolution: str,
                   start: str, end: str) -> Any:
        return self._get("bars", instrument_id)

    def fetch_quotes(self, instrument_id: str, start: str, end: str) -> Any:
        return self._get("quotes", instrument_id)

    def fetch_trades(self, instrument_id: str, start: str, end: str) -> Any:
        return self._get("trades", instrument_id)

    def fetch_order_book(self, instrument_id: str, depth: str,
                         start: str, end: str) -> Any:
        return self._get("book", instrument_id)

    def fetch_corporate_actions(self, instrument_id: str) -> Any:
        return self._get("actions", instrument_id)

    def fetch_fundamentals(self, instrument_id: str, as_of: str) -> Any:
        return self._get("fundamentals", instrument_id)
