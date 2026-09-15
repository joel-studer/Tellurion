"""FUTURE-ONLY LEAN backtest job contract (service/CLI boundary, no install).

Deployment shape (OPTION A/B hybrid): GOD'S EYE writes a job directory
(manifest + dataset refs + strategy package ref + cost/execution refs),
invokes the LEAN CLI (`lean backtest ...`) in a separate process, then
reads the output artifact path into a result manifest. This module builds
the contract and parses results — it never imports LEAN and never runs
anything by itself (no subprocess here; the runner lives in the wiring PR).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class LeanJobSpec:
    job_id: str
    input_manifest_id: str  # ResearchRunManifest or ExecutionRunManifest id
    dataset_snapshot_id: str
    strategy_ref: str  # package/path ref, never a live signal
    cost_model_id: str = "UNKNOWN"
    execution_model_id: str = "UNKNOWN"
    output_dir: str = "UNKNOWN"
    lean_config: tuple = ()  # ((key, value), ...) e.g. job, environment
    notes: str = "UNKNOWN"


def lean_available() -> bool:
    import shutil
    return shutil.which("lean") is not None


def build_job(spec: LeanJobSpec, root: Path) -> Dict[str, Any]:
    """Materialize the job directory (manifest + config), return invocation."""
    jobdir = Path(root) / spec.job_id
    (jobdir / "input").mkdir(parents=True, exist_ok=True)
    (jobdir / "output").mkdir(parents=True, exist_ok=True)
    manifest = {"job_id": spec.job_id, "input_manifest": spec.input_manifest_id,
                "dataset_snapshot": spec.dataset_snapshot_id,
                "strategy_ref": spec.strategy_ref,
                "cost_model": spec.cost_model_id,
                "execution_model": spec.execution_model_id,
                "lean_config": dict(spec.lean_config)}
    import json
    (jobdir / "input" / "godseye-job.json").write_text(
        json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8")
    cmd = ["lean", "backtest", str(jobdir / "input"),
           "--output", str(jobdir / "output")]
    return {"job_dir": str(jobdir), "manifest": manifest, "command": cmd,
            "lean_present": lean_available(), "status": "STAGED (not executed)"}


def parse_results(output_dir: Path) -> Dict[str, Any]:
    """Read LEAN output artifacts if present (UNKNOWN when absent)."""
    output_dir = Path(output_dir)
    found = sorted(p.name for p in output_dir.glob("*") if p.is_file()) \
        if output_dir.is_dir() else []
    return {"artifacts": found, "status": "UNKNOWN (no run in V14)",
            "note": "wiring PR executes the command and maps fills->manifest"}
