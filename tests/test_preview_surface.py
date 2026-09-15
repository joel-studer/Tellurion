"""Developer-preview surface tests (offline, no network, no credentials).

Covers: module-scope import hygiene / portability (no drive letters, no
backslash joins, no PowerShell-only steps) / optional_deps graceful
degradation / explicit-only discovery / CLI doctor shape / demo
localhost-only + strict-port / public API stability surface /
repository .gitignore / SBOM shape / scaffold portability.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))



def _public_modules():
    base = ROOT / "python" / "gods_eye"
    return sorted(p.relative_to(ROOT).as_posix() for p in base.rglob("*.py")
                  if "__pycache__" not in p.parts)


# --- import hygiene (module scope) -----------------------------------------

_SCOPE_IMPORT = re.compile(
    r"^(import|from)\s+(skfolio|pypfopt|riskfolio|cvxpy|nautilus_trader|"
    r"hftbacktest|lean|pyfolio|empyrical|alphalens|torch|qanat|mlflow|dvc|"
    r"dagster|prefect|vectorbt|duckdb|ccxt|exchange_calendars|"
    r"pandas_market_calendars)\b", re.MULTILINE)


def test_public_modules_no_heavy_or_private_module_scope_imports():
    mods = _public_modules()
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
    mods = _public_modules()
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
    # LGPL boundary: nautilus is never importable in-process
    assert od.probe("nautilus_trader")["status"] in ("BLOCKED", "NOT_INSTALLED")


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
    assert "live execution disabled" in names
    live = next(c for c in rep["checks"] if c["name"] == "live execution disabled")
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
    assert demo.health_payload()["allow_live"] is False


# --- public API stability surface -----------------------------------------------

def test_public_api_stability_surface():
    from gods_eye.future import plugins as pl
    from gods_eye.future import public_api as api
    for fn in ("register_sensor", "register_market_data_provider",
               "register_entity_resolver", "register_visualization",
               "register_model_challenger", "register_venue",
               "list_registered", "api_surface"):
        assert callable(getattr(api, fn)), fn
    assert api.api_surface()["schema"] == "public-api-v1"
    for fn in ("declare", "production_qualified", "qualify_or_refuse",
               "rights_declared"):
        assert callable(getattr(pl, fn)), fn
    assert "Sensor" in pl.KINDS and "Venue" in pl.KINDS
    assert "PredictionMarket" in pl.KINDS
    # demo dataset frozen id + CC0 + no holdout refs
    from gods_eye.future import demo_dataset as dd
    assert dd.DATASET_ID == "community-demo-v1"
    assert dd.LICENSE.startswith("CC0")
    assert dd.validate_no_holdout_refs()["ok"] is True


def test_community_mode_no_private_introduced():
    from gods_eye.future import community as co
    rep = co.community_check()
    assert rep["failed"] == [] and rep["private_introduced"] == []


def test_allow_live_false():
    from gods_eye.future import exec_safety as es
    assert es.ALLOW_LIVE is False
    g = es.LiveExecutionGuard().describe()
    assert g["ALLOW_LIVE"] is False and g["ALLOW_PAPER_SANDBOX"] is False


# --- repository .gitignore ---------------------------------------------------

def test_repository_gitignore_public_safe():
    """Shipped assets survive every ignore pattern; hygiene minimums stay."""
    import fnmatch
    gi = ROOT / ".gitignore"
    assert gi.is_file()
    patterns = [ln.strip() for ln in gi.read_text(encoding="utf-8").splitlines()
                if ln.strip() and not ln.strip().startswith(("#", "!"))]
    assert patterns, "gitignore must not be empty"
    for asset in ("pyproject.toml",
                  "console/demo.html",
                  "examples/plugins/example_sensor/fixture.json",
                  "examples/plugins/example_sensor/plugin.py",
                  "docs/guides/clean-linux-check.md",
                  "legal/SBOM.spdx.json",
                  "legal/ASSET_RIGHTS.json"):
        for pat in patterns:
            assert not fnmatch.fnmatch(asset, pat), f"{pat} ignores {asset}"
            assert not fnmatch.fnmatch(asset.rsplit("/", 1)[-1], pat), \
                f"{pat} ignores {asset}"
    for must in ("__pycache__/", "*.py[cod]", ".venv/", "dist/", ".env"):
        assert must in patterns, f"missing ignore: {must}"


def test_sbom_preview_shape():
    sbom_path = ROOT / "legal/SBOM.spdx.json"
    assert sbom_path.is_file()
    sbom = json.loads(sbom_path.read_text(encoding="utf-8"))
    assert sbom["spdxVersion"] == "SPDX-2.3"
    assert sbom["signOff"].startswith("NOT_OBTAINED")
    assert sbom["published"] is False
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
        env = dict(os.environ)
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
