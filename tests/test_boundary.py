"""Open-core boundary tests: the core stands alone and never reaches outside.

* every gods_eye import (any scope) resolves inside python/gods_eye
* the core imports and runs with only the standard library on sys.path
  (no site-packages, so no downstream or third-party package can leak in)
* no runtime state, databases, env or key files in the tree
* no credential material or machine-specific paths
* extension slots fail with a clear error and accept providers
* isolation ships no hardcoded profile
* caller-supplied denylists fail closed without echoing their terms
* every asset has a declared, allowed licence and a matching hash
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from gods_eye.future import boundary  # noqa: E402

CORE_ENTRYPOINTS = (
    "gods_eye.cli", "gods_eye.demo", "gods_eye.core", "gods_eye.plugins",
    "gods_eye.future.ultra_demo", "gods_eye.future.release_check",
    "gods_eye.future.world_now", "gods_eye.future.world_change",
)

_STDLIB_ONLY_PROBE = """
import importlib, json, os, sys
pkg_root = os.path.normcase(os.path.abspath(sys.argv[1]))
sys.path.insert(0, pkg_root)
for name in sys.argv[2:]:
    importlib.import_module(name)
from gods_eye.cli import cmd_doctor
report = cmd_doctor()
outside = sorted(
    n for n, m in list(sys.modules.items())
    if n.split(".")[0] == "gods_eye" and getattr(m, "__file__", None)
    and not os.path.normcase(os.path.abspath(m.__file__)).startswith(pkg_root))
