"""FUTURE-ONLY plugin discovery (explicit, no auto-execute, V16).

Two mechanisms, both explicit:

1. Entry points (standard packaging): group ``gods_eye.plugins``.
   A distribution advertises ``name = "pkg.mod:declaration_dict"`` where
   the target is a module-level dict (the ``declare()`` payload) or a
   zero-argument callable returning one. Discovery never imports plugin
   *code* beyond reading the advertised dict target, and installation of
   a plugin distribution is always an explicit ``pip install`` by the user.

2. Explicit directories: ``discover_from_dirs([paths])`` scans only the
   caller-supplied directories (non-recursive, ``manifest.json`` files).
   No CWD auto-scan, no PATH scan, no downloads.

Discovered declarations are validated with ``plugins.declare()`` and
reported with their ``production_qualified`` flag. Malformed manifests
are reported as errors, never raised past the caller (discovery must
fail nicely; strict mode available via ``strict=True``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


ENTRY_POINT_GROUP = "gods_eye.plugins"


def _validate(declaration: Dict[str, Any], origin: str) -> Dict[str, Any]:
    from gods_eye.future import plugins as pl
    try:
        declared = pl.declare(**declaration)
        return {"origin": origin, "name": declared.get("name", "UNKNOWN"),
                "kind": declared.get("kind", "UNKNOWN"), "ok": True,
                "production_qualified": pl.production_qualified(declared),
                "declaration": declared, "error": ""}
    except Exception as e:
        return {"origin": origin,
                "name": declaration.get("name", "UNKNOWN") if isinstance(
                    declaration, dict) else "UNKNOWN",
                "kind": "UNKNOWN", "ok": False, "production_qualified": False,
                "declaration": {}, "error": f"{type(e).__name__}: {e}"}


def discover_entry_points() -> Dict[str, Any]:
    """Read advertised entry points (no plugin code execution beyond dict read)."""
    found: List[Dict[str, Any]] = []
    errors: List[str] = []
    try:
        from importlib import metadata as md
        eps = md.entry_points()
        group = eps.select(group=ENTRY_POINT_GROUP) if hasattr(
            eps, "select") else eps.get(ENTRY_POINT_GROUP, ())
    except Exception as e:
        return {"mechanism": "entry-points", "group": ENTRY_POINT_GROUP,
                "plugins": [], "errors": [f"entry-point read failed: {e}"],
                "note": "no plugins auto-installed; pip install is explicit"}
    for ep in group:
        origin = f"entry-point:{ep.name}"
        try:
            target = ep.load()
            payload = target() if callable(target) else target
            if not isinstance(payload, dict):
                raise ValueError("entry point must resolve to a dict payload")
            found.append(_validate(payload, origin))
        except Exception as e:
            errors.append(f"{origin}: {type(e).__name__}: {e}")
    return {"mechanism": "entry-points", "group": ENTRY_POINT_GROUP,
            "plugins": found, "errors": errors,
            "note": "no plugins auto-installed; pip install is explicit"}


def discover_from_dirs(dirs: List[str | Path],
                       strict: bool = False) -> Dict[str, Any]:
    """Scan caller-supplied directories for manifest.json files (non-recursive)."""
    from gods_eye.future import plugins as pl  # noqa: F401 (kind check below)
    found: List[Dict[str, Any]] = []
    errors: List[str] = []
    searched: List[str] = []
    for d in dirs:
        p = Path(d)
        searched.append(str(p))
        if not p.is_dir():
            errors.append(f"{p}: not a directory (skipped)")
            continue
        for manifest in sorted(p.glob("*/manifest.json")):
            origin = f"dir:{manifest.parent.name}"
            try:
                payload = json.loads(manifest.read_text(encoding="utf-8"))
                found.append(_validate(payload, origin))
            except Exception as e:
                msg = f"{origin}: {type(e).__name__}: {e}"
                if strict:
                    raise ValueError(msg) from e
                errors.append(msg)
    ok_plugins = [f for f in found if f["ok"]]
    return {"mechanism": "explicit-dirs", "searched": searched,
            "plugins": ok_plugins,
            "invalid": [f for f in found if not f["ok"]],
            "errors": errors,
            "note": "only caller-supplied directories are scanned (no CWD/PATH scan)"}


def discover(dirs: Optional[List[str | Path]] = None) -> Dict[str, Any]:
    """Combined discovery: entry points + optional explicit dirs."""
    ep = discover_entry_points()
    result: Dict[str, Any] = {"entry_points": ep, "dirs": None,
                              "total_ok": len([p for p in ep["plugins"] if p["ok"]])}
    if dirs:
        dd = discover_from_dirs(dirs)
        result["dirs"] = dd
        result["total_ok"] += len(dd["plugins"])
    return result
