"""V16 Developer Preview Hardening tests (offline, no network, no creds).

Covers the preview surface only:
  release_manifest (total, fail-closed) / public-include completeness /
  module-scope import hygiene / portability (no drive letters, no
  backslash joins, no PowerShell-only steps) / optional_deps graceful
  degradation / explicit-only discovery / CLI doctor shape / demo
  localhost-only + strict-port / public API stability surface /
  preview artifact dry-run (0 missing, 0 violations, NOT published).

The private research lane is untouched: this file reads no private code,
no evaluation data and no research state.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from gods_eye.future import release_manifest as rm  # noqa: E402


# --- release_manifest -----------------------------------------------------

def test_manifest_classes_total_and_fail_closed():
    assert set(rm.CLASSES) == {"PUBLIC_INCLUDE", "PUBLIC_EXCLUDE",
                               "DATA_DEPENDENT", "GENERATED", "PRIVATE"}
    # unknown paths default to PRIVATE (fail closed)
    assert rm.classify("some/random/new_file.py") == "PRIVATE"
    # synthetic private-looking paths: the public tree names no real ones
    assert rm.classify("state/example_research.sqlite") != "PUBLIC_INCLUDE"
    assert rm.classify("evals/example_holdout.json") != "PUBLIC_INCLUDE"
    with pytest.raises(rm.ReleaseViolation):
        rm.assert_safe_for_release("state/example_research.sqlite")
    with pytest.raises(rm.ReleaseViolation):
        rm.assert_safe_for_release("evals/example_holdout.json")
    with pytest.raises(rm.ReleaseViolation):
        rm.assert_safe_for_release("python/gods_eye/private_research/model.py")


def test_manifest_injected_private_markers(monkeypatch):
    """Private names are injected at run time, never shipped in the tree."""
    probe = "python/gods_eye/future/zz_injected_marker_probe.py"
    monkeypatch.delenv("TELLURION_DENY_MARKERS", raising=False)
    assert "zz_injected_marker" not in "".join(rm.private_markers())
    monkeypatch.setenv("TELLURION_DENY_MARKERS", "zz_injected_marker, other")
    assert rm.classify(probe) == "PRIVATE"
    assert "zz_injected_marker" in rm.private_markers()


def test_manifest_all_included_classify_clean():
    for f in rm.public_include():
        assert rm.classify(f) == "PUBLIC_INCLUDE", f
        assert rm.assert_safe_for_release(f) == "PUBLIC_INCLUDE"
    summary = rm.manifest_summary()
    assert summary["all_included_classify_clean"] is True
    assert summary["n_public_include"] == len(rm.public_include())


def test_public_include_files_exist_on_disk():
    missing = [f for f in rm.public_include() if not (ROOT / f).is_file()]
    assert missing == [], f"missing preview files: {missing}"


def test_expected_v16_preview_files_present():
    # Canonical public layout: every file named here must exist on disk
    # and classify PUBLIC_INCLUDE (fail-closed manifest).
    for rel in ("docs/public/RIGHTS_POLICY.md",
                "docs/public/SECURITY_DEFAULTS.md",
                "docs/public/TERMS_SNAPSHOTS.md",
                "docs/public/LIVE_AVIATION_SOURCE_DECISION.md",
                "examples/contributor_tasks/add_demo_sensor.md",
                "LICENSE",
                "NOTICE",
                "legal/THIRD_PARTY_NOTICES.md",
                "legal/SBOM.spdx.json",
                "console/world.html",
                "console/world/app.js"):
        assert (ROOT / rel).is_file(), rel
        assert rm.classify(rel) == "PUBLIC_INCLUDE", rel


# --- import hygiene (module scope) -----------------------------------------

_SCOPE_IMPORT = re.compile(
    r"^(import|from)\s+(skfolio|pypfopt|riskfolio|cvxpy|nautilus_trader|"
    r"hftbacktest|lean|pyfolio|empyrical|alphalens|torch|qanat|mlflow|dvc|"
    r"dagster|prefect|vectorbt|duckdb|ccxt|exchange_calendars|"
    r"pandas_market_calendars|gods_eye\.calibration|gods_eye\.watcher|"
    r"gods_eye\.pipeline)\b", re.MULTILINE)


def test_public_modules_no_heavy_or_private_module_scope_imports():
    mods = [f for f in rm.public_include()
            if f.startswith("python/gods_eye/") and f.endswith(".py")]
    assert len(mods) >= 20
    for rel in mods:
        src = (ROOT / rel).read_text(encoding="utf-8")
        assert _SCOPE_IMPORT.search(src) is None, f"forbidden import in {rel}"


# --- portability (no drive letters, backslash joins, pwsh-only) ------------

def test_public_modules_portable_no_drive_or_backslash_join():
    drive = re.compile(r"[A-Za-z]:\\")
    bs_join = re.compile(r"""['"]\\\\['"]\s*\+|os\.path\.join\(.*\\\\""")
    pwsh = re.compile(r"powershell\.exe|PowerShell\s+-Command|"
                      r"\bStart-Job\b|\bReceive-Job\b", re.IGNORECASE)
    mods = [f for f in rm.public_include()
            if f.startswith("python/gods_eye/") and f.endswith(".py")]
    for rel in mods:
        src = (ROOT / rel).read_text(encoding="utf-8")
        assert not drive.search(src), f"drive letter in {rel}"
        assert not bs_join.search(src), f"backslash join in {rel}"
        assert not pwsh.search(src), f"powershell-only step in {rel}"


