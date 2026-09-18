"""Deterministic canonical JSON and content ids.

Canonical JSON (sorted keys, compact separators, UTF-8) -> sha256 id. Two
equal payloads always yield the same id, on every platform and Python run,
which is what makes evidence manifests and rights records comparable.

Used by :mod:`gods_eye.future.rights` for rights-record ids.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str)


def manifest_id(payload: Dict[str, Any]) -> str:
    return hashlib.sha256(canonical(payload).encode("utf-8")).hexdigest()
