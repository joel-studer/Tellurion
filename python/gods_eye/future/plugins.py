"""FUTURE-ONLY open-core plugin SDK (interfaces, no alpha hooks).

Plugin kinds: Sensor | MarketData | EntityResolver | Visualization |
ModelChallenger | Venue | PredictionMarket. Every plugin declares identity,
licence, data rights, capabilities, network/secrets needs, provenance,
health, and schema compatibility. Private alpha hooks are never exposed.

Rights-first policy (V15): a plugin whose data_rights are UNKNOWN (or
missing) can be *discovered* but can never become production-qualified:
`production_qualified()` returns False and `qualify_or_refuse()` raises.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

KINDS = ("Sensor", "EntityResolver", "Visualization")

# Capabilities that prove a plugin smuggles private alpha/research hooks.
FORBIDDEN_CAPABILITY_TOKENS = (
    "alpha", "signal", "edge", "strategy_rank", "strategy-rank",
    "strategyselect", "capital_alloc", "capital-alloc", " alpha",
    "timing_edge", "timing-edge", "settlement_edge", "settlement-edge",
    "source_rank", "source-rank", "model_select", "model-select",
)


class PluginDeclaration(Dict[str, Any]):
    """Plain-dict declaration with required keys (validated by `declare`)."""


REQUIRED_KEYS = ("name", "version", "kind", "license", "data_rights",
                 "capabilities", "network", "secrets", "provenance",
                 "health", "schema")


def _capability_text(capabilities: Any) -> str:
    if isinstance(capabilities, (list, tuple)):
        return " ".join(str(c) for c in capabilities).lower().replace("_", "").replace("-", "")
    return str(capabilities).lower().replace("_", "").replace("-", "")


def declare(**kw: Any) -> Dict[str, Any]:
    missing = [k for k in REQUIRED_KEYS if k not in kw]
    if missing:
        raise ValueError(f"plugin declaration missing: {missing}")
    if kw["kind"] not in KINDS:
        raise ValueError(f"unknown plugin kind: {kw['kind']}")
    text = _capability_text(kw.get("capabilities", ""))
    for tok in FORBIDDEN_CAPABILITY_TOKENS:
        needle = tok.lower().replace("_", "").replace("-", "")
        if needle and needle in text:
            raise ValueError(
                f"plugins must not declare alpha/private capabilities ({tok})")
    return dict(kw)


def rights_declared(declaration: Dict[str, Any]) -> bool:
    """True iff the plugin declares non-UNKNOWN data rights."""
    rights = declaration.get("data_rights", "UNKNOWN")
    if rights is None:
        return False
    if isinstance(rights, dict):
        rights = rights.get("status", rights.get("basis", "UNKNOWN"))
    return str(rights).strip().upper() not in ("", "UNKNOWN", "NONE", "TBD")


def production_qualified(declaration: Dict[str, Any]) -> bool:
    """Rights-first gate: UNKNOWN rights can never be production-qualified."""
    if not rights_declared(declaration):
        return False
    if str(declaration.get("license", "UNKNOWN")).strip().upper() in (
            "", "UNKNOWN", "NONE", "TBD"):
        return False
    if str(declaration.get("schema", "UNKNOWN")).strip().upper() in (
            "", "UNKNOWN", "NONE", "TBD"):
        return False
    return True


def qualify_or_refuse(declaration: Dict[str, Any]) -> Dict[str, Any]:
    """Return the declaration if production-qualified, else raise."""
    if not production_qualified(declaration):
        raise ValueError(
            "plugin not production-qualified: declare license + schema + "
            "non-UNKNOWN data_rights first "
            f"(name={declaration.get('name', '?')})")
    return declaration


class SensorPlugin(ABC):
    kind = "Sensor"

    @abstractmethod
    def poll(self) -> Dict[str, Any]:
        raise NotImplementedError


class EntityResolverPlugin(ABC):
    kind = "EntityResolver"

    @abstractmethod
    def resolve(self, name: str, kind: str, observed_at: str) -> Any:
        raise NotImplementedError


class VisualizationPlugin(ABC):
    kind = "Visualization"

    @abstractmethod
    def render(self, payload: Dict[str, Any]) -> str:
        raise NotImplementedError