# --- optional_deps ----------------------------------------------------------

def test_optional_deps_core_requires_none():
    from gods_eye.future import optional_deps as od
    rep = od.report()
    assert rep["schema"] == "optional-deps-v1"
    assert rep["core_requires_none"] is True
    for row in rep["rows"]:
        assert row["status"] in od.STATUSES, row
    assert od.probe("no_such_dep")["status"] == "UNKNOWN"
    # the catalog itself must stay free of trading or ML engines
    assert set(od.names()) == {"playwright", "pytest"}


# --- discovery (explicit only) ----------------------------------------------

def test_discovery_explicit_only(tmp_path):
    from gods_eye.future import discovery as di
    assert di.ENTRY_POINT_GROUP == "gods_eye.plugins"
    rep = di.discover()
    assert "entry_points" in rep and "total_ok" in rep
    # missing dir -> reported error, never raised
    dd = di.discover_from_dirs([tmp_path / "does-not-exist"])
    assert dd["errors"] and dd["plugins"] == []
    # empty dir -> nothing found, no crash, no CWD scan
    empty = tmp_path / "empty"
    empty.mkdir()
    dd2 = di.discover_from_dirs([empty])
    assert dd2["plugins"] == [] and dd2["searched"] == [str(empty)]
    # example template validates through discovery
    tpl_parent = ROOT / "examples" / "plugins"
    assert (tpl_parent / "example_sensor" / "manifest.json").is_file()
    dd3 = di.discover_from_dirs([tpl_parent])
    assert len(dd3["plugins"]) == 1 and dd3["plugins"][0]["ok"] is True


# --- CLI doctor ---------------------------------------------------------------

def test_cli_doctor_shape_and_live_disabled():
    from gods_eye.cli import cmd_doctor
    rep = cmd_doctor()
    assert {"ok", "verdict", "failed", "warned", "checks"} <= set(rep)
    assert rep["verdict"] in ("PASS", "WARN", "FAIL")
    for c in rep["checks"]:
        assert {"name", "status", "detail", "fix"} <= set(c)
        assert c["status"] in ("PASS", "WARN", "FAIL")
    names = [c["name"] for c in rep["checks"]]
    assert "community-mode imports" in names
    assert "no execution surface" in names
    live = next(c for c in rep["checks"] if c["name"] == "no execution surface")
    assert live["status"] == "PASS"


# --- demo localhost-only + strict port -----------------------------------------

def test_demo_localhost_only_and_port_policy():
    from gods_eye import demo
    from gods_eye.demo import PortOccupied, select_port
    assert demo.HOST == "127.0.0.1"
    assert demo.DEFAULT_PORT == 8765
    with pytest.raises(ValueError):
        select_port(0)
    with pytest.raises(ValueError):
        select_port(70000)
    # occupied port: fallback by default, fail closed in strict mode
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((demo.HOST, 0))
    s.listen(10)  # listening: connects succeed (real occupancy)
    busy = s.getsockname()[1]
    try:
        use_port, fell_back = select_port(busy)
        assert fell_back is True and use_port != busy
        with pytest.raises(PortOccupied):
            select_port(busy, strict=True)
    finally:
        s.close()
    # health payload never allows live
    assert "allow_live" not in demo.health_payload()


# --- public API stability surface -----------------------------------------------

def test_public_api_stability_surface():
    from gods_eye.future import plugins as pl
    from gods_eye.future import public_api as api
    for fn in ("register_sensor", "register_entity_resolver",
               "register_visualization", "list_registered", "api_surface"):
        assert callable(getattr(api, fn)), fn
    for gone in ("register_market_data_provider", "register_venue",
                 "register_model_challenger"):
        assert not hasattr(api, gone), gone
    assert api.api_surface()["schema"] == "public-api-v1"
    for fn in ("declare", "production_qualified", "qualify_or_refuse",
               "rights_declared"):
        assert callable(getattr(pl, fn)), fn
    assert pl.KINDS == ("Sensor", "EntityResolver", "Visualization")
    # demo dataset frozen id + CC0 + no holdout refs
    from gods_eye.future import demo_dataset as dd
    assert dd.DATASET_ID == "community-demo-v1"
    assert dd.LICENSE.startswith("CC0")
    assert dd.validate_no_holdout_refs()["ok"] is True


