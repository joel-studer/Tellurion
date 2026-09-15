"""FUTURE-ONLY hftbacktest validator boundary (invocation contract + fixture demo).

Input: ExecutionDataset + fixed OrderIntent sequence + queue/latency
models + dataset snapshot. Output: fill comparison artifact
(AGREE/PARTIAL/DISAGREE/UNKNOWN per intent). The fixture demo proves the
dual-engine shape with pure-python queue/latency math (no install, no
real data) — the real validator swaps this kernel for hftbacktest replay.
"""

from __future__ import annotations

from typing import Any, Dict, List


def hftbacktest_available() -> bool:
    try:
        import hftbacktest  # noqa: F401
        return True
    except Exception:
        return False


def validate_fills(dataset: Any, intents: List[Any],
                   market: Dict[str, Any]) -> Dict[str, Any]:
    """Fixture-kernel comparison: primary (fixture accept) vs check (queue-aware)."""
    from gods_eye.future import extensions
    assess_fillability = extensions.get("execution.fillability").assess_fillability
    tier = getattr(dataset, "realism_tier", "QUOTE_L1") or "QUOTE_L1"
    if tier == "UNKNOWN":
        tier = "QUOTE_L1"
    rows = []
    for intent in intents:
        f = assess_fillability(intent, market, tier)
        rows.append({"intent_id": getattr(intent, "intent_id", "?"),
                     "primary": "ACCEPTED (fixture)",
                     "check": f.verdict, "reason": f.reason, "tier": tier})
    agree = sum(1 for r in rows if r["check"] == "FILLABLE")
    verdict = "AGREE" if agree == len(rows) and rows else (
        "PARTIAL" if agree else "DISAGREE" if rows else "UNKNOWN")
    return {"rows": rows, "verdict": verdict,
            "engine_check": "hftbacktest (fixture kernel in V14; not installed)",
            "rule": "disagreement -> INVESTIGATE, never pick profitable engine"}
