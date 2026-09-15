"""FUTURE-ONLY point-in-time rights model.

A RightsSnapshot pins the exact usage terms a dataset was retrieved under:
provider, terms reference + hash, per-use allowances, retention, attribution,
and review status. Rights upgrades require evidence; ambiguous clauses stay
UNKNOWN and fail closed (never qualify).

Statuses: UNKNOWN | BLOCKED | RESEARCH_ONLY | COMMERCIAL_INTERNAL |
REDISTRIBUTION_ALLOWED. Commercial/redistribution claims additionally need
an explicit clause each — a general "commercial OK" never implies
redistribution.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from gods_eye.future.lineage import canonical, manifest_id


class RightsStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    BLOCKED = "BLOCKED"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    COMMERCIAL_INTERNAL = "COMMERCIAL_INTERNAL"
    REDISTRIBUTION_ALLOWED = "REDISTRIBUTION_ALLOWED"


@dataclass(frozen=True)
class RightsSnapshot:
    provider: str
    terms_ref: str = "UNKNOWN"      # URL or "client-README/<version>" etc.
    retrieved_at: Optional[str] = None  # ISO; None == UNKNOWN
    terms_hash: str = "UNKNOWN"     # sha256 of archived terms text
    license_type: str = "UNKNOWN"
    research_use: bool = False
    commercial_use: bool = False
    storage: bool = False
    derived_data_use: bool = False
    ml_training_use: bool = False
    redistribution: bool = False
    retention: str = "UNKNOWN"
    attribution: str = "UNKNOWN"
    unknown_clauses: tuple = ()
    review_status: str = "UNREVIEWED"  # UNREVIEWED | REVIEWED | CONTESTED
    status: RightsStatus = RightsStatus.UNKNOWN

    def evaluate(self) -> RightsStatus:
        """Derive the defensible status from clauses (never exceeds evidence).

        BLOCKED wins over everything; redistribution needs its own clause;
        commercial-internal needs commercial_use + storage; research-only
        needs research_use; anything unreviewed or ambiguous -> UNKNOWN
        (BLOCKED if an explicit ban is present).
        """
        if self.review_status == "UNREVIEWED" or self.unknown_clauses:
            # A ban clause is decisive even before full review.
            if self.status == RightsStatus.BLOCKED:
                return RightsStatus.BLOCKED
            return RightsStatus.UNKNOWN
        if self.review_status == "CONTESTED":
            return RightsStatus.UNKNOWN
        if self.redistribution:
            return RightsStatus.REDISTRIBUTION_ALLOWED
        if self.commercial_use and self.storage:
            return RightsStatus.COMMERCIAL_INTERNAL
        if self.commercial_use and not self.storage:
            return RightsStatus.UNKNOWN
        if self.research_use:
            return RightsStatus.RESEARCH_ONLY
        return RightsStatus.UNKNOWN

    def qualifies(self, need: RightsStatus) -> bool:
        """Fail-closed: effective status must rank at/above need."""
        order = list(RightsStatus)
        return order.index(self.evaluate()) >= order.index(need)

    def snapshot_id(self) -> str:
        payload = {"kind": "RIGHTS_SNAPSHOT_V1",
                   "rights": {k: getattr(self, k) for k in (
                       "provider", "terms_ref", "retrieved_at", "terms_hash",
                       "license_type", "research_use", "commercial_use",
                       "storage", "derived_data_use", "ml_training_use",
                       "redistribution", "retention", "attribution",
                       "unknown_clauses", "review_status")}}
        return manifest_id(payload)

    def to_dict(self) -> dict:
        d = {k: getattr(self, k) for k in (
            "provider", "terms_ref", "retrieved_at", "terms_hash",
            "license_type", "research_use", "commercial_use", "storage",
            "derived_data_use", "ml_training_use", "redistribution",
            "retention", "attribution", "unknown_clauses", "review_status")}
        d["status"] = self.status.value
        d["effective_status"] = self.evaluate().value
        d["snapshot_id"] = self.snapshot_id()
        return d


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
