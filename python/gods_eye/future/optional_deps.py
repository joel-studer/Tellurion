"""FUTURE-ONLY optional-dependency reporter (graceful degradation, V16).

The public core runs WITHOUT any of: LEAN, Nautilus, hftbacktest,
skfolio, PyPortfolioOpt, Torch, Kronos, large ML frameworks, Rust
toolchain, broker SDKs. Each probe reports exactly one status:

  AVAILABLE      — importable in this environment
  NOT_INSTALLED  — cleanly absent (normal for community installs)
  BLOCKED        — present but refused by policy (e.g. copyleft boundary)
  UNKNOWN        — probe itself failed unexpectedly (never guessed)

Probes are lazy (function scope) so module import never requires heavies.
"""

from __future__ import annotations

from typing import Any, Dict, List

STATUSES = ("AVAILABLE", "NOT_INSTALLED", "BLOCKED", "UNKNOWN")

# name -> (import_names, policy, relevance)
_CATALOG: Dict[str, Dict[str, Any]] = {
    "lean": {"imports": ("lean",), "policy": "optional boundary",
             "relevance": "backtest engine boundary (job contract only)"},
    "nautilus_trader": {"imports": ("nautilus_trader",), "policy": "BLOCKED in-process (LGPL: separate process only)",
                        "relevance": "execution sim boundary"},
    "hftbacktest": {"imports": ("hftbacktest",), "policy": "optional boundary",
                    "relevance": "microstructure validator boundary"},
    "skfolio": {"imports": ("skfolio",), "policy": "optional boundary",
                "relevance": "portfolio optimizer boundary"},
    "pypfopt": {"imports": ("pypfopt",), "policy": "optional boundary",
                "relevance": "secondary weight validator boundary"},
    "torch": {"imports": ("torch",), "policy": "optional (challenger pool only)",
              "relevance": "ML challengers (not required)"},
    "kronos": {"imports": ("kronos",), "policy": "optional (challenger candidate)",
               "relevance": "forecast challenger (not installed until samples exist)"},
    "duckdb": {"imports": ("duckdb",), "policy": "optional market extra",
               "relevance": "catalog index (graceful in-memory fallback)"},
    "ccxt": {"imports": ("ccxt",), "policy": "optional market extra",
             "relevance": "venue metadata layer (offline describe)"},
    "exchange_calendars": {"imports": ("exchange_calendars",),
                           "policy": "optional market extra",
                           "relevance": "multi-venue session breadth"},
    "sktime": {"imports": ("sktime",), "policy": "optional ml extra",
               "relevance": "challenger pool"},
    "darts": {"imports": ("darts",), "policy": "optional ml extra",
              "relevance": "challenger pool"},
    "statsforecast": {"imports": ("statsforecast",), "policy": "optional ml extra",
                      "relevance": "challenger (model-specific)"},
}


def probe(name: str) -> Dict[str, Any]:
    spec = _CATALOG.get(name)
    if spec is None:
        return {"name": name, "status": "UNKNOWN",
                "detail": "not in optional-dep catalog"}
    if name == "nautilus_trader":
        # Policy: never import in-process even if installed (LGPL boundary).
        try:
            import importlib.util
            found = importlib.util.find_spec("nautilus_trader") is not None
        except Exception:
            return {"name": name, "status": "UNKNOWN",
                    "detail": "probe failed", "policy": spec["policy"]}
        return {"name": name,
                "status": "BLOCKED" if found else "NOT_INSTALLED",
                "detail": ("installed but in-process use refused (separate "
                           "process only)" if found else "absent (normal)"),
                "policy": spec["policy"], "relevance": spec["relevance"]}
    try:
        import importlib.util
        found = any(importlib.util.find_spec(mod) is not None
                    for mod in spec["imports"])
    except Exception:
        return {"name": name, "status": "UNKNOWN",
                "detail": "probe failed unexpectedly",
                "policy": spec["policy"]}
    return {"name": name,
            "status": "AVAILABLE" if found else "NOT_INSTALLED",
            "detail": "importable" if found else "absent (normal for community installs)",
            "policy": spec["policy"], "relevance": spec["relevance"]}


def report() -> Dict[str, Any]:
    rows = [probe(n) for n in sorted(_CATALOG)]
    counts: Dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {"schema": "optional-deps-v1", "rows": rows, "counts": counts,
            "core_requires_none": True,
            "rule": "public core runs with every row NOT_INSTALLED (tested)"}


def names() -> List[str]:
    return sorted(_CATALOG)
