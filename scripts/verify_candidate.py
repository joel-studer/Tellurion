"""Standalone verification for the public candidate (V17).

Run from anywhere; points itself at the candidate dir (default
dist/tellurion-public-candidate, override with --candidate) and
refuses any fallback into the private source tree:

  python scripts/verify_candidate.py [--candidate DIR]

Doctor/release-check gates probe an OS-assigned ephemeral port, so
verification never depends on ambient port occupancy (production
default 8765 is untouched).

Exit 0 + CANDIDATE: PASS only if imports, CLI, doctor, demo smoke,
plugin SDK, dataset, example test, release-check, and path isolation
all hold with the candidate as the ONLY gods_eye source.
"""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATE = ROOT / "dist" / "tellurion-public-candidate"


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


CANDIDATE = DEFAULT_CANDIDATE
CAND_PY = CANDIDATE / "python"


def _run(args: list[str], **kw) -> subprocess.CompletedProcess:
    env = {"PYTHONPATH": str(CAND_PY), "PATH": kw.pop("path", None) or ""}
    import os
    # Scrub every project env var (never rely on them), then point the
    # interpreter at the candidate only.
    full = {k: v for k, v in os.environ.items()
            if not k.upper().startswith(("GODS_EYE_", "TELLURION_"))}
    full["PYTHONPATH"] = str(CAND_PY)
    return subprocess.run(args, cwd=str(CANDIDATE), env=full,
                          capture_output=True, text=True, timeout=120)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", default=str(DEFAULT_CANDIDATE))
    args = ap.parse_args()
    CANDIDATE = Path(args.candidate).resolve()
    CAND_PY = CANDIDATE / "python"
    EPHEMERAL_PORT = _free_port()
    # Rebind module globals so _run targets this candidate.
    globals()["CANDIDATE"] = CANDIDATE
    globals()["CAND_PY"] = CAND_PY
    rows: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        rows.append((name, ok, detail))
        print(("PASS" if ok else "FAIL"), "|", name, "|", detail[:160])

    if not CAND_PY.is_dir():
        print("CANDIDATE: FAIL (build dist/tellurion-public-candidate first)")
        return 1

    # 1. imports (canonical + alias), isolation of module file origin
    p = _run([sys.executable, "-c",
              "import gods_eye, gods_eye.cli, gods_eye.demo, "
              "gods_eye.future.validator, gods_eye.future.release_check, "
              "gods_eye.plugins, gods_eye.demo, gods_eye.market, "
              "gods_eye.execution, gods_eye.portfolio, gods_eye.core; "
              "print(gods_eye.__file__)"])
    origin = (p.stdout or "").strip()
    check("imports (canonical + alias)",
          p.returncode == 0 and str(CANDIDATE) in origin, origin or p.stderr)

    # 2. CLI doctor on an ephemeral port (never ambient 8765).
    p = _run([sys.executable, "-m", "gods_eye.cli", "doctor",
              "--port", str(EPHEMERAL_PORT)])
    try:
        _start = p.stdout.index("{")
        _end = p.stdout.rindex("}")
        rep = json.loads(p.stdout[_start:_end + 1])
        check("doctor", rep.get("verdict") == "PASS",
              f"verdict={rep.get('verdict')}")
    except Exception as e:
        check("doctor", False, f"unparseable: {e}")

    # 3. demo smoke
    p = _run([sys.executable, "scripts/smoke_demo_api.py"])
    check("demo smoke", p.returncode == 0 and "SMOKE: OK" in p.stdout,
          (p.stdout or p.stderr).strip()[:160])

    # 4. plugin SDK: validate + register example sensor
    p = _run([sys.executable, "-m", "gods_eye.cli", "plugins",
              "validate", "examples/plugins/example_sensor"])
    check("plugin validate", p.returncode == 0 and "PASS" in p.stdout,
          (p.stdout or p.stderr).strip()[-160:])

    # 5. demo dataset
    p = _run([sys.executable, "-c",
              "from gods_eye.future import demo_dataset as dd; "
              "assert dd.DATASET_ID=='community-demo-v1'; "
              "assert dd.validate_no_holdout_refs()['ok']; "
              "print('dataset ok')"])
    check("demo dataset", p.returncode == 0 and "dataset ok" in p.stdout,
          (p.stdout or p.stderr).strip()[:160])

    # 6. example plugin offline test (candidate-local pytest)
    p = _run([sys.executable, "-m", "pytest",
              "examples/plugins/example_sensor/test_example_sensor.py", "-q",
              "-p", "no:cacheprovider"])
    check("example plugin test",
          p.returncode == 0 and "passed" in (p.stdout or ""),
          ((p.stdout or "").strip().splitlines() or [""])[-1][:160])

    # 7. release-check on the candidate (full JSON via API; the CLI
    # truncates its printout for terminals). Same ephemeral port.
    p = _run([sys.executable, "-c",
              "import json; from gods_eye.future import release_check as rc; "
              "print(json.dumps(rc.release_check('.', "
              f"port={EPHEMERAL_PORT})))"])
    try:
        import json as _json
        rep = _json.JSONDecoder().raw_decode(p.stdout[p.stdout.index("{"):])[0]
        check("release-check", rep.get("verdict") == "PASS",
              f"verdict={rep.get('verdict')} "
              f"fail={rep.get('failed')} warn={rep.get('warned')} " +
              "; ".join(c["name"] for c in rep.get("checks", [])
                        if c["status"] != "PASS")[:160])
    except Exception as e:
        check("release-check", False,
              f"unparseable: {e} rc={p.returncode} "
              f"out={p.stdout[:120]!r} err={p.stderr[:160]!r}")

    # 8. path isolation: no private-root references in candidate files
    priv = str(ROOT).replace("\\", "/")
    leaks: list[str] = []
    for f in sorted(CANDIDATE.rglob("*")):
        if not f.is_file() or "__pycache__" in f.parts:
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="strict")
        except (UnicodeDecodeError, OSError):
            continue
        if priv in text.replace("\\", "/") or ".env" in f.name:
            leaks.append(f.relative_to(CANDIDATE).as_posix())
    check("no private-path leakage", not leaks, str(leaks[:5]))

    # 9. no private payload dirs in candidate
    bad_dirs = [d for d in ("state", "state_future", "evals", "raw_store",
                            "logs", "src", "proto", "harvest")
                if (CANDIDATE / d).exists()]
    check("no private payload dirs", not bad_dirs, str(bad_dirs))

    failed = [n for n, ok, _ in rows if not ok]
    print(f"CANDIDATE: {'PASS' if not failed else 'FAIL'} "
          f"({len(rows) - len(failed)}/{len(rows)})")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
