"""Tellurion developer CLI (stdlib argparse only).

Commands:
  tellurion doctor      — environment + boundary checks (PASS/WARN/FAIL)
  tellurion demo        — one-command localhost demo (no keys, no network)
  tellurion ultra       — Ultra world surface (strongest deterministic demo)
  tellurion serve       — serve console localhost-only
  tellurion plugins [list] [--dir D] — list SDK kinds + discovered plugins
  tellurion plugins validate PATH    — validate a plugin dir (actionable)
  tellurion plugins inspect PATH     — alias of validate (full report)
  tellurion sources     — source/rights summary (public-safe)
  tellurion new-plugin  — scaffold a plugin from the example template
  tellurion scout       — rank public sensor-source candidates (offline)
  tellurion release-check — launch-candidate readiness probe (read-only)

No heavy CLI dependency. No live execution. No credentials.
Errors are human-readable (no raw tracebacks for expected failures).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"


def _check(checks: List[Dict[str, Any]], name: str, status: str,
           detail: str = "", fix: str = "") -> None:
    checks.append({"name": name, "status": status, "detail": detail,
                   "fix": fix})


def cmd_doctor(port: int | None = None) -> Dict[str, Any]:
    """Doctor V2: PASS/WARN/FAIL per check with actionable messages."""
    import sys as _sys
    checks: List[Dict[str, Any]] = []

    # 1. Python version
    if _sys.version_info >= (3, 13):
        _check(checks, "python>=3.13", PASS, _sys.version.split()[0])
    else:
        _check(checks, "python>=3.13", FAIL, _sys.version.split()[0],
               "install Python 3.13+ from https://www.python.org/downloads/ "
               "then re-run: tellurion doctor")

    # 2. Package import
    try:
        import gods_eye  # noqa: F401
        from gods_eye import cli as _cli  # noqa: F401
        _check(checks, "package import", PASS, "gods_eye importable")
    except Exception as e:
        _check(checks, "package import", FAIL, f"{type(e).__name__}: {e}",
               "run: pip install -e .  (from the repo root)")

    # 3. Public/private isolation (community imports introduce nothing private)
    # NOTE: check name "community-mode imports" is a V15-tested contract.
    try:
        from gods_eye.future import community as co
        rep = co.community_check()
        if not rep["failed"] and not rep["private_introduced"]:
            _check(checks, "community-mode imports", PASS,
                   f"{rep['n_imported']} community modules, "
                   f"private introduced: none")
        else:
            _check(checks, "community-mode imports", FAIL,
                   f"failures={rep['failed']} "
                   f"introduced={rep['private_introduced']}",
                   "open-core code paths may import only modules shipped in "
                   "the gods_eye package")
    except Exception as e:
        _check(checks, "community-mode imports", FAIL,
               f"{type(e).__name__}: {e}",
               "see docs/OPEN_CORE_BOUNDARY.md")

    # 4. Demo dataset (present, CC0, no holdout refs)
    try:
        from gods_eye.future import demo_dataset as dd
        v = dd.validate_no_holdout_refs()
        if v["ok"] and dd.LICENSE.startswith("CC0"):
            _check(checks, "demo dataset", PASS,
                   f"{dd.DATASET_ID} ({dd.LICENSE})")
        else:
            _check(checks, "demo dataset", FAIL, f"hits={v['hits']}",
                   "demo data must stay synthetic CC0; remove the flagged refs")
    except Exception as e:
        _check(checks, "demo dataset", FAIL, f"{type(e).__name__}: {e}",
               "reinstall the package: pip install -e .")

    # 5. Write permissions (demo/catalog need a writable scratch dir)
    try:
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            probe = Path(td) / "godseye-write-probe.tmp"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
        _check(checks, "write permissions", PASS, "temp dir writable")
    except Exception as e:
        _check(checks, "write permissions", FAIL, f"{type(e).__name__}: {e}",
               "check TEMP/TMPDIR permissions for your user")

    # 6. Localhost bind (default demo port or auto-fallback available)
    try:
        from gods_eye.demo import (DEFAULT_PORT, HOST, port_available,
                                   select_port)
        probe_port = DEFAULT_PORT if port is None else int(port)
        if port_available(probe_port, HOST):
            _check(checks, "localhost bind", PASS,
                   f"{HOST}:{probe_port} free")
        else:
            alt, _ = select_port(probe_port, HOST)
            _check(checks, "localhost bind", WARN,
                   f"{HOST}:{probe_port} occupied; auto-fallback to {alt}",
                   f"stop the program on {probe_port}, or run: "
                   f"tellurion demo --port {alt}")
    except Exception as e:
        _check(checks, "localhost bind", FAIL, f"{type(e).__name__}: {e}",
               "check loopback interface / local firewall rules")

    # 7. Optional dependencies (informational: all may be absent)
    try:
        from gods_eye.future import optional_deps as od
        rep = od.report()
        n_avail = rep["counts"].get("AVAILABLE", 0)
        _check(checks, "optional dependencies",
               PASS if n_avail <= len(od.names()) else PASS,
               f"{n_avail} available, "
               f"{rep['counts'].get('NOT_INSTALLED', 0)} not installed "
               f"(core needs none)")
    except Exception as e:
        _check(checks, "optional dependencies", WARN,
               f"{type(e).__name__}: {e}",
               "optional extras are never required; skip if unsure")

    # 8. Plugin discovery (SDK loads; entry-point group readable)
    try:
        from gods_eye.future import discovery as di
        rep = di.discover()
        errs = rep["entry_points"]["errors"]
        if not errs:
            _check(checks, "plugin discovery", PASS,
                   f"group {di.ENTRY_POINT_GROUP} readable; "
                   f"{rep['total_ok']} advertised")
        else:
            _check(checks, "plugin discovery", WARN, f"errors={errs}",
                   "entry-point metadata unreadable; dir-based discovery "
                   "still works: see tellurion new-plugin")
    except Exception as e:
        _check(checks, "plugin discovery", FAIL, f"{type(e).__name__}: {e}",
               "reinstall the package: pip install -e .")

    # 9. Rights metadata (registry loads; UNKNOWN discipline intact)
    try:
        from gods_eye.rights.registry import REGISTRY
        n = len(REGISTRY)
        _check(checks, "rights metadata",
               PASS if n >= 1 else FAIL, f"{n} sources registered",
               "" if n >= 1 else "rights registry failed to load")
    except Exception as e:
        _check(checks, "rights metadata", FAIL, f"{type(e).__name__}: {e}",
               "reinstall the package: pip install -e .")

    # 10. No trading or execution surface (V1 is world intelligence only)
    try:
        from pathlib import Path as _Path
        from gods_eye.future import boundary as _b
        hits = _b.trading_surface_hits(_Path(__file__).resolve().parents[2])
        _check(checks, "no execution surface", PASS if not hits else FAIL,
               "no order, venue, portfolio or backtest modules"
               if not hits else f"{len(hits)} present: {hits[:3]}",
               "" if not hits else
               "remove them: this build must not be able to trade")
    except Exception as e:
        _check(checks, "no execution surface", FAIL,
               f"{type(e).__name__}: {e}", "see docs/guides/security-defaults.md")

    # 11. Telemetry disabled (community paths make no outbound calls)
    try:
        import inspect
        from gods_eye import demo as _demo
        src = inspect.getsource(_demo)
        outbound = [t for t in ("requests.get", "httpx.get", "urlopen(\"http",
                                "urlopen('http", "socket.connect")
                    if t in src]
        # webbrowser.open(localhost-url) + HTTPServer(localhost bind) are
        # local-only and explicitly allowed.
        if not outbound:
            _check(checks, "telemetry disabled", PASS,
                   "no outbound calls in demo path (localhost only)")
        else:
            _check(checks, "telemetry disabled", FAIL,
                   f"outbound tokens: {outbound}",
                   "community edition must not phone home")
    except Exception as e:
        _check(checks, "telemetry disabled", WARN, f"{type(e).__name__}: {e}")

    failed = sum(1 for c in checks if c["status"] == FAIL)
    warned = sum(1 for c in checks if c["status"] == WARN)
    verdict = FAIL if failed else (WARN if warned else PASS)
    # Backward-compat: V15 consumers read `ok`.
    return {"ok": verdict == PASS, "verdict": verdict,
            "failed": failed, "warned": warned, "checks": checks}


def cmd_plugins(dirs: List[str] | None = None) -> Dict[str, Any]:
    from gods_eye.future import plugins as pl
    from gods_eye.future import public_api as api
    from gods_eye.future import discovery as di
    out: Dict[str, Any] = {"kinds": list(pl.KINDS),
                           "api": api.api_surface(),
                           "registered": api.list_registered(),
                           "discovered": di.discover(dirs)}
    return out


def cmd_sources() -> Dict[str, Any]:
    try:
        from gods_eye.rights.registry import REGISTRY
        items = [{"source_id": k, "commercial_use": v.commercial_use,
                  "redistribution": v.redistribution,
                  "rights_basis": v.rights_basis} for k, v in REGISTRY.items()]
    except Exception:
        items = []
    return {"n_sources": len(items), "items": items,
            "note": "software licences and data rights are separate; "
                    "UNKNOWN stays UNKNOWN"}


def cmd_new_plugin(kind: str, name: str, out_dir: str) -> Dict[str, Any]:
    """Scaffold a plugin from the bundled example template (copy + rename)."""
    import json
    import shutil
    from gods_eye.demo import repo_root
    template = repo_root() / "examples" / "plugins" / "example_sensor"
    if not template.is_dir():
        return {"ok": False,
                "error": f"template not found at {template} "
                         f"(reinstall the package: pip install -e .)"}
    dest = Path(out_dir).expanduser()
    try:
        dest.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return {"ok": False,
                "error": f"cannot create {dest}: {e}. "
                         f"Check write permissions for the target directory."}
    for fname in ("manifest.json", "plugin.py", "fixture.json",
                  "test_example_sensor.py"):
        try:
            shutil.copyfile(template / fname, dest / fname)
        except OSError as e:
            return {"ok": False,
                    "error": f"cannot write {dest / fname}: {e}"}
    try:
        manifest_path = dest / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["name"] = name
        kind_map = {"sensor": "Sensor",
                    "entity-resolver": "EntityResolver",
                    "visualization": "Visualization"}
        manifest["kind"] = kind_map.get(kind, "Sensor")
        manifest["provenance"] = f"scaffolded from example_sensor as {name}"
        manifest_path.write_text(json.dumps(manifest, indent=2),
                                 encoding="utf-8")
    except OSError as e:
        return {"ok": False, "error": f"cannot update manifest: {e}"}
    return {"ok": True, "dir": str(dest), "kind": manifest["kind"],
            "name": name,
            "next": [f"edit {dest / 'manifest.json'} (rights + capabilities)",
                     f"edit {dest / 'plugin.py'} (poll over your fixture)",
                     f"run: python -m pytest {dest / 'test_example_sensor.py'} -q",
                     "register: gods_eye.future.public_api.register_sensor(...)",
                     "declare rights honestly; UNKNOWN rights stay "
                     "discoverable but never production-qualified"]}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tellurion",
                                description="Tellurion developer CLI (no keys, no live)")
    sub = p.add_subparsers(dest="cmd", required=True)
    doc = sub.add_parser("doctor",
                         help="environment + boundary checks (PASS/WARN/FAIL)")
    doc.add_argument("--port", type=int, default=None,
                     help="probe this localhost port instead of the default "
                     "(verification harnesses pass an ephemeral port)")
    d = sub.add_parser("demo", help="one-command localhost demo")
    d.add_argument("--port", type=int, default=8765)
    d.add_argument("--no-browser", action="store_true")
    d.add_argument("--strict-port", action="store_true",
                   help="fail with a clear message if --port is occupied")
    d.add_argument("--hero", action="store_true",
                   help="deterministic hero state for screenshots "
                   "(fixed event, camera, selection, timeline)")
    d.add_argument("--ultra", action="store_true",
                   help="open the Ultra world surface (/ultra)")
    u = sub.add_parser("ultra", help="Ultra world surface (hero demo)")
    u.add_argument("--port", type=int, default=8765)
    u.add_argument("--no-browser", action="store_true")
    u.add_argument("--strict-port", action="store_true",
                   help="fail with a clear message if --port is occupied")
    u.add_argument("--hero", action="store_true",
                   help="strongest deterministic demo (/ultra?demo=hero)")
    s = sub.add_parser("serve", help="serve console localhost-only")
    s.add_argument("--port", type=int, default=8765)
    s.add_argument("--strict-port", action="store_true")
    s.add_argument("--hero", action="store_true",
                   help="deterministic hero state (?demo=hero)")
    pl = sub.add_parser("plugins", help="list plugin SDK kinds + discovery")
    pl.add_argument("action", nargs="?", default="list",
                    choices=["list", "validate", "inspect"],
                    help="list (default), validate PATH, or inspect PATH")
    pl.add_argument("path", nargs="?",
                    help="plugin directory for validate/inspect")
    pl.add_argument("--dir", action="append", default=[],
                    help="explicit plugin dir to scan (repeatable)")
    sub.add_parser("sources", help="source/rights summary")
    np = sub.add_parser("new-plugin", help="scaffold a plugin from the template")
    np.add_argument("--kind", default="sensor",
                    choices=["sensor", "entity-resolver", "visualization"])
    np.add_argument("--name", required=True, help="plugin name for the manifest")
    np.add_argument("--dir", default="my_sensor_plugin",
                    help="destination directory (created if needed)")
    sc = sub.add_parser("scout",
                        help="rank sensor-source candidates "
                        "(offline, never connects)")
    sc.add_argument("--category", default=None)
    sc.add_argument("--status", default=None)
    rc = sub.add_parser("release-check",
                        help="launch-candidate readiness probe "
                        "(read-only, never publishes)")
    rc.add_argument("--root", default=None,
                    help="candidate root (default: auto-detect)")
    rc.add_argument("--port", type=int, default=None,
                    help="doctor bind-probe port (default: 8765)")
    return p


def main(argv: List[str] | None = None) -> int:
    import json
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as e:
        return int(e.code or 0)
    if args.cmd == "doctor":
        rep = cmd_doctor(port=args.port)
        print(json.dumps(rep, indent=1))
        if rep["verdict"] == FAIL:
            print("doctor: FAIL — follow each check's `fix` hint, then re-run.",
                  file=sys.stderr)
            return 1
        if rep["verdict"] == WARN:
            print("doctor: PASS with warnings (see `fix` hints).")
            return 0
        print("doctor: PASS — all checks green.")
        return 0
    if args.cmd == "plugins":
        if args.action in ("validate", "inspect"):
            from gods_eye.future import validator as vd
            if not args.path:
                print(f"error: tellurion plugins {args.action} needs a PATH "
                      f"(e.g. tellurion plugins {args.action} ./my_sensor)",
                      file=sys.stderr)
                return 2
            rep = vd.validate_plugin_dir(args.path)
            print(json.dumps(rep, indent=1))
            if rep["verdict"] == "FAIL":
                errs = "; ".join(rep["errors"][:3]) or "see sections"
                print(f"plugin {args.action}: FAIL — {errs}", file=sys.stderr)
                return 1
            print(f"plugin {args.action}: {rep['verdict']} "
                  f"(production_qualified={rep['production_qualified']})")
            return 0
        print(json.dumps(cmd_plugins(args.dir or None), indent=1))
        return 0
    if args.cmd == "sources":
        print(json.dumps(cmd_sources(), indent=1))
        return 0
    if args.cmd == "new-plugin":
        rep = cmd_new_plugin(args.kind, args.name, args.dir)
        print(json.dumps(rep, indent=1))
        if not rep["ok"]:
            print(f"error: {rep['error']}", file=sys.stderr)
            return 1
        print(f"scaffolded '{args.name}' in {rep['dir']} — "
              f"see CONTRIBUTING.md for the 5-step flow.")
        return 0
    if args.cmd == "scout":
        from gods_eye.future import sensor_sources as ss
        rows = ss.scout_rank()
        if args.category:
            rows = [r for r in rows if r["category"] == args.category.upper()]
        if args.status:
            rows = [r for r in rows if r["status"] == args.status.upper()]
        print(json.dumps({"summary": ss.summary(),
                          "candidates": rows}, indent=1))
        print(f"SCOUT: OK ({len(rows)} candidates, discovery only)")
        return 0
    if args.cmd in ("demo", "serve"):
        from gods_eye.demo import PortOccupied, run_demo
        try:
            run_demo(port=args.port,
                     open_browser=(args.cmd == "demo" and not args.no_browser),
                     strict_port=args.strict_port,
                     hero=args.hero,
                     ultra=(args.cmd == "demo" and getattr(
                         args, "ultra", False)))
        except PortOccupied as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        return 0
    if args.cmd == "ultra":
        from gods_eye.demo import PortOccupied, run_demo
        try:
            run_demo(port=args.port,
                     open_browser=not args.no_browser,
                     strict_port=args.strict_port,
                     hero=args.hero, ultra=True)
        except PortOccupied as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        return 0
    if args.cmd == "release-check":
        from gods_eye.future import release_check as rc
        try:
            rep = rc.release_check(args.root, port=args.port)
        except Exception as e:
            print(f"error: release check failed: {type(e).__name__}: {e}",
                  file=sys.stderr)
            return 1
        print(json.dumps(rep, indent=1)[:4000])
        print(f"RELEASE CHECK: {rep['verdict']} "
              f"({rep['failed']} fail, {rep['warned']} warn, NOT published)")
        return 0 if rep["verdict"] == PASS else 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
