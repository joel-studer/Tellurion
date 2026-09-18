"""Release readiness checker (read-only, never publishes).

``tellurion release-check`` (or ``python -m gods_eye.future.release_check``)
verifies this source tree and returns PASS / WARN / FAIL with one
actionable row per check. It never modifies, uploads, or publishes.

Publication is a separate human decision: the ``publication gates`` row
reports ``.github/RELEASE_GATES.json`` and ``publishable`` stays false
until every gate is closed (PASS / OBTAINED).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Sequence, Union

from gods_eye.future import boundary

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"

# Repo-relative POSIX paths. A tuple entry means "any one of these".
REQUIRED_FILES: Sequence[Union[str, tuple]] = (
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "pyproject.toml",
    ".gitignore",
    ".gitattributes",
    "LICENSE",
    "NOTICE",
    "legal/THIRD_PARTY_NOTICES.md",
    "legal/SBOM.spdx.json",
    "legal/ASSET_RIGHTS.json",
    "legal/LICENSE_SIGNOFF.md",
    ".github/RELEASE_GATES.json",
    ".github/workflows/ci.yml",
    "console/demo.html",
    "console/landing.html",
    "console/ultra.html",
    "console/gallery.html",
    "console/world.html",
    "console/world/app.js",
    "console/world/styles.css",
    "python/gods_eye/future/ultra_demo.py",
    "python/gods_eye/future/layers.py",
    "python/gods_eye/future/sensor_sources.py",
    "python/gods_eye/future/world_demo.py",
    "python/gods_eye/future/world_live.py",
    "python/gods_eye/future/world_now.py",
    "python/gods_eye/future/world_air.py",
    "python/gods_eye/future/world_change.py",
    "python/gods_eye/future/world_imagery.py",
    "python/gods_eye/future/world_earth.py",
    "python/gods_eye/future/extensions.py",
    "python/gods_eye/rights/registry.py",
    "python/gods_eye/future/boundary.py",
    "tests/test_boundary.py",
    "tests/test_preview_surface.py",
    "tests/test_ultra.py",
    "tests/test_world.py",
    "tests/test_aviation_v21.py",
    "tests/test_world_now_v20.py",
    "tests/test_world_coverage_v19.py",
    "tests/test_future_preview_v16.py",
    "tests/test_future_ultra_v18.py",
    "plugins/aviation_synth/manifest.json",
    "plugins/camera_synth/manifest.json",
    "plugins/weather_nws/manifest.json",
    "plugins/disaster_eonet/manifest.json",
    "plugins/space_swpc/manifest.json",
    "plugins/austria_pack/manifest.json",
    "docs/OPEN_CORE_BOUNDARY.md",
    "docs/guides/demo-performance.md",
    "examples/plugins/example_sensor/manifest.json",
    "examples/plugins/example_sensor/plugin.py",
    "examples/plugins/example_sensor/fixture.json",
    "examples/plugins/example_sensor/test_example_sensor.py",
    "examples/contributor_tasks/ai_sensor_task.md",
    "scripts/capture_screenshots.py",
    "tests/test_boundary.py",
)

ENVIRONMENT_ONLY_CHECKS = ("localhost bind",)
SBOM_FILE = "legal/SBOM.spdx.json"
GATES_FILE = ".github/RELEASE_GATES.json"
# A gate is closed when it passed, was obtained, or the owner
# explicitly waived it for this release. A waiver is recorded as a
# waiver: it never becomes a PASS.
CLOSED_GATE_VALUES = ("PASS", "OBTAINED",
                      "WAIVED_BY_OWNER_FOR_V1_PUBLIC_BETA")

Rows = List[Dict[str, Any]]


def _row(rows: Rows, name: str, status: str, detail: str = "",
         fix: str = "") -> None:
    rows.append({"name": name, "status": status, "detail": detail,
                 "fix": fix})


def _candidate_root(explicit: str | None = None) -> Path:
    if explicit:
        return Path(explicit)
    here = Path(__file__).resolve()
    for parent in (here, *here.parents):
        if (parent / "console" / "demo.html").is_file():
            return parent
    return Path.cwd()


def read_gates(root: Path) -> Dict[str, Any]:
    """Human/legal publication gates; publishable only when all are closed."""
    try:
        data = json.loads((Path(root) / GATES_FILE).read_text(encoding="utf-8"))
        gates = {str(k): str(v.get("status", "UNKNOWN"))
                 for k, v in data["gates"].items()}
        published = bool(data.get("published", False))
    except (OSError, ValueError, KeyError, AttributeError, TypeError) as e:
        return {"ok": False, "gates": {}, "publishable": False,
                "published": False, "error": f"{type(e).__name__}: {e}"}
    publishable = bool(gates) and all(v in CLOSED_GATE_VALUES
                                      for v in gates.values())
    return {"ok": True, "gates": gates, "publishable": publishable,
            "published": published}


def _check_files(rows: Rows, root: Path) -> None:
    missing = []
    for entry in REQUIRED_FILES:
        options = entry if isinstance(entry, tuple) else (entry,)
        if not any((root / f).is_file() for f in options):
            missing.append(" | ".join(options))
    _row(rows, "required files", PASS if not missing else FAIL,
         f"{len(REQUIRED_FILES) - len(missing)}/{len(REQUIRED_FILES)} present",
         "" if not missing else f"missing: {missing[:5]}")


def _check_imports(rows: Rows, root: Path) -> None:
    problems = boundary.unresolved_internal_imports(root)
    _row(rows, "import boundary", PASS if not problems else FAIL,
         f"{len(problems)} gods_eye imports outside the shipped package",
         "" if not problems else
         "ship the module, or drop the import: "
         + "; ".join(f"{p['file']}:{p['line']} {p['module']}"
                     for p in problems[:3]))


def _check_doctor(rows: Rows, port: int | None = None) -> None:
    try:
        from gods_eye.cli import cmd_doctor
        rep = cmd_doctor(port=port)
    except Exception as e:
        _row(rows, "doctor", FAIL, f"{type(e).__name__}: {e}",
             "run: pip install -e .")
        return
    # A busy local port describes this machine, not the source tree.
    tree_issues = [c for c in rep["checks"] if c["status"] != PASS
                   and c["name"] not in ENVIRONMENT_ONLY_CHECKS]
    env_notes = [f"{c['name']}: {c['detail']}" for c in rep["checks"]
                 if c["status"] != PASS and c["name"] in ENVIRONMENT_ONLY_CHECKS]
    status = PASS if not tree_issues else (
        FAIL if any(c["status"] == FAIL for c in tree_issues) else WARN)
    _row(rows, "doctor", status,
         f"verdict={rep['verdict']} failed={rep['failed']} "
         f"warned={rep['warned']}"
         + (f" (environment only: {'; '.join(env_notes)})" if env_notes else ""),
         "" if status == PASS
         else "run tellurion doctor and follow each fix hint")


def _check_live(rows: Rows, root: Path) -> None:
    hits = boundary.trading_surface_hits(root)
    _row(rows, "no execution surface", PASS if not hits else FAIL,
         "no order, venue, portfolio or backtest modules ship"
         if not hits else f"{len(hits)} trading modules present",
         "" if not hits else f"remove: {hits[:3]}")


def _check_dataset(rows: Rows) -> None:
    try:
        from gods_eye.future import demo_dataset as dd
        v = dd.validate_no_holdout_refs()
    except Exception as e:
        _row(rows, "demo dataset", FAIL, f"{type(e).__name__}: {e}")
        return
    ok = v["ok"] and dd.DATASET_ID == "community-demo-v1"
    _row(rows, "demo dataset", PASS if ok else FAIL,
         f"{dd.DATASET_ID} ({dd.LICENSE})",
         "" if ok else f"flagged refs: {v['hits']}")


def _check_plugin(rows: Rows, root: Path) -> None:
    try:
        from gods_eye.future import validator as vd
        vr = vd.validate_plugin_dir(root / "examples" / "plugins"
                                    / "example_sensor")
    except Exception as e:
        _row(rows, "plugin example", FAIL, f"{type(e).__name__}: {e}")
        return
    _row(rows, "plugin example",
         PASS if vr["verdict"] == "PASS" else vr["verdict"],
         f"example_sensor: {vr['verdict']}",
         "" if vr["verdict"] == "PASS" else "; ".join(vr["errors"][:3]))


def _check_legal(rows: Rows, root: Path) -> Dict[str, Any]:
    try:
        sbom = json.loads((root / SBOM_FILE).read_text(encoding="utf-8"))
        ok = (sbom.get("spdxVersion") == "SPDX-2.3"
              and sbom.get("published") is False
              and str(sbom.get("signOff", "")).startswith(
                  ("NOT_OBTAINED", "OBTAINED")))
        _row(rows, "sbom", PASS if ok else WARN,
             f"{len(sbom.get('packages', []))} packages, "
             f"sign-off={str(sbom.get('signOff', '?'))[:30]}",
             "" if ok else "fix spdxVersion, published flag, or signOff")
    except Exception as e:
        _row(rows, "sbom", FAIL, f"{type(e).__name__}: {e}",
             f"restore {SBOM_FILE}")
    rights = boundary.asset_rights(root)
    _row(rows, "asset rights", PASS if rights["ok"] else FAIL,
         f"{rights['n_assets']} assets, {len(rights['errors'])} problems",
         "" if rights["ok"] else "; ".join(rights["errors"][:3])
         + " (see scripts/update_asset_rights.py)")
    gates = read_gates(root)
    detail = ", ".join(f"{k}={v}" for k, v in sorted(gates["gates"].items()))
    _row(rows, "publication gates", PASS if gates["ok"] else FAIL,
         f"{detail or gates.get('error', '')}; "
         f"publishable={gates['publishable']}",
         "" if gates["ok"] else f"restore {GATES_FILE}")
    return gates


def _check_scans(rows: Rows, root: Path) -> None:
    secrets = boundary.secret_hits(root)
    _row(rows, "secret scan", PASS if not secrets else FAIL,
         f"{len(secrets)} findings (content never printed)",
         "; ".join(f"{h['file']} [{h['kind']}]" for h in secrets[:5]))
    paths = boundary.local_path_hits(root)
    _row(rows, "local path scan", PASS if not paths else FAIL,
         f"{len(paths)} machine-specific paths",
         "; ".join(f"{h['file']} [{h['kind']}]" for h in paths[:5]))
    payload = boundary.payload_hits(root)
    _row(rows, "payload scan", PASS if not payload else FAIL,
         f"{len(payload)} state/database/env/key files",
         "" if not payload else f"remove: {payload[:5]}")
    _check_denylist(rows, root)


def _check_denylist(rows: Rows, root: Path) -> None:
    raw = os.environ.get(boundary.DENYLIST_ENV, "").strip()
    if not raw:
        _row(rows, "external denylist", PASS,
             f"none supplied (downstream CI may set {boundary.DENYLIST_ENV})")
        return
    path = Path(raw)
    try:
        terms = boundary.load_denylist(path)
    except OSError as e:
        _row(rows, "external denylist", FAIL,
             f"unreadable denylist ({type(e).__name__})",
             f"check {boundary.DENYLIST_ENV}")
        return
    try:
        exclude = (path.resolve().relative_to(root.resolve()).as_posix(),)
    except (ValueError, OSError):
        exclude = ()
    hits = boundary.denylist_hits(root, terms, exclude=exclude)
    files = sorted({h["file"] for h in hits})
    _row(rows, "external denylist", PASS if not hits else FAIL,
         f"{len(terms)} terms, {len(hits)} hits in {len(files)} files",
         "" if not hits else f"files: {files[:5]} (terms withheld)")


def _check_docs(rows: Rows, root: Path) -> None:
    readme = root / "README.md"
    text = (readme.read_text(encoding="utf-8", errors="ignore").lower()
            if readme.is_file() else "")
    ok = ("tellurion ultra" in text or "tellurion demo" in text
          or "tellurion ultra" in text or "tellurion doctor" in text)
    _row(rows, "readme", PASS if ok else WARN,
         "quickstart present" if ok else "README missing quickstart",
         "" if ok else "add the three-command quickstart to README.md")
    ci = root / ".github" / "workflows" / "ci.yml"
    _row(rows, "ci", PASS if ci.is_file() else WARN,
         "ci.yml present" if ci.is_file() else "ci.yml missing",
         "" if ci.is_file() else "add .github/workflows/ci.yml")


def release_check(root: str | None = None,
                  port: int | None = None) -> Dict[str, Any]:
    """Run all release checks. Read-only. Never publishes.

    `port` overrides the doctor's localhost-bind probe target so
    verification can use an ephemeral port (default: 8765 behavior,
    where an occupied port is reported as environment-only)."""
    root_p = _candidate_root(root)
    rows: Rows = []
    _check_files(rows, root_p)
    _check_imports(rows, root_p)
    _check_doctor(rows, port=port)
    _check_live(rows, root_p)
    _check_dataset(rows)
    _check_plugin(rows, root_p)
    gates = _check_legal(rows, root_p)
    _check_scans(rows, root_p)
    _check_docs(rows, root_p)
    failed = sum(1 for c in rows if c["status"] == FAIL)
    warned = sum(1 for c in rows if c["status"] == WARN)
    verdict = FAIL if failed else (WARN if warned else PASS)
    return {"ok": verdict == PASS, "verdict": verdict, "failed": failed,
            "warned": warned, "checks": rows, "gates": gates["gates"],
            "publishable": gates["publishable"],
            "published": gates.get("published", False),
            "note": "read-only readiness probe; never publishes"}


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(prog="tellurion release-check")
    p.add_argument("--root", default=None,
                   help="repository root (default: auto-detect)")
    args, _unknown = p.parse_known_args()
    rep = release_check(args.root)
    print(json.dumps(rep, indent=1)[:4000])
    print(f"RELEASE CHECK: {rep['verdict']} ({rep['failed']} fail, "
          f"{rep['warned']} warn, publishable={rep['publishable']}, "
          f"NOT published)")
    return 0 if rep["verdict"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
