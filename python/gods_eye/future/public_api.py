"""FUTURE-ONLY stable-ish public developer API surface (V15).

Capability-driven plugin registration. No internal implementation
details leak: every function validates a declaration dict and returns a
receipt. Alpha/private hooks are refused at the boundary.
"""

from __future__ import annotations

from typing import Any, Dict, List

_REGISTRY: Dict[str, List[Dict[str, Any]]] = {
    "sensor": [], "entity_resolver": [], "visualization": [],
}

_KIND_BY_FN = {
    "register_sensor": ("sensor", "Sensor"),
    "register_entity_resolver": ("entity_resolver", "EntityResolver"),
    "register_visualization": ("visualization", "Visualization"),
}


def _register(fn_name: str, declaration: Dict[str, Any]) -> Dict[str, Any]:
    from gods_eye.future import plugins as pl
    slot, want_kind = _KIND_BY_FN[fn_name]
    declared = pl.declare(**declaration)
    kinds = want_kind if isinstance(want_kind, tuple) else (want_kind,)
    if declared["kind"] not in kinds:
        raise ValueError(f"{fn_name} needs kind {kinds} (got {declared['kind']})")
    _REGISTRY[slot].append(declared)
    qualified = pl.production_qualified(declared)
    return {"ok": True, "slot": slot, "name": declared["name"],
            "version": declared["version"], "kind": declared["kind"],
            "production_qualified": qualified,
            "note": ("discoverable; production use needs license + schema + "
                     "non-UNKNOWN data_rights") if not qualified else "qualified"}


def register_sensor(declaration: Dict[str, Any]) -> Dict[str, Any]:
    return _register("register_sensor", declaration)


def register_entity_resolver(declaration: Dict[str, Any]) -> Dict[str, Any]:
    return _register("register_entity_resolver", declaration)


def register_visualization(declaration: Dict[str, Any]) -> Dict[str, Any]:
    return _register("register_visualization", declaration)


def list_registered(slot: str = "UNKNOWN") -> Any:
    if slot == "UNKNOWN":
        return {k: list(v) for k, v in _REGISTRY.items()}
    return list(_REGISTRY.get(slot, []))


def clear_registry() -> None:  # tests/demo only
    for k in _REGISTRY:
        _REGISTRY[k].clear()


def api_surface() -> Dict[str, Any]:
    return {"functions": sorted(_KIND_BY_FN),
            "slots": sorted(_REGISTRY),
            "schema": "public-api-v1",
            "rule": "capability-driven plugins; no alpha/private hooks"}
