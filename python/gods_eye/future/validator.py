"""FUTURE-ONLY plugin validator (public SDK, V17).

Validates a plugin directory (``manifest.json`` + ``plugin.py`` +
``fixture.json`` + offline test) or a bare manifest dict and returns a
structured, actionable report. No installs, no downloads, no network,
no plugin code execution beyond importing nothing: validation reads the
manifest and fixture as data and inspects ``plugin.py`` as text.

Sections: schema / rights / license / capabilities / network / secrets /
provenance / health / compatibility / fixture / offline-test.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

from gods_eye.future import plugins as pl

SCHEMA_ID = "plugin-v1"

# Tokens that must never appear in plugin code/fixtures (fail closed).
_SECRET_TOKENS = (
    "api_key", "api_secret", "passphrase", "private_key", "secret_key",
    "access_token", "mnemonic", "seed_phrase", "password", "rpc_url",
)

# Plugins may import only modules that ship in the gods_eye package.
_PACKAGE_DIR = Path(__file__).resolve().parents[1]
_GODS_EYE_IMPORT = re.compile(r"^\s*(?:from|import)\s+(gods_eye(?:\.\w+)*)",
                              re.MULTILINE)


def _non_core_imports(src: str) -> list:
    """gods_eye.* imports in plugin source that the core package can't satisfy."""
    missing = []
    for name in _GODS_EYE_IMPORT.findall(src):
        parts = name.split(".")[1:]
        if not parts:
            continue
        base = _PACKAGE_DIR.joinpath(*parts)
        if not (base.with_suffix(".py").is_file()
                or (base / "__init__.py").is_file()):
            missing.append(name)
    return missing

# Outbound-call tokens forbidden in plugin code (localhost demo only).
_NETWORK_TOKENS = (
    "requests.get", "requests.post", "httpx.get", "httpx.post",
    "urlopen(", "socket.connect", "urllib.request",
)


def _section(ok: bool, detail: str = "", fix: str = "") -> Dict[str, Any]:
    return {"ok": ok, "detail": detail, "fix": fix}


