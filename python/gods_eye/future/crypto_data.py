"""FUTURE-ONLY crypto market-data adapter boundaries (offline metadata only).

CryptoMarketDataAdapter: symbol/venue/trade/quote/book/funding shapes.
CryptoVenueMetadataAdapter: exchange metadata inventory with provenance +
rights. No credentials, no trading, no network in tests. Any future fetch
persists provenance + rights info (never assumed).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def ccxt_available() -> bool:
    try:
        import ccxt  # noqa: F401
        return True
    except Exception:
        return False


def list_venues() -> Dict[str, Any]:
    """Offline venue inventory (no network; package metadata only)."""
    if not ccxt_available():
        return {"venues": [], "n": 0, "basis": "UNKNOWN",
                "note": "ccxt absent"}
    import ccxt
    return {"venues": sorted(ccxt.exchanges), "n": len(ccxt.exchanges),
            "basis": "OBSERVED (package metadata, offline)",
            "rights": "per-venue UNKNOWN until licensed",
            "provenance": f"ccxt-{ccxt.__version__}"}


def market_shape(exchange_id: str, symbol: str) -> Dict[str, Any]:
    """The canonical market-structure shape we map (no fetch in V14)."""
    return {"exchange": exchange_id, "symbol": symbol,
            "fields": ["symbol", "base", "quote", "spot", "swap", "future",
                       "option", "contractSize", "precision", "limits",
                       "maker", "taker", "funding"],
            "funding_metadata": ["fundingRate", "fundingTimestamp",
                                 "nextFundingRate", "markPrice", "indexPrice"],
            "status": "SHAPE_DEFINED (no fetch; rights UNKNOWN)"}


def record_fetch_provenance(exchange_id: str, what: str,
                            retrieved_at: str) -> Dict[str, Any]:
    return {"exchange": exchange_id, "what": what,
            "retrieved_at": retrieved_at, "rights": "UNKNOWN (record terms first)",
            "rule": "no fetched row enters a snapshot without rights + raw hash"}
