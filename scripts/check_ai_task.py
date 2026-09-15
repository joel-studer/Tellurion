"""Acceptance checker for the AI-agent sensor task (V17, offline).

Usage: python scripts/check_ai_task.py ./weather_sensor_demo
Exit 0 + AI_TASK: PASS when every machine-verifiable criterion holds.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))


def main() -> int:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("plugin_dir")
    args = p.parse_args()
    from gods_eye.future import validator as vd
    rep = vd.validate_plugin_dir(args.plugin_dir)
    d = Path(args.plugin_dir)
    checks = []
    checks.append(("validate verdict != FAIL",
                   rep["verdict"] in ("PASS", "WARN")))
    manifest = json.loads((d / "manifest.json").read_text(encoding="utf-8")) \
        if (d / "manifest.json").is_file() else {}
    checks.append(("schema plugin-v1",
                   manifest.get("schema") == "plugin-v1"))
    checks.append(("non-UNKNOWN rights",
                   str(manifest.get("data_rights", "UNKNOWN")).upper()
                   != "UNKNOWN"))
    checks.append(("offline test shipped",
                   bool(sorted(d.glob("test_*.py")))))
    try:
        sys.path.insert(0, str(d))
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "task_plugin", str(d / "plugin.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        cls = getattr(mod, "ExampleSensor", None) or getattr(
            mod, "WeatherSensorDemo", None) or getattr(mod, "Sensor", None)
        if cls is None:
            for v in vars(mod).values():
                if isinstance(v, type) and hasattr(v, "poll"):
                    cls = v
                    break
        out = cls().poll() if cls else {}
        checks.append(("poll() returns items+provenance+rights",
                       bool(out.get("items")) and "provenance" in out
                       and "rights" in out))
    except Exception as e:
        checks.append((f"poll() executes offline ({e})", False))
    failed = [n for n, ok in checks if not ok]
    print(json.dumps({"checks": checks, "validate": rep["verdict"],
                      "production_qualified":
                      rep.get("production_qualified")}, indent=1))
    if failed or rep["verdict"] == "FAIL":
        print(f"AI_TASK: FAIL ({failed or rep['errors'][:2]})")
        return 1
    print("AI_TASK: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