print(json.dumps({"verdict": report["verdict"], "outside": outside}))
"""


def test_every_internal_import_resolves_inside_the_package():
    assert boundary.unresolved_internal_imports(ROOT) == []


def test_import_scanner_flags_a_module_that_does_not_ship(tmp_path):
    pkg = tmp_path / "python" / "gods_eye" / "future"
    pkg.mkdir(parents=True)
    (pkg.parent / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "__init__.py").write_text('"""docs only"""\n', encoding="utf-8")
    (pkg / "core.py").write_text(
        "def run():\n"
        "    from gods_eye.future import not_shipped\n"
        "    return not_shipped\n", encoding="utf-8")
    problems = boundary.unresolved_internal_imports(tmp_path)
    assert [p["module"] for p in problems] == ["gods_eye.future.not_shipped"]


def test_core_runs_with_standard_library_only():
    proc = subprocess.run(
        [sys.executable, "-S", "-E", "-c", _STDLIB_ONLY_PROBE,
         str(ROOT / "python"), *CORE_ENTRYPOINTS],
        capture_output=True, text=True, timeout=180, cwd=str(ROOT))
    assert proc.returncode == 0, proc.stderr[-2000:]
    result = json.loads(proc.stdout.strip().splitlines()[-1])
    assert result["outside"] == []
    assert result["verdict"] in ("PASS", "WARN")


def test_no_runtime_payload_in_tree():
    assert boundary.payload_hits(ROOT) == []


def test_no_credential_material_or_local_paths():
    assert boundary.secret_hits(ROOT) == []
    assert boundary.local_path_hits(ROOT) == []


def _synthetic_samples():
    # Assembled at runtime so this file never contains a literal match.
    bs = chr(92)
    return [
        ("-----BEGIN" + " PRIVATE KEY-----", "PRIVATE_KEY_BLOCK"),
        ("token = gh" + "p_" + "a" * 36, "GITHUB_TOKEN"),
        ("AK" + "IA" + "B" * 16, "AWS_ACCESS_KEY"),
        ("wallet" + "_pk = 0x" + "ab" * 32, "HEX_PRIVATE_KEY"),
        ("api" + '_key = "' + "z" * 12 + '"', "CREDENTIAL_ASSIGNMENT"),
        ("C:" + bs + "Users" + bs + "alice" + bs + "repo", "WINDOWS_USER_PATH"),
    ]


def test_scanners_detect_synthetic_material(tmp_path):
    for i, (text, _kind) in enumerate(_synthetic_samples()):
        (tmp_path / f"sample_{i}.txt").write_text(text, encoding="utf-8")
    kinds = {h["kind"] for h in boundary.secret_hits(tmp_path)}
    kinds |= {h["kind"] for h in boundary.local_path_hits(tmp_path)}
    assert {kind for _, kind in _synthetic_samples()} <= kinds


def test_no_trading_or_execution_surface_ships():
    """V1 is world intelligence only: the trading modules must not exist."""
    assert boundary.trading_surface_hits(ROOT) == []
    for name in ("venues", "market", "exec_engine", "portfolio_optimizer",
                 "nautilus_polymarket", "prediction_markets"):
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(f"gods_eye.future.{name}")


def test_public_never_references_private_package():
    """Dependency direction (hard rule): tellurion-private may import
    Tellurion, but Tellurion must never reference tellurion-private.

    Terms are assembled so this file itself never contains the literal
    match (same precedent as _synthetic_samples above)."""
    private = "gods_eye" + "_private"
    hyphen = "gods-eye" + "-private"
    assert boundary.denylist_hits(ROOT, [private, hyphen]) == []


def test_trading_surface_check_detects_a_reintroduced_module(tmp_path):
    pkg = tmp_path / "python" / "gods_eye" / "future"
    pkg.mkdir(parents=True)
    (pkg / "venues.py").write_text("VENUE = 1", encoding="utf-8")
    (pkg / "world_now.py").write_text("NOW = 1", encoding="utf-8")
    assert boundary.trading_surface_hits(tmp_path) == [
        "python/gods_eye/future/venues.py"]


def test_isolation_ships_no_hardcoded_profile(tmp_path):
    from gods_eye.future import isolation as iso
    iso.reset()
    state = iso.read_only_active_state()
    assert state["profile"] == "none"
    assert state["protected_dirs"] == []
    assert state["protected_files"] == []
    assert state["holdout_paths"] == []
    iso.configure(name="test", root=tmp_path, protected_dirs=("locked",),
                  read_forbidden=("sealed/set.json",))
    try:
        assert iso.is_protected(tmp_path / "locked" / "a.db")
        assert iso.is_holdout(tmp_path / "sealed" / "set.json")
        with pytest.raises(iso.IsolationViolation):
            iso.assert_future_writable(tmp_path / "locked" / "a.db")
        with pytest.raises(ValueError):
            iso.configure(name="bad", protected_dirs=("../escape",))
    finally:
        iso.reset()


def test_caller_supplied_denylist_fails_closed(tmp_path, monkeypatch):
    from gods_eye.future import release_check as rc
    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / "notes.md").write_text("mentions Project-Zebra internals\n",
                                   encoding="utf-8")
    deny = tmp_path / "deny.txt"
    deny.write_text("# downstream terms\nproject-zebra\n", encoding="utf-8")
    hits = boundary.denylist_hits(tree, boundary.load_denylist(deny))
    assert [h["file"] for h in hits] == ["notes.md"]
    monkeypatch.setenv(boundary.DENYLIST_ENV, str(deny))
    report = rc.release_check(str(tree))
    row = next(c for c in report["checks"] if c["name"] == "external denylist")
    assert row["status"] == "FAIL"
    assert "project-zebra" not in json.dumps(row)


def test_every_asset_has_declared_rights():
    report = boundary.asset_rights(ROOT)
    assert report["ok"], report["errors"][:10]
    assert report["n_assets"] >= 10


def test_release_check_passes_and_gates_decide_publishability():
    from gods_eye.future import release_check as rc
    report = rc.release_check(str(ROOT))
    not_passing = [c for c in report["checks"] if c["status"] != "PASS"]
    assert report["verdict"] == "PASS", not_passing
    assert report["published"] is False
    gates = rc.read_gates(ROOT)
    closed = all(v in rc.CLOSED_GATE_VALUES for v in gates["gates"].values())
    assert report["publishable"] is closed
