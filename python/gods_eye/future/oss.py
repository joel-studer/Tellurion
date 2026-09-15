"""FUTURE-ONLY OSS component registry (single machine-readable source).

Mirrors docs/future/OSS_MAKE_OR_BUY_MATRIX.md. Statuses:
USE_NOW | WRAP_NOW | OPTIONAL_LATER | REFERENCE_ONLY | REJECT.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

STATUSES = ("USE_NOW", "WRAP_NOW", "OPTIONAL_LATER", "REFERENCE_ONLY", "REJECT")


def _c(name: str, role: str, status: str, license: str, installed: bool,
       wrapped: str, open_core: str, data_rights: str = "n/a (software)",
       notes: str = "") -> Dict[str, Any]:
    assert status in STATUSES, status
    return {"component": name, "role": role, "status": status,
            "license": license, "installed": installed, "wrapped": wrapped,
            "open_core_eligible": open_core, "data_rights": data_rights,
            "notes": notes}


def registry() -> list[Dict[str, Any]]:
    return [
        _c("duckdb", "research metadata/query layer", "USE_NOW", "MIT", True,
           "market_catalog.py", "yes", "n/a (software)",
           "1.5.1 installed; Parquet-native catalog over state_future/market"),
        _c("pyarrow/parquet", "columnar archive format", "USE_NOW", "Apache-2.0",
           True, "convention (state_future layout)", "yes", "n/a (software)"),
        _c("pandas_market_calendars", "US session calendar", "USE_NOW", "BSD",
           True, "session_calendar.py (XNYS)", "yes", "n/a (software)",
           "core dep 5.4.0; qualified leg"),
        _c("exchange_calendars", "multi-venue calendars", "WRAP_NOW",
           "Apache-2.0", True, "session_calendar.py (probe)", "yes",
           "n/a (software)", "4.13.2 installed; 50+ venues; future-only breadth"),
        _c("ccxt", "crypto venue metadata", "WRAP_NOW", "MIT", True,
           "crypto_data.py", "yes", "per-venue UNKNOWN until licensed",
           "4.5.46 installed, 110 venues; offline metadata only"),
        _c("LEAN", "primary backtest engine", "WRAP_NOW", "Apache-2.0", False,
           "lean_engine.py (job contract)", "yes (boundary)",
           "per-vendor UNKNOWN", "service/CLI boundary; not installed"),
        _c("nautilus_trader", "primary execution sim", "WRAP_NOW",
           "LGPL-3.0-only", False,
           "nautilus_engine.py + exec_engine.py stub", "boundary only",
           "per-venue UNKNOWN", "separate process; no static link"),
        _c("hftbacktest", "independent microstructure validator", "WRAP_NOW",
           "MIT", False, "hft_validator.py", "yes (boundary)",
           "needs L2/L3 feeds (none held)"),
        _c("skfolio", "primary portfolio optimizer", "WRAP_NOW", "BSD-3",
           False, "skfolio_engine.py (lazy probe)", "boundary only",
           "n/a (software)"),
        _c("pypfopt", "secondary weight validator", "WRAP_NOW", "MIT", False,
           "pypfopt_validator.py", "yes (boundary)", "n/a (software)"),
        _c("orderflow-metrics", "microstructure/TCA blocks", "WRAP_NOW", "MIT",
           False, "tca.py (contracts; wrap at env creation)", "yes",
           "n/a (software)", "dependency-free; OFI/VPIN/impact/IS"),
        _c("arcticdb", "trial tick store", "OPTIONAL_LATER", "Apache-2.0",
           False, "none yet", "yes", "needs versioned tick data first"),
        _c("cryptofeed", "crypto WS/LOB capture", "OPTIONAL_LATER",
           "MIT-family", False, "crypto_data.py (shape reserved)", "yes",
           "no capture without licensed quote leg"),
        _c("pitedgar-pattern", "PIT fundamentals pattern", "OPTIONAL_LATER",
           "pattern (varies)", False, "none yet (pattern documented)", "yes",
           "public EDGAR data rights clean; own implementation"),
        _c("edgartools", "SEC plumbing", "OPTIONAL_LATER", "varies", False,
           "none yet", "yes", "public EDGAR"),
        _c("sktime", "challenger pool (secondary)", "OPTIONAL_LATER", "BSD-3",
           False, "forecast.py rank", "yes", "n/a"),
        _c("darts", "challenger pool (secondary)", "OPTIONAL_LATER",
           "Apache-2.0", False, "forecast.py rank", "yes", "n/a"),
        _c("statsforecast", "challenger (model-specific)", "OPTIONAL_LATER",
           "Apache-2.0", False, "forecast.py rank", "yes", "n/a"),
        _c("pyfolio-reloaded", "tear sheets (reporting)", "OPTIONAL_LATER",
           "Apache-2.0", False, "none yet (reporting only)", "yes", "n/a"),
        _c("empyrical-reloaded", "risk statistics (reporting)", "OPTIONAL_LATER",
           "Apache-2.0", False, "risk_measures.py aligns", "yes", "n/a"),
        _c("alphalens-reloaded", "factor diagnostics (V15)", "OPTIONAL_LATER",
           "Apache-2.0", False, "none yet", "yes", "n/a"),
        _c("kronos", "challenger (primary candidate)", "OPTIONAL_LATER", "MIT",
           False, "forecast.py rank", "weights: MIT; corpus rights UNKNOWN",
           "install nothing until V15 challenger samples exist"),
        _c("gluonts", "challenger pool", "REFERENCE_ONLY", "Apache-2.0", False,
           "forecast.py rank", "yes", "heavier than darts/sktime for our need"),
        _c("riskfolio-lib", "measure catalogue", "REFERENCE_ONLY", "BSD-3",
           False, "docs only", "yes", "no third optimizer"),
        _c("vibe-trading", "quantlib/loaders/eval patterns", "REFERENCE_ONLY",
           "MIT (subset)", False, "per-component (see decisions doc)", "patterns only",
           "agent/swarm/live REJECT; full weight never installed"),
        _c("openterminal", "fallback/cache/limiter/UX patterns", "REFERENCE_ONLY",
           "MIT code; DATA excluded", False, "per-component (see decisions doc)",
           "patterns only", "feeds REJECT (ToS/scrape risk)"),
        _c("tcapy", "TCA framework", "REFERENCE_ONLY", "Apache-2.0", False,
           "tca.py (contracts)", "yes", "FX-only alpha stale 2021; honest GAP"),
        _c("flowpylib/flowforge", "order-flow research", "REFERENCE_ONLY",
           "BSD-2", False, "none", "yes", "small/researchy"),
        _c("vectorbt", "sweep accelerator", "REFERENCE_ONLY", "Apache-2.0",
           False, "none", "yes", "never scientific truth"),
        _c("tradevodata", "PIT dataset (hosted)", "REFERENCE_ONLY",
           "MIT client; keyed data", False, "none", "no",
           "no procurement; survivorship gaps"),
        _c("lse-data", "datasets (trial)", "REFERENCE_ONLY",
           "client MIT; DATA proprietary", False, "V11 trial artefacts",
           "no", "RESEARCH_TRIAL; redistribution banned"),
        _c("algovex", "product/UX benchmark", "REFERENCE_ONLY", "proprietary SaaS",
           False, "none", "no", "two entities; no code reuse"),
        _c("omniroute", "agent gateway (optional)", "REFERENCE_ONLY", "MIT",
           False, "none", "outside truth", "surface too broad for frozen runs"),
        _c("litellm/openrouter", "agent routing alt", "REFERENCE_ONLY",
           "varies/hosted", False, "none", "outside truth",
           "preferred over OmniRoute if ever needed"),
        _c("freqtrade/cvxportfolio/openbb", "quant refs", "REFERENCE_ONLY",
           "GPL/AGPL family", False, "never linked", "no",
           "copyleft boundary; isolated use only"),
        _c("qanat-ammarmian", "experiment tracker", "REJECT", "GPL-3.0", False,
           "none", "no", "licence hazard + stale 8-star; baggage removed"),
        _c("qanat-fdtl", "alpha DAG backtester", "REJECT", "varies (beta)",
           False, "none", "no",
           "beta 'nobody else has run it'; duplicates manifests; name collision"),
        _c("mlflow", "experiment tracking", "REJECT", "Apache-2.0", False,
           "lineage.py replaces", "n/a", "manifests cover need; confident"),
        _c("dvc", "dataset versioning", "REJECT", "Apache-2.0", False,
           "snapshot ids replace", "n/a", "content-hash ids cover need; confident"),
        _c("dagster/prefect", "orchestration", "REJECT", "Apache-2.0", False,
           "thin replay driver", "n/a", "no scale exists; revisit with scale"),
    ]


def get(name: str) -> Optional[Dict[str, Any]]:
    for c in registry():
        if c["component"] == name:
            return c
    return None


def summary_counts() -> Dict[str, int]:
    out: Dict[str, int] = {}
    for c in registry():
        out[c["status"]] = out.get(c["status"], 0) + 1
    return out
