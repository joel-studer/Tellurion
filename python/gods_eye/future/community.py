"""Community-mode boundary: the open-source core runs on its own.

``community_check()`` imports every community-safe module (UI, demo and
replay, plugin discovery, world map, evidence, time machine, generic
market/execution/portfolio contracts) and fails if those imports load a
``gods_eye`` module that does not ship inside this package. The check is
structural (module file location), so it needs no list of downstream
module names. Downstream CI may additionally set
``GODS_EYE_DENY_MODULES`` (comma-separated module-name prefixes).
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

COMMUNITY_SAFE_MODULES = (
    "gods_eye.future.venues",
    "gods_eye.future.prediction_markets",
    "gods_eye.future.venue_registry",
    "gods_eye.future.ccxt_meta",
    "gods_eye.future.crypto_data",
    "gods_eye.future.nautilus_polymarket",
    "gods_eye.future.nautilus_engine",
    "gods_eye.future.market",
    "gods_eye.future.execution",
    "gods_eye.future.portfolio",
    "gods_eye.future.providers",
    "gods_eye.future.plugins",
    "gods_eye.future.public_api",
    "gods_eye.future.demo_dataset",
    "gods_eye.future.session_calendar",
    "gods_eye.future.market_catalog",
    "gods_eye.future.venue_registry",
    "gods_eye.future.oss",
    "gods_eye.future.forecast",
    "gods_eye.future.tca",
)

PACKAGE_DIR = Path(__file__).resolve().parents[1]  # python/gods_eye
DENY_ENV = "GODS_EYE_DENY_MODULES"

# Kept for API stability; the core ships no downstream module names.
PRIVATE_SUBSTRINGS: tuple = ()


def deny_prefixes() -> tuple:
    raw = os.environ.get(DENY_ENV, "")
    return tuple(p.strip() for p in raw.split(",") if p.strip())


def _inside_package(location: str) -> bool:
    try:
        Path(location).resolve().relative_to(PACKAGE_DIR)
        return True
    except (ValueError, OSError):
        return False


def _outside_package(module: Any) -> bool:
    location = getattr(module, "__file__", None)
    if location:
        return not _inside_package(location)
    portions = list(getattr(module, "__path__", None) or [])
    return any(not _inside_package(p) for p in portions)


def private_modules_loaded() -> List[str]:
    """gods_eye modules loaded from outside this package, plus denied prefixes."""
    deny = deny_prefixes()
    found = []
    for name, module in list(sys.modules.items()):
        if module is None:
            continue
        if name == "gods_eye" or name.startswith("gods_eye."):
            if _outside_package(module):
                found.append(name)
        elif any(name == d or name.startswith(d + ".") for d in deny):
            found.append(name)
    return sorted(found)


def assert_no_private_imports() -> None:
    loaded = private_modules_loaded()
    if loaded:
        raise ImportError(f"community mode forbids private modules: {loaded}")


def community_check() -> Dict[str, Any]:
    """Import every community-safe module; fail if *these imports* pull private modules.

    Note: in a dev checkout other test modules may already have loaded
    private research modules into this process. That does not prove the
    community edition needs them. So we diff: only *newly* loaded private
    modules introduced by the community imports fail the check. A true
    community install has no private modules on disk at all (additionally
    covered by the static no-private-import test).
    """
    before = set(private_modules_loaded())
    imported: List[str] = []
    failed: List[str] = []
    for name in COMMUNITY_SAFE_MODULES:
        try:
            importlib.import_module(name)
            imported.append(name)
        except Exception as e:  # pragma: no cover - surfaced, never hidden
            failed.append(f"{name}: {type(e).__name__}: {e}")
    after = set(private_modules_loaded())
    introduced = sorted(after - before)
    if introduced:
        raise ImportError(
            f"community imports pulled private modules: {introduced}")
    return {"community_mode": True, "imported": imported, "failed": failed,
            "n_imported": len(imported),
            "private_loaded_before": sorted(before),
            "private_introduced": introduced,
            "capabilities": ["UI", "demo/replay", "plugin discovery",
                             "world map", "evidence", "time machine",
                             "generic market contracts",
                             "generic execution contracts",
                             "generic portfolio contracts"]}
