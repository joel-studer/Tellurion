"""FUTURE-ONLY research result manifest (deterministic, serializable).

Every future experiment result must be reproducible from its manifest tuple:
event IDs, signal-definition version, evidence cutoff, market dataset version,
engine + version, cost/execution model versions, code commit, model version,
seed, data-rights state. No result without the full tuple is citable.

Determinism: canonical JSON (sorted keys, compact separators, UTF-8) ->
sha256 manifest_id. Two equal manifests always yield the same id.
Never connected to any official research metric.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from typing import Any, Dict, Optional

from gods_eye.future.market import ResearchExperiment


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str)


def manifest_id(payload: Dict[str, Any]) -> str:
    return hashlib.sha256(canonical(payload).encode("utf-8")).hexdigest()


class ResearchRunManifest:
    """Immutable result manifest (build via from_experiment)."""

    def __init__(self, payload: Dict[str, Any]):
        self._payload = json.loads(canonical(payload))  # normalize
        self._id = manifest_id(self._payload)

    @classmethod
    def from_experiment(cls, exp: ResearchExperiment,
                        result: Optional[Dict[str, Any]] = None,
                        created_at: Optional[str] = None) -> "ResearchRunManifest":
        payload: Dict[str, Any] = {
            "kind": "RESEARCH_RUN_MANIFEST_V1",
            "lineage": exp.lineage_keys(),
            "result": result or {},
        }
        if created_at is not None:
            payload["created_at"] = created_at
        return cls(payload)

    @property
    def id(self) -> str:
        return self._id

    def to_dict(self) -> Dict[str, Any]:
        return json.loads(canonical(self._payload))

    def to_json(self) -> str:
        return canonical(self._payload)

    @classmethod
    def from_json(cls, raw: str) -> "ResearchRunManifest":
        payload = json.loads(raw)
        if payload.get("kind") != "RESEARCH_RUN_MANIFEST_V1":
            raise ValueError("not a RESEARCH_RUN_MANIFEST_V1 document")
        if "lineage" not in payload:
            raise ValueError("manifest missing lineage (refused)")
        return cls(payload)

    def __eq__(self, other: object) -> bool:
        return (isinstance(other, ResearchRunManifest)
                and self._id == other._id)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"ResearchRunManifest({self._id[:12]}...)"
