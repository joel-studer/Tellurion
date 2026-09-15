"""FUTURE-ONLY ccxt venue-metadata normalization (offline, deterministic, V15).

Uses ccxt as a generic crypto venue-metadata layer. Offline/public-safe
first: no `load_markets()` (network), no credentials, no orders.

What we normalize per exchange (from offline `describe()` + package
inventory, both deterministic for a pinned ccxt version):
  exchange id, name, urls, rate-limit, has-flags, required-credentials,
  maker/taker availability shape, funding-capability hint, order-capability
  hints, spot/perp support hints.

Anything that needs the network (symbols, precision, limits, live fees)
is returned as UNKNOWN with an explicit basis — never fetched silently.
A `normalize_markets()` helper maps an explicitly supplied market dict
(e.g. a vendored fixture or a caller-provided, rights-cleared snapshot)
into the canonical MarketInstrument shape; it never calls the network
itself. Provenance is persisted on every output.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

PROVENANCE_NOTE = "offline describe() only; no load_markets(), no keys, no orders"


def ccxt_available() -> bool:
    try:
        import ccxt  # noqa: F401
        return True
    except Exception:
        return False


def ccxt_version() -> str:
    if not ccxt_available():
        return "UNKNOWN"
    import ccxt
    return str(getattr(ccxt, "__version__", "UNKNOWN"))


def list_exchange_ids() -> Dict[str, Any]:
    """Offline inventory (package metadata only). Deterministic."""
    if not ccxt_available():
        return {"venues": [], "n": 0, "basis": "UNKNOWN",
                "note": "ccxt absent", "provenance": "UNKNOWN"}
    import ccxt
    venues = sorted(ccxt.exchanges)
    return {"venues": venues, "n": len(venues),
            "basis": "OBSERVED (package metadata, offline)",
            "rights": "per-venue UNKNOWN until licensed",
            "provenance": f"ccxt-{ccxt.__version__}",
            "note": PROVENANCE_NOTE}


def _unknown_market_fields() -> Dict[str, Any]:
    return {"symbol": "UNKNOWN", "base": "UNKNOWN", "quote": "UNKNOWN",
            "market_type": "UNKNOWN", "spot": "UNKNOWN", "swap": "UNKNOWN",
            "future": "UNKNOWN", "option": "UNKNOWN", "contract_size": "UNKNOWN",
            "precision": "UNKNOWN", "limits": "UNKNOWN",
            "maker": "UNKNOWN", "taker": "UNKNOWN",
            "funding": "UNKNOWN", "orders": "UNKNOWN"}


def describe_exchange(exchange_id: str) -> Dict[str, Any]:
    """Offline `describe()` normalization for one exchange id.

    Never touches the network. Unknown ids stay UNKNOWN (no exception
    leak — callers get a machine-readable UNKNOWN row).
    """
    if not ccxt_available():
        return {"exchange": exchange_id, "status": "UNKNOWN",
                "basis": "UNKNOWN", "note": "ccxt absent",
                "provenance": "UNKNOWN", **_unknown_market_fields()}
    import ccxt
    if exchange_id not in ccxt.exchanges:
        return {"exchange": exchange_id, "status": "UNKNOWN",
                "basis": "UNKNOWN", "note": "unknown exchange id",
                "provenance": f"ccxt-{ccxt.__version__}",
                **_unknown_market_fields()}
    ex = getattr(ccxt, exchange_id)()
    try:
        d: Dict[str, Any] = ex.describe()
    except Exception as e:
        return {"exchange": exchange_id, "status": "UNKNOWN",
                "basis": "UNKNOWN", "note": f"describe failed: {type(e).__name__}",
                "provenance": f"ccxt-{ccxt.__version__}",
                **_unknown_market_fields()}
    has = d.get("has") or {}
    urls = d.get("urls") or {}
    fees = d.get("fees") or {}
    has_keys = sorted(has.keys())

    def _tri(v: Any) -> str:
        if v is True:
            return "SUPPORTED"
        if v is False:
            return "UNSUPPORTED"
        return "UNKNOWN"

    funding_hint = _tri(has.get("fetchFundingRate"))
    if funding_hint == "UNKNOWN" and isinstance(has.get("funding"), bool):
        funding_hint = _tri(has.get("funding"))
    spot_hint = _tri(has.get("fetchMarkets"))  # markets endpoint exists; type UNKNOWN
    return {
        "exchange": exchange_id,
        "name": d.get("name", "UNKNOWN"),
        "status": "DESCRIBED_OFFLINE",
        "basis": "OBSERVED (offline describe(), no markets fetch)",
        "provenance": f"ccxt-{ccxt.__version__}",
        "note": PROVENANCE_NOTE,
        "urls": {"api": (urls.get("api") or "UNKNOWN"),
                 "www": (urls.get("www") or "UNKNOWN")},
        "rate_limit_ms": d.get("rateLimit", "UNKNOWN"),
        "required_credentials": d.get("requiredCredentials", "UNKNOWN"),
        "certified": d.get("certified", "UNKNOWN"),
        "pro": d.get("pro", "UNKNOWN"),
        "has_keys": has_keys,
        "spot_markets_endpoint": _tri(has.get("fetchMarkets")),
        "fetch_ticker": _tri(has.get("fetchTicker")),
        "fetch_trades": _tri(has.get("fetchTrades")),
        "fetch_order_book": _tri(has.get("fetchOrderBook")),
        "fetch_ohlcv": _tri(has.get("fetchOHLCV")),
        "fetch_funding_rate": _tri(has.get("fetchFundingRate")),
        "funding_capability": funding_hint,
        "spot_perp_hint": spot_hint,
        "create_order": _tri(has.get("createOrder")),
        "cancel_order": _tri(has.get("cancelOrder")),
        "fees_shape": sorted(fees.keys()) if isinstance(fees, dict) else "UNKNOWN",
        "timeframes": sorted((d.get("timeframes") or {}).keys()),
        # Live-market fields: explicitly UNKNOWN offline (never fetched).
        "symbol": "UNKNOWN",
        "markets": "UNKNOWN (needs load_markets over network; not done)",
        "precision": "UNKNOWN (needs load_markets; not done)",
        "limits": "UNKNOWN (needs load_markets; not done)",
        "maker": "UNKNOWN (needs load_markets; not done)",
        "taker": "UNKNOWN (needs load_markets; not done)",
        "rights": "per-venue UNKNOWN until licensed",
    }


def normalize_market_dict(exchange_id: str, market: Dict[str, Any]) -> Dict[str, Any]:
    """Map one caller-supplied ccxt-style market dict to canonical shape.

    `market` must come from a rights-cleared snapshot or fixture passed in
    by the caller — this function performs no I/O. Deterministic: same
    input dict -> same output dict. Provenance of the mapping (not of the
    data) is stamped; the data's own rights stay UNKNOWN unless the caller
    supplies them.
    """
    m = dict(market or {})
    symbol = m.get("symbol", "UNKNOWN")
    base = m.get("base", "UNKNOWN")
    quote = m.get("quote", "UNKNOWN")
    spot = m.get("spot")
    swap = m.get("swap")
    future = m.get("future")
    option = m.get("option")
    if swap is True:
        market_type = "swap"
    elif future is True:
        market_type = "future"
    elif option is True:
        market_type = "option"
    elif spot is True:
        market_type = "spot"
    else:
        market_type = "UNKNOWN"
    return {
        "exchange": exchange_id,
        "symbol": symbol,
        "base": base,
        "quote": quote,
        "market_type": market_type,
        "spot": spot if isinstance(spot, bool) else "UNKNOWN",
        "swap": swap if isinstance(swap, bool) else "UNKNOWN",
        "future": future if isinstance(future, bool) else "UNKNOWN",
        "option": option if isinstance(option, bool) else "UNKNOWN",
        "contract_size": m.get("contractSize", "UNKNOWN"),
        "precision": m.get("precision", "UNKNOWN"),
        "limits": m.get("limits", "UNKNOWN"),
        "maker": m.get("maker", "UNKNOWN"),
        "taker": m.get("taker", "UNKNOWN"),
        "funding": {k: m.get(k, "UNKNOWN") for k in
                    ("fundingRate", "fundingTimestamp", "markPrice", "indexPrice")},
        "order_capabilities": "UNKNOWN (venue docs; not inferred)",
        "rights": m.get("rights", "UNKNOWN (record terms first)"),
        "provenance": (f"ccxt-{ccxt_version()}:normalize_market_dict "
                       f"(caller-supplied snapshot; no fetch)"),
        "status": "NORMALIZED (offline mapping, no network)",
    }


def record_provenance(exchange_id: str, what: str,
                      retrieved_at: str) -> Dict[str, Any]:
    return {"exchange": exchange_id, "what": what,
            "retrieved_at": retrieved_at,
            "rights": "UNKNOWN (record terms first)",
            "provenance": f"ccxt-{ccxt_version()}",
            "note": PROVENANCE_NOTE,
            "rule": "no fetched row enters a snapshot without rights + raw hash"}