def test_community_mode_no_private_introduced():
    from gods_eye.future import community as co
    rep = co.community_check()
    assert rep["failed"] == [] and rep["private_introduced"] == []


def test_no_execution_surface():
    from pathlib import Path
    from gods_eye.future import boundary
    from gods_eye import demo
    assert boundary.trading_surface_hits(Path(__file__).resolve().parents[1]) == []
    health = demo.health_payload()
    assert "allow_live" not in health and "venues" not in demo.demo_payload()


# --- preview artifact dry-run -----------------------------------------------------

def test_preview_build_dry_run_ok(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "build_public_candidate", str(ROOT / "scripts" / "build_public_candidate.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    report = mod.build(tmp_path / "tellurion-public-candidate")
    assert report["missing"] == [], report["missing"]
    assert report["ok"] is True
    assert report["published"] is False
    assert report["copied"] == len(rm.public_include())


def test_preview_artifact_gitignore_public_safe(tmp_path):
    """V17.5B: preview artifact ships a public-safe .gitignore that
    release_check requires, and it must not ignore shipped assets."""
    import fnmatch
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "build_public_candidate", str(ROOT / "scripts" / "build_public_candidate.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = tmp_path / "tellurion-public-candidate"
    report = mod.build(out)
    assert report["ok"] is True
    gi = out / ".gitignore"
    assert gi.is_file(), "release_check REQUIRES .gitignore in the artifact"
    assert rm.classify(".gitignore") == "PUBLIC_INCLUDE"
    patterns = [ln.strip() for ln in gi.read_text(encoding="utf-8").splitlines()
                if ln.strip() and not ln.strip().startswith("#")]
    assert patterns, "gitignore must not be empty"
    # shipped public assets must survive every pattern
    for asset in ("pyproject.toml",
                  "console/demo.html",
                  "console/world.html",
                  "examples/plugins/example_sensor/fixture.json",
                  "examples/plugins/example_sensor/plugin.py",
                  "legal/SBOM.spdx.json"):
        for pat in patterns:
            assert not fnmatch.fnmatch(asset, pat), f"{pat} ignores {asset}"
            assert not fnmatch.fnmatch(asset.rsplit("/", 1)[-1], pat), \
                f"{pat} ignores {asset}"
    # hygiene minimums stay covered
    for must in ("__pycache__/", "*.py[cod]", ".venv/", "dist/", ".env"):
        assert must in patterns, f"missing ignore: {must}"


def test_sbom_preview_shape():
    sbom_path = ROOT / "legal" / "SBOM.spdx.json"
    assert sbom_path.is_file()
    sbom = json.loads(sbom_path.read_text(encoding="utf-8"))
    assert sbom["spdxVersion"] == "SPDX-2.3"
    # sign-off is a maintainer decision; the file must state which one
    assert sbom["signOff"].startswith(("NOT_OBTAINED", "OBTAINED"))
    assert isinstance(sbom["published"], bool)
    assert sbom["packages"][0]["license"] == "MIT"
    assert len(sbom["packages"]) >= 1
    for p in sbom["packages"]:
        assert {"name", "version", "license", "source"} <= set(p)


# --- scaffold portability (V17.5B: no repo-depth assumption) -------------------

def test_example_sensor_template_has_no_depth_assumption():
    """The scaffolded test file ships out-of-tree; it must never index
    parents[N] (V17.5B: /tmp/smoke_sensor raised IndexError)."""
    text = (ROOT / "examples" / "plugins" / "example_sensor"
            / "test_example_sensor.py").read_text(encoding="utf-8")
    assert "parents[" not in text


def test_new_plugin_scaffold_runs_at_shallow_depth():
    """Scaffold to the shallowest writable dir and run its tests offline.

    On Linux gettempdir() is /tmp so dest is 2 levels deep — the exact
    shape that raised IndexError before the V17.5B fix. gods_eye resolves
    from the installed package / explicit PYTHONPATH, never from depth.
    """
    import os
    import shutil
    import subprocess
    import tempfile
    from gods_eye import cli as _cli
    dest = Path(tempfile.gettempdir()) / f"smoke_shallow_{os.getpid()}"
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    rep = _cli.cmd_new_plugin("sensor", "smoke-sensor", str(dest))
    assert rep["ok"], rep
    try:
        # isolate from any project env vars (never rely on them)
        env = {k: v for k, v in os.environ.items()
               if not k.upper().startswith(("GODS_EYE_", "TELLURION_"))}
        env["PYTHONPATH"] = str(ROOT / "python")
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", str(dest), "-q",
             "-p", "no:cacheprovider"],
            capture_output=True, text=True, timeout=180, env=env)
        assert proc.returncode == 0, (
            f"depth={len(dest.resolve().parents)} "
            + (proc.stdout or "")[-1500:] + (proc.stderr or "")[-1500:])
    finally:
        shutil.rmtree(dest, ignore_errors=True)
