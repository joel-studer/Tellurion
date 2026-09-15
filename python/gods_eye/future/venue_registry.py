"""FUTURE-ONLY venue capability matrix (machine-readable, V15).

Only verified facts. Anything unverified is the string "UNKNOWN" —
never guessed, never defaulted to a permissive value. Rights fields
are data-rights (not software licences). No network, no credentials.

Sources of verified facts in this file:
  * ccxt package metadata (offline: exchange ids, `describe()` shape for
    a small audited sample) — provenance recorded per row.
  * exchange_calendars / pandas_market_calendars availability (session leg).
  * docs/future/NAUTILUS_INTEGRATION_REVIEW.md (Polymarket adapter shape).
  * SEC EDGAR public-domain posture (docs + rights registry) for the
    data-vendor row.
Everything else is UNKNOWN.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "venue-capability-v1"

CAPABILITY_FIELDS = ("asset_classes", "public_metadata", "quotes", "trades",
                     "l1", "l2", "l3", "funding", "fees", "order_types",
                     "paper_support", "live_support", "historical_access",
                     "rights", "credentials_requirement", "websocket", "rest",
                     "commercial_rights", "redistribution_rights", "status")


def _row(venue_id: str, **kw: Any) -> Dict[str, Any]:
    base: Dict[str, Any] = {f: "UNKNOWN" for f in CAPABILITY_FIELDS}
    base.update({"venue_id": venue_id, "schema_version": SCHEMA_VERSION})
    base.update(kw)
    unknown = [f for f in CAPABILITY_FIELDS if base.get(f) == "UNKNOWN"]
    base["n_unknown"] = len(unknown)
    base["unknown_fields"] = sorted(unknown)
    return base


def _ccxt_prov(version: str) -> str:
    return f"ccxt-{version}:describe:offline"


def registry(ccxt_version: str = "UNKNOWN") -> List[Dict[str, Any]]:
    """Build the matrix. `ccxt_version` stamps provenance (no network)."""
    prov = _ccxt_prov(ccxt_version)
    return [
        _row(
            "polymarket",
            asset_classes=["PREDICTION_MARKET", "BINARY_CONTRACT"],
            public_metadata="SUPPORTED",
            quotes="UNKNOWN",
            trades="UNKNOWN",
            l1="UNKNOWN",
            l2="UNKNOWN",
            l3="UNKNOWN",
            funding="UNSUPPORTED",
            fees="SUPPORTED",
            order_types=["LIMIT", "MARKET", "IOC", "FOK"],
            paper_support="UNKNOWN",
            live_support="UNSUPPORTED",
            historical_access="UNKNOWN",
            rights="per-market UNKNOWN until licensed",
            credentials_requirement="YES",
            websocket="SUPPORTED",
            rest="SUPPORTED",
            commercial_rights="UNKNOWN",
            redistribution_rights="UNKNOWN",
            status="ACTIVE",
            provenance=("docs/future/NAUTILUS_INTEGRATION_REVIEW.md "
                        "(adapter shape: BINARY/pUSD/CLOB/FAK-FOK/cancel-only)"),
            note=("Execution stays DISABLED in this repo; row describes "
                  "public adapter shape only. Live use refused by exec_safety."),
        ),
        _row(
            "binance",
            asset_classes=["CRYPTO_SPOT", "CRYPTO_PERPETUAL"],
            public_metadata="SUPPORTED",
            quotes="UNKNOWN",
            trades="UNKNOWN",
            l1="UNKNOWN",
            l2="UNKNOWN",
            l3="UNKNOWN",
            funding="SUPPORTED",
            fees="UNKNOWN",
            order_types="UNKNOWN",
            paper_support="UNKNOWN",
            live_support="UNSUPPORTED",
            historical_access="UNKNOWN",
            rights="per-venue UNKNOWN until licensed",
            credentials_requirement="YES",
            websocket="SUPPORTED",
            rest="SUPPORTED",
            commercial_rights="UNKNOWN",
            redistribution_rights="UNKNOWN",
            status="ACTIVE",
            provenance=prov,
            note="ccxt offline inventory only; no fetch, no keys, no orders.",
        ),
        _row(
            "coinbase",
            asset_classes=["CRYPTO_SPOT"],
            public_metadata="SUPPORTED",
            quotes="UNKNOWN",
            trades="UNKNOWN",
            l1="UNKNOWN",
            l2="UNKNOWN",
            l3="UNKNOWN",
            funding="UNKNOWN",
            fees="UNKNOWN",
            order_types="UNKNOWN",
            paper_support="UNKNOWN",
            live_support="UNSUPPORTED",
            historical_access="UNKNOWN",
            rights="per-venue UNKNOWN until licensed",
            credentials_requirement="YES",
            websocket="SUPPORTED",
            rest="SUPPORTED",
            commercial_rights="UNKNOWN",
            redistribution_rights="UNKNOWN",
            status="ACTIVE",
            provenance=prov,
            note="ccxt offline inventory only; no fetch, no keys, no orders.",
        ),
        _row(
            "kraken",
            asset_classes=["CRYPTO_SPOT"],
            public_metadata="SUPPORTED",
            quotes="UNKNOWN",
            trades="UNKNOWN",
            l1="UNKNOWN",
            l2="UNKNOWN",
            l3="UNKNOWN",
            funding="UNKNOWN",
            fees="UNKNOWN",
            order_types="UNKNOWN",
            paper_support="UNKNOWN",
            live_support="UNSUPPORTED",
            historical_access="UNKNOWN",
            rights="per-venue UNKNOWN until licensed",
            credentials_requirement="YES",
            websocket="SUPPORTED",
            rest="SUPPORTED",
            commercial_rights="UNKNOWN",
            redistribution_rights="UNKNOWN",
            status="ACTIVE",
            provenance=prov,
            note="ccxt offline inventory only; no fetch, no keys, no orders.",
        ),
        _row(
            "XNYS",
            asset_classes=["EQUITY", "ETF"],
            public_metadata="SUPPORTED",
            quotes="UNKNOWN",
            trades="UNKNOWN",
            l1="UNKNOWN",
            l2="UNKNOWN",
            l3="UNKNOWN",
            funding="UNSUPPORTED",
            fees="UNKNOWN",
            order_types="UNKNOWN",
            paper_support="SUPPORTED",
            live_support="UNSUPPORTED",
            historical_access="UNKNOWN",
            rights="per-vendor UNKNOWN (Yahoo-derived bars are transient/personal-use only)",
            credentials_requirement="NO",
            websocket="UNKNOWN",
            rest="SUPPORTED",
            commercial_rights="UNKNOWN",
            redistribution_rights="UNKNOWN",
            status="ACTIVE",
            provenance="pandas_market_calendars+exchange_calendars:session-leg",
            note="Session calendar leg only (XNYS). Market data gated per dataset.",
        ),
        _row(
            "sec_edgar",
            asset_classes=["UNKNOWN"],
            public_metadata="SUPPORTED",
            quotes="UNSUPPORTED",
            trades="UNSUPPORTED",
            l1="UNSUPPORTED",
            l2="UNSUPPORTED",
            l3="UNSUPPORTED",
            funding="UNSUPPORTED",
            fees="UNSUPPORTED",
            order_types="UNSUPPORTED",
            paper_support="UNSUPPORTED",
            live_support="UNSUPPORTED",
            historical_access="SUPPORTED",
            rights="public-domain (17 U.S.C. Sec. 105)",
            credentials_requirement="NO",
            websocket="UNSUPPORTED",
            rest="SUPPORTED",
            commercial_rights="yes",
            redistribution_rights="yes",
            status="ACTIVE",
            provenance="rights-registry:sec_edgar_8k",
            note="Data vendor, not a trading venue. Included so the matrix "
                 "answers 'where does the world-event leg come from'.",
        ),
    ]


def get(venue_id: str, ccxt_version: str = "UNKNOWN") -> Optional[Dict[str, Any]]:
    for row in registry(ccxt_version):
        if row["venue_id"] == venue_id:
            return row
    return None


def summary(ccxt_version: str = "UNKNOWN") -> Dict[str, Any]:
    rows = registry(ccxt_version)
    return {
        "schema_version": SCHEMA_VERSION,
        "n_venues": len(rows),
        "venue_ids": sorted(r["venue_id"] for r in rows),
        "total_unknown_fields": sum(r["n_unknown"] for r in rows),
        "rule": "UNKNOWN stays UNKNOWN until a verified fact replaces it.",
    }