def validate_declaration(declaration: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a manifest dict. Never raises for bad input; reports it."""
    sections: Dict[str, Dict[str, Any]] = {}
    try:
        declared = pl.declare(**declaration)
    except Exception as e:
        return {
            "ok": False, "verdict": "FAIL",
            "sections": {"schema": _section(
                False, f"{type(e).__name__}: {e}",
                "compare manifest.json with "
                "examples/plugins/example_sensor/manifest.json")},
            "production_qualified": False,
            "errors": [f"schema: {e}"], "warnings": [],
        }
    errors: List[str] = []
    warnings: List[str] = []

    schema = str(declared.get("schema", ""))
    sections["schema"] = _section(
        schema == SCHEMA_ID, f"schema={schema}",
        "" if schema == SCHEMA_ID else
        f"set schema to {SCHEMA_ID!r} (see PLUGIN_TRUST_MODEL.md)")

    rights = declared.get("data_rights", "UNKNOWN")
    rights_ok = pl.rights_declared(declared)
    sections["rights"] = _section(
        rights_ok, f"data_rights={rights!r}",
        "" if rights_ok else
        "declare honest data rights (e.g. 'public-domain (synthetic CC0 "
        "fixture)'); UNKNOWN stays discoverable but never "
        "production-qualified")
    if not rights_ok:
        warnings.append("rights UNKNOWN: discoverable, not production-qualified")

    lic = str(declared.get("license", "UNKNOWN"))
    lic_ok = lic.strip().upper() not in ("", "UNKNOWN", "NONE", "TBD")
    sections["license"] = _section(
        lic_ok, f"license={lic!r}",
        "" if lic_ok else "set a real licence id (e.g. MIT) in manifest.json")

    caps = declared.get("capabilities", [])
    sections["capabilities"] = _section(
        True, f"capabilities={caps!r} (private-capability tokens refused "
        "at declare() time)",
        "")

    net = str(declared.get("network", "UNKNOWN"))
    sec = str(declared.get("secrets", "UNKNOWN"))
    net_ok = net.strip().lower() in ("none", "localhost-only")
    sec_ok = sec.strip().lower() in ("none", "no-secrets", "localhost-only")
    sections["network"] = _section(
        net_ok, f"network={net!r}",
        "" if net_ok else
        "state network needs honestly ('none' or 'localhost-only' for "
        "community plugins)")
    sections["secrets"] = _section(
        sec_ok, f"secrets={sec!r}",
        "" if sec_ok else
        "community plugins must need no secrets ('none')")
    if not net_ok:
        warnings.append(f"network={net!r}: review trust implications")
    if not sec_ok:
        errors.append(f"secrets={sec!r}: community plugins must declare 'none'")

    prov = str(declared.get("provenance", ""))
    sections["provenance"] = _section(
        bool(prov.strip()) and prov.strip().upper() != "UNKNOWN",
        f"provenance={prov!r}",
        "" if prov.strip() else "record where the data comes from")
    health = str(declared.get("health", ""))
    sections["health"] = _section(
        bool(health.strip()), f"health={health!r}",
        "" if health.strip() else "set health (e.g. 'ok')")

    compat = declared.get("schema", "")
    sections["compatibility"] = _section(
        compat == SCHEMA_ID, f"plugin schema {compat!r} vs host {SCHEMA_ID!r}",
        "" if compat == SCHEMA_ID else
        "bump the plugin to the current plugin schema")

    qualified = pl.production_qualified(declared)
    verdict = "PASS" if (qualified and not errors) else (
        "WARN" if not errors else "FAIL")
    return {"ok": verdict == "PASS", "verdict": verdict,
            "sections": sections, "production_qualified": qualified,
            "declaration": declared, "errors": errors, "warnings": warnings}


def validate_plugin_dir(path: str | Path) -> Dict[str, Any]:
    """Validate a plugin directory on disk (manifest + code + fixture)."""
    d = Path(path)
    report: Dict[str, Any] = {"dir": str(d), "verdict": "FAIL",
                              "sections": {}, "errors": [],
                              "warnings": [], "production_qualified": False}
    if not d.is_dir():
        report["errors"].append(f"not a directory: {d}")
        report["sections"]["schema"] = _section(
            False, "missing directory",
            "run: godseye new-plugin --kind sensor --name NAME --dir DIR")
        return report
    manifest_path = d / "manifest.json"
    if not manifest_path.is_file():
        report["errors"].append("manifest.json missing")
        report["sections"]["schema"] = _section(
            False, "manifest.json missing",
            "copy examples/plugins/example_sensor/manifest.json and edit it")
        return report
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:
        report["errors"].append(f"manifest.json unreadable: {e}")
        report["sections"]["schema"] = _section(
            False, f"manifest.json unreadable: {e}",
            "fix the JSON syntax (trailing commas are the usual cause)")
        return report
    report.update(validate_declaration(payload))

    code_path = d / "plugin.py"
    if code_path.is_file():
        try:
            src = code_path.read_text(encoding="utf-8")
        except OSError as e:
            src = ""
            report["warnings"].append(f"plugin.py unreadable: {e}")
        low = src.lower()
        for name in _non_core_imports(src):
            report["errors"].append(
                f"plugin.py imports {name!r}, which does not ship in the "
                "gods_eye package")
        for tok in _NETWORK_TOKENS:
            if tok.lower() in low:
                report["errors"].append(
                    f"plugin.py uses network call {tok!r} "
                    "(community plugins are offline/localhost-only)")
        for tok in _SECRET_TOKENS:
            if re.search(r"(?i)(?<![a-z0-9])(?:[a-z0-9]+_)*"
                         + re.escape(tok) + r"\b", src):
                report["errors"].append(
                    f"plugin.py mentions credential token {tok!r}")
        if re.search(r"\b[A-Z][A-Z0-9]*_PK\b", src):
            report["errors"].append(
                "plugin.py mentions a *_PK credential variable")
        report["sections"]["code_hygiene"] = _section(
            not [e for e in report["errors"] if "plugin.py" in e],
            "plugin.py scanned as text (no code executed)",
            "remove non-core imports, network calls, and credential tokens")
    else:
        report["warnings"].append("plugin.py missing (manifest-only plugin)")
        report["sections"]["code_hygiene"] = _section(
            True, "manifest-only (no code to scan)", "")

    fixture_path = d / "fixture.json"
    if fixture_path.is_file():
        try:
            blob = fixture_path.read_text(encoding="utf-8").lower()
            hits = [t for t in ("api_key", "api_secret", "private_key",
                                "mnemonic", "password") if t in blob]
            report["sections"]["fixture"] = _section(
                not hits, f"fixture.json scanned ({len(blob)} chars)",
                ("remove credential refs: " + ", ".join(hits))
                if hits else "")
            if hits:
                report["errors"].append(f"fixture.json refs: {hits}")
        except OSError as e:
            report["sections"]["fixture"] = _section(
                False, f"fixture unreadable: {e}", "check file permissions")
    else:
        report["sections"]["fixture"] = _section(
            True, "no fixture.json (optional)", "")

    test_files = sorted(d.glob("test_*.py"))
    report["sections"]["offline_test"] = _section(
        bool(test_files),
        f"offline tests: {[t.name for t in test_files] or 'none found'}",
        "" if test_files else
        "ship test_example_sensor.py alongside the plugin "
        "(copy it from the example template)")
    if not test_files:
        report["warnings"].append("no offline test shipped")

    if report["errors"]:
        report["verdict"] = "FAIL"
    elif report["warnings"] or not report.get("production_qualified"):
        report["verdict"] = "WARN"
    else:
        report["verdict"] = "PASS"
    report["ok"] = report["verdict"] == "PASS"
    return report
