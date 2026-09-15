"""Standalone install verification for this repository.

Every check runs in a subprocess whose ``gods_eye`` must come from THIS
checkout (``python/``):

  python scripts/verify_install.py

Exit 0 + ``VERIFY: PASS`` only if imports, doctor, demo smoke, plugin SDK,
demo dataset, example plugin test, release-check, import boundary, and
standard-library-only startup all hold.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = ROOT / "python"
ENVIRONMENT_ONLY_CHECKS = ("localhost bind",)  # mirrors release_check

STDLIB_PROBE = (
    "import importlib, os, sys; root = os.path.normcase(sys.argv[1]); "
    "sys.path.insert(0, root); "
    "[importlib.import_module(m) for m in ('gods_eye.cli', 'gods_eye.demo', "
    "'gods_eye.plugins', 'gods_eye.future.release_check')]; "
    "bad = [n for n, m in list(sys.modules.items()) "
    "if n.startswith('gods_eye') and getattr(m, '__file__', None) "
    "and not os.path.normcase(m.__file__).startswith(root)]; "
    "print('STDLIB-ONLY OK' if not bad else f'OUTSIDE {bad}')"
)


def _run(args: list[str]) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(PY)
    return subprocess.run(args, cwd=str(ROOT), env=env, capture_output=True,
                          text=True, timeout=300)


def _json_from(text: str) -> dict:
    return json.JSONDecoder().raw_decode(text[text.index("{"):])[0]


def _checks() -> list[tuple[str, bool, str]]:
    rows: list[tuple[str, bool, str]] = []
    py = sys.executable

    p = _run([py, "-c", "import gods_eye, gods_eye.cli, gods_eye.demo, "
              "gods_eye.plugins, gods_eye.market, gods_eye.execution, "
              "gods_eye.portfolio, gods_eye.core; print(gods_eye.__file__)"])
    origin = (p.stdout or "").strip()
    inside = os.path.normcase(origin).startswith(os.path.normcase(str(PY)))
    rows.append(("imports from this checkout", p.returncode == 0 and inside,
                 origin or p.stderr[-160:]))

    p = _run([py, "-m", "gods_eye.cli", "doctor"])
    try:
        rep = _json_from(p.stdout)
        # Machine-specific rows (e.g. a busy port) never fail the install.
        tree_issues = [c["name"] for c in rep.get("checks", [])
                       if c["status"] != "PASS"
                       and c["name"] not in ENVIRONMENT_ONLY_CHECKS]
        ok = rep.get("failed") == 0 and not tree_issues
        detail = f"verdict={rep.get('verdict')} tree_issues={tree_issues}"
    except ValueError as e:
        ok, detail = False, f"unparseable ({e})"
    rows.append(("doctor", ok, detail))

    p = _run([py, "scripts/smoke_demo_api.py"])
    rows.append(("demo smoke", p.returncode == 0 and "SMOKE: OK" in p.stdout,
                 (p.stdout or p.stderr).strip()[-160:]))

    p = _run([py, "-m", "gods_eye.cli", "plugins", "validate",
              "examples/plugins/example_sensor"])
    rows.append(("plugin validate", p.returncode == 0 and "PASS" in p.stdout,
                 (p.stdout or p.stderr).strip()[-160:]))

    p = _run([py, "-c", "from gods_eye.future import demo_dataset as dd; "
              "assert dd.DATASET_ID == 'community-demo-v1'; "
              "assert dd.validate_no_holdout_refs()['ok']; print('dataset ok')"])
    rows.append(("demo dataset", "dataset ok" in p.stdout,
                 (p.stdout or p.stderr).strip()[-160:]))

    p = _run([py, "-m", "pytest",
              "examples/plugins/example_sensor/test_example_sensor.py", "-q",
              "-p", "no:cacheprovider"])
    last = ((p.stdout or "").strip().splitlines() or [""])[-1]
    rows.append(("example plugin test", p.returncode == 0 and "passed" in last,
                 last[-160:]))

    p = _run([py, "-c", "import json; from gods_eye.future import release_check "
              "as rc; print(json.dumps(rc.release_check('.')))"])
    try:
        rep = _json_from(p.stdout)
        bad = [c["name"] for c in rep["checks"] if c["status"] != "PASS"]
        rows.append(("release-check", rep["verdict"] == "PASS",
                     f"verdict={rep['verdict']} not-pass={bad}"))
    except ValueError as e:
        rows.append(("release-check", False, f"unparseable: {e}"))

    p = _run([py, "-c", "from gods_eye.future import boundary; "
              "import json; print(json.dumps(boundary."
              "unresolved_internal_imports('.')))"])
    rows.append(("import boundary", p.stdout.strip() == "[]",
                 (p.stdout or p.stderr).strip()[-160:]))

    p = subprocess.run([py, "-S", "-E", "-c", STDLIB_PROBE, str(PY)],
                       cwd=str(ROOT), capture_output=True, text=True,
                       timeout=120)
    rows.append(("standard-library-only startup",
                 "STDLIB-ONLY OK" in p.stdout,
                 (p.stdout or p.stderr).strip()[-160:]))
    return rows


def main() -> int:
    rows = _checks()
    for name, ok, detail in rows:
        print("PASS" if ok else "FAIL", "|", name, "|", detail)
    failed = [name for name, ok, _ in rows if not ok]
    print(f"VERIFY: {'PASS' if not failed else 'FAIL'} "
          f"({len(rows) - len(failed)}/{len(rows)})")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
