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
    "playwright": {"imports": ("playwright",),
                   "policy": "optional capture extra",
                   "relevance": "screenshot and browser-QA scripts only"},
    "pytest": {"imports": ("pytest",), "policy": "optional dev extra",
               "relevance": "test suite"},
}


def probe(name: str) -> Dict[str, Any]:
    spec = _CATALOG.get(name)
    if spec is None:
        return {"name": name, "status": "UNKNOWN",
                "detail": "not in optional-dep catalog"}
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
